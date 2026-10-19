"""Data generators and per-item math: Number Slider, Prompt Template, Expression, Random."""

import itertools
import math
import random
import re

from . import expr as E
from . import tree as T
from .common import IO, CAT_DATA, connected, tree_in, tree_out, to_tree, unwrap
from .preview import label_of

TEMPLATE_VARS = ["a", "b", "c", "d", "e", "f"]
_VAR_RE = re.compile(r"\{([a-f])\}")
MAX_COMBOS = 10000


def _match(tree: T.DataTree, k: int, j: int):
    """Longest-list matching: item j of branch k, repeating the last ones."""
    paths = tree.paths()
    items = tree.branches[paths[min(k, len(paths) - 1)]]
    return items[min(j, len(items) - 1)] if items else None


# A socket that is both: the front end and the server accept "FLOAT,INT" on
# any INT or FLOAT input (comma types match when they overlap).
NUMBER = IO.Custom("FLOAT,INT")


def as_number(v: float) -> int | float:
    """Whole values as int (safe for steps / seeds), the rest as float."""
    return int(v) if float(v).is_integer() else float(v)


def _input_type(class_type: str, name: str):
    try:
        import nodes
        cls = nodes.NODE_CLASS_MAPPINGS.get(class_type)
        spec = cls.INPUT_TYPES() if cls is not None else {}
    except Exception:
        return None
    for group in ("required", "optional"):
        entry = (spec.get(group) or {}).get(name)
        if entry:
            return entry[0]
    return None


def feeds_int(prompt: dict | None, node_id) -> bool:
    """True when any input this node's output is linked to only accepts INT
    (steps, seed, width…): a value like 4.5 must not reach it."""
    if not prompt or node_id is None:
        return False
    for other in prompt.values():
        for name, v in (other.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2 and str(v[0]) == str(node_id):
                t = _input_type(other.get("class_type"), name)
                if isinstance(t, str) and "INT" in t.split(",") and "FLOAT" not in t.split(","):
                    return True
    return False


def step_decimals(step: float) -> int:
    """Decimal places a step implies: 1 -> 0, 0.1 -> 1, 0.05 -> 2 (max 6)."""
    if not step or step <= 0:
        return 6
    text = f"{step:.6f}".rstrip("0").rstrip(".")
    return len(text.split(".")[1]) if "." in text else 0


def slider_value(value: float, lo: float, hi: float, step: float) -> float:
    """Clamp to [lo, hi] and snap to lo + k * step (step 0 = no snapping)."""
    lo, hi = (lo, hi) if lo <= hi else (hi, lo)
    v = min(hi, max(lo, float(value)))
    if step and step > 0:
        v = lo + round((v - lo) / step) * step
        v = min(hi, max(lo, v))
    return float(round(v, step_decimals(step)))


class NumberSlider(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        big = 1e9
        return IO.Schema(
            node_id="Arbor_NumberSlider", display_name="Number Slider", category=CAT_DATA,
            description="Grasshopper-style number slider: drag the bar to set a value between min and max, "
                        "click it to type. A step of 1 gives whole numbers.",
            search_aliases=["slider", "number", "float", "int", "value", "parameter", "range slider"],
            hidden=[IO.Hidden.prompt, IO.Hidden.unique_id],
            inputs=[
                IO.Float.Input("value", default=0.5, min=-big, max=big, step=0.0001, round=False),
                IO.Float.Input("min", default=0.0, min=-big, max=big, step=0.0001, round=False),
                IO.Float.Input("max", default=1.0, min=-big, max=big, step=0.0001, round=False),
                IO.Float.Input("step", default=0.01, min=0.0, max=big, step=0.0001, round=False),
            ],
            outputs=[NUMBER.Output(display_name="value",
                                   tooltip="One output for both: connects to INT and FLOAT inputs. "
                                           "Whole numbers come out as INT, others as FLOAT.")])

    @classmethod
    def execute(cls, value, min, max, step) -> IO.NodeOutput:
        v = slider_value(value, min, max, step)
        h = cls.hidden
        if feeds_int(getattr(h, "prompt", None), getattr(h, "unique_id", None)):
            v = float(math.floor(v + 0.5))  # INT target: round half up, like the slider shows it
        return IO.NodeOutput(as_number(v))


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
        given = {k: to_tree(v) for k, v in (vars or {}).items() if connected(v)}
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
