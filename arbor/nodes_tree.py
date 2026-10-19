"""Building trees, reshaping them, and bridging to ComfyUI's native lists.

Every node here runs with ``is_input_list`` so a native list arriving on a
socket is received whole (and becomes branch {0}) instead of making the node
execute once per item. Widget values therefore arrive as 1-item lists and are
read through ``unwrap``.
"""

import re

from . import tree as T
from .common import IO, TREE, NUMBER, CAT_TREE, CAT_DATA, connected, data_out, tree_in, tree_out, to_tree, unwrap


def _schema(node_id, display_name, category, description, inputs, outputs, aliases=()):
    return IO.Schema(
        node_id=node_id, display_name=display_name, category=category,
        description=description, search_aliases=list(aliases),
        is_input_list=True, inputs=inputs, outputs=outputs)


# ======================================================================= build

class ConstructTree(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_ConstructTree", "Construct Tree", CAT_TREE,
            "Wrap any value, native list or batch into a data tree branch.",
            [IO.AnyType.Input("data", tooltip="Any value or native list"),
             IO.String.Input("path", default="{0}", tooltip="Branch path, e.g. {0} or {0;2}"),
             IO.Boolean.Input("split_batch", default=False,
                              tooltip="Split IMAGE / MASK / LATENT batches into one item per frame")],
            [tree_out()], ["tree", "wrap", "construct path"])

    @classmethod
    def execute(cls, data, path, split_batch) -> IO.NodeOutput:
        items = data if isinstance(data, list) else [data]
        if unwrap(split_batch):
            items = [f for v in items for f in T.split_batch(v)]
        return IO.NodeOutput(T.DataTree({T.parse_path(unwrap(path)): items}))


class NumberSeries(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_Series", "Series", CAT_DATA,
            "Arithmetic sequence: start, start+step, ... (count numbers).",
            [IO.Float.Input("start", default=0.0, step=0.1, min=-1e9, max=1e9),
             IO.Float.Input("step", default=1.0, step=0.1, min=-1e9, max=1e9),
             IO.Int.Input("count", default=5, min=1, max=10000),
             IO.Boolean.Input("as_int", default=False, tooltip="Output integers (for seeds, steps, ...)")],
            [data_out(NUMBER, "The numbers as plain data — connect straight to cfg, steps, seed…, "
                              "or to any Arbor input")], ["sequence", "arithmetic", "number list"])

    @classmethod
    def execute(cls, start, step, count, as_int) -> IO.NodeOutput:
        s, d, n = unwrap(start), unwrap(step), unwrap(count)
        vals = [s + d * i for i in range(n)]
        vals = [int(round(v)) for v in vals] if unwrap(as_int) else [round(v, 10) for v in vals]
        return IO.NodeOutput(vals)


class NumberRange(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_Range", "Range", CAT_DATA,
            "Evenly divide [start, end] into steps parts (steps + 1 numbers, both ends included).",
            [IO.Float.Input("start", default=0.0, step=0.1, min=-1e9, max=1e9),
             IO.Float.Input("end", default=1.0, step=0.1, min=-1e9, max=1e9),
             IO.Int.Input("steps", default=4, min=1, max=10000),
             IO.Boolean.Input("as_int", default=False)],
            [data_out(NUMBER, "The numbers as plain data — connect straight to cfg, denoise…, "
                              "or to any Arbor input")], ["linspace", "domain", "interpolate"])

    @classmethod
    def execute(cls, start, end, steps, as_int) -> IO.NodeOutput:
        a, b, n = unwrap(start), unwrap(end), unwrap(steps)
        vals = [a + (b - a) * i / n for i in range(n + 1)]
        vals = [int(round(v)) for v in vals] if unwrap(as_int) else [round(v, 10) for v in vals]
        return IO.NodeOutput(vals)


class SplitText(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_SplitText", "Split Text", CAT_DATA,
            "One item per line (or separator). A blank line starts a new branch.",
            [IO.String.Input("text", multiline=True, default=""),
             IO.Combo.Input("separator", options=["newline", ",", ";", "|"], default="newline"),
             IO.Boolean.Input("blank_line_branches", default=True,
                              tooltip="Paragraphs separated by an empty line become branches {0},{1},..."),
             IO.Boolean.Input("strip", default=True)],
            [data_out(IO.String, "Every item as plain text data (paragraphs one after another)"),
             tree_out(tooltip="One branch per paragraph")], ["prompt list", "lines", "text list", "wildcard"])

    @classmethod
    def execute(cls, text, separator, blank_line_branches, strip) -> IO.NodeOutput:
        text = str(unwrap(text, "")).replace("\r\n", "\n")
        sep = unwrap(separator)
        blocks = re.split(r"\n\s*\n", text) if unwrap(blank_line_branches) else [text]
        out = {}
        for block in blocks:
            parts = block.split("\n") if sep == "newline" else re.split(rf"[{re.escape(sep)}\n]", block)
            if unwrap(strip):
                parts = [p.strip() for p in parts]
            parts = [p for p in parts if p != ""]
            if parts:
                out[(len(out),)] = parts
        tree = T.DataTree(out or {(0,): []})
        return IO.NodeOutput(tree.flat(), tree)


