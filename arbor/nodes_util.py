"""Flow utilities."""

from .common import IO

CAT_UTIL = "Arbor/Util"


class IndexSwitch(IO.ComfyNode):
    """Pick one of many inputs by index. Inputs are lazy: only the chosen one runs."""

    @classmethod
    def define_schema(cls):
        slot = IO.Autogrow.TemplatePrefix(
            IO.AnyType.Input("input", lazy=True, tooltip="Only evaluated when selected"),
            prefix="input", min=1, max=32)
        return IO.Schema(
            node_id="Arbor_IndexSwitch", display_name="Index Switch", category=CAT_UTIL,
            description="Pass through input N (counting connected inputs, wrapping around). "
                        "Unselected branches are not executed at all.",
            search_aliases=["switch", "select", "stream filter", "choose", "multiplexer", "any switch"],
            hidden=[IO.Hidden.prompt, IO.Hidden.unique_id],
            inputs=[IO.MultiType.Input(
                        IO.Int.Input("index", default=0, min=-1000, max=1000,
                                     tooltip="0 = first connected input; negative counts from the end. "
                                             "A BOOLEAN works too: False = 0, True = 1"),
                        types=[IO.Boolean]),
                    IO.Autogrow.Input("inputs", template=slot)],
            outputs=[IO.AnyType.Output(display_name="output"), IO.Int.Output(display_name="count")])

    @classmethod
    def _connected(cls, inputs) -> list[str]:
        """Names of linked slots, in slot order.

        Unlinked slots arrive as None just like linked-but-not-yet-evaluated
        lazy ones, so the links are read from the prompt itself.
        """
        names = list((inputs or {}).keys())
        h = cls.hidden
        prompt = getattr(h, "prompt", None) if h else None
        uid = getattr(h, "unique_id", None) if h else None
        if prompt and uid in prompt:
            linked = {k.split(".", 1)[1] for k, v in prompt[uid].get("inputs", {}).items()
                      if k.startswith("inputs.") and isinstance(v, list)}
            names = [n for n in names if n in linked]
        names.sort(key=lambda k: int(k.removeprefix("input") or 0))
        if not names:
            raise ValueError("Index Switch: connect at least one input")
        return names

    @classmethod
    def check_lazy_status(cls, index, inputs=None):
        index = int(index)  # BOOLEAN -> 0 / 1
        names = cls._connected(inputs)
        value, full_key = inputs[names[index % len(names)]]
        return [full_key] if value is None else []

    @classmethod
    def execute(cls, index, inputs=None) -> IO.NodeOutput:
        index = int(index)
        names = cls._connected(inputs)
        return IO.NodeOutput(inputs[names[index % len(names)]], len(names))


NODES = [IndexSwitch]
