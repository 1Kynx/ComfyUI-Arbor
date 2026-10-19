"""Image nodes: compare, grid, resize, pick. (Loading and saving live in nodes_files.py.)"""

import math

import numpy as np
import torch

from . import tree as T
from .common import IO, TREE, CAT_IMAGE, schema, connected, tree_in, to_tree, unwrap
from .grid import build_grid, col_labels_for, grid_size, row_labels_for
from .preview import is_image, label_of, save_temp, to_pil

MAX_SLIDES = 64


# ======================================================================= Image Slider

def _slides(slot: str, value) -> list[tuple[torch.Tensor, str]]:
    """(frame, label) for every frame of a socket value: a batch, a list of batches, or a tree.
    Frames of a named branch are labelled with its name, the rest with the slot name;
    a label shared by several frames is numbered."""
    tree = to_tree(value)
    pairs = [(v[i], label_of(tree.names[p]) if p in tree.names else slot)
             for p, items in tree.items() for v in items if is_image(v) for i in range(v.shape[0])]
    total = {lab: sum(1 for _, l in pairs if l == lab) for _, lab in pairs}
    seen: dict[str, int] = {}
    out = []
    for frame, lab in pairs:
        seen[lab] = seen.get(lab, 0) + 1
        out.append((frame, lab if total[lab] == 1 else f"{lab} · {seen[lab]}/{total[lab]}"))
    return out


