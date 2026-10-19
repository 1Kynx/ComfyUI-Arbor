"""Generate translations and help pages from tools/node_info*.py.

    python_embeded\\python.exe tools\\build_locales.py <path-to-ComfyUI>

Writes
  locales/<lang>/nodeDefs.json   names, descriptions, input / output tooltips
  locales/zh/main.json           category names
  web/docs/<node id>/<lang>.md   help page shown in ComfyUI's right-side panel
  web/docs/<node id>.md          English fallback for other languages

ComfyUI picks the language from its own setting (Comfy.Locale). Input types
in the help tables come from the node schemas, so they cannot drift; every
node, input and output must be documented or the build fails.
"""

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])

from comfy_api.latest import IO  # noqa: E402
from node_info import INFO  # noqa: E402
import node_info_tree  # noqa: E402,F401  (registers the tree / list / util nodes)

LANGS = ("en", "zh")
CATEGORIES_ZH = {"Arbor": "Arbor", "Image": "图像", "Data": "数据", "Tree": "数据树", "List": "列表"}
HEAD = {
    "en": {"inputs": "Inputs", "outputs": "Outputs", "name": "Name", "type": "Type", "desc": "Description",
           "optional": "optional", "slots": "grows as you connect", "any": "any", "tree": "TREE"},
    "zh": {"inputs": "输入", "outputs": "输出", "name": "名称", "type": "类型", "desc": "说明",
           "optional": "可选", "slots": "连接后自动增加", "any": "任意", "tree": "数据树"},
}


def load_nodes():
    spec = importlib.util.spec_from_file_location(
        "arbor_pkg", os.path.join(ROOT, "__init__.py"), submodule_search_locations=[ROOT])
    pkg = importlib.util.module_from_spec(spec)
    sys.modules["arbor_pkg"] = pkg
    spec.loader.exec_module(pkg)
    return pkg.NODES


def key(input_id: str) -> str:
    return input_id.replace(".", "_")


def is_autogrow(inp) -> bool:
    return isinstance(inp, IO.Autogrow.Input)


def is_dynamic_combo(inp) -> bool:
    return isinstance(inp, IO.DynamicCombo.Input)


def type_name(inp, lang) -> str:
    h = HEAD[lang]
    if is_autogrow(inp):
        return f"{type_name(inp.template.input, lang)} × N"
    if is_dynamic_combo(inp):
        return "COMBO"
    t = inp.get_io_type()
    parts = [h["any"] if p == "*" else h["tree"] if p == "ARBOR_TREE" else p for p in str(t).split(",")]
    out = " / ".join(parts)
    if out == "COMBO" and getattr(inp, "options", None):
        out += " (" + " · ".join(map(str, inp.options)) + ")"
    return out


def out_type(o, lang) -> str:
    t = o.get_io_type() if hasattr(o, "get_io_type") else getattr(o, "io_type", "")
    h = HEAD[lang]
    t = h["any"] if t == "*" else h["tree"] if t == "ARBOR_TREE" else str(t).replace(",", " / ")
    return t + (" ×N" if getattr(o, "is_output_list", False) else "")


def rows(schema):
    """(input id, input object, is_sub) in display order, DynamicCombo fields expanded."""
    for inp in schema.inputs:
        yield inp.id, inp, False
        if is_dynamic_combo(inp):
            seen = set()
            for opt in inp.options:
                for sub in opt.inputs:
                    sid = f"{inp.id}.{sub.id}"
                    if sid not in seen:
                        seen.add(sid)
                        yield sid, sub, True


def check(nodes):
    problems = []
    for n in nodes:
        s = n.define_schema()
        info = INFO.get(s.node_id)
        if info is None:
            problems.append(f"{s.node_id}: no docs")
            continue
        for lang in LANGS:
            d = info[lang]
            for iid, _, _ in rows(s):
                if iid not in d["inputs"]:
                    problems.append(f"{s.node_id} [{lang}]: input {iid} undocumented")
            extra = set(d["inputs"]) - {iid for iid, _, _ in rows(s)}
            if extra:
                problems.append(f"{s.node_id} [{lang}]: unknown inputs {sorted(extra)}")
            if len(d["outputs"]) != len(s.outputs):
                problems.append(f"{s.node_id} [{lang}]: {len(d['outputs'])} outputs documented, schema has {len(s.outputs)}")
    if problems:
        raise SystemExit("Docs are incomplete:\n  " + "\n  ".join(problems))


