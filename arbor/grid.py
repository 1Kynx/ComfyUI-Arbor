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
    """One label per row. A tree with one branch per row gives its branch names
    when every branch has one, else the first item of each branch (Cross
    Reference's A repeats the row value); anything else is read flat."""
    if value is None:
        return None
    t = to_tree(value)
    if t.branch_count == n_rows and t.names and all(t.label(p) for p in t.paths()):
        return [t.label(p, label_of) for p in t.paths()]
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


def caption_rows(value, row_counts: list[int]) -> list[list[str]] | None:
    """Cell captions shaped like the grid (before wrapping): a tree with one branch per row
    is read branch by branch, anything else flat, cell by cell. Missing captions stay empty."""
    if value is None:
        return None
    t = to_tree(value)
    if t.branch_count == len(row_counts) > 1:
        rows = [[label_of(v) for v in items] for items in t.branches.values()]
    else:
        flat = [label_of(v) for v in t.flat()]
        rows, k = [], 0
        for n in row_counts:
            rows.append(flat[k:k + n])
            k += n
    return [[r[j] if j < len(r) else "" for j in range(n)] for r, n in zip(rows, row_counts)]


# ------------------------------------------------------------------ sheet

FITS = ["fit", "fill", "original", "stretch"]
LABEL_DIRS = ["auto", "horizontal", "vertical"]
CAPTION_STYLES = ["below", "overlay"]
CAPTION_LINES = 3


def fit_box(w: int, h: int, cw: int, ch: int, fit: str) -> tuple[int, int, bool]:
    """(width, height, crop) of a w×h picture in a cw×ch cell: fit scales it inside, fill scales it
    to cover the cell (crop=True: cut the overflow, centred), stretch fills the cell exactly,
    original keeps its size unless it is too large."""
    if fit == "stretch":
        return cw, ch, False
    if fit == "fill":
        s = max(cw / w, ch / h)
        return max(cw, round(w * s)), max(ch, round(h * s)), True
    if fit == "fit" or w > cw or h > ch:
        s = min(cw / w, ch / h)
        return max(1, round(w * s)), max(1, round(h * s)), False
    return w, h, False


def center_crop_box(w: int, h: int, cw: int, ch: int) -> tuple[int, int, int, int]:
    x, y = (w - cw) // 2, (h - ch) // 2
    return x, y, x + cw, y + ch


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
    """(rows, columns) the sheet will have before wrapping."""
    rows = tree.branch_count
    cols = max((sum(v.shape[0] if is_image(v) else 1 for v in items) for items in tree.branches.values()),
               default=0)
    return rows, cols


def wrap_rows(rows: list[list], columns: int) -> tuple[list[list], list[int]]:
    """Break every row (branch) into rows of at most `columns` cells. Returns the rows and,
    per original row, how many rows it became (its label spans them)."""
    if columns <= 0:
        return rows, [1] * len(rows)
    out, blocks = [], []
    for r in rows:
        chunks = [r[k:k + columns] for k in range(0, len(r), columns)] or [[]]
        out += chunks
        blocks.append(len(chunks))
    return out, blocks


def _is_cjk_only(text: str) -> bool:
    return bool(re.search(rf"[{_CJK}]", text)) and not re.search(r"[A-Za-z0-9]", text)


class Sheet:
    """A labelled grid: the background (labels and captions drawn) and where each cell sits."""

    def __init__(self, image, left, top, cw, ch, gap, cap_h, cap_font, cap_line, colors):
        self.image, self.left, self.top, self.cw, self.ch, self.gap = image, left, top, cw, ch, gap
        self.cap_h, self.cap_font, self.cap_line, self.colors = cap_h, cap_font, cap_line, colors

    def cell(self, i: int, j: int) -> tuple[int, int]:
        """Top-left corner of row i, column j."""
        return (self.left + self.gap + j * (self.cw + self.gap),
                self.top + self.gap + i * (self.ch + self.cap_h + self.gap))

    def place(self, i: int, j: int, w: int, h: int) -> tuple[int, int]:
        """Top-left corner of a w×h picture centred in its cell."""
        x0, y0 = self.cell(i, j)
        return x0 + (self.cw - w) // 2, y0 + (self.ch - h) // 2

    def overlay(self, text: str, w: int) -> Image.Image | None:
        """A caption bar (RGBA) for the bottom of a w-wide picture, or None for no text."""
        if not text.strip():
            return None
        probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        lines = _wrap(probe, text, self.cap_font, max(8, w - 12), CAPTION_LINES)
        bar = Image.new("RGBA", (w, len(lines) * self.cap_line + 8), (0, 0, 0, 140))
        d = ImageDraw.Draw(bar)
        y = 4
        for line in lines:
            d.text(((w - d.textlength(line, font=self.cap_font)) / 2, y), line, fill=(255, 255, 255, 255),
                   font=self.cap_font)
            y += self.cap_line
        return bar


