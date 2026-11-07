"""Region Redraw for MiniMax H3: redraw part of a finished video at the size the model draws well.

A face a few dozen pixels wide is more than the model can draw at 2K, whatever the sampler does. Here each region of the
mask is cropped, enlarged, redrawn inside a latent noise mask and feathered back into the video. Low noise repairs what
is there; high noise and a reference picture replace it. Which regions those are is the mask's business: any tool that
makes one will do. A subject has a mask of its own, wired to its picture, so what goes where is never worked out.
"""

import bisect
import logging
import math
import time
from dataclasses import dataclass, field

import torch
import torch.nn.functional as F

from .common import IO, schema
from .nodes_sampling import CAT_SAMPLING

log = logging.getLogger("Arbor")

MAX_RATIO = 2.0                 # the longest a crop gets, either way
SQUARE_WITHIN = 1.4             # a crop this close to square is square: a lone face is
MAX_FRAMES = 243                # frames redrawn in one pass
MIN_FRAMES = 5                  # a shorter run is a blip in the mask
MIN_SIDE = 8                    # a smaller piece of mask (px) is not a face
SAME_SHOT = 0.5                 # frames this alike are one shot however much the light changed. Cuts measure under 0.3
LABEL_SHORT = 720               # masks are split into faces at about this short edge
STEADY = 1.35                   # a face whose size varies less than this keeps one crop size: the rest is mask jitter
MAX_HIDDEN = 24                 # frames a face may be hidden for and still be the same face
MAX_CHANGE = 1.5                # a face is not this much larger from one sighting to the next, and moves less than this x its size
MAX_TOUCHING = 3.0              # faces that touch make a piece at most this much larger; more is a mask slipping onto something
MIN_SIZE = 77                   # at 2560: a smaller region gets the crop of one this size, or its surroundings would vanish
GROUP_SIZE = 512                # longest edge, in video pixels, of a crop shared by nearby regions
MAX_CANVAS = 1536               # longest canvas edge a shared crop may grow to, whatever group_size allows
GROUP_SAVING = 0.15             # faces share a crop only if that saves at least this share of the work
CONTEXT = 2.0                   # default crop size / the face: closer to the original than 4, as quick
CHUNK = 24                      # crops prepared per round, to be put together into a few videos
REEL_TOKENS = 24000             # crops of one canvas are sampled as one video of up to this many tokens
REFINE_SIZE = 512               # faster than H3's 768 by a third, and repairs collapsed faces as well or better
DEFAULT_PROMPT = ("Ordinary people in the background of a film shot. Realistic natural faces with clear eyes, noses "
                  "and mouths, natural skin, shot on a cinema camera.")


