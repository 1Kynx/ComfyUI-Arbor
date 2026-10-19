"""Data generators and per-item math: Number Slider, Prompt Template, Expression, Random."""

import itertools
import random
import re

from . import expr as E
from . import tree as T
from .common import IO, CAT_DATA, tree_in, tree_out, to_tree, unwrap
from .preview import label_of

TEMPLATE_VARS = ["a", "b", "c", "d", "e", "f"]
_VAR_RE = re.compile(r"\{([a-f])\}")
MAX_COMBOS = 10000


def _match(tree: T.DataTree, k: int, j: int):
    """Longest-list matching: item j of branch k, repeating the last ones."""
    paths = tree.paths()
    items = tree.branches[paths[min(k, len(paths) - 1)]]
    return items[min(j, len(items) - 1)] if items else None


def slider_value(value: float, lo: float, hi: float, decimals: int) -> float:
    lo, hi = (lo, hi) if lo <= hi else (hi, lo)
    v = min(hi, max(lo, float(value)))
    return round(v, max(0, int(decimals)))


class NumberSlider(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        big = 1e9
        return IO.Schema(
            node_id="Arbor_NumberSlider", display_name="Number Slider", category=CAT_DATA,
            description="Grasshopper-style number slider: drag to set a value between min and max. "
                        "decimals = 0 gives whole numbers. Double-click the value to type it; "
                        "click min / max to change the range.",
            search_aliases=["slider", "number", "float", "int", "value", "parameter", "range slider"],
            inputs=[
                IO.Float.Input("value", default=0.5, min=-big, max=big, step=0.001),
                IO.Float.Input("min", default=0.0, min=-big, max=big, step=0.001),
                IO.Float.Input("max", default=1.0, min=-big, max=big, step=0.001),
                IO.Int.Input("decimals", default=2, min=0, max=6),
            ],
            outputs=[IO.Float.Output(display_name="value"), IO.Int.Output(display_name="int")])

    @classmethod
    def execute(cls, value, min, max, decimals) -> IO.NodeOutput:
        v = slider_value(value, min, max, decimals)
        return IO.NodeOutput(v, int(round(v)))


class PromptTemplate(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        vars_ = IO.Autogrow.TemplateNames(
            tree_in("var", tooltip="Values for {a}, {b}, ... — a tree, list or single value"),
            names=TEMPLATE_VARS, min=1)
        return IO.Schema(
            node_id="Arbor_PromptTemplate", display_name="Prompt Template", category=CAT_DATA,
            description="Fill {a} {b} ... in a template from trees. Cross: every combination, as a "
                        "grid-ready tree (rows = a, columns = last variable). Zip: item by item.",
            search_aliases=["template", "format", "prompt matrix", "combinations", "wildcard", "fill"],
            is_input_list=True,
            inputs=[
                IO.String.Input("template", multiline=True, default="a photo of {a}, {b}"),
                IO.Combo.Input("mode", options=["cross", "zip"], default="cross"),
                IO.Autogrow.Input("vars", template=vars_, optional=True),
            ],
            outputs=[tree_out("prompts")])

    @classmethod
    def execute(cls, template, mode, vars=None) -> IO.NodeOutput:
        text = str(unwrap(template, ""))
        used = [v for v in TEMPLATE_VARS if f"{{{v}}}" in text]
        given = {k: to_tree(v) for k, v in (vars or {}).items() if v is not None and v != [None]}
        lists = {k: [label_of(x) for x in given[k].flat()] for k in used if k in given}
        lists = {k: v for k, v in lists.items() if v}
        names = [k for k in used if k in lists]

        def fill(values: dict) -> str:
            return _VAR_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)

        if not names:
            return IO.NodeOutput(T.DataTree({(0,): [fill({})]}))
        if unwrap(mode) == "zip":
            n = max(len(lists[k]) for k in names)
            out = [fill({k: lists[k][min(i, len(lists[k]) - 1)] for k in names}) for i in range(n)]
            return IO.NodeOutput(T.DataTree({(0,): out}))

        total = 1
        for k in names:
            total *= len(lists[k])
        if total > MAX_COMBOS:
            raise ValueError(f"Prompt Template: {total} combinations (max {MAX_COMBOS})")
        *outer, last = names
        out = {}
        for idx in itertools.product(*[range(len(lists[k])) for k in outer]):
            vals = {k: lists[k][i] for k, i in zip(outer, idx)}
            out[tuple(idx) or (0,)] = [fill({**vals, last: v}) for v in lists[last]]
        return IO.NodeOutput(T.DataTree(out))


class Expression(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_Expression", display_name="Expression", category=CAT_DATA,
            description="Evaluate an expression for every item of x (y matched longest-list). "
                        "Names: x, y, i (item index), b (branch index), n (branch length). "
                        "Functions: abs min max round int float str sqrt sin cos floor ceil log exp "
                        "clamp lerp upper lower strip replace join len sum.",
            search_aliases=["math", "formula", "evaluate", "calculate", "eval"],
            is_input_list=True,
            inputs=[
                IO.String.Input("expression", default="x * 2"),
                tree_in("x", optional=True),
                tree_in("y", optional=True),
            ],
            outputs=[tree_out("result")])

    @classmethod
    def execute(cls, expression, x=None, y=None) -> IO.NodeOutput:
        code = E.compile_expr(str(unwrap(expression, "")))
        tx = to_tree(x) if x is not None else T.DataTree({(0,): [None]})
        ty = to_tree(y) if y is not None else None
        out = {}
        for b, (path, items) in enumerate(tx.items()):
            n = len(items)
            out[path] = [E.evaluate(code, {"x": v, "y": _match(ty, b, j) if ty is not None else None,
                                           "i": j, "b": b, "n": n})
                         for j, v in enumerate(items)]
        return IO.NodeOutput(T.DataTree(out))


class RandomPick(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_Random", display_name="Random", category=CAT_DATA,
            description="Seeded shuffle, or pick count items (with or without repeats). "
                        "Same seed, same result.",
            search_aliases=["random", "shuffle", "sample", "jitter", "pick random"],
            is_input_list=True,
            inputs=[
                tree_in(),
                IO.Combo.Input("mode", options=["shuffle", "pick", "pick (repeats)"], default="pick"),
                IO.Int.Input("count", default=1, min=1, max=10000, tooltip="Items to pick per branch"),
                IO.Int.Input("seed", default=0, min=0, max=0xFFFFFFFFFFFFFFFF, control_after_generate=True),
                IO.Boolean.Input("per_branch", default=True,
                                 tooltip="Work on every branch separately; off = on all items as one list"),
            ],
            outputs=[tree_out()])

    @classmethod
    def execute(cls, tree, mode, count, seed, per_branch) -> IO.NodeOutput:
        t = to_tree(tree)
        if not unwrap(per_branch):
            t = T.flatten(t)
        rng = random.Random(unwrap(seed))
        m, k = unwrap(mode), unwrap(count)

        def run(_, items):
            if not items:
                return []
            if m == "shuffle":
                items = list(items)
                rng.shuffle(items)
                return items
            if m == "pick":
                return rng.sample(items, min(k, len(items)))
            return [rng.choice(items) for _ in range(k)]

        return IO.NodeOutput(t.map_branches(run))


NODES = [NumberSlider, PromptTemplate, Expression, RandomPick]
