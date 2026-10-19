"""ComfyUI-Arbor

Grasshopper-style data trees, a data Panel and image utilities for ComfyUI.
Inspired by Grasshopper; not affiliated with Robert McNeel & Associates.
"""

from comfy_api.latest import ComfyExtension

from .arbor import nodes_grid, nodes_image, nodes_list, nodes_panel, nodes_tree

WEB_DIRECTORY = "./web"

try:  # live Panel preview endpoint; absent when imported outside a running server
    from .arbor import live
    live.register_routes()
except Exception as e:  # pragma: no cover
    print(f"[Arbor] live preview disabled: {e}")

NODES = [*nodes_image.NODES, *nodes_grid.NODES, *nodes_panel.NODES,
         *nodes_tree.NODES, *nodes_list.NODES]


class ArborExtension(ComfyExtension):
    async def get_node_list(self):
        return NODES


async def comfy_entrypoint() -> ArborExtension:
    return ArborExtension()
