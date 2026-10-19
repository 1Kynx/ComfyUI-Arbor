"""Live Panel preview: evaluate a Panel's upstream in place, without queueing.

Only cheap, side-effect-free nodes may run here — Arbor's data nodes plus a
few core primitive / string / math nodes. If anything upstream is not on
that list (a sampler, a loader, ...) the request is refused and the Panel
waits for a normal run instead, so nothing heavy ever executes behind the
user's back.

Request body (built by web/panel.js from the LiteGraph graph):

    {"prompt": {"<id>": {"class_type": "...", "inputs": {...}}, ...},
     "target": "<panel id>"}

Inputs use the API-prompt convention: a linked input is ``["<src id>", slot]``.
"""

from __future__ import annotations

import asyncio
import inspect

from .preview import panel_payload

CORE_SAFE = {
    "PrimitiveString", "PrimitiveStringMultiline", "PrimitiveInt", "PrimitiveFloat", "PrimitiveBoolean",
    "StringFormat", "StringConcatenate", "StringSubstring", "StringLength", "CaseConverter", "StringTrim",
    "StringReplace", "StringContains", "StringCompare", "RegexMatch", "RegexExtract", "RegexReplace",
    "ComfyMathExpression",
}
ARBOR_UNSAFE = {"Arbor_ImageSlider"}  # writes preview files for every frame
MAX_NODES = 200


class Unsupported(Exception):
    def __init__(self, class_type: str):
        super().__init__(class_type)
        self.class_type = class_type


def _mappings():
    import nodes
    return nodes.NODE_CLASS_MAPPINGS


def safe_types() -> list[str]:
    out = []
    for name, cls in _mappings().items():
        if name in ARBOR_UNSAFE:
            continue
        if (name.startswith("Arbor_") or name in CORE_SAFE) and hasattr(cls, "define_schema"):
            out.append(name)
    return sorted(out)


def _is_link(v) -> bool:
    return isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and isinstance(v[1], int)


def _nest(flat: dict) -> dict:
    """{'trees.tree0': x} -> {'trees': {'tree0': x}} (Autogrow inputs)."""
    out = {}
    for k, v in flat.items():
        if "." in k:
            head, tail = k.split(".", 1)
            out.setdefault(head, {})[tail] = v
        else:
            out[k] = v
    return out


def _call(cls, kwargs):
    res = cls.execute(**kwargs)
    if inspect.isawaitable(res):
        res = asyncio.run(res)
    if isinstance(res, dict):  # v1-style {"result": (...)}
        return tuple(res.get("result") or ())
    return tuple(getattr(res, "args", res) or ())


class _Evaluator:
    def __init__(self, prompt: dict):
        if len(prompt) > MAX_NODES:
            raise ValueError("graph too large for live preview")
        self.prompt = prompt
        self.cache: dict[str, list[list]] = {}
        self.types = set(safe_types())

    def outputs(self, nid: str, stack=()) -> list[list]:
        """Every output slot of node ``nid`` as a list (ComfyUI list semantics)."""
        if nid in self.cache:
            return self.cache[nid]
        if nid in stack:
            raise ValueError("cycle in graph")
        node = self.prompt.get(nid)
        if node is None:
            raise ValueError(f"node {nid} missing")
        ct = node.get("class_type")
        if ct not in self.types:
            raise Unsupported(ct)
        cls = _mappings()[ct]
        schema = cls.define_schema()
        ids = {i.id for i in schema.inputs}

        raw: dict[str, list] = {}
        for k, v in (node.get("inputs") or {}).items():
            if k not in ids and k.split(".", 1)[0] not in ids:
                continue  # front-end-only widgets (control_after_generate, ...)
            raw[k] = self.outputs(v[0], stack + (nid,))[v[1]] if _is_link(v) else [v]

        flags = [bool(getattr(o, "is_output_list", False)) for o in schema.outputs]
        outs: list[list] = [[] for _ in flags]

        def collect(args):
            for slot, (val, is_list) in enumerate(zip(args, flags)):
                outs[slot].extend(val if is_list and isinstance(val, list) else [val])

        if schema.is_input_list:
            collect(_call(cls, _nest(raw)))
        else:
            n = max((len(v) for v in raw.values()), default=1)
            if n and all(len(v) for v in raw.values()):
                for i in range(n):
                    collect(_call(cls, _nest({k: v[min(i, len(v) - 1)] for k, v in raw.items()})))
        self.cache[nid] = outs
        return outs


def evaluate(prompt: dict, target: str, input_name: str = "data") -> dict:
    node = prompt.get(target)
    if node is None:
        raise ValueError("target not in prompt")
    link = (node.get("inputs") or {}).get(input_name)
    if not _is_link(link):
        raise ValueError("input not connected")
    values = _Evaluator(prompt).outputs(link[0])[link[1]]
    payload = panel_payload(values)
    payload["source"] = "input"
    payload["live"] = True
    return payload


def register_routes():
    import sys
    if "server" not in sys.modules:  # imported by tests / tools, not by a running ComfyUI
        raise RuntimeError("no running server")
    from aiohttp import web
    from server import PromptServer

    routes = PromptServer.instance.routes

    @routes.get("/arbor/live_types")
    async def live_types(_request):
        return web.json_response(safe_types())

    @routes.post("/arbor/live")
    async def live(request):
        try:
            body = await request.json()
            payload = await asyncio.to_thread(evaluate, body["prompt"], str(body["target"]))
            return web.json_response({"ok": True, "payload": payload})
        except Unsupported as e:
            return web.json_response({"ok": False, "unsupported": e.class_type})
        except Exception as e:  # shown in the Panel; a live preview must never crash the server
            return web.json_response({"ok": False, "error": f"{type(e).__name__}: {e}"})
