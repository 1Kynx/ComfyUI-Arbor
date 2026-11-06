"""Small Face Refine for MiniMax H3: redraw the faces too small for a whole-frame pass.

A face a few dozen pixels wide is more than the model can draw at 2K, whatever the sampler does. Here each face in the
mask is cropped, enlarged, redrawn at low noise and feathered back into the video. Which faces those are is the mask's
business: any tool that makes one will do, so nothing here knows about trackers or who anyone is. A lead has a mask of
their own, wired to their picture, so which picture belongs to whom is never worked out.
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
LABEL_SHORT = 720               # masks are split into faces at about this short edge
STEADY = 1.35                   # a face whose size varies less than this keeps one crop size: the rest is mask jitter
MAX_HIDDEN = 24                 # frames a face may be hidden for and still be the same face
MAX_CHANGE = 1.5                # a face is not this much larger from one sighting to the next, and moves less than this x its size
MAX_TOUCHING = 3.0              # faces that touch make a piece at most this much larger; more is a mask slipping onto something
MIN_FACE = 77                   # a smaller face gets the crop of one this size, or its surroundings would vanish
GROUP_SIZE = 288                # faces sharing a crop draw worse than faces alone, but above this it gets much worse
CONTEXT = 4.0                   # default crop size / the faces it holds
GROUP_CONTEXT = 2.5             # which faces share a crop is judged at this, whatever context is
LEAD_PROMPT = ("The same person as in <Picture 1>, in a film shot. Their realistic natural face with clear eyes, nose and "
               "mouth, natural skin, shot on a cinema camera.")
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
    lead: int = 0                # which lead_mask it came from; such a face gets a crop to itself

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
    """First frame of each shot: a cut is a frame far more different from the last than the clip's usual change."""
    small = frames[:, ::8, ::8].float().mean(-1)
    change = (small[1:] - small[:-1]).abs().mean((1, 2))
    if len(change) == 0:
        return [0]
    limit = max(0.04, 6 * float(change.median()))
    return [0] + [i + 1 for i, c in enumerate(change.tolist()) if c > limit]


def split_faces(masks: torch.Tensor, height: int, width: int) -> tuple[torch.Tensor, dict]:
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
            regions[f] = parts
    return labels, regions


def _inside(a, b) -> float:
    """How much of box a lies in box b."""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0) / max((a[2] - a[0]) * (a[3] - a[1]), 1e-6)


def link_faces(regions: dict, shots: list[int]) -> list[Run]:
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


def fit_crop(bw: float, bh: float, size: int, context: float = CONTEXT) -> tuple[float, float, tuple[int, int]]:
    """(crop width, crop height, (canvas height, canvas width)) for faces spanning bw x bh: square around a lone face,
    longer around faces side by side or stacked. The canvas has size as its short edge and the crop the canvas's exact
    shape, so nothing is stretched."""
    w, h = max(MIN_FACE, bw) * context, max(MIN_FACE, bh) * context
    ratio = min(max(w / h, 1 / MAX_RATIO), MAX_RATIO)
    if 1 / SQUARE_WITHIN <= ratio <= SQUARE_WITHIN:
        ratio = 1.0
    shape = (size, round(size * ratio / 32) * 32) if ratio >= 1 else (round(size / ratio / 32) * 32, size)
    ratio = shape[1] / shape[0]
    ch = max(h, w / ratio)
    return ch * ratio, ch, shape


def _crop_short(boxes, size: int) -> float:
    """Short edge of the crop that would hold these boxes, for deciding who shares one."""
    bw = max(b[2] for b in boxes) - min(b[0] for b in boxes)
    bh = max(b[3] for b in boxes) - min(b[1] for b in boxes)
    return min(fit_crop(bw, bh, size, GROUP_CONTEXT)[:2])


def _typical(run: Run):
    x, y = _middle(run)
    half = run.size / 2
    return x - half, y - half, x + half, y + half