# ======================================================================= bridge

class TreeToList(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_TreeToList", "Tree → List", CAT_TREE,
            "Flatten a tree into a native ComfyUI list. Downstream nodes then run once "
            "per item; collect the results with List → Tree.",
            [tree_in()],
            [data_out(tooltip="Every item as plain data: downstream nodes run once per item"),
             IO.Int.Output(display_name="count")],
            ["flatten to list", "batch run", "iterate", "for each"])

    @classmethod
    def execute(cls, tree) -> IO.NodeOutput:
        items = to_tree(tree).flat()
        if not items:
            raise ValueError("Tree → List: the tree is empty")
        return IO.NodeOutput(items, len(items))


MAX_COMBOS = 10000


class XYLists(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_XYLists", display_name="XY Lists", category=CAT_TREE,
            description="One step from parameter values to a batch run: every combination of x, y "
                        "(and z) as aligned native lists — wire x, y, z straight into ordinary nodes "
                        "(they run once per combination) — plus the grid shape for List → Tree. "
                        "Rows = x, columns = y (with z: rows = x × y, columns = z).",
            search_aliases=["xy plot", "xyz plot", "grid search", "parameter sweep", "combinations",
                            "cartesian", "batch combinations"],
            is_input_list=True,
            inputs=[
                tree_in("x", tooltip="Values for rows: a tree, a list or a single value"),
                tree_in("y", optional=True, tooltip="Values for columns"),
                tree_in("z", optional=True, tooltip="Optional third parameter (columns; rows become x × y)"),
                IO.Combo.Input("mode", options=["cross", "zip"], default="cross",
                               tooltip="cross: every combination · zip: item by item (longest list)"),
            ],
            outputs=[
                IO.AnyType.Output(display_name="x", is_output_list=True),
                IO.AnyType.Output(display_name="y", is_output_list=True),
                IO.AnyType.Output(display_name="z", is_output_list=True),
                tree_out("shape", tooltip="Grid layout of the runs: connect to List → Tree's shape. "
                                          "Its items are the column values, so it also works as col_labels"),
                IO.Int.Output(display_name="count"),
            ])

    @classmethod
    def execute(cls, x, mode, y=None, z=None) -> IO.NodeOutput:
        xs = to_tree(x).flat()
        ys = to_tree(y).flat() if connected(y) else []
        zs = to_tree(z).flat() if connected(z) else []
        if not xs:
            raise ValueError("XY Lists: x is empty")
        if connected(y) and not ys or connected(z) and not zs:
            raise ValueError("XY Lists: y or z is connected but empty")
        ox, oy, oz, shape = [], [], [], {}

        if unwrap(mode) == "zip":
            n = max(len(xs), len(ys), len(zs))
            pick = lambda vals, i: vals[min(i, len(vals) - 1)] if vals else None
            for i in range(n):
                ox.append(pick(xs, i)), oy.append(pick(ys, i)), oz.append(pick(zs, i))
            shape[(0,)] = list(ox)  # one row, labelled by x
        else:
            total = len(xs) * max(1, len(ys)) * max(1, len(zs))
            if total > MAX_COMBOS:
                raise ValueError(f"XY Lists: {total} combinations (max {MAX_COMBOS})")
            for i, xv in enumerate(xs):
                for j, yv in enumerate(ys or [None]):
                    for zv in zs or [None]:
                        ox.append(xv), oy.append(yv), oz.append(zv)
                    if zs:
                        shape[(i, j)] = list(zs)
                if not zs:
                    shape[(i,)] = list(ys) if ys else [xv]
            if not ys and not zs:  # a single parameter is one row
                shape = {(0,): list(xs)}
        return IO.NodeOutput(ox, oy, oz, T.DataTree(shape), len(ox))


class ListToTree(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_ListToTree", "List → Tree", CAT_TREE,
            "Collect a native list back into a tree. Connect the tree you fed into Tree → List "
            "as shape to restore its branches.",
            [IO.AnyType.Input("list", tooltip="Native list (e.g. the per-item results)"),
             tree_in("shape", optional=True, tooltip="Tree whose branch layout to copy"),
             IO.Boolean.Input("split_batch", default=False,
                              tooltip="Split batches into frames before rebuilding")],
            [tree_out()], ["collect", "gather", "unflatten", "rebuild"])

    @classmethod
    def execute(cls, list, shape=None, split_batch=False) -> IO.NodeOutput:
        values = list if isinstance(list, type([])) else [list]
        if unwrap(split_batch):
            values = [f for v in values for f in T.split_batch(v)]
        if not connected(shape):
            return IO.NodeOutput(T.DataTree({(0,): values}))
        return IO.NodeOutput(T.rebuild(values, to_tree(shape)))


