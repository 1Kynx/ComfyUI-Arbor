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


def crop_payload(payload: dict, box) -> dict:
    """The H3 payload of one tile: guides cropped to it; the layout is left for the model to rebuild."""
    y0, y1, x0, x1 = box
    keyframes = []
    for kf in payload.get("keyframes") or []:
        kf = dict(kf)
        if kf.get("latent") is not None:
            kf["latent"] = kf["latent"][..., y0:y1, x0:x1]
        keyframes.append(kf)
    out = {k: v for k, v in payload.items() if k != "layout"}
    if payload.get("keyframes") is not None:
        out["keyframes"] = keyframes
    # same order as MiniMaxH3._cond_latents: keyframes, then references (whole: they have their own canvas)
    out["cond_video_latents"] = ([kf["latent"] for kf in keyframes if kf.get("latent") is not None]
                                 + [r["latent"] for r in payload.get("refs") or [] if "latent" in r])
    return out


def make_wrapper(tiles_y: int, tiles_x: int, overlap: int, feather: int, previous=None):
    """model_function_wrapper: run each model call tile by tile and blend the denoised predictions."""
    from comfy.model_management import throw_exception_if_processing_interrupted
    from comfy.utils import pack_latents, unpack_latents
    announced = set()

    def run(apply_model, x, t, c, args):
        if previous is not None:
            return previous(apply_model, {**args, "input": x, "timestep": t, "c": c})
        return apply_model(x, t, **c)

    def wrapper(apply_model, args):
        x, t, c = args["input"], args["timestep"], args["c"]
        shapes = c.get("latent_shapes")
        if shapes is None or len(shapes) < 2:
            return run(apply_model, x, t, c, args)
        streams = unpack_latents(x, shapes)
        video = streams[0]
        h, w = video.shape[-2:]
        boxes = plan_tiles(h, w, tiles_y, tiles_x, overlap)
        if (h, w) not in announced:
            announced.add((h, w))
            log.info("H3 Tiled Refine: %dx%d px in %d tiles of up to %dx%d px", w * 16, h * 16, len(boxes),
                     max(b[3] - b[2] for b in boxes) * 16, max(b[1] - b[0] for b in boxes) * 16)
        if len(boxes) == 1:
            return run(apply_model, x, t, c, args)

        out_v = torch.zeros_like(video, dtype=torch.float32)
        weight = torch.zeros(h, w, device=video.device)
        rest = [torch.zeros_like(s, dtype=torch.float32) for s in streams[1:]]
        for box in boxes:
            throw_exception_if_processing_interrupted()  # a step is several model calls: let Cancel in between
            y0, y1, x0, x1 = box
            xt, tshapes = pack_latents([video[..., y0:y1, x0:x1]] + list(streams[1:]))
            ct = dict(c)
            ct["latent_shapes"] = tshapes
            if isinstance(c.get("minimax_payload"), dict):
                ct["minimax_payload"] = crop_payload(c["minimax_payload"], box)
            if torch.is_tensor(c.get("denoise_mask")):
                ct["denoise_mask"] = c["denoise_mask"][..., y0:y1, x0:x1]
            pred = unpack_latents(run(apply_model, xt, t, ct, args), tshapes)
            wt = tile_weights(box, h, w, feather).to(video.device)
            out_v[..., y0:y1, x0:x1] += pred[0].float() * wt
            weight[y0:y1, x0:x1] += wt
            for acc, p in zip(rest, pred[1:]):
                acc += p.float()  # audio is shared by every tile: average its predictions
            del pred, xt, ct
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
                          tooltip="Pixels neighbouring tiles share; predictions are blended there")],
            [IO.Model.Output(display_name="model")],
            ["h3 tiled", "tiled diffusion", "multidiffusion", "tiled sampling", "low vram", "refine", "upscale"],
            input_list=False)

    @classmethod
    def execute(cls, model, tiles_x, tiles_y, overlap) -> IO.NodeOutput:
        if type(model.model).__name__ != "MiniMaxH3":
            raise ValueError(f"Tiled Refine for MiniMax H3: needs a MiniMax H3 model, got {type(model.model).__name__}")
        ov = max(0, int(overlap) // 16)
        ov += ov % 2
        if (tiles_x != 1 or tiles_y != 1) and not getattr(model, "is_dynamic", lambda: True)():
            log.warning("H3 Tiled Refine: dynamic VRAM is off, so every tile streams the weights again — "
                        "tiling saves memory but runs slower in this mode")
        m = model.clone()
        previous = m.model_options.get("model_function_wrapper")
        m.set_model_unet_function_wrapper(make_wrapper(int(tiles_y), int(tiles_x), ov, ov, previous))
        return IO.NodeOutput(m)


NODES = [H3TiledRefine, H3AddGuideFrames]
