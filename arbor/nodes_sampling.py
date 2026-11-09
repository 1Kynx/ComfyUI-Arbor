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


def crop_ref(ref: dict, box, h: int, w: int) -> dict:
    """A same-framed reference video cut to one tile: the box (on the video's latent grid of h x w) taken to the
    reference's own grid, out to whole 2 x 2 patches."""
    z = ref["latent"]
    rh, rw = z.shape[3], z.shape[4]
    y0, y1, x0, x1 = box
    a, b = 2 * math.floor(y0 * rh / h / 2), min(rh, 2 * math.ceil(y1 * rh / h / 2))
    c, d = 2 * math.floor(x0 * rw / w / 2), min(rw, 2 * math.ceil(x1 * rw / w / 2))
    out = dict(ref)
    out["latent"] = z[..., a:b, c:d]
    out["latent_h"], out["latent_w"] = b - a, d - c
    return out


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


# ----------------------------------------------------------------------- guide mask
# A guide is a second copy of the clip's tokens, each with its own (time, row, column) position, packed before the
# target. Left-out tokens leave that place unguided; the rest still anchor it. Two pieces of H3 make this work: the
# packed layout (an object the model takes from the payload when its shape matches) and the guide rows, which a
# small filter on the model picks from the kept tokens. If H3 changes either, masking turns off with a warning.

KEEP = "arbor_guide_keep"  # payload key: which guide rows the model keeps
LAYOUT_FIELDS = {"seq_len", "position_ids", "img_pos", "img_update", "audio_pos", "audio_update", "signature",
                 "segments"}


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


def prune_layout(layout, keeps: list):
    """A copy of an H3 packed layout without the guide rows `keeps` leaves out (one bool per row, per guide)."""
    import copy
    if set(vars(layout)) != LAYOUT_FIELDS:
        raise ValueError(f"unknown H3 layout fields {sorted(set(vars(layout)) ^ LAYOUT_FIELDS)}")
    conds = [s for s in layout.segments if s[2] == "cond"]
    if len(conds) != len(keeps) or any(b - a != k.numel() for (a, b, _), k in zip(conds, keeps)):
        raise ValueError("H3 guide rows do not match the guides")
    keep = torch.ones(layout.seq_len, dtype=torch.bool)
    for (a, b, _), k in zip(conds, keeps):
        keep[a:b] = k
    new = copy.copy(layout)
    index = keep.long().cumsum(0) - 1
    new.seq_len = int(keep.sum())
    new.position_ids = layout.position_ids[keep]
    for pos, upd in (("img_pos", "img_update"), ("audio_pos", "audio_update")):
        kept = keep[getattr(layout, pos)]
        setattr(new, pos, index[getattr(layout, pos)[kept]])
        setattr(new, upd, getattr(layout, upd)[kept])
    segments, off = [], 0
    for a, b, kind in layout.segments:
        n = int(keep[a:b].sum())
        if n or kind != "cond":
            segments.append((off, off + n, kind))
            off += n
    new.segments = segments
    return new


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


def mask_payload(payload: dict, box, grid, text_len: int, video_shape, audio_t: int, margin: int = 1):
    """The tile payload with the guide tokens outside the mask left out: (payload, tokens kept, guide tokens)."""
    from comfy.ldm.minimax.model import PackedLayout
    keyframes = payload.get("keyframes") or []
    keeps = [guide_keep(grid, kf["latent"], kf.get("resolved_frame_index", 0), box, margin)
             for kf in keyframes if kf.get("latent") is not None]
    kept, total = sum(int(k.sum()) for k in keeps), sum(k.numel() for k in keeps)
    if kept == total:
        return payload, kept, total
    if kept == 0:
        return crop_payload(payload, box, False), 0, total
    _, _, lt, lh, lw = video_shape
    layout = PackedLayout(text_len, lt, lh + lh % 2, lw + lw % 2, audio_t, keyframes=keyframes,
                          refs=payload.get("refs"))
    out = dict(payload)
    out["layout"] = prune_layout(layout, keeps)
    refs = [r["latent"] for r in payload.get("refs") or [] if "latent" in r]
    out[KEEP] = torch.cat(keeps + [torch.ones(z.shape[2] * (z.shape[3] // 2) * (z.shape[4] // 2), dtype=torch.bool)
                                   for z in refs])
    return out, kept, total


def make_wrapper(tiles_y: int, tiles_x: int, overlap: int, feather: int, previous=None, guide_mask=None,
                 margin: int = 1):
    """model_function_wrapper: run each model call tile by tile and blend the denoised predictions. With a guide mask,
    only the guide tokens inside it go in: a tile it misses runs without the guide, a tile it touches with part of
    it."""
    from comfy.model_management import throw_exception_if_processing_interrupted
    from comfy.utils import pack_latents, unpack_latents
    announced = set()
    grids = {}
    state = {"masking": guide_mask is not None}

    def run(apply_model, x, t, c, args):
        if previous is not None:
            return previous(apply_model, {**args, "input": x, "timestep": t, "c": c})
        return apply_model(x, t, **c)

    def tile_payload(c, box, video_shape, audio_t, counts):
        payload = c.get("minimax_payload")
        if not isinstance(payload, dict):
            return payload
        full = (video_shape[2], *c["_full_hw"])
        cropped = crop_payload(payload, box, full=full) if video_shape[-2:] != c["_full_hw"] else payload
        videos = [r for r in payload.get("refs") or [] if r.get("kind") in ("video", "video_audio")]
        framed = [i + 1 for i, r in enumerate(videos) if framed_like(r, *full)]  # numbered as <Video N>
        if framed and video_shape[-2:] != c["_full_hw"] and "refs" not in announced:
            announced.add("refs")
            log.info("H3 Tiled Refine: <Video %s> has the video's framing and is cropped to each tile",
                     ">, <Video ".join(map(str, framed)))
        if not state["masking"]:
            return cropped
        try:
            h, w = c["_full_hw"]
            if (h, w) not in grids:
                grids[(h, w)] = mask_grid(guide_mask, h, w)
            out, kept, total = mask_payload(cropped, box, grids[(h, w)], int(c["c_crossattn"].shape[1]),
                                            video_shape, audio_t, margin)
        except Exception as e:  # H3 changed under us: refine with the whole guide rather than fail
            log.warning("H3 Tiled Refine: guide mask off, every tile keeps the whole guide (%s)", e)
            state["masking"] = False
            return cropped
        counts[0] += kept
        counts[1] += total
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
        counts = [0, 0]
        c_full = {**c, "_full_hw": (h, w)}
        audio_t = int(shapes[1][-1])

        def report():
            if (h, w) in announced:
                return
            announced.add((h, w))
            log.info("H3 Tiled Refine: %dx%d px in %d tiles of up to %dx%d px%s", w * 16, h * 16, len(boxes),
                     max(b[3] - b[2] for b in boxes) * 16, max(b[1] - b[0] for b in boxes) * 16,
                     f", guide mask keeps {counts[0] / counts[1]:.0%} of the guide tokens" if counts[1] else "")

        if len(boxes) == 1:
            payload = tile_payload(c_full, boxes[0], tuple(video.shape), audio_t, counts)
            report()
            return run(apply_model, x, t, {**c, "minimax_payload": payload} if payload is not None else c, args)

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
            if isinstance(c.get("minimax_payload"), dict):
                ct["minimax_payload"] = tile_payload(c_full, box, tuple(tile.shape), audio_t, counts)
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
            "step. Each tile keeps all frames (the video is never split in time); guide frames and denoise masks "
            "are cropped to each tile. For low-denoise refinement of an existing video; 1x1 = off.",
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
