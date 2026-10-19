"""Tree → Grid: lay an image tree out as an XY comparison sheet."""

from __future__ import annotations

import os

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

from .common import IO, CAT_IMAGE, tree_in, to_tree, unwrap
from .preview import is_image, label_of, to_pil
from .tree import format_path

THEMES = {
    "light": {"bg": (255, 255, 255), "fg": (34, 34, 38), "sub": (120, 120, 128)},
    "dark": {"bg": (24, 24, 27), "fg": (232, 232, 236), "sub": (140, 140, 150)},
}

_FONT_CANDIDATES = [
    # Windows (CJK first so Chinese prompts render), then Linux / macOS
    r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Helvetica.ttc",
]
_font_cache: dict[int, ImageFont.ImageFont] = {}


def _font(size: int):
    if size not in _font_cache:
        font = None
        for path in _FONT_CANDIDATES:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except OSError:
                    continue
        _font_cache[size] = font or ImageFont.load_default(size=size)
    return _font_cache[size]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int) -> list[str]:
    """Greedy wrap by characters (works for CJK and latin alike)."""
    lines, cur = [], ""
    for ch in text.replace("\n", " "):
        if draw.textlength(cur + ch, font=font) <= width or not cur:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines and cur:
        lines.append(cur)
    if len(lines) == max_lines and "".join(lines) != text.replace("\n", " "):
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _labels(value) -> list[str] | None:
    if value is None:
        return None
    return [label_of(v) for v in to_tree(value).flat()]


def _frames(items) -> list[Image.Image | None]:
    out = []
    for v in items:
        if is_image(v):
            out.extend(to_pil(v[i]).convert("RGB") for i in range(v.shape[0]))
        else:
            out.append(None)
    return out


def build_grid(tree, row_labels=None, col_labels=None, fit="fit", cell_size=0, gap=8,
               font_size=24, theme="light", path_labels=False) -> Image.Image:
    rows = [(p, _frames(items)) for p, items in to_tree(tree).items()]
    rows = [r for r in rows if r[1]]
    if not rows:
        raise ValueError("Tree → Grid: no images in the tree")
    imgs = [im for _, r in rows for im in r if im is not None]
    if not imgs:
        raise ValueError("Tree → Grid: no images in the tree")

    cols = max(len(r) for _, r in rows)
    cw = max(im.width for im in imgs)
    ch = max(im.height for im in imgs)
    if cell_size > 0:  # longest side of a cell
        s = cell_size / max(cw, ch)
        cw, ch = max(1, round(cw * s)), max(1, round(ch * s))

    rl = row_labels or ([format_path(p) for p, _ in rows] if path_labels else None)
    cl = col_labels
    colors = THEMES[theme]
    font = _font(font_size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    line_h = int(font_size * 1.3)

    left = 0
    if rl:
        left = min(max(int(probe.textlength(t, font=font)) for t in rl) + gap * 2, int(cw * 0.9) + gap)
        left = max(left, font_size * 3)
    top = 0
    col_lines = []
    if cl:
        col_lines = [_wrap(probe, cl[j] if j < len(cl) else "", font, cw - 8, 3) for j in range(cols)]
        top = max(len(l) for l in col_lines) * line_h + gap * 2

    W = left + cols * cw + (cols + 1) * gap
    H = top + len(rows) * ch + (len(rows) + 1) * gap
    sheet = Image.new("RGB", (W, H), colors["bg"])
    draw = ImageDraw.Draw(sheet)

    for j, lines in enumerate(col_lines):
        x0 = left + gap + j * (cw + gap)
        y = gap + (top - gap * 2 - len(lines) * line_h)
        for line in lines:
            tw = draw.textlength(line, font=font)
            draw.text((x0 + (cw - tw) / 2, y), line, fill=colors["fg"], font=font)
            y += line_h

    for i, (path, frames) in enumerate(rows):
        y0 = top + gap + i * (ch + gap)
        if rl:
            text = rl[i] if i < len(rl) else ""
            lines = _wrap(draw, text, font, left - gap * 2, max(1, ch // line_h))
            ty = y0 + (ch - len(lines) * line_h) / 2
            for line in lines:
                tw = draw.textlength(line, font=font)
                draw.text((left - gap - tw, ty), line, fill=colors["fg"], font=font)
                ty += line_h
        for j, im in enumerate(frames):
            if im is None:
                continue
            x0 = left + gap + j * (cw + gap)
            if fit == "stretch":
                im = im.resize((cw, ch), Image.LANCZOS)
            elif fit == "fit" or im.width > cw or im.height > ch:
                s = min(cw / im.width, ch / im.height)
                if abs(s - 1) > 1e-3:
                    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
            sheet.paste(im, (x0 + (cw - im.width) // 2, y0 + (ch - im.height) // 2))
    return sheet


class TreeToGrid(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_TreeToGrid", display_name="Tree → Grid", category=CAT_IMAGE,
            description="XY sheet from an image tree: each branch is a row, each item a column. "
                        "Use Flip Matrix to swap axes.",
            search_aliases=["xy plot", "grid", "contact sheet", "image grid", "comparison"],
            is_input_list=True,
            inputs=[
                tree_in("images", tooltip="Image tree (or a plain image list = one row)"),
                tree_in("row_labels", optional=True, tooltip="One label per row (any values)"),
                tree_in("col_labels", optional=True, tooltip="One label per column (any values)"),
                IO.Combo.Input("fit", options=["fit", "original", "stretch"], default="fit",
                               tooltip="How images of different sizes fill a cell"),
                IO.Int.Input("cell_size", default=0, min=0, max=8192, step=8,
                             tooltip="Longest side of a cell in px; 0 = largest image"),
                IO.Int.Input("gap", default=8, min=0, max=256),
                IO.Int.Input("font_size", default=24, min=8, max=200),
                IO.Combo.Input("theme", options=["light", "dark"], default="light"),
                IO.Boolean.Input("path_labels", default=False,
                                 tooltip="Label rows with their branch path when no row labels are given"),
            ],
            outputs=[IO.Image.Output(display_name="image")])

    @classmethod
    def execute(cls, images, row_labels=None, col_labels=None, fit="fit", cell_size=0, gap=8,
                font_size=24, theme="light", path_labels=False) -> IO.NodeOutput:
        sheet = build_grid(images, _labels(row_labels), _labels(col_labels), unwrap(fit),
                           unwrap(cell_size), unwrap(gap), unwrap(font_size), unwrap(theme),
                           unwrap(path_labels))
        arr = np.asarray(sheet, dtype=np.float32) / 255.0
        return IO.NodeOutput(torch.from_numpy(arr)[None])


NODES = [TreeToGrid]