# ======================================================================= structure

def _unary(node_id, name, desc, fn, aliases=(), extra_inputs=()):
    """Factory for tree -> tree nodes with a few widgets."""

    class _Node(IO.ComfyNode):
        @classmethod
        def define_schema(cls):
            return _schema(node_id, name, CAT_TREE, desc,
                           [tree_in(), *[mk() for mk in extra_inputs]], [tree_out()], aliases)

        @classmethod
        def execute(cls, tree, **kw) -> IO.NodeOutput:
            return IO.NodeOutput(fn(to_tree(tree), **{k: unwrap(v) for k, v in kw.items()}))

    _Node.__name__ = node_id
    _Node.__qualname__ = node_id
    return _Node


Graft = _unary("Arbor_Graft", "Graft", "Every item gets its own branch: {p} → {p;i}.",
               T.graft, ["graft tree"])
Flatten = _unary("Arbor_Flatten", "Flatten", "Put every item into one branch.",
                 lambda t, path: T.flatten(t, T.parse_path(path)), ["flatten tree"],
                 [lambda: IO.String.Input("path", default="{0}")])
Simplify = _unary("Arbor_Simplify", "Simplify", "Remove path indices that every branch shares.",
                  T.simplify, ["simplify tree"])
FlipMatrix = _unary("Arbor_FlipMatrix", "Flip Matrix",
                    "Swap rows and columns: item j of every branch goes to {j}.",
                    T.flip_matrix, ["transpose", "swap xy"])
ShiftPaths = _unary("Arbor_ShiftPaths", "Shift Paths",
                    "Drop path indices: +1 removes the first, -1 the last. "
                    "Colliding branches are joined (undoes Graft).",
                    T.shift_paths, ["trim tree", "group"],
                    [lambda: IO.Int.Input("offset", default=-1, min=-16, max=16)])
Renumber = _unary("Arbor_Renumber", "Renumber",
                  "Re-index branches as {0},{1},{2},... keeping their order.",
                  T.renumber, ["clean tree", "reindex"])


class TreeBranch(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_TreeBranch", "Tree Branch", CAT_TREE,
            "Pick one branch by path (e.g. {0;1}) or, when path is empty, by index.",
            [tree_in(),
             IO.String.Input("path", default="", tooltip="Exact path; leave empty to use index"),
             IO.Int.Input("index", default=0, min=-10000, max=10000, tooltip="Branch index (wraps)")],
            [tree_out()], ["get branch", "explode tree"])

    @classmethod
    def execute(cls, tree, path, index) -> IO.NodeOutput:
        p = str(unwrap(path, "")).strip()
        t = to_tree(tree)
        return IO.NodeOutput(T.get_branch(t, T.parse_path(p)) if p else T.get_branch(t, index=unwrap(index)))


def _tree_list_inputs():
    return IO.Autogrow.TemplatePrefix(tree_in("tree"), prefix="tree", min=2, max=16)


class MergeTrees(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_Merge", "Merge", CAT_TREE,
            "Combine trees; items on the same path are appended in input order.",
            [IO.Autogrow.Input("trees", template=_tree_list_inputs())],
            [tree_out()], ["combine", "join", "append"])

    @classmethod
    def execute(cls, trees: IO.Autogrow.Type) -> IO.NodeOutput:
        return IO.NodeOutput(T.merge([to_tree(v) for v in trees.values() if connected(v)]))


class Entwine(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_Entwine", "Entwine", CAT_TREE,
            "Stack trees side by side: input i is placed under {i;...}.",
            [IO.Autogrow.Input("trees", template=_tree_list_inputs())],
            [tree_out()], ["weave", "stack"])

    @classmethod
    def execute(cls, trees: IO.Autogrow.Type) -> IO.NodeOutput:
        return IO.NodeOutput(T.entwine([to_tree(v) for v in trees.values() if connected(v)]))


class TreeInfo(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema(
            "Arbor_TreeInfo", "Tree Statistics", CAT_TREE,
            "Branch count, item count and the list of paths.",
            [tree_in()],
            [IO.Int.Output(display_name="branches"), IO.Int.Output(display_name="items"),
             IO.Int.Output(display_name="depth"), IO.String.Output(display_name="paths")],
            ["tree stats", "count", "length"])

    @classmethod
    def execute(cls, tree) -> IO.NodeOutput:
        t = to_tree(tree)
        paths = "\n".join(f"{T.format_path(p)} N={len(v)}" for p, v in t.items())
        return IO.NodeOutput(t.branch_count, t.item_count, t.depth, paths)


NODES = [ConstructTree, NumberSeries, NumberRange, SplitText,
         XYLists, TreeToList, ListToTree,
         Graft, Flatten, Simplify, FlipMatrix, ShiftPaths, Renumber,
         TreeBranch, MergeTrees, Entwine, TreeInfo]
