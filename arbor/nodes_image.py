import torch

from .common import IO, CAT_IMAGE, to_tree
from .preview import save_temp, to_pil, is_image

COMPARE_MAX_FRAMES = 64


def _collect_images(value) -> list[torch.Tensor]:
    """Images from a socket value: a batch, a list of batches, or a tree."""
    out = []
    for v in to_tree(value).flat():
        if is_image(v):
            out.extend(v[i] for i in range(v.shape[0]))
    return out


class ImageCompare(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        images = IO.Autogrow.TemplatePrefix(
            IO.Image.Input("image", tooltip="Image or batch; every frame becomes a slide"),
            prefix="image", min=1, max=16)
        return IO.Schema(
            node_id="Arbor_ImageCompare",
            display_name="Image Compare",
            category=CAT_IMAGE,
            description="Compare any number of images of any size. Drag the slider to flip "
                        "through them, or switch to wipe mode for a before/after split.",
            search_aliases=["compare", "before after", "slider", "ab test", "image viewer"],
            is_output_node=True,
            is_input_list=True,
            inputs=[IO.Autogrow.Input("images", template=images, optional=True)],
            outputs=[],
        )

    @classmethod
    def execute(cls, images: IO.Autogrow.Type = None) -> IO.NodeOutput:
        slides = []
        for name, value in (images or {}).items():
            frames = _collect_images(value)
            for k, frame in enumerate(frames):
                if len(slides) >= COMPARE_MAX_FRAMES:
                    break
                h, w = int(frame.shape[0]), int(frame.shape[1])
                ref = save_temp(to_pil(frame), "compare", fmt="png")
                label = name if len(frames) == 1 else f"{name} · {k + 1}/{len(frames)}"
                slides.append({**ref, "label": label, "w": w, "h": h})
        return IO.NodeOutput(ui={"arbor_compare": [{"slides": slides}]})


NODES = [ImageCompare]
