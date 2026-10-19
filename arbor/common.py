from comfy_api.latest import IO

from .tree import to_tree, unwrap

TREE = IO.Custom("ARBOR_TREE")
# a socket that is both: "FLOAT,INT" matches INT and FLOAT inputs (comma types overlap)
NUMBER = IO.Custom("FLOAT,INT")

CAT_IMAGE = "Arbor/Image"
CAT_TREE = "Arbor/Tree"
CAT_LIST = "Arbor/List"
CAT_DATA = "Arbor/Data"


def tree_in(id="tree", display_name=None, optional=False, tooltip=None):
    """Tree sockets accept anything: plain values and lists become {0}."""
    return IO.AnyType.Input(id, display_name=display_name, optional=optional,
                            tooltip=tooltip or "A data tree, or any value / list (becomes branch {0})")


def connected(value) -> bool:
    """False for an unconnected optional / Autogrow slot (None, or [None] under is_input_list)."""
    if value is None:
        return False
    if isinstance(value, list) and all(v is None for v in value):
        return False
    return True


def tree_out(display_name="tree", tooltip=None):
    return TREE.Output(display_name=display_name, tooltip=tooltip)


DATA_TIP = "Plain data (a native list): connect to any node — ordinary nodes run once per item."


def data_out(kind=None, tooltip=None, as_list=True):
    """The unified `data` output: a native ComfyUI value / list, usable by every node.

    Structure-free results use it; results that may have branches also expose
    `tree`. kind picks the socket type (default: any).
    """
    return (kind or IO.AnyType).Output(display_name="data", is_output_list=as_list, tooltip=tooltip or DATA_TIP)


__all__ = ["IO", "TREE", "NUMBER", "tree_in", "tree_out", "data_out", "to_tree", "unwrap", "connected",
           "CAT_IMAGE", "CAT_TREE", "CAT_LIST", "CAT_DATA"]
