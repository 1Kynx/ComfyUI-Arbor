"""Image and video nodes: compare, grids, resize, pick. (Loading and saving live in nodes_files.py.)"""

import math

import numpy as np
import torch

from . import media
from . import tree as T
from .common import IO, TREE, CAT_MEDIA, schema, connected, data_out, tree_in, tree_out, to_tree, unwrap
from .grid import CAPTION_STYLES, FITS, LABEL_DIRS, build_grid, caption_rows, col_labels_for, fit_box, \
    grid_size, layout_sheet, row_labels_for, wrap_rows
from .media import is_audio, is_video
from .preview import is_image, label_of, save_temp, to_pil

MAX_SLIDES = 64


# ======================================================================= Compare Viewer

def is_tree_input(value) -> bool:
    """A tree arrived (not a plain value, list or batch) — only trees split the viewer into groups."""
    values = value if isinstance(value, list) else [value]
    return any(isinstance(v, T.DataTree) for v in values)


def _slides(slot: str, value, labels: T.DataTree | None = None) -> list[tuple[str, object, str, str | None]]:
    """(kind, value, label, group) for everything a socket value holds that can be compared: every
    frame of an image batch, every video, every clip of an audio batch — a batch, a list or a tree.
    Items of a named branch are labelled with its name, the rest with the slot name; with
    ``labels`` (matched branch by branch, item by item) an item's label follows the branch name.
    A label shared by several slides is numbered. The group — what the viewer can show on its
    own — is the top-level branch of a tree: its name, or its path when it has none ({0}). Plain
    values, lists and batches have no group (None): they go with every group."""
    tree = to_tree(value)
    grouped = is_tree_input(value)
    found = []
    for b, (p, items) in enumerate(tree.items()):
        branch = tree.label(p, label_of)
        top = tree.names.get(p[:1])
        group = (label_of(top) if top is not None else T.format_path(p[:1])) if grouped else None
        for j, v in enumerate(items):
            own = T.match_item(labels, b, j) if labels else None
            own = label_of(own) if own is not None else None
            lab = " · ".join(x for x in (branch, own) if x) or slot
            if is_image(v):
                found += [("image", v[i], lab, group) for i in range(v.shape[0])]
            elif is_video(v):
                found.append(("video", v, lab, group))
            elif is_audio(v):
                found += [("audio", clip, lab, group) for clip in media.audio_clips(v)]
    total: dict[str, int] = {}
    for _, _, lab, _ in found:
        total[lab] = total.get(lab, 0) + 1
    seen: dict[str, int] = {}
    out = []
    for kind, v, lab, group in found:
        seen[lab] = seen.get(lab, 0) + 1
        out.append((kind, v, lab if total[lab] == 1 else f"{lab} · {seen[lab]}/{total[lab]}", group))
    return out


def _slide(kind: str, v, label: str, group: str | None) -> dict:
    """The UI payload of one slide: a /view reference plus what the viewer needs to lay it out."""
    if kind == "image":
        ref = save_temp(to_pil(v), "compare", fmt="png")
        info = {"w": int(v.shape[1]), "h": int(v.shape[0])}
    elif kind == "video":
        ref, info = media.video_ref(v, "compare"), media.video_info(v)
    else:
        waveform, rate = v
        ref = media.audio_ref(waveform, rate, "compare")
        info = {"dur": waveform.shape[-1] / rate, "peaks": media.peaks(waveform)}
    return {**ref, "kind": kind, "label": label, "group": group, **info}


