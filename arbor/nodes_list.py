"""List nodes: the same operation on every branch of a tree."""

from . import tree as T
from .common import IO, TREE, CAT_LIST, schema, tree_in, tree_out, to_tree, unwrap


def _list_node(node_id, name, desc, inputs, outputs, aliases=()):
    return schema(node_id, name, CAT_LIST, desc, [tree_in(), *inputs], outputs, aliases)


class ListItem(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        index = IO.MultiType.Input(
            IO.String.Input("index", default="0",
                            tooltip="Which items: 0 · -1 (last) · 0, 2 · 1:4 (slice) · 2-5 (inclusive) · ::2 "
                                    "— or connect a number"),
            types=[IO.Int])
        return _list_node("Arbor_ListItem", "List Item",
                          "Pick items from every branch by index, list, range or slice.",
                          [index, IO.Boolean.Input("wrap", default=True,
                                                   tooltip="Out-of-range indices wrap around; off gives null")],
                          [tree_out()], ["get item", "index", "pick", "sub list", "slice", "range of list"])

    @classmethod
    def execute(cls, tree, index, wrap) -> IO.NodeOutput:
        return IO.NodeOutput(T.list_items(to_tree(tree), unwrap(index), unwrap(wrap)))


class Dispatch(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        pattern = IO.MultiType.Input(
            IO.String.Input("pattern", default="T F",
                            tooltip="Type a repeating pattern ('T F', 'true,false', '1 0 1', 'TFT'), "
                                    "or connect BOOLEAN values / a boolean tree (matched by path: a "
                                    "parent branch covers all of its children)"),
            types=[IO.Boolean, TREE])
        return _list_node(
            "Arbor_Dispatch", "Dispatch",
            "Split items by a true / false pattern: A keeps the true ones, B the false ones. "
            "Use A alone to cull (filter) a list.",
            [pattern],
            [tree_out("A", tooltip="Items where the pattern is true — the kept items when culling"),
             tree_out("B", tooltip="Items where the pattern is false")],
            ["cull pattern", "cull", "filter", "split list", "route", "mask list", "every other"])

    @classmethod
    def execute(cls, tree, pattern) -> IO.NodeOutput:
        return IO.NodeOutput(*T.dispatch(to_tree(tree), T.resolve_pattern(pattern)))


class Partition(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _list_node("Arbor_Partition", "Partition",
                          "Chop every branch into chunks of size items: {p} → {p;k}.",
                          [IO.Int.Input("size", default=2, min=1, max=100000)],
                          [tree_out()], ["chunk", "group by", "split into rows"])

    @classmethod
    def execute(cls, tree, size) -> IO.NodeOutput:
        return IO.NodeOutput(T.partition(to_tree(tree), unwrap(size)))


class Repeat(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _list_node("Arbor_Repeat", "Repeat",
                          "Repeat items: 'each' gives aabbcc, 'whole' gives abcabc.",
                          [IO.Int.Input("count", default=2, min=1, max=10000),
                           IO.Combo.Input("mode", options=["each", "whole"], default="each")],
                          [tree_out()], ["duplicate", "tile list"])

    @classmethod
    def execute(cls, tree, count, mode) -> IO.NodeOutput:
        return IO.NodeOutput(T.repeat(to_tree(tree), unwrap(count), unwrap(mode)))


class SortList(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _list_node("Arbor_SortList", "Sort List",
                          "Sort every branch (numbers before text), or reverse its order.",
                          [IO.Combo.Input("order", options=list(T.SORT_ORDERS), default="ascending")],
                          [tree_out()], ["sort", "order", "reverse", "flip list", "invert order"])

    @classmethod
    def execute(cls, tree, order) -> IO.NodeOutput:
        return IO.NodeOutput(T.sort_list(to_tree(tree), unwrap(order)))


class CrossReference(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_CrossReference", "Cross Reference", CAT_LIST,
            "Every combination of A × B, branch by branch (matched by path, then in order). With group "
            "on, each A value gets its own sub-branch, named after it: rows = A, columns = B — ready for "
            "Image Grid.",
            [tree_in("A"), tree_in("B"),
             IO.Boolean.Input("group", default=True, tooltip="One branch per A item")],
            [tree_out("A"), tree_out("B")],
            ["cartesian", "combinations", "xy", "product", "permutation"])

    @classmethod
    def execute(cls, A, B, group) -> IO.NodeOutput:
        return IO.NodeOutput(*T.cross_reference(to_tree(A), to_tree(B), unwrap(group)))


NODES = [ListItem, Dispatch, Partition, Repeat, SortList, CrossReference]
