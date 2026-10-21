"""Shared types and helpers for every Arbor node.

Two kinds of output run through the whole pack:

- data (数据): a native ComfyUI value or list. Any node accepts it; ordinary
  nodes run once per item; Arbor inputs read a list as branch {0}.
- tree (数据树): an Arbor DataTree, output only where branches exist.

Most nodes run with ``is_input_list`` so a native list arrives whole instead
of making the node execute once per item; widget values then arrive as
1-item lists and are read through ``unwrap``.
"""

from comfy_api.latest import IO

from .tree import to_tree, unwrap

TREE = IO.Custom("ARBOR_TREE")
# a socket that is both: "FLOAT,INT" matches INT and FLOAT inputs (comma types overlap)
NUMBER = IO.Custom("FLOAT,INT")

CAT_MEDIA = "Arbor/Media"
CAT_DATA = "Arbor/Data"
CAT_TREE = "Arbor/Tree"
CAT_LIST = "Arbor/List"

DATA_TIP = "Plain data (a native list): connect to any node — ordinary nodes run once per item."


def schema(node_id, name, category, description, inputs, outputs, aliases=(), *, input_list=True, **extra):
    """IO.Schema with Arbor's defaults (input lists on)."""
    return IO.Schema(node_id=node_id, display_name=name, category=category, description=description,
                     search_aliases=list(aliases), is_input_list=input_list,
                     inputs=inputs, outputs=outputs, **extra)


def tree_in(id="tree", optional=False, tooltip=None):
    """Tree sockets accept anything: plain values and lists become {0}."""
    return IO.AnyType.Input(id, optional=optional,
                            tooltip=tooltip or "A data tree, or any value / list (becomes branch {0})")


def tree_out(display_name="tree", tooltip=None):
    return TREE.Output(display_name=display_name, tooltip=tooltip)


def data_out(kind=None, tooltip=None, display_name="data"):
    """The unified `data` output: a native ComfyUI list (kind picks the socket type)."""
    return (kind or IO.AnyType).Output(display_name=display_name, is_output_list=True,
                                       tooltip=tooltip or DATA_TIP)


def connected(value) -> bool:
    """False for an unconnected optional / Autogrow slot (None, or [None] under is_input_list)."""
    if value is None:
        return False
    if isinstance(value, list) and all(v is None for v in value):
        return False
    return True


__all__ = ["IO", "TREE", "NUMBER", "CAT_MEDIA", "CAT_DATA", "CAT_TREE", "CAT_LIST",
           "schema", "tree_in", "tree_out", "data_out", "connected", "to_tree", "unwrap"]
