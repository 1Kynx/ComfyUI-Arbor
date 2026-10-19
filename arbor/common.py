from comfy_api.latest import IO

from .tree import to_tree, unwrap

TREE = IO.Custom("ARBOR_TREE")

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


__all__ = ["IO", "TREE", "tree_in", "tree_out", "to_tree", "unwrap", "connected",
           "CAT_IMAGE", "CAT_TREE", "CAT_LIST", "CAT_DATA"]
