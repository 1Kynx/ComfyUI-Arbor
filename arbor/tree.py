"""Grasshopper-style data tree.

A tree is an ordered mapping of *paths* to *branches*:

    {0;0} -> [a, b, c]
    {0;1} -> [d, e]

A path is a tuple of non-negative ints, written ``{0;1}``. A branch is a plain
Python list whose items can be anything ComfyUI passes around (numbers,
strings, IMAGE tensors, LATENT dicts, ...). A branch may also carry a *name*,
the value it stands for (XY Lists names each row after its x value), which the
Panel shows and Image Grid uses as the row label. Trees are immutable by convention:
every operation returns a new tree and never mutates its input, because
ComfyUI caches node outputs and hands the same object to several consumers.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Iterator

Path = tuple[int, ...]


class DataTree:
    __slots__ = ("branches", "names")

    def __init__(self, branches: dict[Path, list] | None = None, names: dict[Path, Any] | None = None):
        self.branches: dict[Path, list] = {}
        if branches:
            for path, items in branches.items():
                self.branches[tuple(int(i) for i in path)] = list(items)
        self.names: dict[Path, Any] = {p: v for p, v in (names or {}).items() if p in self.branches}

    # ------------------------------------------------------------ queries
    def paths(self) -> list[Path]:
        return list(self.branches.keys())

    def items(self) -> Iterator[tuple[Path, list]]:
        return iter(self.branches.items())

    def flat(self) -> list:
        out = []
        for items in self.branches.values():
            out.extend(items)
        return out

    @property
    def branch_count(self) -> int:
        return len(self.branches)

    @property
    def item_count(self) -> int:
        return sum(len(v) for v in self.branches.values())

    @property
    def depth(self) -> int:
        return max((len(p) for p in self.branches), default=0)

    def map_items(self, fn: Callable[[Any], Any]) -> "DataTree":
        return DataTree({p: [fn(v) for v in items] for p, items in self.branches.items()}, self.names)

    def map_branches(self, fn: Callable[[Path, list], list]) -> "DataTree":
        """Same paths (and names), new items."""
        return DataTree({p: fn(p, list(items)) for p, items in self.branches.items()}, self.names)

    def __len__(self) -> int:
        return self.item_count

    def __repr__(self) -> str:
        return f"DataTree({self.branch_count} branches, {self.item_count} items)"


# ---------------------------------------------------------------- paths

def format_path(path: Iterable[int]) -> str:
    return "{" + ";".join(str(i) for i in path) + "}"


_PATH_SPLIT = re.compile(r"[;,\s]+")


def parse_path(text: str) -> Path:
    body = str(text).strip().strip("{}()[]").strip()
    if not body:
        return (0,)
    try:
        return tuple(int(t) for t in _PATH_SPLIT.split(body) if t)
    except ValueError:
        raise ValueError(f"Invalid path {text!r}: use a form like {{0;1}}") from None


# ---------------------------------------------------------------- coercion

def unwrap(value, default=None):
    """First element of an is_input_list widget value."""
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


def to_tree(value) -> DataTree:
    """Coerce whatever arrived on an input into a tree.

    Nodes that accept trees run with ``is_input_list``, so ``value`` is the
    full list ComfyUI collected for the socket:

    - ``[tree]``            -> that tree
    - ``[tree, tree, ...]`` -> entwined: input i lands under ``{i;...}``
    - ``[a, b, c]``         -> one branch ``{0}`` holding the plain items
    """
    if value is None:
        return DataTree()
    if isinstance(value, DataTree):
        return value
    if not isinstance(value, list):
        value = [value]
    value = [v for v in value if v is not None]
    if value and all(isinstance(v, DataTree) for v in value):
        if len(value) == 1:
            return value[0]
        out: dict[Path, list] = {}
        for i, t in enumerate(value):
            for p, items in t.items():
                out[(i,) + p] = items
        return DataTree(out)
    return DataTree({(0,): value})


def split_batch(value) -> list:
    """Split IMAGE/MASK batches and LATENT dicts into single-frame items."""
    try:
        import torch
    except ImportError:  # pragma: no cover - torch always exists in ComfyUI
        return [value]
    if isinstance(value, torch.Tensor) and value.dim() >= 3 and value.shape[0] > 1:
        return [value[i:i + 1] for i in range(value.shape[0])]
    if isinstance(value, dict) and isinstance(value.get("samples"), torch.Tensor):
        s = value["samples"]
        if s.shape[0] > 1:
            return [{**value, "samples": s[i:i + 1]} for i in range(s.shape[0])]
    return [value]


# ---------------------------------------------------------------- structure ops

def graft(tree: DataTree) -> DataTree:
    out = {}
    for p, items in tree.items():
        if not items:  # an empty branch stays (empty), like Grasshopper, so branches keep lining up
            out[p] = []
        for j, v in enumerate(items):
            out[p + (j,)] = [v]
    return DataTree(out)


def flatten(tree: DataTree, path: Path = (0,)) -> DataTree:
    return DataTree({path: tree.flat()})


def simplify(tree: DataTree) -> DataTree:
    """Drop path indices every branch shares, keeping at least one."""
    paths = tree.paths()
    if len(paths) <= 1:
        return DataTree({(0,): items for items in tree.branches.values()}) if paths else DataTree()
    length = min(len(p) for p in paths)
    keep = [i for i in range(length) if len({p[i] for p in paths}) > 1]
    keep += list(range(length, max(len(p) for p in paths)))
    out: dict[Path, list] = {}
    for p, items in tree.items():
        np_ = tuple(p[i] for i in keep if i < len(p)) or (0,)
        out.setdefault(np_, []).extend(items)
    return DataTree(out)


def flip_matrix(tree: DataTree) -> DataTree:
    """Rows become columns: item j of every branch goes to branch {j}."""
    rows = list(tree.branches.values())
    width = max((len(r) for r in rows), default=0)
    return DataTree({(j,): [r[j] for r in rows if j < len(r)] for j in range(width)})


def shift_paths(tree: DataTree, offset: int) -> DataTree:
    """offset > 0 drops leading indices, offset < 0 drops trailing ones.

    Branches whose shortened paths collide are joined, which is how
    Grasshopper groups data back up after a Graft.
    """
    out: dict[Path, list] = {}
    for p, items in tree.items():
        if offset > 0:
            np_ = p[offset:]
        elif offset < 0:
            np_ = p[:offset]
        else:
            np_ = p
        out.setdefault(np_ or (0,), []).extend(items)
    return DataTree(out)


def merge(trees: list[DataTree]) -> DataTree:
    out: dict[Path, list] = {}
    for t in trees:
        for p, items in t.items():
            out.setdefault(p, []).extend(items)
    return DataTree(out)


def entwine(trees: list[DataTree]) -> DataTree:
    out: dict[Path, list] = {}
    for i, t in enumerate(trees):
        for p, items in t.items():
            out[(i,) + p] = list(items)
    return DataTree(out)


def renumber(tree: DataTree) -> DataTree:
    paths = tree.paths()
    return DataTree({(i,): tree.branches[p] for i, p in enumerate(paths)},
                    {(i,): tree.names[p] for i, p in enumerate(paths) if p in tree.names})


def match_item(tree: DataTree, k: int, j: int):
    """Longest-list matching: item j of branch k, repeating the last branch / item."""
    rows = list(tree.branches.values())
    if not rows:
        return None
    items = rows[min(k, len(rows) - 1)]
    return items[min(j, len(items) - 1)] if items else None


def get_branch(tree: DataTree, path: Path | None = None, index: int | None = None) -> DataTree:
    if path is not None:
        if path not in tree.branches:
            raise KeyError(f"Path {format_path(path)} not in tree; it has "
                           + ", ".join(format_path(p) for p in tree.paths()[:8]))
    else:
        paths = tree.paths()
        if not paths:
            return DataTree()
        path = paths[index % len(paths)]
    return DataTree({path: tree.branches[path]}, tree.names)


# ---------------------------------------------------------------- list ops

_TRUTHY = {"t", "true", "1", "y", "yes", "on"}
_FALSY = {"f", "false", "0", "n", "no", "off", ""}


def to_bool(v) -> bool:
    """Native BOOLEAN, numbers (0 = False) and 'true'/'false'-style text."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        t = v.strip().lower()
        if t in _TRUTHY:
            return True
        if t in _FALSY:
            return False
        raise ValueError(f"{v!r} is not true/false")
    if v is None:
        return False
    try:  # single-element tensors and the like
        return bool(v)
    except Exception:
        raise ValueError(f"{type(v).__name__} is not true/false") from None


