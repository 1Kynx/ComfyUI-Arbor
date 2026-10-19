"""Per-branch list operations. Each one runs independently on every branch."""

from . import tree as T
from .common import IO, CAT_LIST, tree_in, tree_out, to_tree, unwrap


def _schema(node_id, name, desc, inputs, outputs, aliases=()):
    return IO.Schema(node_id=node_id, display_name=name, category=CAT_LIST, description=desc,
                     search_aliases=list(aliases), is_input_list=True,
                     inputs=[tree_in(), *inputs], outputs=outputs)


def _pattern_input():
    return IO.String.Input("pattern", default="T F",
                           tooltip="Repeating true/false pattern: 'T F', 'true,false', '1 0 1' or 'TFT'")


class ListItem(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_ListItem", "List Item", "Pick item i from every branch.",
                       [IO.Int.Input("index", default=0, min=-100000, max=100000),
                        IO.Boolean.Input("wrap", default=True, tooltip="Wrap index around the list length")],
                       [tree_out("item")], ["get item", "index", "pick"])

    @classmethod
    def execute(cls, tree, index, wrap) -> IO.NodeOutput:
        return IO.NodeOutput(T.list_item(to_tree(tree), unwrap(index), unwrap(wrap)))


class SubList(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_SubList", "Sub List", "Slice items [start, end) from every branch.",
                       [IO.Int.Input("start", default=0, min=-100000, max=100000),
                        IO.Int.Input("end", default=-1, min=-100000, max=100000,
                                     tooltip="Exclusive; -1 keeps through the last item")],
                       [tree_out()], ["slice", "range of list"])

    @classmethod
    def execute(cls, tree, start, end) -> IO.NodeOutput:
        s, e = unwrap(start), unwrap(end)
        return IO.NodeOutput(to_tree(tree).map_branches(
            lambda _, items: items[s:] if e == -1 else items[s:e]))


class CullPattern(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_CullPattern", "Cull Pattern",
                       "Keep items where the repeating pattern is true.",
                       [_pattern_input()], [tree_out()], ["filter", "mask list", "every other"])

    @classmethod
    def execute(cls, tree, pattern) -> IO.NodeOutput:
        return IO.NodeOutput(T.cull_pattern(to_tree(tree), T.parse_pattern(unwrap(pattern))))


class Dispatch(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_Dispatch", "Dispatch",
                       "Split items into A (pattern true) and B (pattern false).",
                       [_pattern_input()], [tree_out("A"), tree_out("B")], ["split list", "route"])

    @classmethod
    def execute(cls, tree, pattern) -> IO.NodeOutput:
        a, b = T.dispatch(to_tree(tree), T.parse_pattern(unwrap(pattern)))
        return IO.NodeOutput(a, b)


class Partition(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_Partition", "Partition",
                       "Chop every branch into chunks of size items: {p} → {p;k}.",
                       [IO.Int.Input("size", default=2, min=1, max=100000)],
                       [tree_out()], ["chunk", "group by", "split into rows"])

    @classmethod
    def execute(cls, tree, size) -> IO.NodeOutput:
        return IO.NodeOutput(T.partition(to_tree(tree), unwrap(size)))


class Repeat(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_Repeat", "Repeat",
                       "Repeat items: 'each' gives aabbcc, 'whole' gives abcabc.",
                       [IO.Int.Input("count", default=2, min=1, max=10000),
                        IO.Combo.Input("mode", options=["each", "whole"], default="each")],
                       [tree_out()], ["duplicate", "tile list"])

    @classmethod
    def execute(cls, tree, count, mode) -> IO.NodeOutput:
        return IO.NodeOutput(T.repeat(to_tree(tree), unwrap(count), unwrap(mode)))


class Reverse(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_Reverse", "Reverse List", "Reverse the item order in every branch.",
                       [], [tree_out()], ["flip list", "invert order"])

    @classmethod
    def execute(cls, tree) -> IO.NodeOutput:
        return IO.NodeOutput(T.reverse_list(to_tree(tree)))


class Sort(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("Arbor_Sort", "Sort List",
                       "Sort every branch (numbers before text).",
                       [IO.Boolean.Input("descending", default=False)], [tree_out()], ["order"])

    @classmethod
    def execute(cls, tree, descending) -> IO.NodeOutput:
        return IO.NodeOutput(T.sort_list(to_tree(tree), unwrap(descending)))


class CrossReference(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_CrossReference", display_name="Cross Reference", category=CAT_LIST,
            description="Every combination of A × B. With group on, each A value gets its own "
                        "branch: rows = A, columns = B — ready for Tree → Grid.",
            search_aliases=["cartesian", "combinations", "xy", "product", "permutation"],
            is_input_list=True,
            inputs=[tree_in("A"), tree_in("B"),
                    IO.Boolean.Input("group", default=True, tooltip="One branch per A item")],
            outputs=[tree_out("A"), tree_out("B")])

    @classmethod
    def execute(cls, A, B, group) -> IO.NodeOutput:
        a, b = T.cross_reference(to_tree(A), to_tree(B), unwrap(group))
        return IO.NodeOutput(a, b)


NODES = [ListItem, SubList, CullPattern, Dispatch, Partition, Repeat, Reverse, Sort, CrossReference]