def group_runs(runs: list[Run], group_size: int = GROUP_SIZE, size: int = 768) -> list[list[Run]]:
    """Runs that share frames become one crop, as long as its short edge stays within group_size."""
    groups = []
    for r in sorted(runs, key=lambda r: r.size):
        for g in groups:
            shared = not r.lead and all(not o.lead and o.first <= r.last and r.first <= o.last for o in g)
            if shared and _crop_short([_typical(o) for o in g + [r]], size) <= group_size:
                g.append(r)
                break
        else:
            groups.append([r])
    return groups


def _glide(centres: list) -> list:
    """Centres averaged over a few frames, so what follows them does not take on the mask's jitter."""
    out = []
    for i in range(len(centres)):
        near = centres[max(0, i - 6):i + 7]
        out.append((sum(c[0] for c in near) / len(near), sum(c[1] for c in near) / len(near)))
    return out


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


def crop_window(group: list[Run], height: int, width: int, size: int = 768, context: float = CONTEXT):
    """(frames, {frame: (x0, y0, crop width, crop height)}, canvas shape). The crop's centre follows the faces. So does its
    size when they really grow, which keeps a face in a push-in equally large on the canvas all the way."""
    first, last = min(r.first for r in group), max(r.last for r in group)
    frames = list(range(first, last + 1))
    union = {}
    for f in frames:
        bs = [r.boxes[f] for r in group if f in r.boxes]
        if bs:
            union[f] = (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
    spans = sorted((b[2] - b[0], b[3] - b[1]) for b in union.values())
    middle = spans[len(spans) // 2]
    shape = fit_crop(*middle, size, context)[2]
    ratio = shape[1] / shape[0]
    centres, heights, prev = [], [], next(iter(union.values()))
    for f in frames:
        prev = union.get(f, prev)
        centres.append(_centre(prev))
        heights.append(max(max(MIN_FACE, prev[3] - prev[1]) * context, max(MIN_FACE, prev[2] - prev[0]) * context / ratio))
    typical = sorted(heights)[len(heights) // 2]
    if max(heights) <= typical * STEADY:
        heights = [max(heights)] * len(frames)
    else:
        heights = [sum(heights[max(0, i - 12):i + 13]) / len(heights[max(0, i - 12):i + 13]) for i in range(len(frames))]
    pos = {}
    for f, (cx, cy), ch in zip(frames, _glide(centres), heights):
        scale = min(1.0, width / (ch * ratio), height / ch)
        cw, ch = int(ch * ratio * scale) // 2 * 2, int(ch * scale) // 2 * 2
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

    def region(t):
        x0, y0, cw, ch = pos[f]
        return F.interpolate(t.float()[None, None], size=(height, width), mode="nearest")[..., y0:y0 + ch, x0:x0 + cw]

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
    # eases in and out over a few frames, so a face that loses its mask does not pop
    w = F.avg_pool1d(w.permute(1, 2, 0).reshape(-1, 1, len(frames)), 5, stride=1, padding=2)
    return w.reshape(*grid, len(frames)).permute(2, 0, 1)


def redraw(model, vae, positive, crops: torch.Tensor, area: torch.Tensor, sampler, sigmas: torch.Tensor, seed: int) -> torch.Tensor:
    """[n, H, W, 3] enlarged crops in, redrawn out, inside the [n, H, W] area: the rest of the crop stays as it is and
    gives the model something to match, which steadies the face. Without a guide, so blur is not carried over."""
    from comfy.nested_tensor import NestedTensor
    from comfy_extras.nodes_custom_sampler import Guider_Basic, Noise_RandomNoise
    from comfy_extras.nodes_minimax_h3 import _empty_av_latent

    n, h, w = crops.shape[:3]
    empty, count = _empty_av_latent(w, h, n)
    if count > n:  # H3 takes 17k + 5 frames: hold the last one
        crops = torch.cat([crops, crops[-1:].expand(count - n, -1, -1, -1)])
        area = torch.cat([area, area[-1:].expand(count - n, -1, -1)])
    video = vae.encode(crops[:count])
    audio = empty["samples"].unbind()[1].to(video)
    latent = NestedTensor((video, audio))
    # latents cover several frames and pixels: any of them being in the area puts the latent in. Audio stays silent
    inside = F.adaptive_max_pool3d(area[None, None].float(), tuple(video.shape[-3:])).to(video)
    locked = NestedTensor((inside.expand_as(video).contiguous(), torch.zeros_like(audio)))
    guider = Guider_Basic(model)
    guider.set_conds(positive)
    noise = Noise_RandomNoise(seed).generate_noise({"samples": latent})
    out = guider.sample(noise, latent, sampler, sigmas, denoise_mask=locked, seed=seed)
    images = vae.decode(out.unbind()[0])
    return images.reshape(-1, *images.shape[-3:])[:n]


def refine_group(images, group, height, width, redraw_fn, size=768, paste="mask", grow=0.35, feather=0.12,
                 context=CONTEXT, keep=None) -> tuple[torch.Tensor, str]:
    """Crop one group, redraw it, feather it back into images (in place). Returns what was drawn, as uint8 at the
    enlarged size, and a line saying where it came from."""
    frames, pos, shape = crop_window(group, height, width, size, context)
    short = sorted(min(p[2], p[3]) for p in pos.values())
    wide, tall = max(p[2] for p in pos.values()), max(p[3] for p in pos.values())
    scale = f"{min(shape) / short[-1]:.1f}x" if short[0] == short[-1] else f"{min(shape) / short[-1]:.1f}-{min(shape) / short[0]:.1f}x"
    who = f"lead {group[0].lead}" if group[0].lead else f"faces {sorted(r.number for r in group)}"
    text = (f"{who}, frames {frames[0]}-{frames[-1]}, crop up to {wide} x {tall}, "
            f"redrawn at {shape[1]} x {shape[0]}, enlarged {scale}")
    log.info("H3 Small Face Refine: %s", text)
    weights = paste_mask(group, frames, pos, height, width, paste, grow, feather, keep)
    parts = math.ceil(len(frames) / MAX_FRAMES)
    step = math.ceil(len(frames) / parts)
    clip = []

    def resized(x, hw, mode):  # [h, w, c] to another size
        if tuple(x.shape[:2]) == tuple(hw):
            return x
        extra = {} if mode == "area" else {"align_corners": False}
        return F.interpolate(x.movedim(-1, 0)[None], size=tuple(hw), mode=mode, **extra)[0].movedim(0, -1)

    for s in range(0, len(frames), step):
        part = frames[s:s + step]
        orig = [images[f, pos[f][1]:pos[f][1] + pos[f][3], pos[f][0]:pos[f][0] + pos[f][2]].float() for f in part]
        big = torch.stack([resized(o, shape, "bicubic") for o in orig])
        area = torch.stack([resized(weights[s + i, ..., None], shape, "bilinear")[..., 0] > 0.01 for i in range(len(part))])
        new = redraw_fn(big.clamp(0, 1), area).to(images.device, torch.float32)
        clip.append((new.clamp(0, 1) * 255).round().to(torch.uint8).cpu())
        small = [resized(n, o.shape[:2], "area") for n, o in zip(new, orig)]
        w = [resized(weights[s + i, ..., None], o.shape[:2], "bilinear").to(images.device) for i, o in enumerate(orig)]
        total = sum(x.sum() for x in w).clamp(min=1e-6)
        shift = sum(((o - n) * x).sum((0, 1)) for o, n, x in zip(orig, small, w)) / total  # keep the shot's colour
        for f, o, n, x in zip(part, orig, small, w):
            images[f, pos[f][1]:pos[f][1] + pos[f][3], pos[f][0]:pos[f][0] + pos[f][2]] = \
                (o * (1 - x) + (n + shift) * x).clamp(0, 1).to(images.dtype)
    return torch.cat(clip), text


def join_clips(clips: list[torch.Tensor]) -> torch.Tensor:
    """uint8 clips of any shape, one after another, centred on the smallest canvas that holds them all."""
    h, w = max(c.shape[1] for c in clips), max(c.shape[2] for c in clips)
    out = torch.zeros(sum(len(c) for c in clips), h, w, 3, dtype=torch.uint8)
    at = 0
    for c in clips:
        y, x = (h - c.shape[1]) // 2, (w - c.shape[2]) // 2
        out[at:at + len(c), y:y + c.shape[1], x:x + c.shape[2]] = c
        at += len(c)
    return out.float() / 255


def report(runs: list[Run], max_face: int) -> str:
    rows = [f"{f'lead {r.lead}' if r.lead else f'face {r.number}'}: frames {r.first}-{r.last}, at {round(_middle(r)[0])}, "
            f"{round(_middle(r)[1])}, {round(r.size)} px, {'larger than max_face' if not r.lead and r.least > max_face else 'refine'}"
            for r in runs]
    return "\n".join(rows) or "no faces in the mask"


def numbered(inputs: dict | None) -> dict:
    """{1: value} from an Autogrow's {"name_1": value}, leaving out what isn't connected."""
    return {int(k.rsplit("_", 1)[-1]): v for k, v in (inputs or {}).items() if v is not None}


def plain(masks: torch.Tensor) -> torch.Tensor:
    return masks[None] if masks.dim() == 2 else masks


def reference_cond(clip, vae, image: torch.Tensor, shape: tuple[int, int]):
    """H3's own reference conditioning for one person, at the canvas it will be drawn on."""
    from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo
    return MiniMaxH3ReferenceToVideo.execute(clip, LEAD_PROMPT, shape[1], shape[0], 5, "match", vae,
                                             ref_images={"ref_image_1": image}).result[0]


class H3FaceRefine(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_H3FaceRefine", "Small Face Refine for MiniMax H3", CAT_SAMPLING,
            "Redraw the small faces in a mask. Each face is cropped, enlarged, redrawn at low noise and feathered back; "
            "other frames and pixels are untouched. Faces are redrawn, not recovered: they can change.",
            [IO.Model.Input("model", tooltip="The H3 model, after its LoRAs"),
             IO.Vae.Input("vae", tooltip="The H3 video VAE"),
             IO.Clip.Input("clip", tooltip="The H3 text encoder"),
             IO.Image.Input("images", tooltip="The finished video's frames"),
             IO.Mask.Input("masks", optional=True, tooltip="The faces to redraw, one mask per frame, e.g. from SAM3 Track "
                                                           "to Mask. Leads may be left in: their own masks take them out"),
             IO.Autogrow.Input("lead_masks", optional=True, template=IO.Autogrow.TemplateNames(
                 input=IO.Mask.Input("lead_mask", tooltip="One lead's face, redrawn alone, from the reference of the same number"),
                 names=[f"lead_mask_{i}" for i in range(1, 10)], min=0)),
             IO.Autogrow.Input("references", optional=True, template=IO.Autogrow.TemplateNames(
                 input=IO.Image.Input("reference", tooltip="The picture of the lead with the same number"),
                 names=[f"reference_{i}" for i in range(1, 10)], min=0)),
             IO.Sampler.Input("sampler", tooltip="From KSamplerSelect; lcm is what this was tested with"),
             IO.Sigmas.Input("sigmas", tooltip="Redraw strength: a lower start keeps more of the face. Tested with "
                                               "Manual Sigmas 0.7, 0.494118, 0"),
             IO.String.Input("prompt", multiline=True, default=DEFAULT_PROMPT,
                             tooltip="One description for every redrawn face"),
             IO.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff, control_after_generate=True),
             IO.Int.Input("refine_size", default=768, min=384, max=1536, step=32,
                          tooltip="Short edge a crop is enlarged to before it is redrawn. 768 is H3's native size"),
             IO.Float.Input("context", default=CONTEXT, min=1.2, max=6.0, step=0.1,
                            tooltip="Crop size as a multiple of the face. Lower: the face fills the crop and is enlarged "
                                    "more. Higher: the model sees more of what surrounds it"),
             IO.Int.Input("max_face", default=128, min=16, max=4096,
                          tooltip="Faces that never get smaller than this (px) stay. A face that does is redrawn whole"),
             IO.Int.Input("group_size", default=0, min=0, max=2048, step=8,
                          tooltip="0: every face has its own crop, which draws best. Above 0: nearby faces share a crop "
                                  "up to this short edge (px), which is quicker in a crowd. 288 is a good limit"),
             IO.Combo.Input("paste", options=["mask", "bbox"], default="mask",
                            tooltip="What is pasted back: the mask's outline of the face, or a steady box around it"),
             IO.Float.Input("grow", default=0.35, min=0.0, max=1.0, step=0.01,
                            tooltip="How far the pasted area reaches past the face, as a share of the face's size"),
             IO.Float.Input("feather", default=0.12, min=0.0, max=0.5, step=0.01,
                            tooltip="Softness of the pasted edge, as a share of the face's size")],
            [IO.Image.Output(display_name="images"), IO.Image.Output(display_name="face_clips"),
             IO.String.Output(display_name="report")],
            ["face", "small face", "face fix", "face detailer", "adetailer", "h3", "refine", "mask"],
            input_list=False)

    @classmethod
    def execute(cls, model, vae, clip, images, sampler, sigmas, prompt, seed, refine_size, context, max_face, group_size,
                paste, grow, feather, masks=None, lead_masks=None, references=None) -> IO.NodeOutput:
        from comfy.model_management import throw_exception_if_processing_interrupted
        from comfy.utils import ProgressBar

        n, height, width = images.shape[:3]
        leads = {i: plain(m) for i, m in numbered(lead_masks).items()}
        refs = numbered(references)
        masks = None if masks is None else plain(masks)
        for m in [*leads.values(), *([] if masks is None else [masks])]:
            if m.shape[0] != n:
                raise ValueError(f"Small Face Refine: {n} frames, but {m.shape[0]} masks")
        start = time.perf_counter()
        shots = shot_starts(images)
        runs, keep = [], None
        for i, m in sorted(leads.items()):
            labels, regions = split_faces(m, height, width)
            for r in link_faces(regions, shots):
                r.labels, r.lead = labels, i
                runs.append(r)
            m = F.interpolate(m[:, None].float(), size=(height, width), mode="nearest")[:, 0] > 0.5
            keep = m if keep is None else keep | m
        if masks is not None:
            if keep is not None:  # a lead left in the mask of everyone else is drawn once, from their picture
                masks = F.interpolate(masks[:, None].float(), size=(height, width), mode="nearest")[:, 0] * ~keep
            labels, regions = split_faces(masks, height, width)
            others = link_faces(regions, shots)
            for r in others:
                r.labels = labels
            runs += others
        chosen = [r for r in runs if r.lead or r.least <= max_face]
        text = report(runs, max_face)
        for i in sorted(set(refs) - set(leads)):
            text += f"\nreference {i} has no lead mask, so it was not used"
        log.info("H3 Small Face Refine: shots start at %s\n%s", shots, text)
        if not chosen:
            return IO.NodeOutput(images, torch.zeros(1, refine_size, refine_size, 3), text)

        planned = time.perf_counter()
        positive = clip.encode_from_tokens_scheduled(clip.tokenize(prompt))
        groups = group_runs(chosen, group_size, refine_size)
        conds = {}  # encoded up front: the text encoder would otherwise push the model out between crops
        for g in groups:
            lead = g[0].lead
            if lead in refs:
                shape = crop_window(g, height, width, refine_size, context)[2]
                if (lead, shape) not in conds:
                    conds[lead, shape] = reference_cond(clip, vae, refs[lead], shape)
        encoded = time.perf_counter()
        out = images.clone()
        bar = ProgressBar(len(groups))
        clips, rows, at = [], [], 0
        for i, group in enumerate(groups):
            throw_exception_if_processing_interrupted()
            drawn, row = refine_group(
                out, group, height, width,
                lambda crops, area, s=seed + i, lead=group[0].lead: redraw(
                    model, vae, conds.get((lead, tuple(crops.shape[1:3])), positive), crops, area, sampler, sigmas, s),
                refine_size, paste, grow, feather, context, None if group[0].lead else keep)
            clips.append(drawn)
            rows.append(f"crop {i + 1}: {row}; face_clips frames {at}-{at + len(drawn) - 1}")
            at += len(drawn)
            bar.update(1)
        log.info("H3 Small Face Refine: plan %.0f s, prompt %.0f s, %d crops %.0f s", planned - start, encoded - planned,
                 len(groups), time.perf_counter() - encoded)
        return IO.NodeOutput(out, join_clips(clips), "\n".join([text, "", *rows]))


NODES = [H3FaceRefine]