def parse_pattern(text: str) -> list[bool]:
    """'T F', 'true,false', '1 0 1', 'TFT' -> [True, False, ...]"""
    s = str(text).strip().lower()
    if not s:
        return [True]
    tokens = [t for t in re.split(r"[\s,;|]+", s) if t]
    if len(tokens) == 1 and len(tokens[0]) > 1 and set(tokens[0]) <= set("tf10"):
        tokens = list(tokens[0])
    try:
        return [to_bool(t) for t in tokens]
    except ValueError as e:
        raise ValueError(f"Pattern: {e}") from None


def resolve_pattern(value) -> "list[bool] | DataTree":
    """A pattern socket value: typed text, native BOOLEAN(s), or a tree of booleans.

    Typed text -> one repeating list. Booleans / trees -> a tree of bools that
    is matched branch by branch (longest list), like Grasshopper.
    """
    items = value if isinstance(value, list) else [value]
    if len(items) == 1 and isinstance(items[0], str):
        return parse_pattern(items[0])
    t = to_tree(items)
    return t.map_items(to_bool)


def _branch_pattern(pattern, k: int) -> list[bool]:
    if isinstance(pattern, DataTree):
        rows = list(pattern.branches.values())
        row = rows[min(k, len(rows) - 1)] if rows else []
        return row or [True]
    return pattern or [True]


