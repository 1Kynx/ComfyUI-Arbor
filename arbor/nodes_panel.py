from .common import IO, CAT_DATA
from .preview import panel_payload


class Panel(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_Panel", display_name="Panel", category=CAT_DATA,
            description="Inspect anything: data trees show their branches and paths, images show "
                        "thumbnails. The input is passed through unchanged.",
            search_aliases=["preview any", "show", "inspect", "debug", "watch", "display"],
            is_output_node=True, is_input_list=True,
            inputs=[IO.AnyType.Input("data", optional=True)],
            outputs=[IO.AnyType.Output(display_name="data", is_output_list=True)])

    @classmethod
    def execute(cls, data=None) -> IO.NodeOutput:
        values = data if isinstance(data, list) else ([] if data is None else [data])
        return IO.NodeOutput(values, ui={"arbor_panel": [panel_payload(values)]})


NODES = [Panel]
