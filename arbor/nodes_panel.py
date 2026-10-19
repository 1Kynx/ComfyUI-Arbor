"""Panel: inspect anything, or type data in (Grasshopper's Panel)."""

import re

from .common import IO, CAT_DATA, schema, data_out, tree_out, to_tree, unwrap
from .preview import panel_payload
from .tree import DataTree

_INT = re.compile(r"[+-]?\d+")
_FLOAT = re.compile(r"[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?")
_HEADING = re.compile(r"\s*#\s+(.*\S)\s*")


def parse_value(s: str):
    t = s.strip()
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if _INT.fullmatch(t):
        return int(t)
    if _FLOAT.fullmatch(t):
        return float(t)
    return s


def parse_text(text: str, numbers: bool = True, multiline: bool = False) -> DataTree:
    """Panel text → tree, Grasshopper style.

    Each line is an item; an empty line starts a new branch, and a ``# title``
    line names the branch it is in. With ``multiline`` the whole text is a
    single item instead.
    """
    text = (text or "").replace("\r\n", "\n")
    if multiline:
        return DataTree({(0,): [text]})
    out, names = {}, {}
    for block in re.split(r"\n[ \t]*\n", text):
        lines = [l for l in block.split("\n") if l.strip() != ""]
        if not lines:
            continue
        path, items = (len(out),), []
        for line in lines:
            heading = _HEADING.fullmatch(line)
            if heading:
                names.setdefault(path, heading.group(1))
            else:
                items.append(parse_value(line) if numbers else line)
        out[path] = items
    return DataTree(out or {(0,): []}, names)


class Panel(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_Panel", "Panel", CAT_DATA,
            "Inspect anything, or type data in. Connected: shows the input (trees with branches and "
            "paths, images as thumbnails) and passes it on. Unconnected: each line you type is an "
            "item, an empty line starts a new branch and a '# title' line names it.",
            [IO.AnyType.Input("data", optional=True),
             IO.String.Input("text", multiline=True, default="", tooltip="Typed data, used when nothing is connected"),
             IO.Boolean.Input("parse_numbers", default=True,
                              tooltip="Lines like 7 / 3.5 / true become INT / FLOAT / BOOLEAN"),
             IO.Boolean.Input("multiline", default=False,
                              tooltip="Whole text is one item instead of one item per line")],
            [data_out(tooltip="Every item as plain data (a tree is flattened): downstream nodes run once per item"),
             tree_out(tooltip="The data as a tree — keeps the branches")],
            ["preview any", "show", "inspect", "debug", "watch", "display", "text", "note", "input",
             "list input", "prompt list"],
            is_output_node=True)

    @classmethod
    def execute(cls, data=None, text=None, parse_numbers=None, multiline=None) -> IO.NodeOutput:
        if data is not None:  # viewing: show what arrived, pass it on as data + tree
            values = data if isinstance(data, list) else [data]
            tree = to_tree(values)
            payload = panel_payload(values)
            payload["source"] = "input"
            return IO.NodeOutput(tree.flat(), tree, ui={"arbor_panel": [payload]})
        tree = parse_text(unwrap(text, ""), unwrap(parse_numbers, True), unwrap(multiline, False))
        payload = panel_payload([tree])
        payload["source"] = "text"
        return IO.NodeOutput(tree.flat() or [""], tree, ui={"arbor_panel": [payload]})


NODES = [Panel]
