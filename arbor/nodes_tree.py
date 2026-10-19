"""Tree nodes: bridging to ComfyUI's native lists, building trees, reshaping them."""

from . import tree as T
from .common import IO, CAT_TREE, schema, connected, tree_in, tree_out, to_tree, unwrap
from .preview import label_of

MAX_COMBOS = 10000


# ======================================================================= bridge

class XYLists(IO.ComfyNode):
    """Trees / values -> aligned native lists that ordinary nodes run over, plus the grid shape."""

    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_XYLists", "XY Lists", CAT_TREE,
            "Turn values into a batch run: every combination of x, y (and z) as aligned plain data — "
            "wire x, y, z into ordinary nodes and they run once per combination — plus the shape of "
            "the runs. With only x connected it flattens any tree, and the shape keeps x's branches.",
            [tree_in("x", tooltip="Values for the rows — or any tree to flatten"),
             tree_in("y", optional=True, tooltip="Values for the columns"),
             tree_in("z", optional=True, tooltip="Optional third parameter (columns; rows become x × y)"),
             IO.Combo.Input("mode", options=["cross", "zip"], default="cross",
                            tooltip="cross: every combination · zip: item by item (longest list)")],
            [IO.AnyType.Output(display_name="x", is_output_list=True, tooltip="x of every run"),
             IO.AnyType.Output(display_name="y", is_output_list=True, tooltip="y of every run"),
             IO.AnyType.Output(display_name="z", is_output_list=True, tooltip="z of every run"),
             tree_out("shape", tooltip="Layout of the runs — connect to Image Grid or Construct Tree "
                                       "to put the results back into rows and columns. Rows are named "
                                       "after x, items are the column values, so the grid labels itself"),
             IO.Int.Output(display_name="count", tooltip="Number of runs")],
            ["xy plot", "xyz plot", "grid search", "parameter sweep", "combinations", "cartesian",
             "tree to list", "flatten to list", "for each", "batch run"])

    @classmethod
    def execute(cls, x, mode, y=None, z=None) -> IO.NodeOutput:
        tx = to_tree(x)
        xs = tx.flat()
        ys = to_tree(y).flat() if connected(y) else None
        zs = to_tree(z).flat() if connected(z) else None
        if not xs:
            raise ValueError("XY Lists: x is empty")
        if ys == [] or zs == []:
            raise ValueError("XY Lists: y or z is connected but empty")
        if zs is not None and ys is None:
            raise ValueError("XY Lists: connect y before z")

        if ys is None:  # one parameter: plain data, and the shape keeps x's own branches
            n = len(xs)
            return IO.NodeOutput(xs, [None] * n, [None] * n, tx, n)

        ox, oy, oz, shape, names = [], [], [], {}, {}
        if unwrap(mode) == "zip":
            n = max(len(xs), len(ys), len(zs or []))
            pick = lambda vals, i: vals[min(i, len(vals) - 1)] if vals else None
            for i in range(n):
                ox.append(pick(xs, i))
                oy.append(pick(ys, i))
                oz.append(pick(zs, i))
            shape[(0,)] = list(oz if zs else oy)  # one row, labelled by the last variable
        else:
            total = len(xs) * len(ys) * len(zs or [None])
            if total > MAX_COMBOS:
                raise ValueError(f"XY Lists: {total} combinations (max {MAX_COMBOS})")
            for i, xv in enumerate(xs):
                for j, yv in enumerate(ys):
                    for zv in zs or [None]:
                        ox.append(xv)
                        oy.append(yv)
                        oz.append(zv)
                    if zs:
                        shape[(i, j)] = list(zs)
                        names[(i, j)] = f"{label_of(xv)} · {label_of(yv)}"
                if not zs:
                    shape[(i,)] = list(ys)
                    names[(i,)] = xv
        return IO.NodeOutput(ox, oy, oz, T.DataTree(shape, names), len(ox))


# ======================================================================= build

