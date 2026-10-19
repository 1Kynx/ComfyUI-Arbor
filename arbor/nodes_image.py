import math
import re

import torch

from .common import IO, CAT_IMAGE, to_tree
from .preview import save_temp, to_pil, is_image

MAX_SLIDES = 64


def _collect_images(value) -> list[torch.Tensor]:
    """Images from a socket value: a batch, a list of batches, or a tree."""
    out = []
    for v in to_tree(value).flat():
        if is_image(v):
            out.extend(v[i] for i in range(v.shape[0]))
    return out


class ImageSlider(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        images = IO.Autogrow.TemplatePrefix(
            IO.Image.Input("image", tooltip="Image or batch; every frame becomes a slide"),
            prefix="image", min=1, max=16)
        return IO.Schema(
            node_id="Arbor_ImageSlider",
            display_name="Image Slider",
            category=CAT_IMAGE,
            description="Compare any number of images of any size. Drag the slider to flip "
                        "through them, or switch to wipe mode for a before/after split.",
            search_aliases=["image compare", "compare", "before after", "ab test", "image viewer", "flipbook"],
            is_output_node=True,
            is_input_list=True,
            inputs=[IO.Autogrow.Input("images", template=images, optional=True)],
            outputs=[],
        )

    @classmethod
    def execute(cls, images: IO.Autogrow.Type = None) -> IO.NodeOutput:
        slides = []
        for name, value in (images or {}).items():
            frames = _collect_images(value)
            for k, frame in enumerate(frames):
                if len(slides) >= MAX_SLIDES:
                    break
                h, w = int(frame.shape[0]), int(frame.shape[1])
                ref = save_temp(to_pil(frame), "slider", fmt="png")
                label = name if len(frames) == 1 else f"{name} · {k + 1}/{len(frames)}"
                slides.append({**ref, "label": label, "w": w, "h": h})
        return IO.NodeOutput(ui={"arbor_slider": [{"slides": slides}]})


RESIZE_METHODS = ["lanczos", "bicubic", "bilinear", "area", "nearest-exact"]


def target_size(w: int, h: int, mode: dict, multiple: int, allow_upscale: bool) -> tuple[int, int, bool]:
    """(width, height, crop) for Smart Resize."""
    m = mode["mode"]
    crop = False
    if m == "fill & crop":
        tw, th, crop = mode["width"], mode["height"], True
        if not allow_upscale and (tw > w or th > h):
            k = min(w / tw, h / th, 1.0)
            tw, th = tw * k, th * k
    else:
        if m == "longest side":
            s = mode["size"] / max(w, h)
        elif m == "shortest side":
            s = mode["size"] / min(w, h)
        elif m == "megapixels":
            s = math.sqrt(mode["megapixels"] * 1_000_000 / (w * h))
        elif m == "fit inside":
            s = min(mode["width"] / w, mode["height"] / h)
        else:  # scale
            s = mode["factor"]
        if not allow_upscale:
            s = min(s, 1.0)
        tw, th = w * s, h * s
    q = max(1, multiple)
    tw = max(q, int(round(tw / q)) * q)
    th = max(q, int(round(th / q)) * q)
    return tw, th, crop


class SmartResize(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        size = lambda: IO.Int.Input("size", default=1024, min=8, max=16384, step=8)
        wh = lambda: [IO.Int.Input("width", default=1024, min=8, max=16384, step=8),
                      IO.Int.Input("height", default=1024, min=8, max=16384, step=8)]
        return IO.Schema(
            node_id="Arbor_SmartResize", display_name="Smart Resize", category=CAT_IMAGE,
            description="Resize by longest / shortest side, megapixels, a box or a scale factor, "
                        "snapping both sides to a multiple (8 / 16 / 64 for latent-friendly sizes).",
            search_aliases=["resize", "scale image", "fit", "megapixels", "upscale image", "crop to size"],
            inputs=[
                IO.Image.Input("image"),
                IO.DynamicCombo.Input("mode", options=[
                    IO.DynamicCombo.Option("longest side", [size()]),
                    IO.DynamicCombo.Option("shortest side", [size()]),
                    IO.DynamicCombo.Option("megapixels", [
                        IO.Float.Input("megapixels", default=1.0, min=0.01, max=64.0, step=0.05)]),
                    IO.DynamicCombo.Option("fit inside", wh()),
                    IO.DynamicCombo.Option("fill & crop", wh()),
                    IO.DynamicCombo.Option("scale", [
                        IO.Float.Input("factor", default=1.0, min=0.01, max=16.0, step=0.05)]),
                ]),
                IO.Combo.Input("multiple_of", options=["1", "8", "16", "32", "64"], default="16"),
                IO.Combo.Input("method", options=RESIZE_METHODS, default="lanczos"),
                IO.Boolean.Input("allow_upscale", default=True),
                IO.Mask.Input("mask", optional=True, tooltip="Resized (and cropped) the same way"),
            ],
            outputs=[IO.Image.Output(display_name="image"), IO.Mask.Output(display_name="mask"),
                     IO.Int.Output(display_name="width"), IO.Int.Output(display_name="height")])

    @classmethod
    def execute(cls, image, mode, multiple_of, method, allow_upscale, mask=None) -> IO.NodeOutput:
        import comfy.utils

        h, w = int(image.shape[1]), int(image.shape[2])
        tw, th, crop = target_size(w, h, mode, int(multiple_of), allow_upscale)
        crop_mode = "center" if crop else "disabled"
        if (tw, th) == (w, h):
            out = image
        else:
            out = comfy.utils.common_upscale(image.movedim(-1, 1), tw, th, method, crop_mode).movedim(1, -1)
        out = out.clamp(0, 1)
        if mask is None:
            m = torch.ones((out.shape[0], th, tw), dtype=out.dtype)
        else:
            m = mask if mask.dim() == 3 else mask[None]
            m = comfy.utils.common_upscale(m[:, None], tw, th, "bilinear", crop_mode)[:, 0].clamp(0, 1)
        return IO.NodeOutput(out, m, tw, th)


def parse_indices(text: str, n: int) -> list[int]:
    """'0, 2, -1, 3-5, 1:4' -> indices into a batch of n (ranges inclusive, slices python-style)."""
    out = []
    for tok in re.split(r"[\s,;]+", str(text).strip()):
        if not tok:
            continue
        if re.fullmatch(r"\d+-\d+", tok):
            a, b = map(int, tok.split("-"))
            step = 1 if b >= a else -1
            out.extend(range(a, b + step, step))
        elif ":" in tok:
            parts = [int(p) if p else None for p in tok.split(":")]
            out.extend(range(n)[slice(*parts)])
        else:
            try:
                out.append(int(tok))
            except ValueError:
                raise ValueError(f"Batch Pick: can't read index {tok!r}") from None
    picked = []
    for i in out:
        if not -n <= i < n:
            raise IndexError(f"Batch Pick: index {i} out of range for a batch of {n}")
        picked.append(i % n)
    return picked


class BatchPick(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_BatchPick", display_name="Batch Pick", category=CAT_IMAGE,
            description="Pick frames from an image batch: '0, 2, -1', ranges '3-5' (inclusive) "
                        "or slices '1:8:2'. Order and repeats are kept.",
            search_aliases=["select from batch", "image from batch", "frames", "batch index"],
            inputs=[IO.Image.Input("images"),
                    IO.String.Input("indices", default="0", tooltip="e.g. 0, 2, -1, 3-5, ::2")],
            outputs=[IO.Image.Output(display_name="images"), IO.Int.Output(display_name="count")])

    @classmethod
    def execute(cls, images, indices) -> IO.NodeOutput:
        idx = parse_indices(indices, int(images.shape[0]))
        if not idx:
            raise ValueError("Batch Pick: no indices given")
        return IO.NodeOutput(images[idx], len(idx))


NODES = [ImageSlider, SmartResize, BatchPick]
