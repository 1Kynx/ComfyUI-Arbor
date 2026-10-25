"""Data nodes: where values come from (slid, generated, split, templated, computed) and which one goes on.

(The Panel, which both shows and types data, lives in nodes_panel.py.)
"""

import itertools
import math
import random
import re

from . import expr as E
from . import tree as T
from .common import IO, NUMBER, CAT_DATA, schema, connected, data_out, tree_in, tree_out, to_tree, unwrap
from .preview import label_of

MAX_COMBOS = 10000


def both(tree: T.DataTree) -> IO.NodeOutput:
    """data (every item, flat) + tree (with its branches)."""
    return IO.NodeOutput(tree.flat(), tree)


# ======================================================================= Number Slider

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


class NumberSlider(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        num = lambda id, d, lo=-1e9: IO.Float.Input(id, default=d, min=lo, max=1e9, step=0.0001, round=False)
        return schema(
            "Arbor_NumberSlider", "Number Slider", CAT_DATA,
            "Grasshopper-style number slider: drag the bar to set a value between min and max, "
            "click it to type. A step of 1 gives whole numbers.",
            [num("value", 0.5), num("min", 0.0), num("max", 1.0), num("step", 0.01, lo=0.0)],
            [NUMBER.Output(display_name="data",
                           tooltip="One output for both: connects to INT and FLOAT inputs. "
                                   "Whole numbers come out as INT, others as FLOAT.")],
            ["slider", "number", "float", "int", "value", "parameter", "range slider"],
            input_list=False, hidden=[IO.Hidden.prompt, IO.Hidden.unique_id])

    @classmethod
    def execute(cls, value, min, max, step) -> IO.NodeOutput:
        v = slider_value(value, min, max, step)
        h = cls.hidden
        if feeds_int(getattr(h, "prompt", None), getattr(h, "unique_id", None)):
            v = float(math.floor(v + 0.5))  # INT target: round half up, like the slider shows it
        return IO.NodeOutput(as_number(v))


# ======================================================================= Number Sequence

def sequence_values(mode: str, a: float, b: float, n: int, as_int: bool) -> list:
    """series: a, a+b, … (n numbers) · range: a → b split into n parts (n + 1 numbers)."""
    n = max(1, int(n))
    vals = [a + (b - a) * i / n for i in range(n + 1)] if mode == "range" else [a + b * i for i in range(n)]
    return [int(round(v)) for v in vals] if as_int else [round(v, 10) for v in vals]


class NumberSequence(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        num = lambda id, d: IO.Float.Input(id, default=d, step=0.1, min=-1e9, max=1e9)
        return schema(
            "Arbor_NumberSequence", "Number Sequence", CAT_DATA,
            "A list of numbers. series: start, start + step, … (count numbers). "
            "range: start → end split evenly (steps + 1 numbers, both ends included).",
            [IO.DynamicCombo.Input("mode", options=[
                IO.DynamicCombo.Option("series", [num("start", 0.0), num("step", 1.0),
                                                  IO.Int.Input("count", default=5, min=1, max=10000)]),
                IO.DynamicCombo.Option("range", [num("start", 0.0), num("end", 1.0),
                                                 IO.Int.Input("steps", default=4, min=1, max=10000)]),
            ]),
             IO.Boolean.Input("as_int", default=False, tooltip="Output whole numbers (for seeds, steps, sizes)")],
            [data_out(NUMBER, "The numbers as plain data — connect straight to cfg, steps, seed…, "
                              "or to any Arbor input")],
            ["series", "range", "sequence", "linspace", "arithmetic", "number list", "domain"],
            input_list=False)

    @classmethod
    def execute(cls, mode, as_int) -> IO.NodeOutput:
        if mode["mode"] == "range":
            return IO.NodeOutput(sequence_values("range", mode["start"], mode["end"], mode["steps"], as_int))
        return IO.NodeOutput(sequence_values("series", mode["start"], mode["step"], mode["count"], as_int))


# ======================================================================= Split Text

class SplitText(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_SplitText", "Split Text", CAT_DATA,
            "Split text into items — one per line or separator; an empty line starts a new branch. "
            "'table' reads a pasted spreadsheet (tab or comma separated): one branch per column, named "
            "after its header. For text coming from other nodes (to type it, use a Panel).",
            [IO.String.Input("text", multiline=True, default=""),
             IO.Combo.Input("separator", options=["newline", ",", ";", "|", "table"], default="newline",
                            tooltip="table: rows from a spreadsheet or CSV (cells split by tabs, or by commas "
                                    "when there are no tabs; quotes allowed). The first row names the columns; "
                                    "every column becomes a branch"),
             IO.Boolean.Input("blank_line_branches", default=True,
                              tooltip="Paragraphs separated by an empty line become branches {0},{1},…"),
             IO.Boolean.Input("strip", default=True)],
            [data_out(IO.String, "Every item as plain text data (paragraphs one after another)"),
             tree_out(tooltip="One branch per paragraph")],
            ["prompt list", "lines", "text list", "wildcard"])

    @classmethod
    def execute(cls, text, separator, blank_line_branches, strip) -> IO.NodeOutput:
        text = str(unwrap(text, "")).replace("\r\n", "\n")
        sep = unwrap(separator)
        if sep == "table":
            return both(split_table(text, unwrap(strip)))
        blocks = re.split(r"\n\s*\n", text) if unwrap(blank_line_branches) else [text]
        out = {}
        for block in blocks:
            parts = block.split("\n") if sep == "newline" else re.split(rf"[{re.escape(sep)}\n]", block)
            if unwrap(strip):
                parts = [p.strip() for p in parts]
            parts = [p for p in parts if p != ""]
            if parts:
                out[(len(out),)] = parts
        return both(T.DataTree(out or {(0,): []}))


def split_table(text: str, strip: bool = True) -> T.DataTree:
    """A pasted spreadsheet / CSV -> one branch per column, named after its header cell."""
    import csv
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        return T.DataTree({(0,): []})
    delim = "\t" if "\t" in lines[0] else ","
    rows = list(csv.reader(lines, delimiter=delim))
    if strip:
        rows = [[c.strip() for c in r] for r in rows]
    header, body = rows[0], rows[1:]
    out, names = {}, {}
    for c in range(max(len(r) for r in rows)):
        out[(c,)] = [r[c] if c < len(r) else "" for r in body]
        if c < len(header) and header[c]:
            names[(c,)] = header[c]
    return T.DataTree(out, names)


# ======================================================================= Prompt Template

TEMPLATE_VARS = ["a", "b", "c", "d", "e", "f"]
_VAR_RE = re.compile(r"\{([a-f])\}")


class PromptTemplate(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        vars_ = IO.Autogrow.TemplateNames(
            tree_in("var", tooltip="Values for {a}, {b}, … — a tree, list or single value"),
            names=TEMPLATE_VARS, min=1)
        return schema(
            "Arbor_PromptTemplate", "Prompt Template", CAT_DATA,
            "Fill {a} {b} … in a template from trees. Cross: every combination, as a grid-ready tree "
            "(rows = a, columns = last variable). Zip: item by item, branches paired like Grasshopper "
            "(in order, longest list); {name} is the branch's name.",
            [IO.String.Input("template", multiline=True, default="a photo of {a}, {b}"),
             IO.Combo.Input("mode", options=["cross", "zip"], default="cross"),
             IO.Autogrow.Input("vars", template=vars_, optional=True)],
            [data_out(IO.String, "Every prompt as plain text data — connect straight to a text encoder"),
             tree_out(tooltip="The prompts as a tree (cross: rows × columns, ready for Image Grid)")],
            ["template", "format", "prompt matrix", "combinations", "wildcard", "fill"])

    @classmethod
    def execute(cls, template, mode, vars=None) -> IO.NodeOutput:
        text = str(unwrap(template, ""))
        used = [v for v in TEMPLATE_VARS if f"{{{v}}}" in text]
        given = {k: to_tree(v) for k, v in (vars or {}).items() if connected(v)}
        lists = {k: [label_of(x) for x in given[k].flat()] for k in used if k in given}
        filled = [k for k in used if lists.get(k)]

        def fill(values: dict) -> str:
            return _VAR_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)

        if not filled:
            return both(T.DataTree({(0,): [fill({})]}))
        if unwrap(mode) == "zip":
            # branches pair in order, items longest-list (Expression's matching); the tree keeps the
            # branches and names of the input with the longest paths, and {name} is the branch's name
            pairs, master = T.match_branches(*(given[k] for k in filled))
            out = {}
            for path, branches in pairs:
                lengths = [len(b) if b else 0 for b in branches]
                n = 0 if 0 in lengths else max(lengths)
                name = master.label(path, label_of) or ""
                out[path] = [fill({k: label_of(b[min(i, len(b) - 1)]) for k, b in zip(filled, branches)})
                             .replace("{name}", name) for i in range(n)]
            return both(T.DataTree(out, master.names))
        total = math.prod(len(lists[k]) for k in filled)
        if total > MAX_COMBOS:
            raise ValueError(f"Prompt Template: {total} combinations (max {MAX_COMBOS})")
        *outer, last = filled
        out, row_names = {}, {}
        for idx in itertools.product(*[range(len(lists[k])) for k in outer]):
            vals = {k: lists[k][i] for k, i in zip(outer, idx)}
            out[tuple(idx) or (0,)] = [fill({**vals, last: v}) for v in lists[last]]
            if vals:
                row_names[tuple(idx)] = " · ".join(vals.values())  # the row's outer values, for Image Grid
        return both(T.DataTree(out, row_names))


# ======================================================================= Expression

class Expression(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_Expression", "Expression", CAT_DATA,
            "Evaluate an expression for every item, matching x and y like Grasshopper: branches in "
            "order, items longest-list, paths from the input with the longest paths. Names: x, y, "
            "i (item index), b (branch index), n (branch length), name (the branch's name, e.g. a scene title). "
            "Functions: abs min max round int float str sqrt sin cos floor ceil log exp "
            "clamp lerp upper lower strip replace join len sum.",
            [IO.String.Input("expression", default="x * 2"), tree_in("x", optional=True), tree_in("y", optional=True)],
            [data_out(tooltip="Every result as plain data"), tree_out(tooltip="The results in x's tree layout")],
            ["math", "formula", "evaluate", "calculate", "eval"])

    @classmethod
    def execute(cls, expression, x=None, y=None) -> IO.NodeOutput:
        code = E.compile_expr(str(unwrap(expression, "")))
        tx = to_tree(x) if connected(x) else None
        ty = to_tree(y) if connected(y) else None
        if tx is None and ty is None:
            tx = T.DataTree({(0,): [None]})  # nothing connected: one constant result
        pairs, master = T.match_branches(tx, ty)
        out = {}
        for b, (path, (bx, by)) in enumerate(pairs):
            lengths = [len(v) for v in (bx, by) if v is not None]
            n = 0 if 0 in lengths else max(lengths)  # longest list; an empty branch gives nothing
            pick = lambda items, j: items[min(j, len(items) - 1)] if items else None
            name = master.label(path, label_of) or ""
            out[path] = [E.evaluate(code, {"x": pick(bx, j), "y": pick(by, j), "i": j, "b": b, "n": n, "name": name})
                         for j in range(n)]
        return both(T.DataTree(out, master.names))


# ======================================================================= Random

class Random(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_Random", "Random", CAT_DATA,
            "Seeded shuffle, or pick count items (with or without repeats). Same seed, same result.",
            [tree_in(),
             IO.Combo.Input("mode", options=["shuffle", "pick", "pick (repeats)"], default="pick"),
             IO.Int.Input("count", default=1, min=1, max=10000, tooltip="Items to pick per branch"),
             IO.Int.Input("seed", default=0, min=0, max=0xFFFFFFFFFFFFFFFF, control_after_generate=True),
             IO.Boolean.Input("per_branch", default=True,
                              tooltip="Work on every branch separately; off = on all items as one list")],
            [data_out(tooltip="The picked items as plain data"), tree_out(tooltip="The picked items, branch by branch")],
            ["random", "shuffle", "sample", "jitter", "pick random"])

    @classmethod
    def execute(cls, tree, mode, count, seed, per_branch) -> IO.NodeOutput:
        t = to_tree(tree) if unwrap(per_branch) else T.flatten(to_tree(tree))
        rng = random.Random(unwrap(seed))
        m, k = unwrap(mode), unwrap(count)

        def run(_, items):
            if not items:
                return []
            if m == "shuffle":
                return rng.sample(items, len(items))
            if m == "pick":
                return rng.sample(items, min(k, len(items)))
            return [rng.choice(items) for _ in range(k)]

        return both(t.map_branches(run))


# ======================================================================= Collect

COLLECT_MODES = ["branch per input", "one list"]


class Collect(IO.ComfyNode):
    """Gather anything — pictures, masks, latents, audio, video, text — into a list or one branch per input."""

    @classmethod
    def define_schema(cls):
        slot = IO.Autogrow.TemplatePrefix(
            IO.AnyType.Input("input", tooltip="Anything: an image or batch, a mask, a latent, audio, video, "
                                              "text, a list or a tree"),
            prefix="input", min=1, max=32)
        return schema(
            "Arbor_Collect", "Collect", CAT_DATA,
            "Gather any values — not only text — into data. branch per input: every connected input becomes "
            "its own branch {0}, {1}, …, named from the names box; one list: everything in one list.",
            [IO.Autogrow.Input("inputs", template=slot),
             IO.Combo.Input("mode", options=COLLECT_MODES, default=COLLECT_MODES[0],
                            tooltip="branch per input: {0}, {1}, … one per connected input · one list: all in {0}"),
             IO.String.Input("names", multiline=True, default="",
                             tooltip="One name per line, for the branches in input order — they label grid "
                                     "rows and name saved folders"),
             IO.Boolean.Input("split_batch", default=False,
                              tooltip="Split IMAGE / MASK / LATENT batches into one item per frame")],
            [data_out(tooltip="Every collected item as plain data"),
             tree_out(tooltip="The collected items as a tree, one (named) branch per input")],
            ["collect", "gather", "create list", "make list", "create data", "bundle", "group inputs",
             "compare pipelines", "收集", "创建数据", "创建列表"])

    @classmethod
    def execute(cls, inputs: IO.Autogrow.Type, mode, names, split_batch) -> IO.NodeOutput:
        slots = [v for k, v in sorted((inputs or {}).items(), key=lambda kv: int(kv[0].removeprefix("input") or 0))
                 if connected(v)]
        if not slots:
            raise ValueError("Collect: connect at least one input")
        split = bool(unwrap(split_batch))
        labels = [line.strip() for line in str(unwrap(names, "")).splitlines() if line.strip()]

        def items(values: list) -> list:
            out = []
            for v in values:
                if isinstance(v, T.DataTree):
                    out.extend(items(v.flat()))
                elif v is not None:
                    out.extend(T.split_batch(v) if split else [v])
            return out

        if unwrap(mode) == "one list":
            tree = T.DataTree({(0,): items([v for s in slots for v in s])}, {(0,): labels[0]} if labels else None)
            return both(tree)
        branches, branch_names = {}, {}
        for i, value in enumerate(slots):
            values = value if isinstance(value, list) else [value]
            if len(values) == 1 and isinstance(values[0], T.DataTree):  # a tree keeps its branches, under {i;…}
                sub = values[0]
                for p, its in sub.items():
                    branches[(i,) + p] = items(its)
                branch_names.update({(i,) + p: n for p, n in sub.names.items()})
            else:
                branches[(i,)] = items(values)
            if i < len(labels):
                branch_names[(i,)] = labels[i]
        return both(T.DataTree(branches, branch_names))


# ======================================================================= Index Switch

class IndexSwitch(IO.ComfyNode):
    """Pick one of many inputs by index. Inputs are lazy: only the chosen one runs."""

    @classmethod
    def define_schema(cls):
        slot = IO.Autogrow.TemplatePrefix(
            IO.AnyType.Input("input", lazy=True, tooltip="Only evaluated when selected"),
            prefix="input", min=1, max=32)
        index = IO.MultiType.Input(
            IO.Int.Input("index", default=0, min=-1000, max=1000,
                         tooltip="0 = first connected input; negative counts from the end. "
                                 "A BOOLEAN works too: False = 0, True = 1"),
            types=[IO.Boolean])
        return schema(
            "Arbor_IndexSwitch", "Index Switch", CAT_DATA,
            "Pass through input N (counting connected inputs, wrapping around). "
            "Unselected branches are not executed at all.",
            [index, IO.Autogrow.Input("inputs", template=slot)],
            [IO.AnyType.Output(display_name="data", tooltip="The selected input, passed through"),
             IO.Int.Output(display_name="count")],
            ["switch", "select", "stream filter", "choose", "multiplexer", "any switch"],
            input_list=False, hidden=[IO.Hidden.prompt, IO.Hidden.unique_id])

    @classmethod
    def _connected(cls, inputs) -> list[str]:
        """Names of linked slots, in slot order.

        Unlinked slots arrive as None just like linked-but-not-yet-evaluated
        lazy ones, so the links are read from the prompt itself.
        """
        names = list((inputs or {}).keys())
        prompt = getattr(cls.hidden, "prompt", None)
        uid = getattr(cls.hidden, "unique_id", None)
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
        names = cls._connected(inputs)
        value, full_key = inputs[names[int(index) % len(names)]]  # int(): BOOLEAN -> 0 / 1
        return [full_key] if value is None else []

    @classmethod
    def execute(cls, index, inputs=None) -> IO.NodeOutput:
        names = cls._connected(inputs)
        return IO.NodeOutput(inputs[names[int(index) % len(names)]], len(names))


NODES = [NumberSlider, NumberSequence, SplitText, PromptTemplate, Expression, Random, Collect, IndexSwitch]