class ConstructTree(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_ConstructTree", "Construct Tree", CAT_TREE,
            "Build a tree from plain data: put every item on one path, or — with shape connected — "
            "pour the items back into another tree's branches (e.g. the results of a batch run).",
            [IO.AnyType.Input("data", tooltip="Any value or plain data (a native list)"),
             IO.String.Input("path", default="{0}", tooltip="Branch path when no shape is connected, e.g. {0;2}"),
             tree_in("shape", optional=True, tooltip="Copy this tree's branch layout (XY Lists' shape, or "
                                                     "the tree you flattened); the item counts must match"),
             IO.Boolean.Input("split_batch", default=False,
                              tooltip="Split IMAGE / MASK / LATENT batches into one item per frame first")],
            [tree_out()], ["tree", "wrap", "construct path", "list to tree", "collect", "rebuild", "unflatten"])

    @classmethod
    def execute(cls, data, path, split_batch, shape=None) -> IO.NodeOutput:
        items = data if isinstance(data, list) else [data]
        if unwrap(split_batch):
            items = [f for v in items for f in T.split_batch(v)]
        if connected(shape):
            return IO.NodeOutput(T.rebuild(items, to_tree(shape)))
        return IO.NodeOutput(T.DataTree({T.parse_path(unwrap(path)): items}))


# ======================================================================= structure

RESHAPE = {
    "graft": lambda t: T.graft(t),
    "flatten": lambda t, path: T.flatten(t, T.parse_path(path)),
    "simplify": lambda t: T.simplify(t),
    "flip matrix": lambda t: T.flip_matrix(t),
    "shift paths": lambda t, offset: T.shift_paths(t, offset),
    "renumber": lambda t: T.renumber(t),
}


class ReshapeTree(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        options = {
            "flatten": [IO.String.Input("path", default="{0}", tooltip="Path of the single branch")],
            "shift paths": [IO.Int.Input("offset", default=-1, min=-16, max=16,
                                         tooltip="-1 drops the last path index (undoes graft), +1 the first")],
        }
        return schema(
            "Arbor_ReshapeTree", "Reshape Tree", CAT_TREE,
            "Change how items are grouped into branches. graft: every item its own branch · flatten: "
            "all items in one branch · simplify: drop shared path indices · flip matrix: swap rows and "
            "columns · shift paths: drop path indices, joining branches · renumber: {0}, {1}, {2}, …",
            [tree_in(),
             IO.DynamicCombo.Input("mode", options=[IO.DynamicCombo.Option(k, options.get(k, []))
                                                    for k in RESHAPE])],
            [tree_out()],
            ["graft", "flatten", "simplify", "flip matrix", "transpose", "swap xy", "shift paths", "trim tree",
             "renumber", "reindex", "path mapper"])

    @classmethod
    def execute(cls, tree, mode) -> IO.NodeOutput:
        opts = {k: unwrap(v) for k, v in mode.items()}
        return IO.NodeOutput(RESHAPE[opts.pop("mode")](to_tree(tree), **opts))


class TreeBranch(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
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


class Merge(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        trees = IO.Autogrow.TemplatePrefix(tree_in("tree"), prefix="tree", min=2, max=16)
        return schema(
            "Arbor_Merge", "Merge", CAT_TREE,
            "Combine trees. merge: items on the same path are appended in input order · entwine: "
            "input i is placed under {i;…}, side by side.",
            [IO.Autogrow.Input("trees", template=trees),
             IO.Combo.Input("mode", options=["merge", "entwine"], default="merge")],
            [tree_out()], ["combine", "join", "append", "entwine", "weave", "stack"])

    @classmethod
    def execute(cls, trees: IO.Autogrow.Type, mode) -> IO.NodeOutput:
        given = [to_tree(v) for v in trees.values() if connected(v)]
        return IO.NodeOutput(T.entwine(given) if unwrap(mode) == "entwine" else T.merge(given))


class TreeStatistics(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_TreeStatistics", "Tree Statistics", CAT_TREE,
            "Branch count, item count, depth and the list of paths.",
            [tree_in()],
            [IO.Int.Output(display_name="branches"), IO.Int.Output(display_name="items"),
             IO.Int.Output(display_name="depth"), IO.String.Output(display_name="paths")],
            ["tree stats", "tree info", "count", "length"])

    @classmethod
    def execute(cls, tree) -> IO.NodeOutput:
        t = to_tree(tree)
        paths = "\n".join(f"{T.format_path(p)} N={len(v)}" for p, v in t.items())
        return IO.NodeOutput(t.branch_count, t.item_count, t.depth, paths)


NODES = [XYLists, ConstructTree, ReshapeTree, TreeBranch, Merge, TreeStatistics]
