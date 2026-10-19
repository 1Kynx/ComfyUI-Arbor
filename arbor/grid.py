"""Drawing an image tree as a labelled grid sheet (used by the Image Grid node)."""

from __future__ import annotations

import os
import re

from PIL import Image, ImageDraw, ImageFont

from .preview import is_image, label_of, to_pil
from .tree import DataTree, format_path, to_tree

THEMES = {
    "light": {"bg": (255, 255, 255), "fg": (34, 34, 38)},
    "dark": {"bg": (24, 24, 27), "fg": (232, 232, 236)},
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


# CJK ideographs, kana, hangul and full-width forms wrap per character, other text between words
_CJK = "".join(f"{chr(a)}-{chr(b)}" for a, b in ((0x2E80, 0x9FFF), (0xAC00, 0xD7AF), (0xF900, 0xFAFF),
                                                 (0xFF00, 0xFFEF)))
_TOKENS = re.compile(rf"[{_CJK}]|[^\s{_CJK}]+|\s+")


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int) -> list[str]:
    """Greedy wrap between words (every CJK character counts as a word); a word wider than
    the line is broken by characters. "…" marks text that did not fit."""
    def fits(t):
        return draw.textlength(t, font=font) <= width

    tokens = _TOKENS.findall(text.replace("\n", " "))
    lines, cur = [], ""
    while tokens and len(lines) < max_lines:
        tok = tokens.pop(0)
        if fits(cur + tok):
            cur += tok
        elif tok.isspace():  # break at the space
            lines.append(cur)
            cur = ""
        elif cur.strip():  # the word moves to the next line
            lines.append(cur.rstrip())
            cur = ""
            tokens.insert(0, tok)
        else:  # a word wider than the line
            k = next((i for i in range(len(tok) - 1, 0, -1) if fits(tok[:i])), 1)
            lines.append(tok[:k])
            tokens.insert(0, tok[k:])
            cur = ""
    cut = any(not t.isspace() for t in tokens)
    if cur.strip():
        if len(lines) < max_lines:
            lines.append(cur.rstrip())
        else:
            cut = True
    if cut and lines:
        last = lines[-1]
        while last and not fits(last + "…"):
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


# ------------------------------------------------------------------ labels

def _flat_labels(value) -> list[str]:
    return [label_of(v) for v in to_tree(value).flat()]


def row_labels_for(value, n_rows: int) -> list[str] | None:
    """One label per row. A tree with one branch per row (e.g. Cross Reference's
    A output, where every item of a branch repeats the row value) gives the
    first item of each branch; anything else is read flat."""
    if value is None:
        return None
    t = to_tree(value)
    if t.branch_count == n_rows > 1 and all(t.branches.values()):
        return [label_of(items[0]) for items in t.branches.values()]
    return _flat_labels(t)


def col_labels_for(value, n_cols: int) -> list[str] | None:
    """One label per column. A tree whose branches each hold a full row of
    column values (XY Lists' shape, Cross Reference's B) gives its first branch."""
    if value is None:
        return None
    t = to_tree(value)
    if t.branch_count > 1:
        first = next(iter(t.branches.values()))
        if len(first) == n_cols:
            return [label_of(v) for v in first]
    return _flat_labels(t)


# ------------------------------------------------------------------ sheet

def _frames(items) -> list[Image.Image | None]:
    """Every frame of every item; non-images leave an empty cell."""
    out = []
    for v in items:
        if is_image(v):
            out.extend(to_pil(v[i]).convert("RGB") for i in range(v.shape[0]))
        else:
            out.append(None)
    return out


def grid_size(tree: DataTree) -> tuple[int, int]:
    """(rows, columns) the sheet will have."""
    rows = tree.branch_count
    cols = max((sum(v.shape[0] if is_image(v) else 1 for v in items) for items in tree.branches.values()),
               default=0)
    return rows, cols


def build_grid(tree: DataTree, row_labels=None, col_labels=None, fit="fit", cell_size=0, gap=8,
               font_size=24, theme="light", path_labels=False) -> Image.Image:
    rows = [(p, _frames(items)) for p, items in tree.items()]
    rows = [r for r in rows if r[1]]
    imgs = [im for _, r in rows for im in r if im is not None]
    if not imgs:
        raise ValueError("Image Grid: no images to lay out")

    cols = max(len(r) for _, r in rows)
    cw = max(im.width for im in imgs)
    ch = max(im.height for im in imgs)
    if cell_size > 0:  # longest side of a cell
        s = cell_size / max(cw, ch)
        cw, ch = max(1, round(cw * s)), max(1, round(ch * s))

    rl = row_labels or ([format_path(p) for p, _ in rows] if path_labels else None)
    colors = THEMES[theme]
    font = _font(font_size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    line_h = int(font_size * 1.3)

    left = 0
    if rl:
        left = min(max(int(probe.textlength(t, font=font)) for t in rl) + gap * 2, int(cw * 0.9) + gap)
        left = max(left, font_size * 3)
    col_lines = [_wrap(probe, col_labels[j] if j < len(col_labels) else "", font, cw - 8, 3)
                 for j in range(cols)] if col_labels else []
    top = max(len(l) for l in col_lines) * line_h + gap * 2 if col_lines else 0

    sheet = Image.new("RGB", (left + cols * cw + (cols + 1) * gap, top + len(rows) * ch + (len(rows) + 1) * gap),
                      colors["bg"])
    draw = ImageDraw.Draw(sheet)

    for j, lines in enumerate(col_lines):
        x0 = left + gap + j * (cw + gap)
        y = gap + (top - gap * 2 - len(lines) * line_h)
        for line in lines:
            draw.text((x0 + (cw - draw.textlength(line, font=font)) / 2, y), line, fill=colors["fg"], font=font)
            y += line_h

    for i, (_, frames) in enumerate(rows):
        y0 = top + gap + i * (ch + gap)
        if rl:
            lines = _wrap(draw, rl[i] if i < len(rl) else "", font, left - gap * 2, max(1, ch // line_h))
            ty = y0 + (ch - len(lines) * line_h) / 2
            for line in lines:
                draw.text((left - gap - draw.textlength(line, font=font), ty), line, fill=colors["fg"], font=font)
                ty += line_h
        for j, im in enumerate(frames):
            if im is None:
                continue
            if fit == "stretch":
                im = im.resize((cw, ch), Image.LANCZOS)
            elif fit == "fit" or im.width > cw or im.height > ch:
                s = min(cw / im.width, ch / im.height)
                if abs(s - 1) > 1e-3:
                    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
            x0 = left + gap + j * (cw + gap)
            sheet.paste(im, (x0 + (cw - im.width) // 2, y0 + (ch - im.height) // 2))
    return sheet
