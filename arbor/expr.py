"""A small, safe expression language (Grasshopper Expression style).

Only literals, arithmetic, comparisons, boolean logic, ``a if c else b``,
indexing/slicing and a whitelist of functions are allowed — no attribute
access, no imports, no comprehensions — so typed expressions can never
reach Python internals.
"""

from __future__ import annotations

import ast
import math
import operator as op

_BIN = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow}
_UNARY = {ast.USub: op.neg, ast.UAdd: op.pos, ast.Not: op.not_}
_CMP = {ast.Eq: op.eq, ast.NotEq: op.ne, ast.Lt: op.lt, ast.LtE: op.le, ast.Gt: op.gt, ast.GtE: op.ge,
        ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}

FUNCS = {
    "abs": abs, "min": min, "max": max, "round": round, "int": int, "float": float, "str": str,
    "bool": bool, "len": len, "sum": sum,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "atan2": math.atan2,
    "floor": math.floor, "ceil": math.ceil, "log": math.log, "exp": math.exp,
    "clamp": lambda v, lo, hi: max(lo, min(hi, v)),
    "lerp": lambda a, b, t: a + (b - a) * t,
    "upper": lambda s: str(s).upper(), "lower": lambda s: str(s).lower(),
    "strip": lambda s: str(s).strip(),
    "replace": lambda s, a, b: str(s).replace(a, b),
    "join": lambda sep, *xs: str(sep).join(map(str, xs)),
}
CONSTS = {"pi": math.pi, "e": math.e, "True": True, "False": False, "None": None}
MAX_POW = 10000


class ExprError(ValueError):
    pass


def compile_expr(text: str) -> ast.Expression:
    try:
        tree = ast.parse(text.strip() or "None", mode="eval")
    except SyntaxError as e:
        raise ExprError(f"Expression syntax error: {e.msg}") from None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Attribute, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                             ast.GeneratorExp, ast.NamedExpr, ast.Starred)):
            raise ExprError(f"'{type(node).__name__}' is not allowed in expressions")
    return tree


def evaluate(tree: ast.Expression, names: dict):
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in names:
                return names[n.id]
            if n.id in CONSTS:
                return CONSTS[n.id]
            raise ExprError(f"Unknown name '{n.id}'")
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and isinstance(b, (int, float)):
                bits = a.bit_length() if isinstance(a, int) else 64
                if abs(b) > MAX_POW or bits * abs(b) > 200_000:
                    raise ExprError("Result too large")
            if isinstance(n.op, ast.Mult):
                s, k = (a, b) if isinstance(a, (str, list)) else (b, a)
                if isinstance(s, (str, list)) and isinstance(k, int) and len(s) * k > 1_000_000:
                    raise ExprError("Result too large")
            return _BIN[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UNARY:
            return _UNARY[type(n.op)](ev(n.operand))
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                v = True
                for x in n.values:
                    v = ev(x)
                    if not v:
                        return v
                return v
            v = False
            for x in n.values:
                v = ev(x)
                if v:
                    return v
            return v
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for o, c in zip(n.ops, n.comparators):
                right = ev(c)
                if not _CMP[type(o)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords:
            return FUNCS[n.func.id](*[ev(a) for a in n.args])
        if isinstance(n, (ast.Tuple, ast.List)):
            return [ev(x) for x in n.elts]
        if isinstance(n, ast.Subscript):
            return ev(n.value)[ev(n.slice)]
        if isinstance(n, ast.Slice):
            return slice(*(ev(x) if x is not None else None for x in (n.lower, n.upper, n.step)))
        raise ExprError(f"'{type(n).__name__}' is not allowed in expressions")

    try:
        return ev(tree)
    except ExprError:
        raise
    except Exception as e:
        raise ExprError(f"{type(e).__name__}: {e}") from None