def _draw_vertical(sheet: Image.Image, text: str, font, line_h: int, x0: int, x1: int, y0: int, y1: int, fg):
    """A row label standing up in the box (x0..x1, y0..y1): Chinese / Japanese characters stacked
    upright (columns right to left), anything else rotated to read bottom to top."""
    box_w, box_h = x1 - x0, y1 - y0
    draw = ImageDraw.Draw(sheet)
    if _is_cjk_only(text):
        chars = [c for c in text if not c.isspace()]
        step = line_h
        per_col = max(1, box_h // step)
        n_cols = min(CAPTION_LINES, -(-len(chars) // per_col), max(1, box_w // line_h))
        cols = [chars[k * per_col:(k + 1) * per_col] for k in range(n_cols)]
        if len(chars) > per_col * n_cols:
            cols[-1][-1] = "︙"  # vertical ellipsis
        width = n_cols * line_h
        for k, col in enumerate(cols):  # first column on the right
            cx = x0 + (box_w + width) / 2 - (k + 0.5) * line_h
            y = y0 + (box_h - len(col) * step) / 2
            for c in col:
                draw.text((cx - draw.textlength(c, font=font) / 2, y), c, fill=fg, font=font)
                y += step
        return
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines = _wrap(probe, text, font, max(8, box_h - 8), max(1, min(CAPTION_LINES, box_w // line_h)))
    tile = Image.new("RGBA", (box_h, len(lines) * line_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    for k, line in enumerate(lines):
        d.text(((box_h - d.textlength(line, font=font)) / 2, k * line_h), line, fill=fg, font=font)
    tile = tile.rotate(90, expand=True)
    sheet.paste(tile, (int(x0 + (box_w - tile.width) / 2), int(y0 + (box_h - tile.height) / 2)), tile)


def layout_sheet(sizes: list[list[tuple[int, int] | None]], row_labels=None, col_labels=None, cell_size=0,
                 gap=8, font_size=24, theme="light", path_labels=False, paths=(), what="Image Grid",
                 even=False, blocks: list[int] | None = None, captions: list[list[str]] | None = None,
                 caption_style="below", label_dir="auto") -> Sheet:
    """Lay out rows of pictures of the given (w, h) sizes (None = empty cell) and draw the labels.
    `blocks` gives how many rows each row label spans (wrapped branches), `captions` one text per
    cell (drawn below it here; overlay captions are drawn by the caller with Sheet.overlay).
    `even` rounds the sheet to even sides (video encoders need them)."""
    found = [wh for row in sizes for wh in row if wh]
    if not found:
        raise ValueError(f"{what}: nothing to lay out")
    blocks = blocks or [1] * len(sizes)
    cols = max(len(r) for r in sizes)
    cw = max(w for w, _ in found)
    ch = max(h for _, h in found)
    if cell_size > 0:  # longest side of a cell
        s = cell_size / max(cw, ch)
        cw, ch = max(1, round(cw * s)), max(1, round(ch * s))

    rl = row_labels or ([format_path(p) for p in paths] if path_labels else None)
    colors = THEMES[theme]
    font = _font(font_size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    line_h = int(font_size * 1.3)
    cap_size = max(10, round(font_size * 0.75))
    cap_font, cap_line = _font(cap_size), int(cap_size * 1.3)

    # captions below the cells: one height for every row, from the longest caption
    cap_h = 0
    cap_lines = None
    if captions and caption_style == "below" and any(c.strip() for r in captions for c in r):
        cap_lines = [[_wrap(probe, c, cap_font, cw - 8, CAPTION_LINES) for c in r] for r in captions]
        cap_h = max(len(l) for r in cap_lines for l in r) * cap_line + gap // 2 + 2

    # row labels: horizontal while they fit in two lines, else standing up (label_dir auto)
    row_h = ch + cap_h
    starts = [sum(blocks[:k]) for k in range(len(blocks))]
    span = lambda k: blocks[k] * row_h + (blocks[k] - 1) * gap
    left, vertical = 0, False
    if rl:
        widest = max(int(probe.textlength(t, font=font)) for t in rl)
        h_left = max(min(widest + gap * 2, int(cw * 0.9) + gap), font_size * 3)
        lines = [_wrap(probe, t, font, h_left - gap * 2, 99) for t in rl]
        vertical = label_dir == "vertical" or (label_dir == "auto" and any(len(l) > 2 for l in lines))
        if vertical:
            need = 1
            for k, t in enumerate(rl[:len(blocks)]):
                if _is_cjk_only(t):
                    need = max(need, min(CAPTION_LINES, -(-len(t.replace(" ", "")) // max(1, span(k) // line_h))))
                else:
                    need = max(need, len(_wrap(probe, t, font, max(8, span(k) - 8), CAPTION_LINES)))
            left = need * line_h + gap * 2
        else:
            left = h_left

    col_lines = [_wrap(probe, col_labels[j] if j < len(col_labels) else "", font, cw - 8, 3)
                 for j in range(cols)] if col_labels else []
    top = max(len(l) for l in col_lines) * line_h + gap * 2 if col_lines else 0

    W = left + cols * cw + (cols + 1) * gap
    H = top + len(sizes) * row_h + (len(sizes) + 1) * gap
    if even:
        W, H = W + W % 2, H + H % 2
    sheet = Image.new("RGB", (W, H), colors["bg"])
    draw = ImageDraw.Draw(sheet)

    for j, lines in enumerate(col_lines):
        x0 = left + gap + j * (cw + gap)
        y = gap + (top - gap * 2 - len(lines) * line_h)
        for line in lines:
            draw.text((x0 + (cw - draw.textlength(line, font=font)) / 2, y), line, fill=colors["fg"], font=font)
            y += line_h

    if rl:
        for k, start in enumerate(starts):
            text = rl[k] if k < len(rl) else ""
            if not text:
                continue
            y0 = top + gap + start * (row_h + gap)
            if vertical:
                _draw_vertical(sheet, text, font, line_h, gap, left - gap, y0, y0 + span(k) - cap_h, colors["fg"])
                continue
            lines = _wrap(draw, text, font, left - gap * 2, max(1, (span(k) - cap_h) // line_h))
            ty = y0 + (span(k) - cap_h - len(lines) * line_h) / 2
            for line in lines:
                draw.text((left - gap - draw.textlength(line, font=font), ty), line, fill=colors["fg"], font=font)
                ty += line_h

    out = Sheet(sheet, left, top, cw, ch, gap, cap_h, cap_font, cap_line, colors)
    if cap_lines:
        for i, row in enumerate(cap_lines):
            for j, lines in enumerate(row):
                x0, y0 = out.cell(i, j)
                y = y0 + ch + gap // 2
                for line in lines:
                    draw.text((x0 + (cw - draw.textlength(line, font=cap_font)) / 2, y), line, fill=colors["fg"],
                              font=cap_font)
                    y += cap_line
    return out


def build_grid(tree: DataTree, row_labels=None, col_labels=None, fit="fit", cell_size=0, gap=8,
               font_size=24, theme="light", path_labels=False, columns=0, captions=None,
               caption_style="below", label_dir="auto") -> Image.Image:
    branches = [(p, _frames(items)) for p, items in tree.items()]
    branches = [b for b in branches if b[1]]
    if not any(im is not None for _, r in branches for im in r):
        raise ValueError("Image Grid: no images to lay out")
    caps = caption_rows(captions, [len(r) for _, r in branches])
    rows, blocks = wrap_rows([r for _, r in branches], columns)
    cap_rows = wrap_rows(caps, columns)[0] if caps else None
    sheet = layout_sheet([[im.size if im else None for im in r] for r in rows], row_labels,
                         None if columns > 0 else col_labels, cell_size, gap, font_size, theme, path_labels,
                         [p for p, _ in branches], blocks=blocks, captions=cap_rows, caption_style=caption_style,
                         label_dir=label_dir)
    for i, frames in enumerate(rows):
        for j, im in enumerate(frames):
            if im is None:
                continue
            w, h, crop = fit_box(im.width, im.height, sheet.cw, sheet.ch, fit)
            if (w, h) != im.size:
                im = im.resize((w, h), Image.LANCZOS)
            if crop:
                im = im.crop(center_crop_box(w, h, sheet.cw, sheet.ch))
            x, y = sheet.place(i, j, im.width, im.height)
            sheet.image.paste(im, (x, y))
            if cap_rows and caption_style == "overlay":
                bar = sheet.overlay(cap_rows[i][j], im.width)
                if bar:
                    sheet.image.paste(bar, (x, y + im.height - bar.height), bar)
    return sheet.image