def parse_indices(spec, n: int) -> list[int]:
    """'0, 2, -1, 3-5, 1:4, ::2' -> indices into a list of n items.

    Ranges ``a-b`` are inclusive, slices are Python-style and clipped to n;
    single indices are returned as written, so the caller decides what an
    out-of-range index means (wrap, null or an error).
    """
    out = []
    for tok in re.split(r"[\s,;]+", str(spec).strip()):
        if not tok:
            continue
        if re.fullmatch(r"\d+-\d+", tok):
            a, b = map(int, tok.split("-"))
            out.extend(range(a, b + (1 if b >= a else -1), 1 if b >= a else -1))
        elif ":" in tok:
            try:
                out.extend(range(n)[slice(*[int(p) if p else None for p in tok.split(":")])])
            except (TypeError, ValueError):
                raise ValueError(f"can't read slice {tok!r}") from None
        else:
            try:
                out.append(int(float(tok)))
            except ValueError:
                raise ValueError(f"can't read index {tok!r}") from None
    return out


def list_items(tree: DataTree, spec, wrap: bool = True) -> DataTree:
    """Pick items from every branch; out-of-range indices wrap, or give null."""
    def pick(_, items):
        n = len(items)
        if wrap:
            return [items[i % n] for i in parse_indices(spec, n)] if n else []
        return [items[i] if -n <= i < n else None for i in parse_indices(spec, n)]
    return tree.map_branches(pick)


def dispatch(tree: DataTree, pattern) -> tuple[DataTree, DataTree]:
    """Split by a repeating pattern (list) or a per-branch boolean tree."""
    a, b = {}, {}
    for k, (path, items) in enumerate(tree.items()):
        pat = _branch_pattern(pattern, k)
        a[path] = [v for j, v in enumerate(items) if pat[j % len(pat)]]
        b[path] = [v for j, v in enumerate(items) if not pat[j % len(pat)]]
    return DataTree(a), DataTree(b)


def partition(tree: DataTree, size: int) -> DataTree:
    size = max(1, int(size))
    out = {}
    for p, items in tree.items():
        for k in range(0, max(len(items), 1), size):
            chunk = items[k:k + size]
            if chunk or not items:
                out[p + (k // size,)] = chunk
    return DataTree(out)


def repeat(tree: DataTree, count: int, mode: str = "each") -> DataTree:
    count = max(1, int(count))
    if mode == "each":
        return tree.map_branches(lambda _, items: [v for v in items for _ in range(count)])
    return tree.map_branches(lambda _, items: items * count)


def _sort_key(v):
    if isinstance(v, bool):
        return (0, int(v), "")
    if isinstance(v, (int, float)):
        return (0, v, "")
    return (1, 0, str(v))


SORT_ORDERS = ("ascending", "descending", "reverse")


def sort_list(tree: DataTree, order: str = "ascending") -> DataTree:
    """Sort every branch (numbers before text), or just reverse it."""
    if order == "reverse":
        return tree.map_branches(lambda _, items: items[::-1])
    return tree.map_branches(lambda _, items: sorted(items, key=_sort_key, reverse=order == "descending"))


def cross_reference(a: DataTree, b: DataTree, group: bool = True) -> tuple[DataTree, DataTree]:
    """Every combination of A and B items, branch-matched (longest list).

    With ``group`` each A item gets its own sub-branch, so the result is a
    ready-made grid: rows = A values, columns = B values.
    """
    pa, pb = a.paths(), b.paths()
    if not pa or not pb:
        return DataTree(), DataTree()
    n = max(len(pa), len(pb))
    out_a: dict[Path, list] = {}
    out_b: dict[Path, list] = {}
    names: dict[Path, Any] = {}
    for k in range(n):
        path = pa[min(k, len(pa) - 1)] if len(pa) >= len(pb) else pb[min(k, len(pb) - 1)]
        items_a = a.branches[pa[min(k, len(pa) - 1)]]
        items_b = b.branches[pb[min(k, len(pb) - 1)]]
        for i, va in enumerate(items_a):
            key = path + (i,) if group else path
            out_a.setdefault(key, []).extend([va] * len(items_b))
            out_b.setdefault(key, []).extend(items_b)
            if group:
                names[key] = va
    return DataTree(out_a, names), DataTree(out_b, names)


def rebuild(values: list, shape: DataTree) -> DataTree:
    """Pour a flat list back into the branch layout (and names) of ``shape``."""
    total = shape.item_count
    if len(values) != total:
        raise ValueError(
            f"shape: got {len(values)} values but the shape holds {total} items. "
            "Connect the shape of the run that produced these values.")
    out, k = {}, 0
    for p, items in shape.items():
        out[p] = values[k:k + len(items)]
        k += len(items)
    return DataTree(out, shape.names)