def label_tip(lang, value, fallback):
    """zh entries are (label, tip); en entries are a tip, or (label, tip) to rename the socket."""
    if isinstance(value, tuple):
        return value
    return fallback, value


def node_defs(nodes, lang):
    defs = {}
    for n in nodes:
        s = n.define_schema()
        d = INFO[s.node_id][lang]
        entry = {"display_name": d.get("name", s.display_name), "description": d["desc"]}
        ins = {}
        for iid, inp, _ in rows(s):
            name, tip = label_tip(lang, d["inputs"][iid], iid.split(".")[-1])
            ins[key(iid)] = {"name": name, "tooltip": tip}
            if is_autogrow(inp):
                t = inp.template
                for slot in t.names:
                    ins[key(f"{iid}.{slot}")] = {
                        "name": slot if lang == "en" or len(slot) == 1 else f"{name}{slot.lstrip('abcdefghijklmnopqrstuvwxyz_')}",
                        "tooltip": tip}
        if ins:
            entry["inputs"] = ins
        outs = {}
        for i, o in enumerate(s.outputs):
            name, tip = label_tip(lang, d["outputs"][i], o.display_name or o.get_io_type())
            outs[str(i)] = {"name": name, "tooltip": tip}
        if outs:
            entry["outputs"] = outs
        defs[s.node_id] = entry
    return defs


def help_page(n, lang):
    """Inputs / outputs as a list, not a table: the right-side panel is narrow."""
    s = n.define_schema()
    d = INFO[s.node_id][lang]
    h = HEAD[lang]
    title = d.get("name", s.display_name)
    lines = [f"# {title}", "", d["desc"], ""]

    def item(label, ident, typ, tip, sub=False):
        name = f"**{label}**" if label == ident else f"**{label}** `{ident}`"
        pad = "  " if sub else ""
        return f"{pad}- {name} · *{typ}*  \n{pad}  {tip}"

    if s.inputs:
        lines += [f"## {h['inputs']}", ""]
        for iid, inp, sub in rows(s):
            label, tip = label_tip(lang, d["inputs"][iid], iid)
            flags = []
            if getattr(inp, "optional", False):
                flags.append(h["optional"])
            if is_autogrow(inp):
                flags.append(h["slots"])
            sep = ", " if lang == "en" else "，"
            typ = type_name(inp, lang) + (sep + sep.join(flags) if flags else "")
            lines.append(item(label, iid.split(".")[-1] if sub else iid, typ, tip, sub))
        lines.append("")
    if s.outputs:
        lines += [f"## {h['outputs']}", ""]
        for i, o in enumerate(s.outputs):
            label, tip = label_tip(lang, d["outputs"][i], o.display_name)
            lines.append(item(label, o.display_name, out_type(o, lang), tip))
        lines.append("")
    lines.append(d["doc"].strip())
    return "\n".join(lines) + "\n"


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    nodes = load_nodes()
    check(nodes)
    for lang in LANGS:
        write_json(os.path.join(ROOT, "locales", lang, "nodeDefs.json"), node_defs(nodes, lang))
    write_json(os.path.join(ROOT, "locales", "zh", "main.json"), {"nodeCategories": CATEGORIES_ZH})
    for n in nodes:
        nid = n.define_schema().node_id
        for lang in LANGS:
            write_text(os.path.join(ROOT, "web", "docs", nid, f"{lang}.md"), help_page(n, lang))
        write_text(os.path.join(ROOT, "web", "docs", f"{nid}.md"), help_page(n, "en"))
    print(f"wrote locales (en, zh) and help pages for {len(nodes)} nodes")


if __name__ == "__main__":
    main()
