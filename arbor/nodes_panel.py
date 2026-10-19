import re

from .common import IO, CAT_DATA, tree_out, to_tree, unwrap
from .preview import panel_payload
from .tree import DataTree

_INT = re.compile(r"[+-]?\d+")
_FLOAT = re.compile(r"[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?")


def parse_value(s: str):
    t = s.strip()
    if _INT.fullmatch(t):
        return int(t)
    if _FLOAT.fullmatch(t):
        return float(t)
    return s


def parse_text(text: str, numbers: bool = True, multiline: bool = False) -> DataTree:
    """Panel text → tree, Grasshopper style.

    Each line is an item; an empty line starts a new branch. With
    ``multiline`` the whole text is a single item instead.
    """
    text = (text or "").replace("\r\n", "\n")
    if multiline:
        return DataTree({(0,): [text]})
    out = {}
    for block in re.split(r"\n[ \t]*\n", text):
        lines = [l for l in block.split("\n") if l.strip() != ""]
        if lines:
            out[(len(out),)] = [parse_value(l) if numbers else l for l in lines]
    return DataTree(out or {(0,): []})


class Panel(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_Panel", display_name="Panel", category=CAT_DATA,
            description="Inspect anything, or type data in. Connected: shows the input (trees with "
                        "branches and paths, images as thumbnails) and passes it through. "
                        "Unconnected: each line you type is an item, an empty line starts a new branch.",
            search_aliases=["preview any", "show", "inspect", "debug", "watch", "display",
                            "text", "note", "input", "list input", "prompt list"],
            is_output_node=True, is_input_list=True,
            inputs=[
                IO.AnyType.Input("data", optional=True),
                IO.String.Input("text", multiline=True, default="",
                                tooltip="Typed data, used when nothing is connected"),
                IO.Boolean.Input("parse_numbers", default=True,
                                 tooltip="Lines that look like numbers become INT / FLOAT"),
                IO.Boolean.Input("multiline", default=False,
                                 tooltip="Whole text is one item instead of one item per line"),
            ],
            outputs=[IO.AnyType.Output(display_name="data", is_output_list=True,
                                       tooltip="Native list: downstream nodes run once per item"),
                     tree_out("tree")])

    @classmethod
    def execute(cls, data=None, text=None, parse_numbers=None, multiline=None) -> IO.NodeOutput:
        if data is not None:
            values = data if isinstance(data, list) else [data]
            tree = to_tree(values)
            source = "input"
        else:
            tree = parse_text(unwrap(text, ""), unwrap(parse_numbers, True), unwrap(multiline, False))
            values = tree.flat() or [""]
            source = "text"
        payload = panel_payload(values if source == "input" else [tree])
        payload["source"] = source
        return IO.NodeOutput(values, tree, ui={"arbor_panel": [payload]})


NODES = [Panel]
