"""ComfyUI-Arbor

Grasshopper-style data trees, a data Panel and image utilities for ComfyUI.
Inspired by Grasshopper; not affiliated with Robert McNeel & Associates.
"""

from comfy_api.latest import ComfyExtension

from .arbor import nodes_grid, nodes_image, nodes_list, nodes_panel, nodes_tree

WEB_DIRECTORY = "./web"

NODES = [*nodes_image.NODES, *nodes_grid.NODES, *nodes_panel.NODES,
         *nodes_tree.NODES, *nodes_list.NODES]


class ArborExtension(ComfyExtension):
    async def get_node_list(self):
        return NODES


async def comfy_entrypoint() -> ArborExtension:
    return ArborExtension()