class ImageSlider(IO.ComfyNode):
    """Compare Viewer (kept under its first id, Image Slider, so saved workflows still load)."""

    @classmethod
    def define_schema(cls):
        items = IO.Autogrow.TemplatePrefix(
            IO.MultiType.Input(IO.Image.Input("image", tooltip="Image, video or audio — a single value, a batch, "
                                                               "a list or a tree; each one becomes a slide"),
                               types=[IO.Video, IO.Audio, TREE]),
            prefix="image", min=1, max=16)
        return schema(
            "Arbor_ImageSlider", "Compare Viewer", CAT_MEDIA,
            "Compare images, videos and audio of any size. Flip through them with the slider, or wipe A against B; "
            "videos and audio play in sync and keep their place when you switch.",
            [IO.Autogrow.Input("images", template=items, optional=True),
             tree_in("labels", optional=True,
                     tooltip="Optional: a label per item, matched branch by branch and item by item (one list "
                             "serves every branch); shown after the branch name — 'Mei · Back'")],
            [],
            ["image compare", "video compare", "audio compare", "compare", "before after", "ab test",
             "image slider", "image viewer", "video viewer", "flipbook"],
            is_output_node=True)

    @classmethod
    def execute(cls, images: IO.Autogrow.Type = None, labels=None) -> IO.NodeOutput:
        label_tree = to_tree(labels) if connected(labels) else None
        slides = []
        for name, value in (images or {}).items():
            for kind, v, label, group in _slides(name, value, label_tree)[:MAX_SLIDES - len(slides)]:
                slides.append(_slide(kind, v, label, group))
        # groups of every input meet by name (or path): input 1's Mei and input 2's Mei are one group;
        # fewer than two groups is no grouping at all
        if len({s["group"] for s in slides if s["group"] is not None}) < 2:
            for s in slides:
                s["group"] = None
        return IO.NodeOutput(ui={"arbor_slider": [{"slides": slides}]})


# ======================================================================= Image Grid

def _grid_inputs(values, shape, row_labels, col_labels):
    """The tree to lay out and the row / column labels, shared by Image Grid and Video Grid."""
    tree = to_tree(values)
    if connected(shape):
        layout = to_tree(shape)
        tree = T.rebuild(tree.flat(), layout)
        row_values = [[label_of(v) for v in items] for items in layout.branches.values()]
        if not connected(col_labels) and all(r == row_values[0] for r in row_values):
            col_labels = shape  # a true matrix (XY Lists): every row holds the column values
    if not connected(row_labels) and tree.names:  # e.g. XY Lists' x values, "Mira · lab coat"
        row_labels = [tree.label(p, label_of) or "" for p in tree.paths()]
    return tree, (row_labels if connected(row_labels) else None), (col_labels if connected(col_labels) else None)


def _label_inputs(what: str):
    return [tree_in("shape", optional=True,
                    tooltip=f"Layout to pour plain {what} into (XY Lists' shape); labels the columns when "
                            "every row holds the same values"),
            tree_in("row_labels", optional=True,
                    tooltip="One label per row — overrides the row names the tree or shape carries"),
            tree_in("col_labels", optional=True,
                    tooltip="One label per column — overrides the labels taken from shape"),
            tree_in("captions", optional=True,
                    tooltip="One caption per cell — a tree shaped like the grid, or a list read cell by cell")]


def _style_inputs(cell_size_default: int):
    return [IO.Combo.Input("fit", options=FITS, default="fit",
                           tooltip="fit: whole picture, bars around · fill: covers the cell, edges cut · "
                                   "original: no scaling · stretch: fills the cell, distorted"),
            IO.Int.Input("cell_size", default=cell_size_default, min=0, max=8192, step=8,
                         tooltip="Longest side of a cell in px; 0 = largest picture"),
            IO.Int.Input("gap", default=8, min=0, max=256),
            IO.Int.Input("font_size", default=24, min=8, max=200),
            IO.Combo.Input("theme", options=["light", "dark"], default="light"),
            IO.Boolean.Input("path_labels", default=False,
                             tooltip="Label rows with their branch path when there are no row labels or names")]


def _layout_inputs():
    """Added after the original widgets so workflows saved before keep their values."""
    return [IO.Int.Input("columns", default=0, min=0, max=256,
                         tooltip="0: one row per branch · N: wrap every branch after N cells (a flat list "
                                 "becomes rows of N)"),
            IO.Combo.Input("label_direction", options=LABEL_DIRS, default="auto",
                           tooltip="Row labels — auto: horizontal while they fit in two lines, else standing up"),
            IO.Combo.Input("caption_style", options=CAPTION_STYLES, default="below",
                           tooltip="below: under each cell · overlay: on a dark bar over the picture's bottom")]