@dataclass
class Run:
    """One face in one shot, or faces that touch in the mask: boxes are (x0, y0, x1, y1) in image pixels, keyed by frame;
    parts says which pieces of the labelled mask it is at each frame."""
    boxes: dict
    parts: dict = field(default_factory=dict)
    number: int = 0
    labels: torch.Tensor = None  # the labelled mask it came from
    subject: int = 0             # which subject_mask it came from; such a region gets a crop to itself

    def add(self, frame: int, box, pieces: list) -> None:
        old = self.boxes.get(frame, box)
        self.boxes[frame] = (min(old[0], box[0]), min(old[1], box[1]), max(old[2], box[2]), max(old[3], box[3]))
        self.parts.setdefault(frame, []).extend(pieces)

    @property
    def first(self):
        return min(self.boxes)

    @property
    def last(self):
        return max(self.boxes)

    @property
    def size(self):
        return self.sides[len(self.sides) // 2]

    @property
    def sides(self):
        return sorted(_side(b) for b in self.boxes.values())

    @property
    def least(self):
        """How small the face gets, past a stray frame or two."""
        return self.sides[len(self.sides) // 10]


def _side(box) -> float:
    return max(box[2] - box[0], box[3] - box[1])


def _centre(box):
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _middle(run: Run):
    xs, ys = zip(*(_centre(b) for b in run.boxes.values()))
    return sorted(xs)[len(xs) // 2], sorted(ys)[len(ys) // 2]


def shot_starts(frames: torch.Tensor) -> list[int]:
    """First frame of each shot: a cut is a frame far more different from the last than the clip's usual change, and with
    nothing where it was: light sweeping over a shot changes as much, but leaves everything in place. Two cuts within a few
    frames are a flash, not a shot: what was in it would be too short to redraw."""
    small = frames[:, ::8, ::8].float().mean(-1)
    change = (small[1:] - small[:-1]).abs().mean((1, 2))
    if len(change) == 0:
        return [0]
    limit = max(0.04, 6 * float(change.median()))
    flat = small.flatten(1) - small.mean((1, 2))[:, None]
    alike = F.cosine_similarity(flat[1:], flat[:-1], dim=1)
    starts = [0]
    for i, (c, a) in enumerate(zip(change.tolist(), alike.tolist())):
        if c > limit and a < SAME_SHOT and i + 1 - starts[-1] >= MIN_FRAMES:
            starts.append(i + 1)
    return starts


def _gather(parts: list, labels: torch.Tensor) -> list:
    """A subject's pieces around its largest are the subject, cut up by whatever stands in front of it: one piece. Those
    further off stay apart, or a crop would stretch across the frame between them."""
    main, box = max(parts, key=lambda p: _side(p[1]))
    reach = _side(box) / 2
    near = (box[0] - reach, box[1] - reach, box[2] + reach, box[3] + reach)
    rest = []
    for label, b in parts:
        if label == main:
            continue
        if b[0] < near[2] and b[2] > near[0] and b[1] < near[3] and b[3] > near[1]:
            labels[labels == label] = main
            box = (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
        else:
            rest.append((label, b))
    return [(main, box), *rest]


def split_regions(masks: torch.Tensor, height: int, width: int, subject: bool = False) -> tuple[torch.Tensor, dict]:
    """([frames, h, w] uint8 labels, {frame: [(label, box)]}): the separate pieces of a [frames, h, w] mask. Pieces a
    couple of pixels apart are one face, cut by a strand of hair or the mask's edge."""
    import numpy as np
    from scipy import ndimage

    step = max(1, min(masks.shape[1:]) // LABEL_SHORT)
    small = (masks[:, ::step, ::step] > 0.5).cpu().numpy()
    sy, sx = step * height / masks.shape[1], step * width / masks.shape[2]
    labels = torch.zeros(small.shape, dtype=torch.uint8)
    regions = {}
    for f, m in enumerate(small):
        if not m.any():
            continue
        found = ndimage.label(ndimage.binary_dilation(m, iterations=2), structure=np.ones((3, 3)))[0] * m
        found = np.minimum(found, 255).astype(np.uint8)
        labels[f] = torch.from_numpy(found)
        parts = []
        for i, where in enumerate(ndimage.find_objects(found)):
            if where is not None:
                y, x = where
                box = (x.start * sx, y.start * sy, x.stop * sx, y.stop * sy)
                if _side(box) >= MIN_SIDE:
                    parts.append((i + 1, box))
        if parts:
            regions[f] = _gather(parts, labels[f]) if subject else parts
    return labels, regions


def _inside(a, b) -> float:
    """How much of box a lies in box b."""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0) / max((a[2] - a[0]) * (a[3] - a[1]), 1e-6)


def link_regions(regions: dict, shots: list[int]) -> list[Run]:
    """Follow the pieces from frame to frame within each shot. A merged mask can't say where one face ends, so faces
    that touch come and go as one piece: whatever overlaps stays in one run, or a face would change mid-shot as its crop
    changed. Apart from that, a face is found again by where it is and how large, even after being hidden for a moment.
    Numbered in order of appearance."""
    runs, active, shot = [], [], 0
    for f in sorted(regions):
        here = bisect.bisect(shots, f)
        if here != shot:
            active, shot = [], here
        seen = set()
        for part, box in sorted(regions[f], key=lambda p: -_side(p[1])):
            hits = []
            for r in active:
                last = r.boxes[r.last]
                touching = max(_inside(box, last), _inside(last, box)) > 0.5
                if touching and f - r.last <= 2 and max(_side(box), _side(last)) <= MAX_TOUCHING * min(_side(box), _side(last)):
                    hits.append(r)
            if hits:
                for other in hits[1:]:  # two faces came together
                    for g, b in other.boxes.items():
                        hits[0].add(g, b, other.parts[g])
                    runs.remove(other)
                    active.remove(other)
                best = hits[0]
            else:
                best, nearest = None, math.inf
                for r in active:
                    last = r.boxes[r.last]
                    far = math.dist(_centre(box), _centre(last))
                    large = max(_side(box), _side(last))
                    if (id(r) not in seen and f - r.last <= MAX_HIDDEN and far < nearest and far < MAX_CHANGE * large
                            and large <= MAX_CHANGE * min(_side(box), _side(last))):
                        best, nearest = r, far
            if best is None:
                best = Run({})
                runs.append(best)
                active.append(best)
            best.add(f, box, [part])
            seen.add(id(best))
    runs = sorted((r for r in runs if len(r.boxes) >= MIN_FRAMES), key=lambda r: r.first)
    for i, r in enumerate(runs):
        r.number = i + 1
    return runs


def _gaussian(x: torch.Tensor, sigma: float) -> torch.Tensor:
    """Separable blur of [n, 1, h, w]."""
    r = max(1, math.ceil(sigma * 3))
    k = torch.exp(-(torch.arange(-r, r + 1, dtype=x.dtype, device=x.device) ** 2) / (2 * sigma * sigma))
    k = k / k.sum()
    x = F.conv2d(F.pad(x, (r, r, 0, 0), mode="replicate"), k.view(1, 1, 1, -1))
    return F.conv2d(F.pad(x, (0, 0, r, r), mode="replicate"), k.view(1, 1, -1, 1))


def _dilate(x: torch.Tensor, kernel: int) -> torch.Tensor:
    """Square dilation of [n, 1, h, w], one axis at a time: on the CPU a wide square kernel takes minutes per crop."""
    x = F.max_pool2d(x, (kernel, 1), stride=1, padding=(kernel // 2, 0))
    return F.max_pool2d(x, (1, kernel), stride=1, padding=(0, kernel // 2))


def canvas(ratio: float, size: int) -> tuple[int, int]:
    """(height, width) with size as the short edge, for a width / height of ratio."""
    ratio = min(max(ratio, 1 / MAX_RATIO), MAX_RATIO)
    return (size, round(size * ratio / 32) * 32) if ratio >= 1 else (round(size / ratio / 32) * 32, size)


def padded(bw: float, bh: float, face, context: float, least: float) -> tuple[float, float]:
    """The crop around regions spanning bw x bh, the largest of them face = (w, h): as much room around them as that
    region would have alone. A lone region gets context times itself."""
    return (max(least, bw) + (context - 1) * max(least, face[0]),
            max(least, bh) + (context - 1) * max(least, face[1]))


def fit_crop(bw: float, bh: float, size: int, context: float = CONTEXT, least: float = MIN_SIZE,
             face=None) -> tuple[float, float, tuple[int, int]]:
    """(crop width, crop height, (canvas height, canvas width)) for regions spanning bw x bh: square around a lone face,
    longer around faces side by side or stacked. A lone region's canvas has size as its short edge; regions sharing a
    crop get a larger canvas, so each is enlarged as much as it would be alone. The crop has the canvas's exact shape,
    so nothing is stretched."""
    face = face or (bw, bh)
    w, h = padded(bw, bh, face, context, least)
    ratio = 1.0 if 1 / SQUARE_WITHIN <= w / h <= SQUARE_WITHIN else w / h
    near = canvas(ratio, 1024)
    ch = max(h, w * near[0] / near[1])
    short = min(ch, ch * near[1] / near[0]) * size / (max(least, *face) * context)
    shape = canvas(ratio, max(size, round(short / 32) * 32))
    ratio = shape[1] / shape[0]
    ch = max(h, w / ratio)
    return ch * ratio, ch, shape


def _typical(run: Run):
    x, y = _middle(run)
    half = run.size / 2
    return x - half, y - half, x + half, y + half


def _face(group: list[Run]):
    """The largest region's usual width and height."""
    return (max(sorted(b[2] - b[0] for b in r.boxes.values())[len(r.boxes) // 2] for r in group),
            max(sorted(b[3] - b[1] for b in r.boxes.values())[len(r.boxes) // 2] for r in group))


def _work(group: list[Run], size: int, context: float, least: float) -> tuple[float, int, float]:
    """(canvas pixels times frames, longest canvas edge, longest crop edge in the video) for a group in one crop."""
    boxes = [_typical(r) for r in group]
    bw = max(b[2] for b in boxes) - min(b[0] for b in boxes)
    bh = max(b[3] for b in boxes) - min(b[1] for b in boxes)
    cw, ch, shape = fit_crop(bw, bh, size, context, least, _face(group))
    frames = max(r.last for r in group) - min(r.first for r in group) + 1
    return shape[0] * shape[1] * frames, max(shape), max(cw, ch)


def group_runs(runs: list[Run], group_size: int = GROUP_SIZE, size: int = 512, context: float = CONTEXT,
               least: float = MIN_SIZE) -> list[list[Run]]:
    """Regions that are on screen together and near each other share a crop when that is less work than a crop each,
    the crop is at most group_size pixels of the video across, and its canvas at most MAX_CANVAS. Each keeps the room
    around it and the enlargement it would have alone, so sharing costs nothing in how a face is drawn."""
    groups = []
    for r in sorted(runs, key=lambda r: r.size):
        best, most = None, 0.0
        for g in groups if group_size and not r.subject else ():
            if g[0].subject:
                continue
            first, last = min(o.first for o in g), max(o.last for o in g)
            if min(last, r.last) - max(first, r.first) + 1 < 0.5 * (r.last - r.first + 1):
                continue  # mostly at other times: the crop would be redrawn where it isn't
            apart = _work(g, size, context, least)[0] + _work([r], size, context, least)[0]
            work, edge, across = _work(g + [r], size, context, least)
            if across <= group_size and edge <= MAX_CANVAS and apart - work > max(most, GROUP_SAVING * apart):
                best, most = g, apart - work
        if best is None:
            groups.append([r])
        else:
            best.append(r)
    return groups


def _glide(centres: list) -> list:
    """Centres averaged over a few frames, so what follows them does not take on the mask's jitter."""
    out = []
    for i in range(len(centres)):
        near = centres[max(0, i - 6):i + 7]
        out.append((sum(c[0] for c in near) / len(near), sum(c[1] for c in near) / len(near)))
    return out


def _hold(centres: list, room: list) -> list:
    """One axis of the crop's path: it stays put while what it follows wanders within room, and otherwise moves only as
    far as it has to. A model takes a crop that moves for a camera that moves, and shakes everything around the region."""
    path, at = list(centres), centres[0]
    for order in (range(len(path)), range(len(path) - 1, -1, -1)):
        for i in order:
            at = min(max(at, centres[i] - room[i]), centres[i] + room[i])
            path[i] = at
    return path


def steady_boxes(run: Run) -> dict:
    """{frame: box} over the whole run: its usual size, gliding, and no holes where the mask lost the face."""
    w = sorted(b[2] - b[0] for b in run.boxes.values())[len(run.boxes) // 2]
    h = sorted(b[3] - b[1] for b in run.boxes.values())[len(run.boxes) // 2]
    frames = range(run.first, run.last + 1)
    centres, prev = [], run.boxes[run.first]
    for f in frames:
        prev = run.boxes.get(f, prev)
        centres.append(_centre(prev))
    return {f: (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2) for f, (cx, cy) in zip(frames, _glide(centres))
            if any(g in run.boxes for g in range(f - 2, f + 3))}  # a short dropout is filled, a face behind something is not


def smallest(height: int, width: int) -> float:
    """MIN_SIZE for a video this large: a face is as many pixels smaller as the video is."""
    return MIN_SIZE * max(height, width) / 2560


def crop_window(group: list[Run], height: int, width: int, size: int = 768, context: float = CONTEXT):
    """(frames, {frame: (x0, y0, crop width, crop height)}, canvas shape). The crop holds still and follows the faces only
    when they would otherwise near its edge. Its size follows them when they really grow, which keeps a face in a push-in
    equally large on the canvas all the way."""
    first, last = min(r.first for r in group), max(r.last for r in group)
    frames = list(range(first, last + 1))
    union = {}
    for f in frames:
        bs = [r.boxes[f] for r in group if f in r.boxes]
        if bs:
            union[f] = (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
    spans = sorted((b[2] - b[0], b[3] - b[1]) for b in union.values())
    middle = spans[len(spans) // 2]
    least = smallest(height, width)
    face = _face(group)
    shape = fit_crop(*middle, size, context, least, face)[2]
    w, h = padded(*middle, face, context, least)
    if w > width or h > height:  # what the frame cuts off one way is no reason to lose the other way too
        shape = canvas(min(w, width) / min(h, height), size)
    ratio = shape[1] / shape[0]
    centres, spans, heights, prev, largest = [], [], [], next(iter(union.values())), face
    for f in frames:
        prev = union.get(f, prev)
        here = [r.boxes[f] for r in group if f in r.boxes]
        if here:  # the largest face this frame, so a face growing in a push-in keeps its room
            largest = (max(b[2] - b[0] for b in here), max(b[3] - b[1] for b in here))
        centres.append(_centre(prev))
        spans.append((prev[2] - prev[0], prev[3] - prev[1]))
        pw, ph = padded(prev[2] - prev[0], prev[3] - prev[1], largest, context, least)
        heights.append(max(ph, pw / ratio))
    typical = sorted(heights)[len(heights) // 2]
    if max(heights) <= typical * STEADY:
        heights = [max(heights)] * len(frames)
    else:
        heights = [sum(heights[max(0, i - 12):i + 13]) / len(heights[max(0, i - 12):i + 13]) for i in range(len(frames))]
    sizes = []
    for ch in heights:
        scale = min(1.0, width / (ch * ratio), height / ch)
        sizes.append((int(ch * ratio * scale) // 2 * 2, int(ch * scale) // 2 * 2))
    # half of the margin is room to wander, the other half is what stays around the region
    xs = _hold([c[0] for c in centres], [max(s[0] - b[0], 0) / 4 for s, b in zip(sizes, spans)])
    ys = _hold([c[1] for c in centres], [max(s[1] - b[1], 0) / 4 for s, b in zip(sizes, spans)])
    pos = {}
    for f, (cx, cy), (cw, ch) in zip(frames, _glide(list(zip(xs, ys))), sizes):
        pos[f] = (min(max(round(cx - cw / 2), 0), width - cw), min(max(round(cy - ch / 2), 0), height - ch), cw, ch)
    return frames, pos, shape


def paste_mask(group: list[Run], frames: list[int], pos: dict, height: int, width: int, paste: str = "mask",
               grow: float = 0.35, feather: float = 0.12, keep: torch.Tensor | None = None) -> torch.Tensor:
    """[frames, h, w] blend weights on the largest crop's grid: the group's faces, grown over the head and feathered, away
    from keep. "mask" follows the mask's outline; "bbox" is a steady box that ignores it."""
    steady = [steady_boxes(r) for r in group] if paste == "bbox" else []
    grid = max(p[3] for p in pos.values()), max(p[2] for p in pos.values())
    usual = sorted(p[3] for p in pos.values())[len(pos) // 2]
    size = max(r.size for r in group)

    def region(t):  # the crop of a mask of any size, as nearest scaling to the frame would give, without scaling all of it
        x0, y0, cw, ch = pos[f]
        rows = torch.arange(y0, y0 + ch) * t.shape[0] // height
        cols = torch.arange(x0, x0 + cw) * t.shape[1] // width
        return t[rows][:, cols].float()[None, None]

    out = []
    for f in frames:
        x0, y0, cw, ch = pos[f]
        here = size * ch / usual  # the crop follows the face, so the face's size here follows the crop
        kernel = int(here * grow) * 2 + 1
        if paste == "bbox":
            m = torch.zeros(1, 1, ch, cw)
            for boxes in steady:
                if f in boxes:
                    a, b, c, d = boxes[f]
                    m[..., max(round(b) - y0, 0):max(round(d) - y0, 0), max(round(a) - x0, 0):max(round(c) - x0, 0)] = 1
        else:
            m = torch.zeros(1, 1, ch, cw)
            for r in group:
                for part in r.parts.get(f, ()):
                    m = torch.maximum(m, region(r.labels[f] == part))
        w = _gaussian(_dilate(m, kernel), max(1.0, here * feather))
        if keep is not None:
            w = w * (1 - _dilate(region(keep[f]), 9))
        out.append(w[0, 0] if (ch, cw) == grid else F.interpolate(w, size=grid, mode="bilinear", align_corners=False)[0, 0])
    w = torch.stack(out)
    # a gap in the mask eases in and out over a few frames, so nothing pops. Not the two ends: a run mostly ends at a cut,
    # where the old picture would show through what replaced it
    w = F.pad(w.permute(1, 2, 0).reshape(-1, 1, len(frames)), (2, 2), mode="replicate")
    w = F.avg_pool1d(w, 5, stride=1)
    return w.reshape(*grid, len(frames)).permute(2, 0, 1)


def latent_area(area: torch.Tensor, shape: tuple, vae) -> torch.Tensor:
    """[n, h, w] area down to latents of [frames, h, w]: a latent is in it if any pixel it holds is. The VAE says which
    frames make up each latent: H3's first takes 1 and the next four 4, in chunks of 17, and the last takes what is left."""
    coder = getattr(vae, "first_stage_model", None)
    ratio, chunk = getattr(coder, "vae_ratio_t", None), getattr(coder, "tokens_chunk_size", None)
    area = area.float()
    if not ratio or not chunk:
        return F.adaptive_max_pool3d(area[None, None], shape)[0, 0]
    cycle, at, frames = [ratio - coder.frame_pre_padding] + [ratio] * (chunk - 1), 0, []
    for i in range(shape[0]):
        last = i == shape[0] - 1
        start = min(at, len(area) - 1)
        at += cycle[i % chunk]
        frames.append(area[start:len(area) if last else max(at, start + 1)].amax(0))
    return F.adaptive_max_pool2d(torch.stack(frames)[None], shape[1:])[0]


def _hold_to(x: torch.Tensor, frames: int) -> torch.Tensor:
    """x with its last frame held until it has this many."""
    return torch.cat([x, x[-1:].expand(frames - len(x), *x.shape[1:])]) if frames > len(x) else x


def reels(jobs: list, clip_length) -> list[list[int]]:
    """Which jobs are sampled together, one after another in one video: crops of one canvas and prompt, until the video
    is REEL_TOKENS long. Each starts on a clip of the VAE, which encodes clips apart, so none leaks into the next."""
    if not clip_length:
        return [[i] for i in range(len(jobs))]
    out, open_ = [], {}
    for i, (crops, area, cond, seed) in enumerate(jobs):
        h, w = crops.shape[1:3]
        cost = math.ceil((len(crops) + 1) / clip_length) * clip_length * (h // 32) * (w // 32) // 4
        key = (id(cond), h, w)
        if key in open_ and open_[key][1] + cost <= REEL_TOKENS:
            open_[key][0].append(i)
            open_[key][1] += cost
        else:
            open_[key] = [[i], cost]
            out.append(open_[key][0])
    return out


def redraw_batch(model, vae, jobs: list, sampler, sigmas: torch.Tensor, progress=None) -> list:
    """[(crops [n, H, W, 3], area [n, H, W], conditioning, seed)] in, the redrawn crops out, each only inside its area:
    the rest of a crop stays as it is and gives the model something to match, which steadies the face. Without a guide,
    so blur is not carried over. H3 samples one video at a time and every call has a fixed cost far above that of a
    small crop, so crops of one canvas are put one after another into one video, cut to cut, and sampled together.
    progress(crops) is called after every step with the number of crops in the video."""
    from comfy.nested_tensor import NestedTensor
    from comfy_extras.nodes_custom_sampler import Guider_Basic, Noise_RandomNoise
    from comfy_extras.nodes_minimax_h3 import _empty_av_latent

    coder = getattr(vae, "first_stage_model", None)
    clip_length, tokens = getattr(coder, "clip_length", None), getattr(coder, "tokens_chunk_size", None)
    drawn = [None] * len(jobs)
    groups = reels(jobs, clip_length if tokens else None)
    t0 = time.perf_counter()
    for members in groups:
        h, w = jobs[members[0]][0].shape[1:3]
        lengths = [len(jobs[i][0]) for i in members]
        if len(members) == 1:
            spans = [len(jobs[members[0]][0])]
        else:  # each from the start of a VAE clip, with a frame held after it at least
            spans = [math.ceil((n + 1) / clip_length) * clip_length for n in lengths]
        crops = torch.cat([_hold_to(jobs[i][0], f) for i, f in zip(members, spans)])
        area = torch.cat([_hold_to(jobs[i][1], f) for i, f in zip(members, spans)])
        empty, count = _empty_av_latent(w, h, len(crops))
        crops, area = _hold_to(crops, count)[:count], _hold_to(area, count)[:count]
        video = vae.encode(crops)
        audio = empty["samples"].unbind()[1].to(video)
        inside = latent_area(area, tuple(video.shape[-3:]), vae).to(video)[None, None]  # audio stays silent
        latent = NestedTensor((video, audio))
        locked = NestedTensor((inside.expand_as(video).contiguous(), torch.zeros_like(audio)))
        cond, seed = jobs[members[0]][2], jobs[members[0]][3]
        guider = Guider_Basic(model)
        guider.set_conds(cond)
        noise = Noise_RandomNoise(seed).generate_noise({"samples": latent})
        step = (lambda *_, k=len(members): progress(k)) if progress else None
        out = guider.sample(noise, latent, sampler, sigmas, denoise_mask=locked, callback=step, seed=seed).unbind()[0]
        at = 0
        for i, n, f in zip(members, lengths, spans):
            part = out if len(members) == 1 else out[:, :, at:at + f // clip_length * tokens]
            images = vae.decode(part)
            images = images.reshape(-1, *images.shape[-3:])
            drawn[i] = _hold_to(images, n)[:n]
            at += f // clip_length * tokens if len(members) > 1 else 0
    log.info("H3 Region Redraw: %d crops in %d videos, %.0f s", len(jobs), len(groups), time.perf_counter() - t0)
    return drawn


def _resize(x: torch.Tensor, hw, mode: str) -> torch.Tensor:
    """[..., h, w, c] to another size."""
    if tuple(x.shape[-3:-1]) == tuple(hw):
        return x
    flat = x.reshape(-1, *x.shape[-3:]).movedim(-1, 1)
    out = F.interpolate(flat, size=tuple(hw), mode=mode, align_corners=False, antialias=mode == "bicubic")
    return out.movedim(1, -1).reshape(*x.shape[:-3], *hw, x.shape[-1])


def _each(xs: list, hw_of, mode: str) -> list:
    """Resize a list of [h, w, c] at once when they are all one size, as a steady crop's frames are."""
    sizes = [tuple(hw_of(i)) for i in range(len(xs))]
    if len(set(sizes)) == 1 and len({tuple(x.shape) for x in xs}) == 1:
        return list(_resize(torch.stack(xs), sizes[0], mode))
    return [_resize(x, hw, mode) for x, hw in zip(xs, sizes)]


def compare(before: torch.Tensor, after: torch.Tensor) -> torch.Tensor:
    """[n, h, w, 3] twice, the same size: one clip with before above after, or beside it for a crop taller than wide,
    with a black line between. Float in [0, 1]."""
    tall = before.shape[1] > before.shape[2]
    gap = torch.zeros(len(before), *((before.shape[1], 4) if tall else (4, before.shape[2])), 3)
    return torch.cat([before.float(), gap, after.float()], 2 if tall else 1)


@dataclass
class Crop:
    """Where one crop goes back: per frame its box in the video, the blend weights (uint8, on the largest box's grid)
    and the colour shift of each stretch of frames it was drawn in."""
    frames: list
    pos: dict
    shape: tuple
    weights: torch.Tensor
    shifts: list = field(default_factory=list)  # (first index, end index, [3] shift)
    text: str = ""
    height: int = 0
    width: int = 0


def paste_crop(images: torch.Tensor, crop: Crop, drawn: torch.Tensor, first: int = 0) -> None:
    """Feather drawn (frames first..first + len(drawn) of the crop, at any size of the crop's shape) into images, in
    place."""
    sy, sx = images.shape[1] / crop.height, images.shape[2] / crop.width
    for i, new in enumerate(drawn, first):
        f = crop.frames[i]
        x0, y0, cw, ch = crop.pos[f]
        ax, ay = round(x0 * sx), round(y0 * sy)
        bx, by = min(round((x0 + cw) * sx), images.shape[2]), min(round((y0 + ch) * sy), images.shape[1])
        hw = (by - ay, bx - ax)
        shift = next(v for a, b, v in crop.shifts if a <= i < b).to(images.device)
        w = _resize(crop.weights[i, ..., None].float() / 255, hw, "bilinear").to(images.device)
        n = _resize(new.float()[None], hw, "bicubic" if hw[0] < new.shape[0] else "bilinear")[0].to(images.device)
        o = images[f, ay:by, ax:bx].float()
        images[f, ay:by, ax:bx] = (o * (1 - w) + (n + shift) * w).clamp(0, 1).to(images.dtype)


def refine_groups(images, groups, height, width, redraw_many, size=768, paste="mask", grow=0.35, feather=0.12,
                  context=CONTEXT, keep=None, chunk=CHUNK) -> tuple[list, list]:
    """Crop each group, redraw them a few at a time with redraw_many([Job]) -> [crops], and feather them back into images
    (in place). Subjects ignore keep. Returns, per group, its Crop and before beside after at the canvas size."""
    plans, jobs = [], []
    for g, group in enumerate(groups):
        frames, pos, shape = crop_window(group, height, width, size, context)
        short = sorted(min(p[2], p[3]) for p in pos.values())
        wide, tall = max(p[2] for p in pos.values()), max(p[3] for p in pos.values())
        scale = f"{min(shape) / short[-1]:.1f}x" if short[0] == short[-1] else f"{min(shape) / short[-1]:.1f}-{min(shape) / short[0]:.1f}x"
        who = f"subject {group[0].subject}" if group[0].subject else f"regions {sorted(r.number for r in group)}"
        text = (f"{who}, frames {frames[0]}-{frames[-1]}, crop up to {wide} x {tall}, "
                f"redrawn at {shape[1]} x {shape[0]}, enlarged {scale}")
        plans.append(dict(crop=Crop(frames, pos, shape, None, text=text), compare=[],
                          keep=None if group[0].subject else keep))
        parts = math.ceil(len(frames) / MAX_FRAMES)
        step = math.ceil(len(frames) / parts)
        jobs += [(g, s, frames[s:s + step]) for s in range(0, len(frames), step)]
    for c in range(0, len(jobs), chunk):
        ready = []
        for g, s, part in jobs[c:c + chunk]:
            plan, crop = plans[g], plans[g]["crop"]
            log.info("H3 Region Redraw: %s", crop.text)
            if s == 0:
                weights = paste_mask(groups[g], crop.frames, crop.pos, height, width, paste, grow, feather, plan["keep"])
                crop.weights = (weights * 255).round().to(torch.uint8)
            pos, shape = crop.pos, crop.shape
            orig = [images[f, pos[f][1]:pos[f][1] + pos[f][3], pos[f][0]:pos[f][0] + pos[f][2]].float() for f in part]
            big = torch.stack(_each(orig, lambda i: shape, "bicubic")).clamp(0, 1)
            area = torch.stack([w[..., 0] > 2 for w in _each([crop.weights[s + i, ..., None].float() for i in range(len(part))],
                                                              lambda i: shape, "bilinear")])
            ready.append(Job(g, s, part, big, area, groups[g][0].subject))
        for job, new in zip(ready, redraw_many(ready)):
            plan, crop = plans[job.group], plans[job.group]["crop"]
            new = new.to(images.device, torch.float32).clamp(0, 1)
            plan["compare"].append(compare(job.crops, new).cpu())
            pos = crop.pos
            orig = [images[f, pos[f][1]:pos[f][1] + pos[f][3], pos[f][0]:pos[f][0] + pos[f][2]].float() for f in job.frames]
            small = _each(list(new), lambda i: orig[i].shape[:2], "bicubic")
            rest = [x[..., 0] <= 2 for x in _each([crop.weights[job.start + i, ..., None].float() for i in range(len(orig))],
                                                  lambda i: orig[i].shape[:2], "bilinear")]
            # outside the area nothing was redrawn: any drift there is the VAE's
            total = max(sum(float(x.sum()) for x in rest), 1e-6)
            shift = sum((o - n)[x].sum(0) for o, n, x in zip(orig, small, rest)) / total
            crop.shifts.append((job.start, job.start + len(job.frames), shift.float().cpu()))
            crop.height, crop.width = height, width
            paste_crop(images, crop, new, job.start)
    return [p["crop"] for p in plans], [torch.cat(p["compare"]) for p in plans]


@dataclass
class Job:
    """One stretch of frames of one group's crop, enlarged and ready to redraw."""
    group: int
    start: int
    frames: list
    crops: torch.Tensor
    area: torch.Tensor
    subject: int = 0


def refine_group(images, group, height, width, redraw_fn, size=768, paste="mask", grow=0.35, feather=0.12,
                 context=CONTEXT, keep=None):
    """One group through refine_groups, with redraw_fn(crops, area) -> crops: (Crop, compare)."""
    crops, compares = refine_groups(images, [group], height, width,
                                           lambda jobs: [redraw_fn(j.crops, j.area) for j in jobs],
                                    size, paste, grow, feather, context, keep)
    return crops[0], compares[0]


def report(runs: list[Run], max_size: int) -> str:
    rows = [f"{f'subject {r.subject}' if r.subject else f'region {r.number}'}: frames {r.first}-{r.last}, at {round(_middle(r)[0])}, "
            f"{round(_middle(r)[1])}, {round(r.size)} px, {'larger than max_size' if not r.subject and r.least > max_size else 'redraw'}"
            for r in runs]
    return "\n".join(rows) or "nothing in the masks"


def numbered(inputs: dict | None) -> dict:
    """{1: value} from an Autogrow's {"name_1": value}, leaving out what isn't connected."""
    return {int(k.rsplit("_", 1)[-1]): v for k, v in (inputs or {}).items() if v is not None}


def plain(masks: torch.Tensor) -> torch.Tensor:
    return masks[None] if masks.dim() == 2 else masks


def denoised(sigmas: torch.Tensor, denoise: float) -> torch.Tensor:
    """The last steps of sigmas, as Split Sigmas Denoise's low_sigmas: denoise 0.5 of 0.7, 0.49, 0 keeps 0.49, 0."""
    steps = round(max(len(sigmas) - 1, 0) * denoise)
    return sigmas[-(steps + 1):]


def reference_cond(clip, vae, prompt: str, image: torch.Tensor, shape: tuple[int, int]):
    """H3's own reference conditioning for one subject, at the canvas it will be drawn on."""
    from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo
    return MiniMaxH3ReferenceToVideo.execute(clip, prompt, shape[1], shape[0], 5, "match", vae,
                                             ref_images={"ref_image_1": image}).result[0]


class H3RegionRedraw(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_H3RegionRedraw", "Region Redraw for MiniMax H3", CAT_SAMPLING,
            "Repair the small faces of a finished video, which is what the defaults are for. With other settings it repairs "
            "or replaces anything else in a mask, from a reference picture if you like. Each region is cropped, enlarged, "
            "redrawn and feathered back; other frames and pixels are untouched.",
            [IO.Model.Input("model", tooltip="The H3 model, after its LoRAs"),
             IO.Vae.Input("vae", tooltip="The H3 video VAE"),
             IO.Clip.Input("clip", tooltip="The H3 text encoder"),
             IO.Image.Input("images", tooltip="The finished video's frames"),
             IO.Mask.Input("masks", optional=True, tooltip="What to redraw from the prompt, one mask per frame, e.g. from "
                                                           "SAM3 Track to Mask. Subjects may be left in: their own masks "
                                                           "take them out"),
             IO.Autogrow.Input("subject_masks", optional=True, template=IO.Autogrow.TemplateNames(
                 input=IO.Mask.Input("subject_mask", tooltip="One subject, redrawn alone, from the reference of the same number"),
                 names=[f"subject_mask_{i}" for i in range(1, 10)], min=0)),
             IO.Autogrow.Input("subject_references", optional=True, template=IO.Autogrow.TemplateNames(
                 input=IO.Image.Input("subject_reference", tooltip="The picture for the subject mask of the same number. "
                                                                   "The prompt calls it <Picture 1>"),
                 names=[f"subject_reference_{i}" for i in range(1, 10)], min=0)),
             IO.Sampler.Input("sampler", tooltip="From KSamplerSelect; lcm is what this was tested with"),
             IO.Sigmas.Input("sigmas", tooltip="Redraw strength, as on a custom sampler. Repair: Manual Sigmas 0.7, "
                                               "0.494118, 0. To replace something, start near 1"),
             IO.Float.Input("denoise", default=1.0, min=0.0, max=1.0, step=0.01,
                            tooltip="Share of the sigmas' steps to take, from the end, as Split Sigmas Denoise does: 1 "
                                    "takes them all, as they are; 0.5 of 0.7, 0.494118, 0 takes 0.494118, 0"),
             IO.String.Input("prompt", multiline=True, default=DEFAULT_PROMPT,
                             tooltip="What the regions should look like, subjects included. The default is for faces. "
                                     "A subject's picture is <Picture 1>"),
             IO.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff, control_after_generate=True),
             IO.Int.Input("refine_size", default=REFINE_SIZE, min=384, max=1536, step=32,
                          tooltip="Short edge a crop is enlarged to before it is redrawn. 512 is quick; 768, H3's native "
                                  "size, suits replacing something"),
             IO.Float.Input("context", default=CONTEXT, min=1.2, max=6.0, step=0.1,
                            tooltip="Crop size as a multiple of the region. Lower: it fills the crop and is enlarged "
                                    "more. Higher: the model sees more of what surrounds it"),
             IO.Int.Input("max_size", default=128, min=16, max=1024, step=8,
                          tooltip="Regions in masks that never get smaller than this (px) stay. One that does is "
                                  "redrawn whole. Subjects are always redrawn"),
             IO.Int.Input("group_size", default=GROUP_SIZE, min=0, max=2048, step=32,
                          tooltip="Longest canvas edge a crop shared by nearby regions may have. They share one only "
                                  "when that is quicker, and each keeps the size it would have alone. 0: a crop each"),
             IO.Combo.Input("paste", options=["mask", "bbox"], default="mask",
                            tooltip="What is redrawn and pasted back: the mask's outline, or a steady box around it. "
                                    "bbox leaves room for something of another shape"),
             IO.Float.Input("grow", default=0.35, min=0.0, max=1.0, step=0.01,
                            tooltip="How far the redrawn area reaches past the mask, as a share of the region's size"),
             IO.Float.Input("feather", default=0.12, min=0.0, max=0.5, step=0.01,
                            tooltip="Softness of the pasted edge, as a share of the region's size")],
            [IO.Image.Output(display_name="images"),
             IO.Image.Output(display_name="compare", is_output_list=True,
                             tooltip="Each crop before and after, one clip per crop at the canvas size"),
             IO.String.Output(display_name="report")],
            ["face", "small face", "face fix", "face detailer", "adetailer", "h3", "refine", "mask", "inpaint", "replace",
             "region", "detail"],
            input_list=False)

    @classmethod
    def execute(cls, model, vae, clip, images, sampler, sigmas, denoise, prompt, seed, refine_size, context, max_size,
                group_size, paste, grow, feather, masks=None, subject_masks=None,
                subject_references=None) -> IO.NodeOutput:
        from comfy.model_management import throw_exception_if_processing_interrupted
        from comfy.utils import ProgressBar

        n, height, width = images.shape[:3]
        subjects = {i: plain(m) for i, m in numbered(subject_masks).items()}
        refs = numbered(subject_references)
        masks = None if masks is None else plain(masks)
        for m in [*subjects.values(), *([] if masks is None else [masks])]:
            if m.shape[0] != n:
                raise ValueError(f"Region Redraw: {n} frames, but {m.shape[0]} masks")
        start = time.perf_counter()
        shots = shot_starts(images)
        runs, keep = [], None
        for i, m in sorted(subjects.items()):
            labels, regions = split_regions(m, height, width, subject=True)
            for r in link_regions(regions, shots):
                r.labels, r.subject = labels, i
                runs.append(r)
            m = F.interpolate(m[:, None].float(), size=(height, width), mode="nearest")[:, 0] > 0.5
            keep = m if keep is None else keep | m
        if masks is not None:
            if keep is not None:  # a subject left in the shared mask is drawn once, from its picture
                masks = F.interpolate(masks[:, None].float(), size=(height, width), mode="nearest")[:, 0] * ~keep
            labels, regions = split_regions(masks, height, width)
            others = link_regions(regions, shots)
            for r in others:
                r.labels = labels
            runs += others
        chosen = [r for r in runs if r.subject or r.least <= max_size]
        text = report(runs, max_size)
        for i in sorted(set(refs) - set(subjects)):
            text += f"\nsubject reference {i} has no subject mask, so it was not used"
        log.info("H3 Region Redraw: shots start at %s\n%s", shots, text)
        sigmas = None if sigmas is None else denoised(sigmas, denoise)
        if sigmas is not None and len(sigmas) < 2:
            text += "\ndenoise 0 leaves everything as it was"
        if not chosen or sigmas is None or len(sigmas) < 2:
            return IO.NodeOutput(images, [], text)

        planned = time.perf_counter()
        positive = clip.encode_from_tokens_scheduled(clip.tokenize(prompt))
        groups = group_runs(chosen, group_size, refine_size, context, smallest(height, width))
        conds = {}  # encoded up front: the text encoder would otherwise push the model out between crops
        for g in groups:
            subject = g[0].subject
            if subject in refs:
                shape = crop_window(g, height, width, refine_size, context)[2]
                if (subject, shape) not in conds:
                    conds[subject, shape] = reference_cond(clip, vae, prompt, refs[subject], shape)
        encoded = time.perf_counter()
        out = images.clone()
        spans = [max(r.last for r in g) - min(r.first for r in g) + 1 for g in groups]
        bar = ProgressBar(sum(math.ceil(n / MAX_FRAMES) for n in spans) * (len(sigmas) - 1))  # a step of a crop each

        def redraw_many(jobs):
            throw_exception_if_processing_interrupted()
            return redraw_batch(model, vae, [(j.crops, j.area, conds.get((j.subject, tuple(j.crops.shape[1:3])), positive),
                                              seed + j.group) for j in jobs], sampler, sigmas, bar.update)

        crops, compares = refine_groups(out, groups, height, width, redraw_many, refine_size, paste, grow, feather,
                                        context, keep)
        rows = [f"crop {i + 1}: {c.text}" for i, c in enumerate(crops)]
        log.info("H3 Region Redraw: plan %.0f s, prompt %.0f s, %d crops %.0f s", planned - start, encoded - planned,
                 len(groups), time.perf_counter() - encoded)
        return IO.NodeOutput(out, compares, "\n".join([text, "", *rows]))


NODES = [H3RegionRedraw]
