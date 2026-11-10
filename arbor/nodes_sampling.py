"""Sampling helpers for MiniMax H3: re-sample an existing video close to the original, with less memory.

- **H3 Add Guide Frames** anchors chosen frames of the original video at the same frames of the target, one
  single-frame guide each (core "Add Guide for MiniMax H3" once per frame, in one node). A single-frame guide
  costs one latent frame of attention; a whole-clip guide doubles the sequence.
- **H3 Tiled Refine** samples the video in overlapping spatial tiles that each keep the whole timeline, blended
  at every step, so a step only holds one tile's tokens.
"""

import logging
import math

import torch
import torch.nn.functional as F

from . import tree as T
from .common import IO, schema
from .media import is_video

CAT_SAMPLING = "Arbor/Sampling"
log = logging.getLogger("Arbor")

# H3's native canvas (768 x 1344 px) in latent pixels (1/16), +10% for the overlap: auto-sized tiles stay
# within it (2K portrait = 2x2, measured closer to the original than untiled)
NATIVE_LATENT_AREA = round((768 // 16) * (1344 // 16) * 1.1)


# ======================================================================= Add Guide Frames

def guide_indices(spec, n: int) -> list[int]:
    """Frames of an n-frame clip, Batch Pick syntax, in order and without repeats; out of range is an error."""
    try:
        idx = T.parse_indices(spec, n)
    except ValueError as e:
        raise ValueError(f"H3 Add Guide Frames: {e}") from None
    out = []
    for i in idx:
        if not -n <= i < n:
            raise IndexError(f"H3 Add Guide Frames: frame {i} is outside the {n}-frame video")
        if i % n not in out:
            out.append(i % n)
    return out


class H3AddGuideFrames(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_H3AddGuideFrames", "Add Guide Frames for MiniMax H3", CAT_SAMPLING,
            "Anchor the listed frames of a video, each as its own single-frame guide, at the same frames of the "
            "H3 target — one core 'Add Guide for MiniMax H3' per frame, in one node. Each guide costs one latent "
            "frame of attention (9 on a 124-frame video: +24%); a whole-clip guide costs +100%.",
            [IO.Conditioning.Input("positive"),
             IO.Vae.Input("vae", tooltip="The H3 video VAE"),
             IO.Latent.Input("latent", tooltip="The H3 AV latent being sampled"),
             IO.MultiType.Input(IO.Image.Input("images", tooltip="The original video's frames, or the video"),
                                types=[IO.Video]),
             IO.String.Input("frames", default="0, 17::17, -1",
                             tooltip="Frames to anchor, e.g. 0, 17::17, -1 (every 17th and the last)")],
            [IO.Conditioning.Output(display_name="positive"), IO.Int.Output(display_name="count")],
            ["h3 guide", "keyframes", "guide frames", "anchor frames", "add guide", "refine", "video to video"],
            input_list=False)

    @classmethod
    def execute(cls, positive, vae, latent, images, frames) -> IO.NodeOutput:
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3AddGuide

        if is_video(images):
            images = images.get_components().images
        picked = guide_indices(frames, int(images.shape[0]))
        if not picked:
            raise ValueError("H3 Add Guide Frames: no frames picked")
        for i in picked:
            positive = MiniMaxH3AddGuide.execute(positive, latent, i, vae=vae, image=images[i:i + 1]).result[0]
        return IO.NodeOutput(positive, len(picked))


# ======================================================================= Tiled Refine

def _spans(size: int, n: int, overlap: int) -> list[tuple[int, int]]:
    """n spans of even length covering 0..size (latent units), neighbours sharing ~overlap."""
    if n <= 1 or size <= 2:
        return [(0, size)]
    length = math.ceil((size + (n - 1) * overlap) / n)
    length = min(size, length + length % 2)  # the DiT works on 2x2 patches
    starts = [round(i * (size - length) / (n - 1)) for i in range(n)]
    out = []
    for s in starts:
        s -= s % 2
        span = (s, min(size, s + length))
        if span not in out:
            out.append(span)
    return out


def auto_grid(h: int, w: int, overlap: int) -> tuple[int, int]:
    """(tiles down, tiles across): the fewest tiles that keep every tile within H3's native canvas."""
    best = None
    for ty in range(1, 7):
        for tx in range(1, 7):
            th = max(b - a for a, b in _spans(h, ty, overlap))
            tw = max(b - a for a, b in _spans(w, tx, overlap))
            too_big = th * tw > NATIVE_LATENT_AREA or max(th, tw) > 2 * min(th, tw)  # H3 canvases are <= 1:1.75
            if too_big and (ty, tx) != (6, 6):
                continue
            key = (ty * tx, abs(math.log(th / tw)))  # fewest tiles, then the least stretched (H3 trains near 1:1.75)
            if best is None or key < best[0]:
                best = (key, (ty, tx))
    return best[1]


def plan_tiles(h: int, w: int, tiles_y: int, tiles_x: int, overlap: int) -> list[tuple[int, int, int, int]]:
    """(y0, y1, x0, x1) latent boxes, row by row; 0 tiles on both axes = auto."""
    if tiles_y <= 0 or tiles_x <= 0:
        ay, ax = auto_grid(h, w, overlap)
        tiles_y, tiles_x = tiles_y if tiles_y > 0 else ay, tiles_x if tiles_x > 0 else ax
    return [(y0, y1, x0, x1) for y0, y1 in _spans(h, tiles_y, overlap) for x0, x1 in _spans(w, tiles_x, overlap)]


def _ramp(lo: int, hi: int, size: int, feather: int) -> torch.Tensor:
    """Blend weights along one axis of a tile, rising over `feather` from edges that are not the image border."""
    n = hi - lo
    r = torch.ones(n)
    if feather <= 0:
        return r
    d = torch.arange(n, dtype=torch.float32)
    if lo > 0:
        r = torch.minimum(r, (d + 1) / (feather + 1))
    if hi < size:
        r = torch.minimum(r, (n - d) / (feather + 1))
    return r


def tile_weights(box, h: int, w: int, feather: int) -> torch.Tensor:
    y0, y1, x0, x1 = box
    return _ramp(y0, y1, h, feather)[:, None] * _ramp(x0, x1, w, feather)[None, :]


SAME_FRAMING = 0.03  # a reference video this close to the video's shape, and as long, shows the same frame


def framed_like(ref: dict, latent_t: int, h: int, w: int) -> bool:
    """Whether a reference video shows the same frame as the video being refined: as long, and the same shape within
    3%. That is how the IC refiner and edits give their source, and such a reference is cropped to each tile like the
    video. A reference of another shape or length (a motion, camera or style reference) goes to every tile whole."""
    z = ref.get("latent")
    if ref.get("kind") not in ("video", "video_audio") or z is None or z.dim() != 5:
        return False
    return z.shape[2] == latent_t and abs((z.shape[4] / z.shape[3]) / (w / h) - 1) < SAME_FRAMING


def ref_box(ref: dict, box, h: int, w: int) -> tuple[int, int, int, int]:
    """A tile's box (on the video's latent grid of h x w) on a same-framed reference's own grid, out to whole 2 x 2
    patches: (y0, y1, x0, x1)."""
    rh, rw = ref["latent"].shape[3], ref["latent"].shape[4]
    y0, y1, x0, x1 = box
    return (2 * math.floor(y0 * rh / h / 2), min(rh, 2 * math.ceil(y1 * rh / h / 2)),
            2 * math.floor(x0 * rw / w / 2), min(rw, 2 * math.ceil(x1 * rw / w / 2)))


def crop_ref(ref: dict, box, h: int, w: int) -> dict:
    """A same-framed reference video cut to one tile."""
    a, b, c, d = ref_box(ref, box, h, w)
    out = dict(ref)
    out["latent"] = ref["latent"][..., a:b, c:d]
    out["latent_h"], out["latent_w"] = b - a, d - c
    return out


def ref_place(ref: dict, box, h: int, w: int) -> tuple[float, float, float, float]:
    """Where a same-framed reference cut to a tile lies, as fractions of the tile: (y0, y1, x0, x1). Its grid is
    coarser than the video's and the cut goes out to whole patches of it, so it reaches a little past the tile:
    0 to 1.05 of a 2K tile, from a 768p draft."""
    rh, rw = ref["latent"].shape[3], ref["latent"].shape[4]
    a, b, c, d = ref_box(ref, box, h, w)
    y0, y1, x0, x1 = box
    return ((a * h / rh - y0) / (y1 - y0), (b * h / rh - y0) / (y1 - y0),
            (c * w / rw - x0) / (x1 - x0), (d * w / rw - x0) / (x1 - x0))


def crop_payload(payload: dict, box, guided: bool = True, full=None) -> dict:
    """The H3 payload of one tile: guides cropped to it, or left out when not guided; with full (latent t, h, w of the
    whole video), a reference video framed like the video is cropped to the tile too. The layout is left for the model
    to rebuild."""
    y0, y1, x0, x1 = box
    keyframes = []
    for kf in payload.get("keyframes") or []:
        kf = dict(kf)
        if kf.get("latent") is not None:
            if guided:
                kf["latent"] = kf["latent"][..., y0:y1, x0:x1]
            else:
                del kf["latent"]
                if kf.get("audio_latent") is None:
                    continue
        keyframes.append(kf)
    out = {k: v for k, v in payload.items() if k != "layout"}
    if payload.get("keyframes") is not None:
        out["keyframes"] = keyframes
    refs = payload.get("refs") or []
    if full is not None and refs:
        t, h, w = full
        refs = [crop_ref(r, box, h, w) if framed_like(r, t, h, w) else r for r in refs]
        out["refs"] = refs
    # same order as MiniMaxH3._cond_latents: keyframes, then references (whole, but for one framed like the video:
    # the others have a canvas of their own)
    out["cond_video_latents"] = ([kf["latent"] for kf in keyframes if kf.get("latent") is not None]
                                 + [r["latent"] for r in refs if "latent" in r])
    return out


# ----------------------------------------------------------------------- what the text says of a reference video
# The text encoder reads a reference video too: two frames a second, as blocks of picture tokens in the prompt's own
# rows, one token per 32 px. They go to every tile whole, though a tile sees only its part of that video, and are a
# good part of a tile's rows (a 5 s draft: 6000 of 59000). A tile keeps the tokens over its own part.

QWEN_FPS = 2          # frames a second the text encoder is shown (MiniMaxH3ReferenceToVideo)
QWEN_PAIR = 2         # frames in one block of picture tokens
VISION_TAG = 0        # payload text_token_tags: a picture token, or the marker either side of a block


def ref_frames(latent_t: int) -> int:
    """Pixel frames of a reference video with this many latent frames (H3 clips are 17k + 5 frames)."""
    return 5 if latent_t <= 2 else (latent_t - 2) // 5 * 17 + 5


def text_keep(tags: torch.Tensor, refs: list, box, full) -> torch.Tensor | None:
    """Which rows of the text a tile keeps: all of them but the picture tokens of same-framed reference videos that
    lie outside the tile. None if nothing is left out, or if the blocks are not laid out as expected (then the text
    stays whole)."""
    t, h, w = full
    flat = (tags.reshape(-1) == VISION_TAG).long()
    edge = torch.diff(flat, prepend=flat.new_zeros(1), append=flat.new_zeros(1))
    runs = list(zip((edge == 1).nonzero().flatten().tolist(), (edge == -1).nonzero().flatten().tolist()))
    owners = []  # the reference each block belongs to, in the order the tokenizer writes them
    for i, r in enumerate(refs):
        if r.get("kind") == "image":
            owners.append(i)
        elif r.get("kind") in ("video", "video_audio"):
            shown = math.ceil(ref_frames(r["latent_t"]) / (24 // QWEN_FPS))
            owners += [i] * math.ceil(shown / QWEN_PAIR)
    if len(owners) != len(runs):
        return None
    keep = torch.ones(flat.numel(), dtype=torch.bool)
    for (start, stop), i in zip(runs, owners):
        r = refs[i]
        if not framed_like(r, t, h, w):
            continue
        gh, gw = r["latent"].shape[3] // 2, r["latent"].shape[4] // 2
        if stop - start != gh * gw + 2:  # the block, and a marker either side
            return None
        a, b, c, d = ref_box(r, box, h, w)
        grid = torch.zeros(gh, gw, dtype=torch.bool)
        grid[a // 2:b // 2, c // 2:d // 2] = True
        keep[start + 1:stop - 1] = grid.reshape(-1)
    return None if bool(keep.all()) else keep


# ----------------------------------------------------------------------- a tile's own packing
# H3 packs one sequence: text, guides, references, audio, video. Each row has its own (time, row, column) position, so
# rows can be left out, or given the position of where they really lie, and the model reads them as that. Two things
# use it: a guide mask leaves out the guide rows outside it (a guide is a second copy of the clip's tokens), and a
# reference cut to a tile is put where its patches are.
#
# Two pieces of H3 make this work: the packed layout (an object the model takes from the payload when its shape
# matches) and the guide rows, which a small filter on the model picks from the kept tokens. If H3 changes either,
# both turn off with a warning.

KEEP = "arbor_guide_keep"  # payload key: which guide rows the model keeps
LAYOUT_FIELDS = {"seq_len", "position_ids", "img_pos", "img_update", "audio_pos", "audio_update", "signature",
                 "segments"}
PICTURES = ("cond", "ref_img", "video")       # segments of picture rows; the model embeds them in this order
SOUND = ("cond_audio", "ref_audio", "audio")


def mask_grid(mask, h: int, w: int) -> torch.Tensor:
    """[frames, H, W] mask -> [frames, h, w] uint8 on the latent grid: 1 where any pixel of the cell is in it."""
    out = [(F.adaptive_max_pool2d(mask[i:i + 8].float()[:, None], (h, w))[:, 0] > 0.5).to(torch.uint8)
           for i in range(0, mask.shape[0], 8)]  # a few frames at a time: a 2K clip at once is gigabytes
    return torch.cat(out)


def guide_keep(grid: torch.Tensor, latent, frame: int, box, margin: int = 1) -> torch.Tensor:
    """Which tokens of one guide stay, in the model's row order (time, row, column): those the mask touches in the
    pixel frames of their latent frame, grown by `margin` tokens."""
    from comfy.ldm.minimax.model import FRAME_PER_TOKEN
    y0, y1, x0, x1 = box
    g = grid[:, y0:y1, x0:x1]
    last = g.shape[0] - 1
    frames, p = [], int(frame)
    for j in range(latent.shape[2]):
        n = FRAME_PER_TOKEN[j % len(FRAME_PER_TOKEN)]
        lo = min(max(p, 0), last)
        frames.append(g[lo:min(max(p + n, lo + 1), last + 1)].amax(0))
        p += n
    m = F.max_pool2d(torch.stack(frames).float()[:, None], 2, 2, ceil_mode=True)  # 2x2 latent cells per token
    if margin > 0:
        m = F.max_pool2d(m, 2 * margin + 1, 1, margin)
    return m.reshape(-1) > 0.5


def rows_of(latent: torch.Tensor) -> int:
    """Rows a conditioning latent takes in the packed sequence."""
    return latent.shape[2] * (latent.shape[3] // 2) * (latent.shape[4] // 2)


def _axis(size: int, area: float, lo: float, hi: float, n: int) -> torch.Tensor:
    """Positions along one axis of n rows spread over lo..hi (fractions) of a canvas `size` latents long: H3 puts a
    canvas of any size on the same span about 16, and a row at where it starts. 0..1 in size / 2 rows is the
    canvas's own grid."""
    ratio = size / area
    return ((1 - ratio) / 2 + ratio * (lo + torch.arange(n, dtype=torch.float64) / n * (hi - lo))) * 32


def place(layout, latents: list, places: list, th: int, tw: int) -> None:
    """Give conditioning the positions of where it lies on a canvas of th x tw latents, in place: places has
    (y0, y1, x0, x1) as fractions of the canvas, or None, per conditioning latent. H3 lays a reference out as if it
    showed exactly the canvas; one cut to a tile shows a little more, and without this would sit up to 5% off the
    tile it is the source of."""
    conds = [s for s in layout.segments if s[2] in ("cond", "ref_img")]
    if len(conds) != len(places) or len(conds) != len(latents):
        raise ValueError("H3 conditioning rows do not match the conditioning")
    area = math.sqrt(th * tw)
    for (a, b, _), z, at in zip(conds, latents, places):
        if at is None:
            continue
        t, nh, nw = z.shape[2], z.shape[3] // 2, z.shape[4] // 2
        if b - a != t * nh * nw:
            raise ValueError("an H3 reference does not have the rows of its latent")
        ys, xs = torch.meshgrid(_axis(th, area, at[0], at[1], nh), _axis(tw, area, at[2], at[3], nw), indexing="ij")
        layout.position_ids[a:b, 1:] = torch.stack([ys.reshape(-1), xs.reshape(-1)], -1).repeat(t, 1)


def repack(layout, keeps: list):
    """A copy of an H3 packed layout with rows of its picture conditioning left out: keeps has one entry per guide and
    reference picture or video, in the layout's order, the rows kept (one bool per row, None for all of them). Every
    row left keeps its position. Returns the layout and which conditioning still has rows, as indices into keeps."""
    import copy
    if set(vars(layout)) != LAYOUT_FIELDS:
        raise ValueError(f"unknown H3 layout fields {sorted(set(vars(layout)) ^ LAYOUT_FIELDS)}")
    conds = [i for i, s in enumerate(layout.segments) if s[2] in ("cond", "ref_img")]
    if len(conds) != len(keeps) or any(
            k is not None and layout.segments[i][1] - layout.segments[i][0] != k.numel() for i, k in zip(conds, keeps)):
        raise ValueError("H3 conditioning rows do not match the conditioning")
    which = {i: j for j, i in enumerate(conds)}
    rows, segments, left, off = [], [], [], 0
    for i, (a, b, kind) in enumerate(layout.segments):
        r = torch.arange(a, b)
        j = which.get(i)
        if j is not None:
            if keeps[j] is not None:
                r = r[keeps[j]]
            if len(r) == 0:
                continue  # a guide the mask leaves nothing of
            left.append(j)
        rows.append(r)
        segments.append((off, off + len(r), kind))
        off += len(r)
    new = copy.copy(layout)
    new.seq_len = off
    new.position_ids = layout.position_ids[torch.cat(rows)]
    new.segments = segments
    for pos, update, kinds in (("img_pos", "img_update", PICTURES), ("audio_pos", "audio_update", SOUND)):
        mine = [s for s in segments if s[2] in kinds]
        setattr(new, pos, torch.cat([torch.arange(a, b) for a, b, _ in mine]))
        setattr(new, update, torch.cat([torch.full((b - a,), kind == kinds[-1], dtype=torch.bool) for a, b, kind in mine]))
    return new, left


def install_row_filter(diffusion_model) -> bool:
    """Let the model drop guide rows a payload's KEEP leaves out. Once per model; False if H3 has no such step."""
    if getattr(diffusion_model, "_arbor_row_filter", False):
        return True
    original = getattr(diffusion_model, "_cond_video_rows", None)
    if original is None:
        return False

    def cond_video_rows(payload, device):
        rows = original(payload, device)
        keep = payload.get(KEEP)
        if keep is None or rows is None:
            return rows
        if keep.numel() != rows.shape[0]:
            raise RuntimeError(f"H3 Tiled Refine: guide mask covers {keep.numel()} rows, the guides have "
                               f"{rows.shape[0]}")
        return rows[keep.to(rows.device)]
    diffusion_model._cond_video_rows = cond_video_rows
    diffusion_model._arbor_row_filter = True
    return True


def packed(payload: dict, text_len: int, video_shape, audio_t: int, keeps: list, places: list | None = None) -> dict:
    """The payload with a layout of its own: conditioning put where it lies (place) and rows left out (repack). One
    entry per conditioning latent, in the payload's order."""
    from comfy.ldm.minimax.model import PackedLayout
    _, _, lt, lh, lw = video_shape
    layout = PackedLayout(text_len, lt, lh + lh % 2, lw + lw % 2, audio_t, keyframes=payload.get("keyframes"),
                          refs=payload.get("refs"))
    latents = payload["cond_video_latents"]
    if places is not None and any(p is not None for p in places):
        place(layout, latents, places, lh + lh % 2, lw + lw % 2)
    out = dict(payload)
    out["layout"], left = repack(layout, keeps)
    out["cond_video_latents"] = [latents[j] for j in left]
    if any(keeps[j] is not None for j in left):
        out[KEEP] = torch.cat([torch.ones(rows_of(latents[j]), dtype=torch.bool) if keeps[j] is None else keeps[j]
                               for j in left])
    return out


def make_wrapper(tiles_y: int, tiles_x: int, overlap: int, feather: int, previous=None, guide_mask=None,
                 margin: int = 1, text_crop: bool = True, exact_refs: bool = True):
    """model_function_wrapper: run each model call tile by tile and blend the denoised predictions. With a guide mask,
    only the guide tokens inside it go in: a tile it misses runs without the guide, a tile it touches with part of
    it. A reference video framed like the video is cut to each tile, with what the text says of it (text_crop), and
    put at the positions of where it lies in the tile (exact_refs)."""
    from comfy.model_management import throw_exception_if_processing_interrupted
    from comfy.utils import pack_latents, unpack_latents
    announced = set()
    grids = {}
    state = {"masking": guide_mask is not None, "packing": True, "text": text_crop}

    def run(apply_model, x, t, c, args):
        if previous is not None:
            return previous(apply_model, {**args, "input": x, "timestep": t, "c": c})
        return apply_model(x, t, **c)

    def say(key, message, *values):
        if key not in announced:
            announced.add(key)
            log.info("H3 Tiled Refine: " + message, *values)

    def tile_conds(c, box, video_shape, audio_t, counts):
        """What one tile's conds differ in from the whole video's: its payload, and its text if that was cropped."""
        payload = c.get("minimax_payload")
        if not isinstance(payload, dict):
            return {}
        h, w = c["_full_hw"]
        full = (video_shape[2], h, w)
        whole = tuple(video_shape[-2:]) == (h, w)
        refs = payload.get("refs") or []
        framed = [framed_like(r, *full) for r in refs]
        tile = payload if whole else crop_payload(payload, box, full=full)
        out = {"minimax_payload": tile}
        text = c.get("c_crossattn")
        if any(framed) and not whole:
            videos = [f for r, f in zip(refs, framed) if r.get("kind") in ("video", "video_audio")]
            say("refs", "<Video %s> has the video's framing and is cropped to each tile",
                ">, <Video ".join(str(i + 1) for i, f in enumerate(videos) if f))  # numbered as the prompt does
            tags = payload.get("text_token_tags")
            if state["text"] and torch.is_tensor(tags) and torch.is_tensor(text) and tags.numel() == text.shape[1]:
                keep = text_keep(tags.cpu(), refs, box, full)
                if keep is not None:
                    text = text[:, keep.to(text.device)]
                    tile["text_token_tags"] = tags.reshape(-1)[keep.to(tags.device)].reshape(*tags.shape[:-1], -1)
                    out["c_crossattn"] = text
                    counts[2] += int(keep.sum())
                    counts[3] += keep.numel()
        if not state["packing"] or not torch.is_tensor(text):
            return out
        try:
            keyframes = [kf for kf in tile.get("keyframes") or [] if kf.get("latent") is not None]
            keeps = [None] * len(tile.get("cond_video_latents") or [])
            if state["masking"] and keyframes:
                if (h, w) not in grids:
                    grids[(h, w)] = mask_grid(guide_mask, h, w)
                for j, kf in enumerate(keyframes):
                    k = guide_keep(grids[(h, w)], kf["latent"], kf.get("resolved_frame_index", 0), box, margin)
                    counts[0] += int(k.sum())
                    counts[1] += k.numel()
                    keeps[j] = None if bool(k.all()) else k
            places = [None] * len(keyframes) + [ref_place(r, box, h, w) if f and exact_refs and not whole else None
                                                for r, f in zip(refs, framed) if "latent" in r]
            if len(places) != len(keeps):
                raise ValueError("H3 conditioning does not match its latents")
            placed = any(p is not None for p in places)
            if any(k is not None for k in keeps) or placed:
                if all(k is not None and not bool(k.any()) for k in keeps[:len(keyframes)]) and not placed:
                    out["minimax_payload"] = crop_payload(tile, (0, video_shape[3], 0, video_shape[4]), False)
                else:
                    out["minimax_payload"] = packed(tile, int(text.shape[1]), video_shape, audio_t, keeps, places)
        except Exception as e:  # H3 changed under us: refine with the stock packing rather than fail
            log.warning("H3 Tiled Refine: the tiles' own packing is off, every tile keeps the whole guide (%s)", e)
            state["packing"] = False
        return out

    def wrapper(apply_model, args):
        x, t, c = args["input"], args["timestep"], args["c"]
        shapes = c.get("latent_shapes")
        if shapes is None or len(shapes) < 2:
            return run(apply_model, x, t, c, args)
        streams = unpack_latents(x, shapes)
        video = streams[0]
        h, w = video.shape[-2:]
        boxes = plan_tiles(h, w, tiles_y, tiles_x, overlap)
        counts = [0, 0, 0, 0]  # guide tokens kept, of; text rows kept, of
        c_full = {**c, "_full_hw": (h, w)}
        audio_t = int(shapes[1][-1])

        def report():
            say((h, w), "%dx%d px in %d tiles of up to %dx%d px%s%s", w * 16, h * 16, len(boxes),
                max(b[3] - b[2] for b in boxes) * 16, max(b[1] - b[0] for b in boxes) * 16,
                f", guide mask keeps {counts[0] / counts[1]:.0%} of the guide tokens" if counts[1] else "",
                f", a tile keeps {counts[2] / counts[3]:.0%} of the text rows" if counts[3] else "")

        if len(boxes) == 1:
            conds = tile_conds(c_full, boxes[0], tuple(video.shape), audio_t, counts)
            report()
            return run(apply_model, x, t, {**c, **conds}, args)

        out_v = torch.zeros_like(video, dtype=torch.float32)
        weight = torch.zeros(h, w, device=video.device)
        rest = [torch.zeros_like(s, dtype=torch.float32) for s in streams[1:]]
        for box in boxes:
            throw_exception_if_processing_interrupted()  # a step is several model calls: let Cancel in between
            y0, y1, x0, x1 = box
            tile = video[..., y0:y1, x0:x1]
            xt, tshapes = pack_latents([tile] + list(streams[1:]))
            ct = dict(c)
            ct["latent_shapes"] = tshapes
            ct.update(tile_conds(c_full, box, tuple(tile.shape), audio_t, counts))
            if torch.is_tensor(c.get("denoise_mask")):
                ct["denoise_mask"] = c["denoise_mask"][..., y0:y1, x0:x1]
            pred = unpack_latents(run(apply_model, xt, t, ct, args), tshapes)
            wt = tile_weights(box, h, w, feather).to(video.device)
            out_v[..., y0:y1, x0:x1] += pred[0].float() * wt
            weight[y0:y1, x0:x1] += wt
            for acc, p in zip(rest, pred[1:]):
                acc += p.float()  # audio is shared by every tile: average its predictions
            del pred, xt, ct
        report()
        out_v /= weight
        rest = [r / len(boxes) for r in rest]
        return pack_latents([out_v.to(video.dtype)] + [r.to(s.dtype) for r, s in zip(rest, streams[1:])])[0]

    return wrapper


class H3TiledRefine(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_H3TiledRefine", "Tiled Refine for MiniMax H3", CAT_SAMPLING,
            "Lower an H3 step's memory by sampling the video in overlapping spatial tiles, blended at every "
            "step. Each tile keeps all frames (the video is never split in time); guide frames, denoise masks and "
            "a reference video of the same frame are cropped to each tile. For low-denoise refinement of an "
            "existing video; 1x1 = off.",
            [IO.Model.Input("model", tooltip="A MiniMax H3 model (after LoRAs and attention patches)"),
             IO.Int.Input("tiles_x", default=0, min=0, max=6,
                          tooltip="Tiles across; 0 = auto (tiles about H3's native 768 x 1344 size)"),
             IO.Int.Input("tiles_y", default=0, min=0, max=6, tooltip="Tiles down; 0 = auto"),
             IO.Int.Input("overlap", default=128, min=0, max=1024, step=32,
                          tooltip="Pixels neighbouring tiles share; predictions are blended there"),
             IO.Mask.Input("guide_mask", optional=True,
                           tooltip="Where the guide counts, frame by frame. Only the guide tokens inside it go in: "
                                   "the masked area follows the guide, the rest is redrawn freely (how freely "
                                   "depends on the start noise), and fewer tokens run faster. Not connected: the "
                                   "whole guide. Grow it with Grow Mask for more margin")],
            [IO.Model.Output(display_name="model")],
            ["h3 tiled", "tiled diffusion", "multidiffusion", "tiled sampling", "low vram", "refine", "upscale"],
            input_list=False)

    @classmethod
    def execute(cls, model, tiles_x, tiles_y, overlap, guide_mask=None) -> IO.NodeOutput:
        if type(model.model).__name__ != "MiniMaxH3":
            raise ValueError(f"Tiled Refine for MiniMax H3: needs a MiniMax H3 model, got {type(model.model).__name__}")
        ov = max(0, int(overlap) // 16)
        ov += ov % 2
        if (tiles_x != 1 or tiles_y != 1) and not getattr(model, "is_dynamic", lambda: True)():
            log.warning("H3 Tiled Refine: dynamic VRAM is off, so every tile streams the weights again — "
                        "tiling saves memory but runs slower in this mode")
        m = model.clone()
        previous = m.model_options.get("model_function_wrapper")
        mask = None if guide_mask is None else (guide_mask[None] if guide_mask.dim() == 2 else guide_mask).cpu()
        if mask is not None and not install_row_filter(m.model.diffusion_model):
            log.warning("H3 Tiled Refine: this H3 build can't take a guide mask; every tile keeps the whole guide")
            mask = None
        m.set_model_unet_function_wrapper(make_wrapper(int(tiles_y), int(tiles_x), ov, ov, previous, mask))
        return IO.NodeOutput(m)


NODES = [H3TiledRefine, H3AddGuideFrames]