class ImageGrid(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_ImageGrid", "Image Grid", CAT_MEDIA,
            "XY sheet: each branch is a row, each item a column. Connect XY Lists' shape to lay out "
            "and label the images of a batch run directly; use Reshape Tree (flip matrix) to swap the axes.",
            [tree_in("images", tooltip="Image tree, or the plain images of a batch run (with shape)"),
             *_label_inputs("images"), *_style_inputs(0), *_layout_inputs()],
            [IO.Image.Output(display_name="image")],
            ["xy plot", "xyz plot", "grid", "contact sheet", "comparison", "tree to grid", "captions"])

    @classmethod
    def execute(cls, images, fit, cell_size, gap, font_size, theme, path_labels, columns=0,
                label_direction="auto", caption_style="below", shape=None, row_labels=None, col_labels=None,
                captions=None) -> IO.NodeOutput:
        tree, row_labels, col_labels = _grid_inputs(images, shape, row_labels, col_labels)
        rows, cols = grid_size(tree)
        sheet = build_grid(tree, row_labels_for(row_labels, rows), col_labels_for(col_labels, cols),
                           unwrap(fit), unwrap(cell_size), unwrap(gap), unwrap(font_size), unwrap(theme),
                           unwrap(path_labels), unwrap(columns, 0), captions if connected(captions) else None,
                           unwrap(caption_style, "below"), unwrap(label_direction, "auto"))
        return IO.NodeOutput(torch.from_numpy(np.asarray(sheet, dtype=np.float32) / 255.0)[None])


# ======================================================================= Video Grid

def _clip_size(v) -> tuple[int, int]:
    if isinstance(v, torch.Tensor):
        return int(v.shape[2]), int(v.shape[1])
    info = media.video_info(v)
    if info.get("w") and info.get("h"):
        return info["w"], info["h"]
    images = v.get_components().images
    return int(images.shape[2]), int(images.shape[1])


class VideoGrid(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_VideoGrid", "Video Grid", CAT_MEDIA,
            "Image Grid for video: each branch is a row, each clip a column, all playing in sync in one labelled "
            "video. Shorter clips hold their last frame until the longest one ends.",
            [tree_in("videos", tooltip="Video tree, or the plain videos of a batch run (with shape); "
                                       "an image batch counts as one clip"),
             *_label_inputs("videos"), *_style_inputs(512),
             IO.Float.Input("fps", default=0.0, min=0.0, max=240.0, step=1.0,
                            tooltip="Frame rate of the grid video; 0 = the highest rate among the clips"),
             IO.Combo.Input("audio", options=["none", "mix"], default="none",
                            tooltip="none: silent · mix: every clip's sound mixed together"),
             *_layout_inputs()],
            [IO.Video.Output(display_name="video")],
            ["video grid", "video xy plot", "video contact sheet", "video comparison", "side by side video",
             "video collage", "captions"],
            is_output_node=True)

    @classmethod
    def execute(cls, videos, fit, cell_size, gap, font_size, theme, path_labels, fps, audio, columns=0,
                label_direction="auto", caption_style="below", shape=None, row_labels=None, col_labels=None,
                captions=None) -> IO.NodeOutput:
        from comfy_api.latest import InputImpl

        tree, row_labels, col_labels = _grid_inputs(videos, shape, row_labels, col_labels)
        branches = [(p, [v for v in items if is_video(v) or is_image(v)]) for p, items in tree.items()]
        branches = [b for b in branches if b[1]]
        if not branches:
            raise ValueError("Video Grid: no videos to lay out")
        fit, columns, style = unwrap(fit), unwrap(columns, 0), unwrap(caption_style, "below")
        caps = caption_rows(captions if connected(captions) else None, [len(c) for _, c in branches])
        rows, blocks = wrap_rows([c for _, c in branches], columns)
        cap_rows = wrap_rows(caps, columns)[0] if caps else None
        n_cols = max(len(c) for _, c in branches)
        sheet = layout_sheet([[_clip_size(v) for v in clips] for clips in rows],
                             row_labels_for(row_labels, len(branches)),
                             None if columns > 0 else col_labels_for(col_labels, n_cols),
                             unwrap(cell_size), unwrap(gap), unwrap(font_size), unwrap(theme), unwrap(path_labels),
                             [p for p, _ in branches], "Video Grid", even=True, blocks=blocks, captions=cap_rows,
                             caption_style=style, label_dir=unwrap(label_direction, "auto"))

        size = lambda w, h: fit_box(w, h, sheet.cw, sheet.ch, fit)[:2]
        crop = (sheet.cw, sheet.ch) if fit == "fill" else None
        cells = []  # (x, y, frames, fps, caption bar)
        for i, clips in enumerate(rows):
            for j, v in enumerate(clips):
                frames, rate = media.clip_frames(v, size, crop)
                if not len(frames):
                    continue
                h, w = frames.shape[1:3]
                x, y = sheet.place(i, j, w, h)
                bar = None
                if cap_rows and style == "overlay":
                    img = sheet.overlay(cap_rows[i][j], w)
                    if img is not None:
                        rgba = np.asarray(img, dtype=np.float32) / 255.0
                        bar = (rgba[..., :3] * 255.0, rgba[..., 3:])
                cells.append((x, y, frames, rate, bar))
        out_fps = unwrap(fps) or max((c[3] for c in cells), default=0) or 24.0
        length = max(len(c[2]) / (c[3] or out_fps) for c in cells)
        count = max(1, math.ceil(length * out_fps - 1e-6))
        background = np.asarray(sheet.image, dtype=np.uint8)

        def frames():
            for k in range(count):
                t = k / out_fps
                buf = background.copy()
                for x, y, f, r, bar in cells:
                    frame = f[min(int(t * (r or out_fps) + 1e-6), len(f) - 1)]
                    fh, fw = frame.shape[:2]
                    buf[y:y + fh, x:x + fw] = frame
                    if bar is not None:  # caption over the picture's bottom
                        rgb, a = bar
                        bh = min(rgb.shape[0], fh)
                        region = buf[y + fh - bh:y + fh, x:x + fw].astype(np.float32)
                        buf[y + fh - bh:y + fh, x:x + fw] = (rgb[-bh:] * a[-bh:] + region * (1 - a[-bh:])).astype(np.uint8)
                yield buf

        sound = None
        if unwrap(audio) == "mix":
            sound = media.mix([media.video_audio(v) for clips in rows for v in clips if is_video(v)])
        path = media.encode_mp4(frames(), count, out_fps, background.shape[1], background.shape[0], sound)
        return IO.NodeOutput(InputImpl.VideoFromFile(path),
                             ui={"images": [media.view_ref(path)], "animated": [True]})


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
            "Arbor_SmartResize", "Smart Resize", CAT_MEDIA,
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
            "Arbor_BatchPick", "Batch Pick", CAT_MEDIA,
            "Pick frames from an image batch or a video: '0, 2, -1', ranges '3-5' (inclusive) or slices "
            "'1:8:2'. Order and repeats are kept. '0, -1' gives a clip's first and last frame.",
            [IO.MultiType.Input(IO.Image.Input("images", tooltip="An image batch, or a video (its frames)"),
                                types=[IO.Video]),
             IO.String.Input("indices", default="0", tooltip="e.g. 0, 2, -1, 3-5, ::2")],
            [IO.Image.Output(display_name="images"), IO.Int.Output(display_name="count")],
            ["select from batch", "image from batch", "frames", "batch index", "video frame", "last frame",
             "first frame", "extract frames"],
            input_list=False)

    @classmethod
    def execute(cls, images, indices) -> IO.NodeOutput:
        if is_video(images):
            images = images.get_components().images
        idx = parse_indices(indices, int(images.shape[0]))
        if not idx:
            raise ValueError("Batch Pick: no indices given")
        return IO.NodeOutput(images[idx], len(idx))


