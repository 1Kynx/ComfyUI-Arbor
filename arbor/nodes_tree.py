"""Tree nodes: bridging to ComfyUI's native lists, building trees, reshaping them."""

from . import tree as T
from .common import IO, CAT_TREE, schema, connected, data_out, tree_in, tree_out, to_tree, unwrap
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
                            tooltip="cross: every combination · zip: item by item (longest list). Trees pair "
                                    "branch by branch like Grasshopper; a plain list is one branch")],
            [IO.AnyType.Output(display_name="x", is_output_list=True, tooltip="x of every run"),
             IO.AnyType.Output(display_name="y", is_output_list=True, tooltip="y of every run"),
             IO.AnyType.Output(display_name="z", is_output_list=True, tooltip="z of every run"),
             tree_out("shape", tooltip="Layout of the runs — connect to Image Grid or Construct Tree "
                                       "to put the results back into rows and columns. Rows are named "
                                       "after x, items are the column values, so the grid labels itself"),
             IO.Int.Output(display_name="count", tooltip="Number of runs")],
            ["xy plot", "xyz plot", "grid search", "parameter sweep", "combinations", "cartesian",
             "batch run", "zip lists"])

    @classmethod
    def execute(cls, x, mode, y=None, z=None) -> IO.NodeOutput:
        tx = to_tree(x)
        ty = to_tree(y) if connected(y) else None
        tz = to_tree(z) if connected(z) else None
        xs = tx.flat()
        ys = ty.flat() if ty is not None else None
        zs = tz.flat() if tz is not None else None
        if not xs:
            raise ValueError("XY Lists: x is empty")
        if ys == [] or zs == []:
            raise ValueError("XY Lists: y or z is connected but empty")
        if zs is not None and ys is None:
            raise ValueError("XY Lists: connect y before z")

        if ys is None:  # one parameter: plain data, and the shape keeps x's own branches
            n = len(xs)
            return IO.NodeOutput(xs, [None] * n, [None] * n, tx, n)

        # Branches pair the Grasshopper way (in order, the last branch repeating), like Cross Reference and
        # Prompt Template: x, y and z only meet inside matching branches. Plain lists are one branch each.
        pairs, master = T.match_branches(tx, ty, tz)
        names = dict(master.names)
        for t in (tx, ty, tz):  # a branch the master leaves unnamed takes the name another input gives it
            for p, nm in (t.names.items() if t is not None else ()):
                names.setdefault(p, nm)
        ox, oy, oz = [], [], []
        shape = {}
        if unwrap(mode) == "zip":
            # inside each branch pair: item by item, the shorter list repeating its last item
            pick = lambda vals, i: vals[min(i, len(vals) - 1)] if vals else None
            for path, (bx, by, bz) in pairs:
                lengths = [len(b) for b in (bx, by, bz) if b is not None]
                n = 0 if 0 in lengths else max(lengths)
                for i in range(n):
                    ox.append(pick(bx, i))
                    oy.append(pick(by, i))
                    oz.append(pick(bz, i))
                # the shape's items are the last variable's values, for column labels
                shape[path] = [pick(bz if zs else by, i) for i in range(n)]
            kept = {p: nm for p, nm in names.items() if any(q[:len(p)] == p for q in shape)}  # parents too
            return IO.NodeOutput(ox, oy, oz, T.DataTree(shape, kept), len(ox))

        total = sum(len(bx or []) * len(by or []) * len(bz or [None]) for _, (bx, by, bz) in pairs)
        if total > MAX_COMBOS:
            raise ValueError(f"XY Lists: {total} combinations (max {MAX_COMBOS})")
        # inside each branch pair: every combination, one row per x value (x × y with z). One branch pair
        # gives rows {i} / {i;j} as before; several give one group of rows per pair, under its path.
        single = len(pairs) == 1
        rows = {}
        for path, (bx, by, bz) in pairs:
            base = () if single else path
            for i, xv in enumerate(bx or []):
                for j, yv in enumerate(by or []):
                    for zv in bz or [None]:
                        ox.append(xv)
                        oy.append(yv)
                        oz.append(zv)
                    if zs:
                        shape[base + (i, j)] = list(bz)
                        rows[base + (i, j)] = f"{label_of(xv)} · {label_of(yv)}"
                if not zs:
                    shape[base + (i,)] = list(by or [])
                    rows[base + (i,)] = xv
            if not single and path in names:
                rows[path] = names[path]  # the group keeps its branch's name: rows read "Mei · 4"
        return IO.NodeOutput(ox, oy, oz, T.DataTree(shape, rows), len(ox))


class TreeToData(IO.ComfyNode):
    """The compact bridge for one tree: XY Lists with only x, without the other outputs."""

    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_TreeToData", "Tree to Data", CAT_TREE,
            "Every item of a tree as plain data, so ordinary nodes run once per item — plus its shape, "
            "to put the results back with Construct Tree or Image Grid.",
            [tree_in(tooltip="The tree to run over")],
            [data_out(tooltip="Every item in branch order — ordinary nodes run once per item"),
             tree_out("shape", tooltip="The tree itself: connect to Construct Tree or Image Grid to put the "
                                       "results back into the same branches")],
            ["tree to list", "flatten to list", "unpack", "for each", "tree to data"])

    @classmethod
    def execute(cls, tree) -> IO.NodeOutput:
        t = to_tree(tree)
        return IO.NodeOutput(t.flat(), t)


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
            "Pick branches by path (e.g. {0;1}) or name — several separated by commas — or, when path is empty, one by index.",
            [tree_in(),
             IO.String.Input("path", default="", tooltip="Paths such as {0;1} or branch names, separated by commas; leave empty to use index"),
             IO.Int.Input("index", default=0, min=-10000, max=10000, tooltip="Branch index (wraps)")],
            [tree_out(), data_out(tooltip="The branch's items as plain data")], ["get branch", "explode tree", "branch by name"])

    @classmethod
    def execute(cls, tree, path, index) -> IO.NodeOutput:
        p = str(unwrap(path, "")).strip()
        t = to_tree(tree)
        if not p:
            picked = T.get_branch(t, index=unwrap(index))
        else:  # one or more paths / branch names, separated by commas
            by_name = {n: q for q, n in t.names.items() if q in t.branches}
            parts = [T.get_branch(t, by_name[k] if k in by_name else T.parse_path(k))
                     for k in (s.strip() for s in p.split(",")) if k]
            picked = T.DataTree({q: v for b in parts for q, v in b.branches.items()}, t.names)
        return IO.NodeOutput(picked, picked.flat())


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


NODES = [XYLists, TreeToData, ConstructTree, ReshapeTree, TreeBranch, Merge, TreeStatistics]