class ImageSlider(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        images = IO.Autogrow.TemplatePrefix(
            IO.MultiType.Input(IO.Image.Input("image", tooltip="Image, batch or image tree; every frame "
                                                               "becomes a slide"), types=[TREE]),
            prefix="image", min=1, max=16)
        return schema(
            "Arbor_ImageSlider", "Image Slider", CAT_IMAGE,
            "Compare any number of images of any size. Drag the slider to flip through them, "
            "or switch to wipe mode for a before / after split.",
            [IO.Autogrow.Input("images", template=images, optional=True)], [],
            ["image compare", "compare", "before after", "ab test", "image viewer", "flipbook"],
            is_output_node=True)

    @classmethod
    def execute(cls, images: IO.Autogrow.Type = None) -> IO.NodeOutput:
        slides = []
        for name, value in (images or {}).items():
            for frame, label in _slides(name, value)[:MAX_SLIDES - len(slides)]:
                ref = save_temp(to_pil(frame), "slider", fmt="png")
                slides.append({**ref, "label": label, "w": int(frame.shape[1]), "h": int(frame.shape[0])})
        return IO.NodeOutput(ui={"arbor_slider": [{"slides": slides}]})


# ======================================================================= Image Grid

class ImageGrid(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_ImageGrid", "Image Grid", CAT_IMAGE,
            "XY sheet: each branch is a row, each item a column. Connect XY Lists' shape to lay out "
            "and label the images of a batch run directly; use Reshape Tree (flip matrix) to swap the axes.",
            [tree_in("images", tooltip="Image tree, or the plain images of a batch run (with shape)"),
             tree_in("shape", optional=True,
                     tooltip="Layout to pour plain images into (XY Lists' shape); also labels the columns"),
             tree_in("row_labels", optional=True,
                     tooltip="One label per row — overrides the row names the tree or shape carries"),
             tree_in("col_labels", optional=True,
                     tooltip="One label per column — overrides the labels taken from shape"),
             IO.Combo.Input("fit", options=["fit", "original", "stretch"], default="fit",
                            tooltip="How images of different sizes fill a cell"),
             IO.Int.Input("cell_size", default=0, min=0, max=8192, step=8,
                          tooltip="Longest side of a cell in px; 0 = largest image"),
             IO.Int.Input("gap", default=8, min=0, max=256),
             IO.Int.Input("font_size", default=24, min=8, max=200),
             IO.Combo.Input("theme", options=["light", "dark"], default="light"),
             IO.Boolean.Input("path_labels", default=False,
                              tooltip="Label rows with their branch path when no row labels are given")],
            [IO.Image.Output(display_name="image")],
            ["xy plot", "xyz plot", "grid", "contact sheet", "comparison", "tree to grid"])

    @classmethod
    def execute(cls, images, fit, cell_size, gap, font_size, theme, path_labels,
                shape=None, row_labels=None, col_labels=None) -> IO.NodeOutput:
        tree = to_tree(images)
        if connected(shape):
            layout = to_tree(shape)
            tree = T.rebuild(tree.flat(), layout)
            rows = [[label_of(v) for v in items] for items in layout.branches.values()]
            if not connected(col_labels) and all(r == rows[0] for r in rows):
                col_labels = shape  # a true matrix (XY Lists): every row holds the column values
        rows, cols = grid_size(tree)
        if not connected(row_labels) and tree.names:
            row_labels = [tree.names.get(p, "") for p in tree.paths()]  # e.g. XY Lists' x values
        sheet = build_grid(tree, row_labels_for(row_labels if connected(row_labels) else None, rows),
                           col_labels_for(col_labels if connected(col_labels) else None, cols),
                           unwrap(fit), unwrap(cell_size), unwrap(gap), unwrap(font_size), unwrap(theme),
                           unwrap(path_labels))
        return IO.NodeOutput(torch.from_numpy(np.asarray(sheet, dtype=np.float32) / 255.0)[None])


# ======================================================================= Smart Resize

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
    return max(q, int(round(tw / q)) * q), max(q, int(round(th / q)) * q), crop


class SmartResize(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        size = lambda: IO.Int.Input("size", default=1024, min=8, max=16384, step=8)
        wh = lambda: [IO.Int.Input("width", default=1024, min=8, max=16384, step=8),
                      IO.Int.Input("height", default=1024, min=8, max=16384, step=8)]
        return schema(
            "Arbor_SmartResize", "Smart Resize", CAT_IMAGE,
            "Resize by longest / shortest side, megapixels, a box or a scale factor, "
            "snapping both sides to a multiple (8 / 16 / 64 for latent-friendly sizes).",
            [IO.Image.Input("image"),
             IO.DynamicCombo.Input("mode", options=[
                 IO.DynamicCombo.Option("longest side", [size()]),
                 IO.DynamicCombo.Option("shortest side", [size()]),
                 IO.DynamicCombo.Option("megapixels", [
                     IO.Float.Input("megapixels", default=1.0, min=0.01, max=64.0, step=0.05)]),
                 IO.DynamicCombo.Option("fit inside", wh()),
                 IO.DynamicCombo.Option("fill & crop", wh()),
                 IO.DynamicCombo.Option("scale", [IO.Float.Input("factor", default=1.0, min=0.01, max=16.0,
                                                                 step=0.05)]),
             ]),
             IO.Combo.Input("multiple_of", options=["1", "8", "16", "32", "64"], default="16"),
             IO.Combo.Input("method", options=RESIZE_METHODS, default="lanczos"),
             IO.Boolean.Input("allow_upscale", default=True),
             IO.Mask.Input("mask", optional=True, tooltip="Resized (and cropped) the same way")],
            [IO.Image.Output(display_name="image"), IO.Mask.Output(display_name="mask"),
             IO.Int.Output(display_name="width"), IO.Int.Output(display_name="height")],
            ["resize", "scale image", "fit", "megapixels", "upscale image", "crop to size"],
            input_list=False)

    @classmethod
    def execute(cls, image, mode, multiple_of, method, allow_upscale, mask=None) -> IO.NodeOutput:
        import comfy.utils

        h, w = int(image.shape[1]), int(image.shape[2])
        tw, th, crop = target_size(w, h, mode, int(multiple_of), allow_upscale)
        crop_mode = "center" if crop else "disabled"
        out = image if (tw, th) == (w, h) else \
            comfy.utils.common_upscale(image.movedim(-1, 1), tw, th, method, crop_mode).movedim(1, -1)
        out = out.clamp(0, 1)
        if mask is None:
            m = torch.ones((out.shape[0], th, tw), dtype=out.dtype)
        else:
            m = mask if mask.dim() == 3 else mask[None]
            m = comfy.utils.common_upscale(m[:, None], tw, th, "bilinear", crop_mode)[:, 0].clamp(0, 1)
        return IO.NodeOutput(out, m, tw, th)


# ======================================================================= Batch Pick

def parse_indices(text: str, n: int) -> list[int]:
    """Batch Pick indices: like List Item's, but out of range is an error."""
    try:
        idx = T.parse_indices(text, n)
    except ValueError as e:
        raise ValueError(f"Batch Pick: {e}") from None
    for i in idx:
        if not -n <= i < n:
            raise IndexError(f"Batch Pick: index {i} out of range for a batch of {n}")
    return [i % n for i in idx]


class BatchPick(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_BatchPick", "Batch Pick", CAT_IMAGE,
            "Pick frames from an image batch: '0, 2, -1', ranges '3-5' (inclusive) or slices '1:8:2'. "
            "Order and repeats are kept.",
            [IO.Image.Input("images"), IO.String.Input("indices", default="0", tooltip="e.g. 0, 2, -1, 3-5, ::2")],
            [IO.Image.Output(display_name="images"), IO.Int.Output(display_name="count")],
            ["select from batch", "image from batch", "frames", "batch index"],
            input_list=False)

    @classmethod
    def execute(cls, images, indices) -> IO.NodeOutput:
        idx = parse_indices(indices, int(images.shape[0]))
        if not idx:
            raise ValueError("Batch Pick: no indices given")
        return IO.NodeOutput(images[idx], len(idx))


NODES = [ImageSlider, ImageGrid, SmartResize, BatchPick]