# ======================================================================= Split Grid

def flat_lines(gray: np.ndarray, axis: int, tol: float = 0.05) -> np.ndarray:
    """Per column (axis 0) or row (axis 1): is the whole line one flat colour, as a gutter is?"""
    med = np.median(gray, axis=axis, keepdims=True)
    return (np.abs(gray - med) < tol).mean(axis=axis) > 0.97


def _runs(mask) -> list[tuple[int, int]]:
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def even_spans(size: int, n: int) -> list[tuple[int, int]]:
    return [(round(i * size / n), round((i + 1) * size / n)) for i in range(n)]


def grid_spans(flat: np.ndarray, n: int) -> list[tuple[int, int]]:
    """Split one axis into n panels, leaving out the margins and the gutters (flat lines) found near
    where an even split would cut; where there is none, that cut is even."""
    size = len(flat)
    edge = size // (4 * n)
    lo, hi = 0, size
    while lo < edge and flat[lo]:
        lo += 1
    while hi > size - edge and flat[hi - 1]:
        hi -= 1
    lo = 0 if lo >= edge else lo  # a flat stretch that long is picture, not a margin
    hi = size if hi <= size - edge else hi
    step = (hi - lo) / n
    gutters = [(s + lo, e + lo) for s, e in _runs(flat[lo:hi]) if e - s < step * 0.3]
    edges = [lo]
    for k in range(1, n):
        x = lo + step * k
        near = [g for g in gutters if abs((g[0] + g[1]) / 2 - x) <= step * 0.15]
        s, e = min(near, key=lambda g: abs((g[0] + g[1]) / 2 - x)) if near else (round(x), round(x))
        edges += [s, e]
    edges.append(hi)
    return [(edges[2 * i], edges[2 * i + 1]) for i in range(n)]


MAX_CUT_PREVIEWS = 4


def cut_preview(frame: torch.Tensor, boxes: list[tuple[int, int, int, int]], max_px: int = 1280):
    """The sheet with what was cut away shaded red and every panel outlined and numbered."""
    from PIL import Image, ImageDraw
    from .grid import _font

    img = to_pil(frame).convert("RGBA")
    s = min(1.0, max_px / max(img.size))
    if s < 1:
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    boxes = [tuple(round(v * s) for v in box) for box in boxes]
    shade = Image.new("RGBA", img.size, (230, 50, 50, 120))
    draw = ImageDraw.Draw(shade)
    for x0, y0, x1, y1 in boxes:
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(0, 0, 0, 0))
    img = Image.alpha_composite(img, shade)
    draw = ImageDraw.Draw(img)
    size = max(14, round(min(img.size) * 0.05))
    for k, (x0, y0, x1, y1) in enumerate(boxes):
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 220, 60, 255), width=max(2, size // 8))
        draw.text((x0 + size // 3, y0 + size // 4), str(k), font=_font(size), fill=(255, 220, 60, 255),
                  stroke_width=max(1, size // 10), stroke_fill=(0, 0, 0, 255))
    return img.convert("RGB")


class SplitGrid(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_SplitGrid", "Split Grid", CAT_MEDIA,
            "Cut a grid picture — a storyboard sheet, a contact sheet, a sprite sheet — into its panels, "
            "row by row. Gutters and margins (lines of one flat colour) are found and left out, so panels "
            "that are not quite even still come out clean; without gutters the picture is cut evenly.",
            [IO.Image.Input("image", tooltip="One sheet, or a batch / list of sheets (one branch each)"),
             IO.Int.Input("rows", default=2, min=1, max=64),
             IO.Int.Input("columns", default=3, min=1, max=64),
             IO.Boolean.Input("find_gutters", default=True,
                              tooltip="Look for gutters and margins near every cut and leave them out. "
                                      "Off: cut the picture into even parts"),
             IO.Int.Input("inset", default=2, min=0, max=256,
                          tooltip="Pixels shaved off every panel edge — drops the soft edge of a gutter")],
            [data_out(IO.Image, "Every panel as plain data, in reading order (left to right, top to bottom)"),
             tree_out(tooltip="One branch per sheet, its panels in reading order")],
            ["split grid", "split image", "crop grid", "slice image", "tiles", "image to tiles",
             "storyboard sheet", "contact sheet", "sprite sheet", "panels", "uncollage"])

    @classmethod
    def execute(cls, image, rows, columns, find_gutters, inset) -> IO.NodeOutput:
        rows, cols, inset = int(unwrap(rows)), int(unwrap(columns)), int(unwrap(inset))
        sheets = [im[k:k + 1] for im in image if im is not None for k in range(im.shape[0])]
        out, previews = {}, []
        for b, sheet in enumerate(sheets):
            h, w = int(sheet.shape[1]), int(sheet.shape[2])
            if unwrap(find_gutters):
                gray = sheet[0].float().mean(-1).cpu().numpy()
                ys, xs = grid_spans(flat_lines(gray, 1), rows), grid_spans(flat_lines(gray, 0), cols)
            else:
                ys, xs = even_spans(h, rows), even_spans(w, cols)
            panels, boxes = [], []
            for y0, y1 in ys:
                for x0, x1 in xs:
                    dy, dx = min(inset, (y1 - y0 - 1) // 2), min(inset, (x1 - x0 - 1) // 2)
                    panels.append(sheet[:, y0 + dy:y1 - dy, x0 + dx:x1 - dx])
                    boxes.append((x0 + dx, y0 + dy, x1 - dx, y1 - dy))
            out[(b,)] = panels
            if b < MAX_CUT_PREVIEWS:
                previews.append(save_temp(cut_preview(sheet[0], boxes), "split", fmt="webp"))
        tree = T.DataTree(out or {(0,): []})
        return IO.NodeOutput(tree.flat(), tree, ui={"images": previews})


NODES = [ImageSlider, ImageGrid, VideoGrid, SmartResize, BatchPick, SplitGrid]
