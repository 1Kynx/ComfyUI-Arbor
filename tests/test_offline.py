"""Offline tests: tree algebra + every node's execute(), no GPU or models.

Run with ComfyUI's embedded python so comfy_api / folder_paths import:

    python_embeded\\python.exe tests\\test_offline.py <path-to-ComfyUI>
"""

import math
import importlib.util
import os
import sys

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFY = sys.argv[1] if len(sys.argv) > 1 else None
if COMFY:
    sys.path.insert(0, COMFY)

import torch  # noqa: E402

# load the package under a hyphen-free name so relative imports resolve
_spec = importlib.util.spec_from_file_location(
    "arbor_pkg", os.path.join(PKG_DIR, "__init__.py"), submodule_search_locations=[PKG_DIR])
pkg = importlib.util.module_from_spec(_spec)
sys.modules["arbor_pkg"] = pkg
_spec.loader.exec_module(pkg)

from arbor_pkg.arbor import grid, live, nodes_data, nodes_region, nodes_files, nodes_image, nodes_list, nodes_panel, \
    nodes_sampling, nodes_tree  # noqa: E402
from arbor_pkg.arbor import tree as T  # noqa: E402

P = T.format_path


def run(node, **kw):
    """Call execute the way ComfyUI does for is_input_list nodes."""
    if node.define_schema().is_input_list:
        kw = {k: v if isinstance(v, (list, dict)) else [v] for k, v in kw.items()}
    return node.execute(**kw)


def res(out):
    return out.result if hasattr(out, "result") else out.args


def raises(exc, fn, *args, **kw):
    try:
        fn(*args, **kw)
    except exc:
        return
    raise AssertionError(f"{fn.__name__} should raise {exc.__name__}")


def grid_kw(**kw):
    return dict(fit="fit", cell_size=0, gap=2, font_size=10, theme="light", path_labels=False) | kw


# ====================================================================== tree algebra

def test_tree_algebra():
    t = T.DataTree({(0,): [1, 2, 3], (1,): [4, 5]})
    g = T.graft(t)
    assert [P(p) for p in g.paths()] == ["{0;0}", "{0;1}", "{0;2}", "{1;0}", "{1;1}"]
    assert T.shift_paths(g, -1).branches == t.branches, "shift -1 undoes graft"
    assert T.graft(T.DataTree({(0,): [1, 2], (1,): []})).branches == {(0, 0): [1], (0, 1): [2], (1,): []}, \
        "graft keeps empty branches so later ones still line up"
    assert T.flatten(t).branches == {(0,): [1, 2, 3, 4, 5]}
    assert T.flip_matrix(t).branches == {(0,): [1, 4], (1,): [2, 5], (2,): [3]}
    s = T.simplify(T.DataTree({(0, 0, 1): ["a"], (0, 0, 2): ["b"]}))
    assert s.branches == {(1,): ["a"], (2,): ["b"]}, s.branches
    assert T.parse_path("{0; 2}") == (0, 2) and T.parse_path("") == (0,)
    assert T.parse_pattern("TFT") == [True, False, True]
    assert T.parse_pattern("true, 0") == [True, False]
    assert T.partition(T.DataTree({(0,): list(range(5))}), 2).branches == {
        (0, 0): [0, 1], (0, 1): [2, 3], (0, 2): [4]}
    assert T.repeat(t, 2, "whole").branches[(1,)] == [4, 5, 4, 5]
    assert T.list_items(t, "-1").branches == {(0,): [3], (1,): [5]}
    picks = T.DataTree({(0,): ["2"], (1,): [0, 1]})
    assert T.list_items(t, picks).branches == {(0,): [3], (1,): [4, 5]}, "one pick per branch"
    loc = T.DataTree({(0,): ["tea"], (1,): ["bamboo"]}, {(0,): "Tea house"})
    shots = T.DataTree({(0, 0): ["s1", "s2", "s3"], (0, 1): ["s1", "s2"], (0, 2): ["s1"]})
    m = T.repeat_to(loc, shots)
    assert m.branches == {(0, 0): ["tea"] * 3, (0, 1): ["bamboo"] * 2, (0, 2): ["bamboo"]}, m.branches
    assert m.names == {(0, 0): "Tea house"}, "a branch keeps its name where the shape has none"
    ab = T.DataTree({(0,): ["a", "b"]})
    four = T.DataTree({(0,): [1, 2, 3, 4]})
    assert T.repeat_to(ab, four, "each").branches[(0,)] == ["a", "a", "b", "b"]
    assert T.repeat_to(ab, four, "whole").branches[(0,)] == ["a", "b", "a", "b"]
    assert T.list_items(t, "0, 5", wrap=False).branches == {(0,): [1, None], (1,): [4, None]}, "null keeps alignment"
    assert T.parse_indices("0, -1, 2-4, ::3, 4-2", 6) == [0, -1, 2, 3, 4, 0, 3, 4, 3, 2]
    assert T.parse_indices(3, 5) == [3], "a connected number"
    raises(ValueError, T.parse_indices, "x", 3)
    assert T.sort_list(T.DataTree({(0,): [2, 1, 3]}), "reverse").branches == {(0,): [3, 1, 2]}
    # branch names ride along where paths stay put, and through a shape
    named = T.DataTree({(0,): [1], (1,): [2]}, {(1,): "b", (5,): "gone"})
    assert named.names == {(1,): "b"}, "names only for existing branches"
    assert named.map_items(lambda v: v * 2).names == {(1,): "b"}
    assert T.rebuild(["x", "y"], named).names == {(1,): "b"}
    assert T.renumber(T.DataTree({(3,): [1], (7,): [2]}, {(7,): "b"})).names == {(1,): "b"}
    assert T.get_branch(named, (1,)).names == {(1,): "b"}
    m = T.merge([t, T.DataTree({(1,): [9], (2,): [8]})])
    assert m.branches == {(0,): [1, 2, 3], (1,): [4, 5, 9], (2,): [8]}
    assert T.entwine([t, t]).paths()[2] == (1, 0)
    assert T.to_tree([1, 2]).branches == {(0,): [1, 2]}
    assert T.to_tree([t]) is t
    assert [T.match_item(t, 1, j) for j in range(4)] == [4, 5, 5, 5], "longest-list matching"
    assert T.to_bool("TRUE") and not T.to_bool(0) and not T.to_bool("off")
    raises(ValueError, T.to_bool, "maybe")
    print("tree algebra: OK")


def test_cross_and_rebuild():
    a = T.DataTree({(0,): [3, 5]})
    b = T.DataTree({(0,): ["x", "y", "z"]})
    ca, cb = T.cross_reference(a, b)
    assert ca.branches == {(0, 0): [3, 3, 3], (0, 1): [5, 5, 5]}
    assert ca.names == cb.names == {(0, 0): 3, (0, 1): 5}, "each row named after its A value"
    assert cb.branches == {(0, 0): ["x", "y", "z"], (0, 1): ["x", "y", "z"]}
    back = T.rebuild([f"img{i}" for i in range(ca.item_count)], ca)
    assert back.branches[(0, 1)] == ["img3", "img4", "img5"]
    raises(ValueError, T.rebuild, [1], ca)
    print("cross reference / rebuild: OK")


# ====================================================================== data nodes

def test_data_nodes():
    # Number Sequence: plain data (a native list), by step or by both ends
    seq = nodes_data.NumberSequence
    out = seq.define_schema().outputs[0]
    assert out.is_output_list and out.get_io_type() == "FLOAT,INT" and out.display_name == "data"
    assert res(seq.execute({"mode": "series", "start": 1.0, "step": 0.5, "count": 4}, False))[0] == [1.0, 1.5, 2.0, 2.5]
    assert res(seq.execute({"mode": "range", "start": 0.0, "end": 1.0, "steps": 4}, False))[0] == [0, 0.25, 0.5, 0.75, 1.0]
    ints = res(seq.execute({"mode": "range", "start": 3.0, "end": 9.0, "steps": 3}, True))[0]
    assert ints == [3, 5, 7, 9] and all(isinstance(v, int) for v in ints)

    # Split Text: data (every item) + tree (one branch per paragraph)
    flat, st = res(run(nodes_data.SplitText, text="cat\ndog\n\nred, blue", separator="newline",
                       blank_line_branches=True, strip=True))
    assert flat == ["cat", "dog", "red, blue"]
    assert st.branches == {(0,): ["cat", "dog"], (1,): ["red, blue"]}
    st2 = res(run(nodes_data.SplitText, text="red, blue", separator=",", blank_line_branches=True, strip=True))[1]
    assert st2.branches == {(0,): ["red", "blue"]}
    sheet = "scene\tmotion\tsound\nArrival\tthe train pulls away\thorn\nVillage\tmist drifts\n"
    tab = res(run(nodes_data.SplitText, text=sheet, separator="table", blank_line_branches=True, strip=True))[1]
    assert tab.branches == {(0,): ["Arrival", "Village"], (1,): ["the train pulls away", "mist drifts"],
                            (2,): ["horn", ""]}, tab.branches
    assert tab.names == {(0,): "scene", (1,): "motion", (2,): "sound"}, "columns named after the header"
    csv_tab = res(run(nodes_data.SplitText, text='name,prompt\ncat,"a cat, sleeping"', separator="table",
                      blank_line_branches=True, strip=True))[1]
    assert csv_tab.branches[(1,)] == ["a cat, sleeping"], "quoted commas stay in the cell"

    # Prompt Template
    a = T.DataTree({(0,): ["cat", "dog"]})
    b = T.DataTree({(0,): ["oil", "ink", "pixel"]})
    data, cross = res(run(nodes_data.PromptTemplate, template="{a} in {b} style", mode="cross",
                          vars={"a": [a], "b": [b]}))
    assert cross.branches == {(0,): ["cat in oil style", "cat in ink style", "cat in pixel style"],
                              (1,): ["dog in oil style", "dog in ink style", "dog in pixel style"]}
    assert data == cross.flat(), "data = every prompt, flat"
    z = res(run(nodes_data.PromptTemplate, template="{a}/{b}/{c}", mode="zip", vars={"a": [a], "b": [b]}))[1]
    assert z.branches == {(0,): ["cat/oil/{c}", "dog/ink/{c}", "dog/pixel/{c}"]}, z.branches
    # zip pairs branches like Grasshopper: two shots per scene, one sound line per scene, {name} = scene
    shots = T.DataTree({(0,): ["door", "map"], (1,): ["mist", "steps"]}, {(0,): "Arrival", (1,): "Village"})
    sounds = T.DataTree({(0,): ["horn"], (1,): ["bells"]})
    sz = res(run(nodes_data.PromptTemplate, template="{name}: {a} + {b}", mode="zip",
                 vars={"a": [shots], "b": [sounds]}))[1]
    assert sz.branches == {(0,): ["Arrival: door + horn", "Arrival: map + horn"],
                           (1,): ["Village: mist + bells", "Village: steps + bells"]}, sz.branches
    assert sz.names == shots.names
    one =res(run(nodes_data.PromptTemplate, template="{a}!", mode="cross", vars={"a": [7, 8]}))[1]
    assert one.branches == {(0,): ["7!", "8!"]}
    # the trailing empty Autogrow slot arrives as [None] in a real run
    pt = res(run(nodes_data.PromptTemplate, template="{a}-{b}", mode="cross",
                 vars={"a": ["x"], "b": [None], "c": [None]}))[1]
    assert pt.branches == {(0,): ["x-{b}"]}, pt.branches

    # Expression
    from arbor_pkg.arbor import expr as E
    xs = T.DataTree({(0,): [1, 2, 3], (1,): [10]})
    data, r = res(run(nodes_data.Expression, expression="x * 2 + i", x=[xs]))
    assert r.branches == {(0,): [2, 5, 8], (1,): [20]} and data == [2, 5, 8, 20]
    scenes = T.DataTree({(0,): ["train"], (1,): ["dawn"]}, {(1,): "Village"})
    styled = res(run(nodes_data.Expression, expression='x + ", " + y', x=[scenes], y=["anime"]))[1]
    assert styled.branches[(1,)] == ["dawn, anime"] and styled.names == {(1,): "Village"}, "names survive"
    r = res(run(nodes_data.Expression, expression="x + y", x=[xs], y=[T.DataTree({(0,): [100]})]))[1]
    assert r.branches == {(0,): [101, 102, 103], (1,): [110]}, "longest-list matching"
    r = res(run(nodes_data.Expression, expression="upper(x) if len(x) > 2 else x", x=["ab", "cat"]))[1]
    assert r.branches == {(0,): ["ab", "CAT"]}
    for bad in ["__import__('os')", "x.__class__", "(lambda: 1)()", "9 ** 9 ** 9", "'a' * 10**7"]:
        raises(E.ExprError, run, nodes_data.Expression, expression=bad, x=[1])

    # Random: deterministic per seed
    t = T.DataTree({(0,): list(range(20))})
    r1 = res(run(nodes_data.Random, tree=[t], mode="pick", count=5, seed=42, per_branch=True))[1]
    r2 = res(run(nodes_data.Random, tree=[t], mode="pick", count=5, seed=42, per_branch=True))[1]
    assert r1.branches == r2.branches and len(r1.branches[(0,)]) == 5
    sh = res(run(nodes_data.Random, tree=[t], mode="shuffle", count=1, seed=1, per_branch=True))[1]
    assert sorted(sh.branches[(0,)]) == list(range(20))

    # Index Switch: lazy status asks only for the chosen, connected input; a BOOLEAN works as index
    sw = nodes_data.IndexSwitch
    ins = {"input0": (None, "inputs.input0"), "input1": (None, "inputs.input1"), "input2": (None, "inputs.input2")}
    assert sw.check_lazy_status(1, ins) == ["inputs.input1"]
    assert sw.check_lazy_status(-1, ins) == ["inputs.input2"]
    assert list(res(sw.execute(4, {"input0": "a", "input1": "b"}))) == ["a", 2]
    assert res(sw.execute(True, {"input0": "off", "input1": "on"}))[0] == "on"
    # Collect: any values, one branch per connected input, named; or one list
    batch = torch.rand(2, 8, 8, 3)
    collect = lambda **kw: res(run(nodes_data.Collect, **({"mode": "branch per input", "names": "", "split_batch": False} | kw)))
    data, t = collect(inputs={"input0": [batch], "input1": ["x", "y"], "input2": [None]}, names="Qwen\n\nFlux\nextra")
    assert t.paths() == [(0,), (1,)] and t.branches[(1,)] == ["x", "y"] and t.branches[(0,)][0] is batch
    assert t.names == {(0,): "Qwen", (1,): "Flux"} and data == [batch, "x", "y"]
    assert len(collect(inputs={"input0": [batch]}, split_batch=True)[1].branches[(0,)]) == 2, "batch split into frames"
    one = collect(inputs={"input0": [1], "input2": [2, 3]}, mode="one list", names="all")[1]
    assert one.branches == {(0,): [1, 2, 3]} and one.names == {(0,): "all"}
    sub = T.DataTree({(0,): [1], (1,): [2]}, {(1,): "inner"})
    nested = collect(inputs={"input0": [sub], "input1": ["z"]}, names="outer")[1]
    assert nested.branches == {(0, 0): [1], (0, 1): [2], (1,): ["z"]} and nested.label((0, 1)) == "outer · inner"
    raises(ValueError, collect, inputs={"input0": [None]})
    print("data nodes: OK")


def test_number_slider():
    from comfy_execution.validation import validate_node_input

    def slide(**kw):
        out = res(nodes_data.NumberSlider.execute(**kw))
        assert len(out) == 1, "a single output"
        return out[0]

    v = slide(value=7.3456, min=0.0, max=5.0, step=0.01)
    assert v == 5 and isinstance(v, int), "clamped, whole -> INT"
    v = slide(value=0.3456, min=1.0, max=0.0, step=0.01)
    assert v == 0.35 and isinstance(v, float), "reversed range swapped"
    v = slide(value=2.6, min=0.0, max=10.0, step=1.0)
    assert v == 3 and isinstance(v, int), "integer slider feeds INT inputs"
    assert slide(value=0.537, min=0.0, max=1.0, step=0.05) == 0.55
    assert slide(value=4.0, min=1.0, max=9.0, step=2.0) == 5, "snaps to min + k * step"
    assert slide(value=0.1234567, min=0.0, max=1.0, step=0.0) == 0.123457, "step 0 = continuous"

    # wired to an INT-only input (KSampler steps / seed) the value is rounded half up, as shown
    prompt = {"7": {"class_type": "Arbor_NumberSlider", "inputs": {}},
              "9": {"class_type": "KSampler", "inputs": {"steps": ["7", 0], "cfg": 8.0}},
              "11": {"class_type": "KSampler", "inputs": {"cfg": ["12", 0]}}}
    assert nodes_data.feeds_int(prompt, "7"), "steps is INT-only"
    assert not nodes_data.feeds_int(prompt, "12"), "cfg is FLOAT"
    assert not nodes_data.feeds_int(None, "7")

    class _Hidden:
        def __init__(self, prompt, uid):
            self.prompt, self.unique_id = prompt, uid

    nodes_data.NumberSlider.hidden = _Hidden(prompt, "7")
    try:
        v = slide(value=4.5, min=0.0, max=10.0, step=0.05)
        assert v == 5 and isinstance(v, int), "4.5 into steps arrives as INT 5"
        nodes_data.NumberSlider.hidden = _Hidden(prompt, "12")
        assert slide(value=4.5, min=0.0, max=10.0, step=0.05) == 4.5, "FLOAT targets keep the fraction"
    finally:
        nodes_data.NumberSlider.hidden = None
    out = nodes_data.NumberSlider.define_schema().outputs
    assert len(out) == 1 and out[0].get_io_type() == "FLOAT,INT"
    assert validate_node_input("FLOAT,INT", "INT") and validate_node_input("FLOAT,INT", "FLOAT")
    assert not validate_node_input("FLOAT,INT", "STRING")
    assert [nodes_data.step_decimals(s) for s in (1, 0.1, 0.05, 2.5)] == [0, 1, 2, 1]
    print("number slider: OK")


def test_panel():
    from arbor_pkg.arbor.preview import PANEL_MAX_CHARS

    img = torch.rand(2, 32, 48, 3)
    tree = T.DataTree({(0, 0): [1, 2.5, "hi"], (0, 1): [img, None, True]})
    out = run(nodes_panel.Panel, data=[tree])
    payload = out.ui["arbor_panel"][0]
    assert payload["kind"] == "tree" and payload["stats"]["items"] == 6
    br1 = payload["branches"][1]
    assert br1["path"] == "{0;1}" and br1["items"][0]["t"] == "image" and "img" in br1["items"][0]
    assert br1["items"][0]["v"] == "Image 48×32 ×2"
    data, ptree = res(out)
    assert data == tree.flat(), "data output = every item, flattened"
    assert ptree is tree, "tree output is the input tree"
    named = run(nodes_panel.Panel, data=[T.DataTree({(0,): [1], (1,): [2]}, {(1,): 7})]).ui["arbor_panel"][0]
    assert "name" not in named["branches"][0] and named["branches"][1]["name"] == "7"
    # audio and video say what they are
    from fractions import Fraction
    from arbor_pkg.arbor.preview import describe
    assert describe({"waveform": torch.zeros(1, 2, 64000), "sample_rate": 32000}) == ("audio", "Audio 2.0 s · 32 kHz · stereo")
    assert describe({"waveform": torch.zeros(2, 1, 44100), "sample_rate": 44100})[1] == "Audio 1.0 s · 44.1 kHz · mono ×2"
    from comfy_api.latest import InputImpl, Types
    clip = InputImpl.VideoFromComponents(Types.VideoComponents(images=torch.rand(12, 16, 24, 3), audio=None,
                                                               frame_rate=Fraction(24)))
    assert describe(clip) == ("video", "Video 24×16 · 12 frames · 24 fps · 0.5 s"), describe(clip)
    flat = run(nodes_panel.Panel, data=[1, 2, 3]).ui["arbor_panel"][0]
    assert flat["kind"] == "list" and flat["stats"]["items"] == 3

    # unconnected: typed text, Grasshopper style
    typed = run(nodes_panel.Panel, text="a cat\n7\n3.5\n\n  \n-2\nnot 1", parse_numbers=True, multiline=False)
    values, ttree = res(typed)
    assert ttree.branches == {(0,): ["a cat", 7, 3.5], (1,): [-2, "not 1"]}, ttree.branches
    assert values == ["a cat", 7, 3.5, -2, "not 1"]
    assert typed.ui["arbor_panel"][0]["source"] == "text"
    raw = res(run(nodes_panel.Panel, text="7\n8", parse_numbers=False, multiline=False))[1]
    assert raw.branches == {(0,): ["7", "8"]}
    story = res(run(nodes_panel.Panel, text="# Arrival\ntrain\nmap\n\n#Not a title\n# The village\n  # dawn  \nstairs",
                    parse_numbers=False, multiline=False))[1]
    assert story.branches == {(0,): ["train", "map"], (1,): ["#Not a title", "stairs"]}, story.branches
    assert story.names == {(0,): "Arrival", (1,): "The village"}, "'# title' names its branch, the first one wins"
    tt = res(run(nodes_panel.Panel, text="true\nFalse\nTRUE\ntrue-ish", parse_numbers=True, multiline=False))[1]
    assert tt.branches == {(0,): [True, False, True, "true-ish"]}, tt.branches
    one = res(run(nodes_panel.Panel, text="line 1\n\nline 2", parse_numbers=True, multiline=True))
    assert one[0] == ["line 1\n\nline 2"]
    empty = res(run(nodes_panel.Panel, text="", parse_numbers=True, multiline=False))
    assert empty[0] == [""], "empty panel still emits one item"

    # long text reaches the Panel in full up to the limit, and is flagged when cut
    long = "x" * (PANEL_MAX_CHARS + 50)
    rows = run(nodes_panel.Panel, data=["short", long]).ui["arbor_panel"][0]["branches"][0]["items"]
    assert rows[0]["v"] == "short" and "len" not in rows[0]
    assert len(rows[1]["v"]) == PANEL_MAX_CHARS and rows[1]["len"] == PANEL_MAX_CHARS + 50
    print("panel: OK")


# ====================================================================== tree / list nodes

def test_tree_nodes():
    tr = T.DataTree({(0,): [1.0, 1.5, 2.0, 2.5]})

    # Reshape Tree: the mode arrives the way ComfyUI builds it for list nodes, every value list-wrapped
    def reshape(t, mode, **kw):
        return res(run(nodes_tree.ReshapeTree, tree=[t], mode={"mode": [mode], **{k: [v] for k, v in kw.items()}}))[0]

    g = reshape(tr, "graft")
    assert g.branch_count == 4
    assert reshape(g, "flatten", path="{3}").paths() == [(3,)]
    assert reshape(g, "shift paths", offset=-1).branches == tr.branches
    assert reshape(T.DataTree({(0, 0, 1): ["a"], (0, 0, 2): ["b"]}), "simplify").paths() == [(1,), (2,)]
    assert reshape(T.DataTree({(0,): [1, 2], (1,): [3, 4]}), "flip matrix").branches == {(0,): [1, 3], (1,): [2, 4]}
    assert reshape(g, "renumber").paths() == [(0,), (1,), (2,), (3,)]
    mode = next(i for i in nodes_tree.ReshapeTree.define_schema().inputs if i.id == "mode")
    assert [o.key for o in mode.options] == list(nodes_tree.RESHAPE)
    assert res(run(nodes_tree.TreeBranch, tree=[g], path="{0;2}", index=0))[0].branches == {(0, 2): [2.0]}
    assert res(run(nodes_tree.TreeBranch, tree=[g], path="", index=-1))[0].paths() == [(0, 3)]
    named = T.DataTree({(0,): ["mei", "kai"], (1,): ["tea", "roof"]}, {(0,): "Characters", (1,): "Places"})
    t, d = res(run(nodes_tree.TreeBranch, tree=[named], path="Places", index=0))
    assert t.names == {(1,): "Places"} and d == ["tea", "roof"], "by name, and its items as data"
    t, d = res(run(nodes_tree.TreeBranch, tree=[named], path="Places, {0}", index=0))
    assert list(t.branches) == [(1,), (0,)] and d == ["tea", "roof", "mei", "kai"], "several, in the order asked"
    trees = {"tree0": [tr], "tree1": [5, 6], "tree2": [None]}
    mg = res(run(nodes_tree.Merge, trees=trees, mode="merge"))[0]
    assert mg.branches == {(0,): [1.0, 1.5, 2.0, 2.5, 5, 6]}, "unconnected Autogrow slot ignored"
    ew = res(run(nodes_tree.Merge, trees=trees, mode="entwine"))[0]
    assert ew.paths() == [(0, 0), (1, 0)]
    assert list(res(run(nodes_tree.TreeStatistics, tree=[g]))[:3]) == [4, 4, 2]

    # Construct Tree: one path, or poured into a shape
    ct = res(run(nodes_tree.ConstructTree, data=[torch.zeros(3, 8, 8, 3)], path="{1}", split_batch=True))[0]
    assert ct.paths() == [(1,)] and len(ct.branches[(1,)]) == 3
    shape = T.DataTree({(0,): [None, None], (1,): [None, None]})
    back = res(run(nodes_tree.ConstructTree, data=["a", "b", "c", "d"], path="{0}", split_batch=False,
                   shape=[shape]))[0]
    assert back.branches == {(0,): ["a", "b"], (1,): ["c", "d"]}
    raises(ValueError, run, nodes_tree.ConstructTree, data=["a"], path="{0}", split_batch=False, shape=[shape])
    # Tree to Data: every item as plain data + the tree as shape, and back with Construct Tree
    scenes = T.DataTree({(0,): ["a", "b"], (1,): ["c"]}, {(0,): "Arrival", (1,): "Village"})
    data, shape = res(run(nodes_tree.TreeToData, tree=[scenes]))
    assert data == ["a", "b", "c"] and shape is scenes
    out = nodes_tree.TreeToData.define_schema().outputs
    assert out[0].is_output_list and len(out) == 2, "small on purpose: data + shape"
    back = res(run(nodes_tree.ConstructTree, data=[v.upper() for v in data], path="{0}", split_batch=False,
                   shape=[shape]))[0]
    assert back.branches == {(0,): ["A", "B"], (1,): ["C"]} and back.label((1,)) == "Village"
    assert res(run(nodes_tree.TreeToData, tree=["x", "y"]))[0] == ["x", "y"], "a plain list passes through"
    print("tree nodes: OK")


def test_list_nodes():
    tr = T.DataTree({(0,): [1.0, 1.5, 2.0, 2.5]})
    a, b = res(run(nodes_list.Dispatch, tree=[tr], pattern="T F"))
    assert a.branches[(0,)] == [1.0, 2.0] and b.branches[(0,)] == [1.5, 2.5]
    # the pattern accepts typed text, a BOOLEAN, a list of BOOLEANs, or a boolean tree
    t = T.DataTree({(0,): [1, 2, 3, 4], (1,): [5, 6]})
    keep = lambda pattern: res(run(nodes_list.Dispatch, tree=[t], pattern=pattern))[0].branches
    assert keep("T F") == {(0,): [1, 3], (1,): [5]}
    assert keep([False]) == {(0,): [], (1,): []}
    assert keep([True, True, False]) == {(0,): [1, 2, 4], (1,): [5, 6]}, "a list repeats like a typed pattern"
    mask = res(run(nodes_data.Expression, expression="x > 2", x=[t]))[1]
    a, b = res(run(nodes_list.Dispatch, tree=[t], pattern=[mask]))
    assert a.branches == {(0,): [3, 4], (1,): [5, 6]} and b.branches == {(0,): [1, 2], (1,): []}
    pat = next(i for i in nodes_list.Dispatch.define_schema().inputs if i.id == "pattern")
    assert "BOOLEAN" in pat.get_io_type() and "STRING" in pat.get_io_type()

    st = T.DataTree({(0,): ["red", "blue"]})
    cx, cy = res(run(nodes_list.CrossReference, A=[tr], B=[st], group=True))
    assert cx.branch_count == 4 and cy.item_count == 8
    def item(index, wrap=True):
        return res(run(nodes_list.ListItem, tree=[tr], index=index, wrap=wrap))[0].branches[(0,)]

    assert item("1:") == [1.5, 2.0, 2.5] and item("1-2") == [1.5, 2.0] and item("::2") == [1.0, 2.0]
    assert item(5) == [1.5] and item("-1") == [2.5] and item("9", wrap=False) == [None]

    def order(o):
        return res(run(nodes_list.SortList, tree=[T.DataTree({(0,): [3, "b", 1, "a"]})], order=o))[0].branches[(0,)]

    assert order("ascending") == [1, 3, "a", "b"] and order("descending") == ["b", "a", 3, 1]
    assert order("reverse") == ["a", 1, "b", 3]
    assert res(run(nodes_list.Partition, tree=[tr], size=3))[0].paths() == [(0, 0), (0, 1)]
    assert res(run(nodes_list.Repeat, tree=[tr], count=2, mode="whole"))[0].item_count == 8
    print("list nodes: OK")


# ====================================================================== nested trees

def test_grasshopper_matching():
    """Combining trees follows Grasshopper: branches in order, items longest-list, paths from the master."""
    expr = lambda e, **kw: res(run(nodes_data.Expression, expression=e, **kw))[1]
    # David Rutten's example: B has the longest paths, so it is the master; its paths run out and grow
    a = T.DataTree({(0, 0): [1], (0, 1): [2], (0, 2): [3]})
    b = T.DataTree({(0, 1, 0): [10]})
    assert expr("x + y", x=[a], y=[b]).branches == {(0, 1, 0): [11], (0, 1, 1): [12], (0, 1, 2): [13]}
    # branches pair by order, not by path: x's {2} meets y's {1}; the output keeps x's paths and grows past them
    x = T.DataTree({(0,): [1], (2,): [2]})
    y = T.DataTree({(0,): [10], (1,): [20], (2,): [30]})
    assert expr("x + y", x=[x], y=[y]).branches == {(0,): [11], (2,): [22], (3,): [32]}
    # items longest-list over both inputs, whichever is longer
    assert expr("x + y", x=[5], y=[10, 20, 30]).branches == {(0,): [15, 25, 35]}
    assert expr("x + y", x=[T.DataTree({(0,): [1, 2, 3]})], y=[100]).branches == {(0,): [101, 102, 103]}
    # an empty branch gives an empty result branch
    assert expr("x", x=[T.DataTree({(0,): [], (1,): [7]})], y=[1]).branches == {(0,): [], (1,): [7]}
    # an unconnected x (also [None]) leaves y to drive; nothing connected gives one constant
    assert expr("y * 2", x=[None], y=[T.DataTree({(0,): [1], (1,): [2]})]).branches == {(0,): [2], (1,): [4]}
    assert res(run(nodes_data.Expression, expression="1 + 1", x=[None]))[0] == [2]
    # Dispatch: a boolean tree pairs with the list's branches in order, the last one repeating
    rows = T.DataTree({(0, 0): [1, 2], (0, 1): [3, 4], (1, 0): [5]})
    keep, drop = res(run(nodes_list.Dispatch, tree=[rows], pattern=[T.DataTree({(0,): [True], (1,): [False]})]))
    assert keep.branches == {(0, 0): [1, 2], (0, 1): [], (1, 0): []} and drop.item_count == 3
    # Cross Reference: plain by default (all combinations in the branch), branches in order
    plain = res(run(nodes_list.CrossReference, A=["a", "b"], B=["x", "y", "z"], group=False))
    assert plain[0].branches == {(0,): ["a", "a", "a", "b", "b", "b"]} and plain[1].branches == {(0,): ["x", "y", "z"] * 2}
    shots = T.DataTree({(0,): ["s0"], (2,): ["s2"]})
    edits = T.DataTree({(0,): ["e0"], (1,): ["e1"], (2,): ["e2a", "e2b"]})
    sa, sb = res(run(nodes_list.CrossReference, A=[shots], B=[edits], group=False))
    assert sb.branches == {(0,): ["e0"], (2,): ["e1"], (3,): ["e2a", "e2b"]} and sa.branches[(3,)] == ["s2", "s2"]
    # group = graft A first: each A item its own sub-branch
    grouped = res(run(nodes_list.CrossReference, A=["a", "b"], B=["x", "y"], group=True))[1]
    assert grouped.branches == {(0, 0): ["x", "y"], (0, 1): ["x", "y"]}
    # Flip Matrix keeps the path prefix, like Grasshopper
    flip = lambda t: res(run(nodes_tree.ReshapeTree, tree=[t], mode={"mode": ["flip matrix"]}))[0].branches
    assert flip(T.DataTree({(0, 0): ["a", "b"], (0, 1): ["c", "d"]})) == {(0, 0): ["a", "c"], (0, 1): ["b", "d"]}
    assert flip(T.DataTree({(2, 5): ["a", "b"]})) == {(2, 0): ["a"], (2, 1): ["b"]}
    assert flip(T.DataTree({(0,): [1, 2], (1,): [3]})) == {(0,): [1, 3], (1,): [2]}
    # List Item: a connected list of indices picks all of them
    assert res(run(nodes_list.ListItem, tree=["a", "b", "c"], index=[0, 2], wrap=True))[0].branches == {(0,): ["a", "c"]}
    sheets = T.DataTree({(0,): ["a0", "a1", "a2"], (1,): ["b0", "b1", "b2"]})
    assert res(run(nodes_list.ListItem, tree=[sheets], index="1", wrap=True))[1] == ["a1", "b1"], \
        "data: item 1 of every branch as one plain list"
    print("grasshopper matching: OK")


def test_nested_trees():
    """character -> outfit -> pose, built the Grasshopper way: combine at the level where branches line up."""
    chars = res(run(nodes_panel.Panel, text="# Mira\nbotanist\nraincoat\nlab coat\n\n# Theo\nbaker\njacket",
                    parse_numbers=False, multiline=False))[1]
    first = lambda spec: res(run(nodes_list.ListItem, tree=[chars], index=spec, wrap=True))[0]
    desc, outfits = first("0"), first("1:")
    assert outfits.branches == {(0,): ["raincoat", "lab coat"], (1,): ["jacket"]} and outfits.names == chars.names
    # one description and a list of outfits per character: branches in the same order, the description repeats
    who = res(run(nodes_data.Expression, expression='y + " in " + x', x=[outfits], y=[desc]))[1]
    assert who.branches == {(0,): ["botanist in raincoat", "botanist in lab coat"], (1,): ["baker in jacket"]}
    assert who.names == chars.names
    ca, cb = res(run(nodes_list.CrossReference, A=[who], B=["front", "side"], group=True))
    assert ca.paths() == [(0, 0), (0, 1), (1, 0)]
    assert ca.label((0, 1)) == "Mira · botanist in lab coat", "the parent keeps its name, the sub-branch is named after A"
    full = res(run(nodes_data.Expression, expression='x + ", " + y', x=[ca], y=[cb]))[1]
    assert full.branches[(0, 1)] == ["botanist in lab coat, front", "botanist in lab coat, side"]
    # flatten for the sampler, then put the results back and regroup per character
    x, *_, shape, n = res(run(nodes_tree.XYLists, x=[full], mode="cross"))
    assert n == 6 and shape.label((0, 0)) == "Mira · botanist in raincoat"
    imgs = res(run(nodes_tree.ConstructTree, data=[f"img{k}" for k in range(n)], path="{0}", split_batch=False,
                   shape=[shape]))[0]
    per_char = res(run(nodes_tree.ReshapeTree, tree=[imgs], mode={"mode": ["shift paths"], "offset": [-1]}))[0]
    assert per_char.branches == {(0,): ["img0", "img1", "img2", "img3"], (1,): ["img4", "img5"]}
    assert per_char.names == {(0,): "Mira", (1,): "Theo"}, "shifting back up lands on the named parents"
    # outfit names as row labels: a flat list, one per row
    assert grid.row_labels_for([outfits], 3) == ["raincoat", "lab coat", "jacket"]
    assert grid.row_labels_for([desc], 2) == ["Mira", "Theo"], "a tree with one branch per row gives its names"
    # graft / entwine / renumber carry names too
    assert T.graft(chars).label((1, 0)) == "Theo"
    assert T.entwine([outfits, outfits]).label((1, 0)) == "Mira"
    assert T.renumber(ca).names[(1,)] == "Mira · botanist in lab coat"
    # Expression knows the branch name: per-shot file names from the structure
    files = res(run(nodes_data.Expression, expression='name + "/shot_" + str(i + 1)', x=[outfits]))[0]
    assert files == ["Mira/shot_1", "Mira/shot_2", "Theo/shot_1"], files
    # pictures cross-referenced with edits: sub-branches are numbered, not named "Image 8×8"
    pics = T.DataTree({(0,): [torch.rand(1, 8, 8, 3), torch.rand(1, 8, 8, 3)]}, {(0,): "Arrival"})
    pa, pb = res(run(nodes_list.CrossReference, A=[pics], B=["snow", "ink"], group=True))
    assert [pa.label(p) for p in pa.paths()] == ["Arrival · 1", "Arrival · 2"] and pb.branches[(0, 1)] == ["snow", "ink"]
    print("nested trees: OK")


# ====================================================================== XY workflow

def test_xy_lists():
    cfg = T.DataTree({(0,): [4, 7]})
    prompts = T.DataTree({(0,): ["cat", "dog", "fox"]})
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[cfg], y=[prompts], mode="cross"))
    assert n == 6 and x == [4, 4, 4, 7, 7, 7] and y == ["cat", "dog", "fox"] * 2 and z == [None] * 6
    assert shape.branches == {(0,): ["cat", "dog", "fox"], (1,): ["cat", "dog", "fox"]}
    assert shape.names == {(0,): 4, (1,): 7}, "rows named after x"
    assert all(o.is_output_list for o in nodes_tree.XYLists.define_schema().outputs[:3])
    # z: rows = x × y, columns = z
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[cfg], y=[1, 2], z=["a", "b", "c"], mode="cross"))
    assert n == 12 and shape.paths() == [(0, 0), (0, 1), (1, 0), (1, 1)] and z[:3] == ["a", "b", "c"]
    assert shape.names[(1, 0)] == "7 · 1"
    raises(ValueError, run, nodes_tree.XYLists, x=[cfg], z=["a"], mode="cross")
    # zip: item by item, longest list; the shape holds the y values
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[cfg], y=[prompts], mode="zip"))
    assert x == [4, 7, 7] and y == ["cat", "dog", "fox"] and shape.branches == {(0,): ["cat", "dog", "fox"]}
    # zip two trees of the same layout (Cross Reference's A and B): flat side by side, shape keeps x's branches
    pics = T.DataTree({(0, 0): ["p1", "p1"], (0, 1): ["p2", "p2"], (1, 0): ["p3"]}, {(0,): "Arrival", (1,): "Village"})
    edits = T.DataTree({(0, 0): ["cat", "scarf"], (0, 1): ["cat", "scarf"], (1, 0): ["balloon"]})
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[pics], y=[edits], mode="zip"))
    assert x == ["p1", "p1", "p2", "p2", "p3"] and y == ["cat", "scarf", "cat", "scarf", "balloon"] and n == 5
    assert shape.branches == edits.branches and shape.label((1, 0)) == "Village", "x's branches and names, y's items"
    # a longer tree on y: the shape follows y's branches, not one row
    scenes = T.DataTree({(0,): ["a1", "a2"], (1,): ["b1"]}, {(0,): "Arrival", (1,): "Village"})
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[7], y=[scenes], mode="zip"))
    assert x == [7, 7, 7] and shape.branches == scenes.branches and shape.names == scenes.names
    # z the longest: its branches; the items are still the last variable's values
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[1], y=[2], z=[scenes], mode="zip"))
    assert n == 3 and shape.branches == scenes.branches
    # trees pair branch by branch (Grasshopper), not across branches
    who = T.DataTree({(0,): ["Mei"], (1,): ["Kai"]}, {(0,): "Mei", (1,): "Kai"})
    where = T.DataTree({(0,): ["tea", "bamboo"], (1,): ["roof"]})
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[who], y=[where], mode="zip"))
    assert list(zip(x, y)) == [("Mei", "tea"), ("Mei", "bamboo"), ("Kai", "roof")], "bamboo stays in Mei's branch"
    assert shape.branches == where.branches and shape.names == who.names
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[who], y=[where], mode="cross"))
    assert n == 3 and list(zip(x, y)) == [("Mei", "tea"), ("Mei", "bamboo"), ("Kai", "roof")]
    assert shape.branches == {(0, 0): ["tea", "bamboo"], (1, 0): ["roof"]} and shape.label((1, 0)) == "Kai · Kai"
    ab = T.DataTree({(0,): ["a", "b"], (1,): ["c"]})
    nums = T.DataTree({(0,): [1, 2], (1,): [3, 4]})
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[ab], y=[nums], mode="cross"))
    assert n == 6 and list(zip(x, y)) == [("a", 1), ("a", 2), ("b", 1), ("b", 2), ("c", 3), ("c", 4)]
    assert shape.paths() == [(0, 0), (0, 1), (1, 0)] and shape.names[(0, 1)] == "b"
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[ab], y=[nums], mode="zip"))
    assert list(zip(x, y)) == [("a", 1), ("b", 2), ("c", 3), ("c", 4)], "the shorter branch repeats its last item"
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[ab], y=[10, 20], mode="cross"))
    assert n == 6 and y == [10, 20] * 3, "a plain list (one branch) repeats for every branch"
    # a plain x against a grafted y: the branches sit side by side as columns, not stacked as row blocks
    grafted = res(run(nodes_tree.ReshapeTree, tree=["a", "b"], mode={"mode": ["graft"]}))[0]
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[1, 2, 3], y=[grafted], mode="cross"))
    assert n == 6 and list(zip(x, y)) == [(1, "a"), (1, "b"), (2, "a"), (2, "b"), (3, "a"), (3, "b")]
    assert shape.branches == {(0,): ["a", "b"], (1,): ["a", "b"], (2,): ["a", "b"]}
    assert shape.names == {(0,): 1, (1,): 2, (2,): 3}, "rows named after x"
    cells = T.rebuild([f"{xv}{yv}" for xv, yv in zip(x, y)], shape)
    assert cells.branches[(1,)] == ["2a", "2b"], "each run lands in its own row and column"
    tiles = [torch.full((1, 8, 8, 3), k / 10) for k in range(6)]
    grid_img = res(run(nodes_image.ImageGrid, images=tiles, shape=[shape], **grid_kw(gap=0, font_size=8)))[0]
    assert grid_img.shape[1] >= 3 * 8 and grid_img.shape[2] < 3 * 8 + 8 * 6, "3 rows x 2 columns"
    x2, _, _, shape2, _ = res(run(nodes_tree.XYLists, x=[grafted], y=[1, 2, 3], mode="cross"))
    assert shape2.paths() == [(0, 0, 0), (0, 1, 0)] and x2 == ["a"] * 3 + ["b"] * 3, "grafted x: rows a and b"
    # x only: flattens any tree, the shape is the tree itself
    branched = T.DataTree({(0,): [1, 2], (1,): [3]})
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[branched], mode="cross"))
    assert x == [1, 2, 3] and y == [None] * 3 and n == 3 and shape.branches == branched.branches
    # ... and Construct Tree puts per-item results back into the same branches
    back = res(run(nodes_tree.ConstructTree, data=[v * 10 for v in x], path="{0}", split_batch=False,
                   shape=[shape]))[0]
    assert back.branches == {(0,): [10, 20], (1,): [30]}
    # Prompt Template rows are named after their outer variables
    pt = res(run(nodes_data.PromptTemplate, template="{a} {b}", mode="cross",
                 vars={"a": [T.DataTree({(0,): ["cat", "dog"]})], "b": ["oil", "ink"]}))[1]
    assert pt.names == {(0,): "cat", (1,): "dog"}
    print("xy lists: OK")


def test_image_grid():
    a = T.DataTree({(0,): [3, 5]})
    b = T.DataTree({(0,): ["cat", "一只猫在雨中"]})
    ca, cb = T.cross_reference(a, b)
    imgs = T.rebuild([torch.rand(1, 40 + 8 * i, 60, 3) for i in range(4)], ca)
    sheet = res(run(nodes_image.ImageGrid, images=[imgs], row_labels=[a], col_labels=[b],
                    **grid_kw(gap=8, font_size=16)))[0]
    assert sheet.dim() == 4 and sheet.shape[0] == 1 and sheet.shape[-1] == 3
    assert sheet.shape[2] > 2 * 60 and sheet.shape[1] > 2 * 56, sheet.shape  # 2 × 2 cells + labels
    plain = res(run(nodes_image.ImageGrid, images=[torch.rand(1, 16, 16, 3), torch.rand(3, 16, 16, 3)],
                    **grid_kw(fit="original", gap=0, theme="dark")))[0]
    assert plain.shape[2] == 4 * 16, plain.shape  # one row, batch expanded to columns

    # labels straight from Cross Reference outputs render like the originals
    a = T.DataTree({(0,): [256, 384, 512]})
    b = T.DataTree({(0,): ["red", "blue"]})
    ca, cb = T.cross_reference(a, b)
    assert grid.row_labels_for([ca], 3) == ["256", "384", "512"] == grid.row_labels_for([a], 3)
    assert grid.col_labels_for([cb], 2) == ["red", "blue"] == grid.col_labels_for([b], 2)
    imgs = T.rebuild([torch.rand(1, 8, 8, 3) for _ in range(6)], ca)
    g1 = res(run(nodes_image.ImageGrid, images=[imgs], row_labels=[ca], col_labels=[cb], **grid_kw()))[0]
    g2 = res(run(nodes_image.ImageGrid, images=[imgs], row_labels=[a], col_labels=[b], **grid_kw()))[0]
    assert torch.equal(g1, g2)

    # a batch run: plain images + XY Lists' shape -> rows × columns, columns labelled from the shape
    x, y, z, shape, n = res(run(nodes_tree.XYLists, x=[a], y=[b], mode="cross"))
    flat = imgs.flat()
    g3 = res(run(nodes_image.ImageGrid, images=flat, shape=[shape], **grid_kw()))[0]
    assert torch.equal(g3, g1), "shape lays out and labels rows and columns, nothing else to connect"
    g4 = res(run(nodes_image.ImageGrid, images=[imgs], col_labels=[cb], **grid_kw()))[0]
    assert torch.equal(g4, g1), "Cross Reference rows carry their names too"
    # a shape whose rows differ (a storyboard) gets row names but no column labels
    story = T.DataTree({(0,): ["train", "map"], (1,): ["dawn", "stairs"]}, {(0,): "Arrival", (1,): "Village"})
    frames = [torch.rand(1, 8, 8, 3) for _ in range(4)]
    g5 = res(run(nodes_image.ImageGrid, images=frames, shape=[story], **grid_kw()))[0]
    g6 = res(run(nodes_image.ImageGrid, images=frames, shape=[story], row_labels=["Arrival", "Village"],
                 **grid_kw()))[0]
    assert torch.equal(g5, g6), "no column labels from rows that differ"
    # labels wrap between words; CJK wraps per character
    from PIL import Image, ImageDraw
    draw, font = ImageDraw.Draw(Image.new("RGB", (8, 8))), grid._font(26)
    lines = grid._wrap(draw, "a cozy reading nook by a rainy window", font, 420, 3)
    assert lines[-1] == "window" and all(not l.endswith(" ") for l in lines), lines
    assert grid._wrap(draw, "one two three four five six", font, 160, 2)[-1].endswith("…")
    assert len(grid._wrap(draw, "一只猫在雨中的窗台上睡觉", font, 200, 2)[0]) > 1
    raises(ValueError, run, nodes_image.ImageGrid, images=flat[:5], shape=[shape], **grid_kw())
    print("image grid: OK")


def test_grid_layout():
    sheet = lambda **kw: res(run(nodes_image.ImageGrid, **kw))[0]
    pics = [torch.rand(1, 30, 60, 3) for _ in range(6)]
    flat = T.DataTree({(0,): pics})
    one_row = sheet(images=[flat], **grid_kw())
    wrapped = sheet(images=[flat], **grid_kw(columns=4))
    assert tuple(one_row.shape[1:3]) == (30 + 2 * 2, 6 * 60 + 7 * 2)
    assert tuple(wrapped.shape[1:3]) == (2 * 30 + 3 * 2, 4 * 60 + 5 * 2), "6 cells wrap into rows of 4"
    caps = [f"shot {i}" for i in range(6)]
    below = sheet(images=[flat], captions=[caps], **grid_kw(columns=4))
    assert below.shape[1] > wrapped.shape[1] and below.shape[2] == wrapped.shape[2], "captions below add height"
    over = sheet(images=[flat], captions=[caps], **grid_kw(columns=4, caption_style="overlay"))
    assert over.shape == wrapped.shape and not torch.equal(over, wrapped), "overlay captions keep the size"
    # above: the same band, over the picture instead of under it
    above = sheet(images=[flat], captions=[caps], **grid_kw(columns=4, caption_style="above"))
    cap_h = (below.shape[1] - wrapped.shape[1]) // 2
    assert above.shape == below.shape and not torch.equal(above, below)
    assert torch.allclose(below[0, 2:32, 2:62], pics[0][0], atol=0.01), "below: picture at the top of its cell"
    assert torch.allclose(above[0, 2 + cap_h:32 + cap_h, 2:62], pics[0][0], atol=0.01), "above: picture under its caption"
    # overlay top: the bar covers the picture's top rows instead of its bottom ones
    over_top = sheet(images=[flat], captions=[caps], **grid_kw(columns=4, caption_style="overlay top"))
    assert over_top.shape == wrapped.shape and not torch.equal(over_top, over)
    assert torch.allclose(over[0, 2, 2:62], pics[0][0, 0], atol=0.01) and not torch.allclose(over_top[0, 2, 2:62], pics[0][0, 0], atol=0.01)
    assert torch.allclose(over_top[0, 31, 2:62], pics[0][0, 29], atol=0.01) and not torch.allclose(over[0, 31, 2:62], pics[0][0, 29], atol=0.01)
    assert grid.caption_rows(T.DataTree({(0,): ["a"], (1,): ["b", "c"]}), [2, 2]) == [["a", ""], ["b", "c"]]
    assert grid.caption_rows(["a", "b", "c"], [2, 2]) == [["a", "b"], ["c", ""]], "a list is read cell by cell"

    # fit keeps the whole picture, fill covers the cell (cut), stretch distorts
    assert grid.fit_box(160, 90, 100, 100, "fit") == (100, 56, False)
    assert grid.fit_box(160, 90, 100, 100, "fill") == (178, 100, True)
    assert grid.fit_box(160, 90, 100, 100, "stretch") == (100, 100, False)
    black = T.DataTree({(0,): [torch.zeros(1, 30, 60, 3), torch.zeros(1, 60, 30, 3)]})
    assert sheet(images=[black], **grid_kw(fit="fill", gap=0)).max() < 0.01, "fill leaves no background"
    assert sheet(images=[black], **grid_kw(fit="fit", gap=0)).max() > 0.99

    # row labels stand up when they would not fit in two lines (auto), short ones stay horizontal
    long_tree = T.DataTree({(0,): pics[:2], (1,): pics[2:4]},
                           {(0,): "a very long row label that does not fit in two lines at all", (1,): "b"})
    auto = sheet(images=[long_tree], **grid_kw())
    flat_labels = sheet(images=[long_tree], **grid_kw(label_direction="horizontal"))
    assert auto.shape[2] < flat_labels.shape[2], "a standing label takes less width"
    short = T.DataTree({(0,): pics[:2], (1,): pics[2:4]}, {(0,): "a", (1,): "b"})
    assert torch.equal(sheet(images=[short], **grid_kw()), sheet(images=[short], **grid_kw(label_direction="horizontal")))
    stacked = sheet(images=[T.DataTree({(0,): pics[:2]}, {(0,): "清晨的村庄与石阶小路"})], **grid_kw(label_direction="vertical"))
    assert stacked.shape[2] < 2 * 60 + 3 * 2 + 60, "Chinese stacks upright in a narrow column"
    print("grid layout: OK")


# ====================================================================== image / file nodes

def test_image_nodes():
    img = torch.rand(2, 32, 48, 3)
    ui = run(nodes_image.ImageSlider, images={"image0": [img], "image1": [torch.rand(1, 64, 64, 3)]}).ui
    slides = ui["arbor_slider"][0]["slides"]
    assert [s["label"] for s in slides] == ["image0 · 1/2", "image0 · 2/2", "image1"]
    assert slides[2]["w"] == 64
    scenes = T.DataTree({(0,): [img[:1]], (1,): [img], (2,): [img[:1]]}, {(0,): "Arrival", (1,): "Village"})
    tree_ui = run(nodes_image.ImageSlider, images={"image0": [scenes]}).ui
    assert [s["label"] for s in tree_ui["arbor_slider"][0]["slides"]] == [
        "Arrival", "Village · 1/2", "Village · 2/2", "image0"], "an image tree works too, named branches label it"
    angles = T.DataTree({(0,): [img[:1], img[1:]], (1,): [img[:1], img[1:]]}, {(0,): "Mei", (1,): "Kai"})
    labelled = run(nodes_image.ImageSlider, images={"image0": [angles]}, labels=["original", "back"]).ui
    assert [s["label"] for s in labelled["arbor_slider"][0]["slides"]] == [
        "Mei · original", "Mei · back", "Kai · original", "Kai · back"], "one label list serves every branch"
    assert [s["group"] for s in labelled["arbor_slider"][0]["slides"]] == ["Mei", "Mei", "Kai", "Kai"], \
        "the viewer can show one person at a time"
    # groups: only trees split the viewer, by top-level branch (name, else path); they meet across inputs
    px = lambda: torch.rand(1, 8, 8, 3)
    groups = lambda **inputs: [s["group"] for s in run(nodes_image.ImageSlider, images={
        k: v if isinstance(v, list) else [v] for k, v in inputs.items()}).ui["arbor_slider"][0]["slides"]]
    named = lambda a, b: T.DataTree({(0,): [px()], (1,): [px()]}, {(0,): a, (1,): b})
    assert groups(image0=[px(), px()], image1=[px()]) == [None, None, None], "two plain lists: no groups"
    assert groups(image0=named("Mei", "Kai"), image1=[px()]) == ["Mei", "Kai", None], \
        "tree + plain list: the list has no group, so it goes with every group"
    assert groups(image0=named("Mei", "Kai"), image1=named("Mei", "Kai")) == ["Mei", "Kai", "Mei", "Kai"], \
        "two trees: same names meet in one group"
    assert groups(image0=named("Mei", "Kai"), image1=T.DataTree({(0,): [px()], (1,): [px()]})) == \
        ["Mei", "Kai", "{0}", "{1}"], "a named branch never meets an unnamed one"
    assert groups(image0=named("Mei", "Kai"), image1=named("Ayu", "Ren")) == ["Mei", "Kai", "Ayu", "Ren"]
    nested = T.DataTree({(0, 0): [px()], (0, 1): [px()], (1, 0): [torch.rand(2, 8, 8, 3)]})
    assert groups(image0=nested) == ["{0}", "{0}", "{1}", "{1}"], "top level only; a batch's frames stay together"
    assert groups(image0=T.DataTree({(0,): [px(), px()]}, {(0,): "Mei"}), image1=[px()]) == [None, None, None], \
        "one branch is no grouping"
    slot = nodes_image.ImageSlider.define_schema().inputs[0].template.input
    assert "IMAGE" in slot.get_io_type() and "ARBOR_TREE" in slot.get_io_type()

    img = torch.rand(2, 300, 500, 3)
    out = res(nodes_image.SmartResize.execute(img, {"mode": "longest side", "size": 1000}, "64", "bilinear", True))
    assert tuple(out[0].shape) == (2, 576, 1024, 3) and (out[2], out[3]) == (1024, 576), out[0].shape
    out = res(nodes_image.SmartResize.execute(img, {"mode": "fill & crop", "width": 256, "height": 256},
                                              "8", "area", True))
    assert tuple(out[0].shape) == (2, 256, 256, 3) and tuple(out[1].shape) == (2, 256, 256)
    out = res(nodes_image.SmartResize.execute(img, {"mode": "scale", "factor": 3.0}, "1", "bilinear", False))
    assert (out[2], out[3]) == (500, 300), "no upscale"

    assert nodes_image.parse_indices("0, -1, 2-4, ::3", 6) == [0, 5, 2, 3, 4, 0, 3]
    picked = res(nodes_image.BatchPick.execute(torch.rand(6, 4, 4, 3), "1, 1, -1"))
    assert picked[0].shape[0] == 3 and picked[1] == 3
    from fractions import Fraction
    from comfy_api.latest import InputImpl, Types
    frames = torch.rand(10, 4, 6, 3)
    vid = InputImpl.VideoFromComponents(Types.VideoComponents(images=frames, audio=None, frame_rate=Fraction(24)))
    ends = res(nodes_image.BatchPick.execute(vid, "0, -1"))
    assert ends[1] == 2 and torch.equal(ends[0][1], frames[-1]), "first and last frame of a video"

    # Split Grid: a 2 x 3 sheet drawn unevenly, white margin and gutters, panels coloured by index
    sheet = torch.ones(1, 130, 320, 3)
    xs, ys = [(4, 100), (110, 214), (222, 316)], [(3, 60), (68, 127)]
    for r, (y0, y1) in enumerate(ys):
        for c, (x0, x1) in enumerate(xs):
            sheet[0, y0:y1, x0:x1] = torch.rand(y1 - y0, x1 - x0, 3) * 0.5 + (r * 3 + c) / 12
    cut = run(nodes_image.SplitGrid, image=[sheet], rows=2, columns=3, find_gutters=True, inset=0)
    flat, tree = res(cut)
    assert len(cut.ui["images"]) == 1, "a preview of the cuts on the node"
    assert len(flat) == 6 and list(tree.branches) == [(0,)]
    assert [tuple(p.shape[1:3]) for p in flat] == [(y1 - y0, x1 - x0) for y0, y1 in ys for x0, x1 in xs], \
        "gutters and margins found and left out, panels in reading order"
    assert torch.equal(flat[4], sheet[:, 68:127, 110:214])
    even = res(run(nodes_image.SplitGrid, image=[sheet], rows=2, columns=3, find_gutters=False, inset=2))[0]
    assert tuple(even[0].shape[1:3]) == (61, 103), "even split, inset on every side"
    two = res(run(nodes_image.SplitGrid, image=[torch.cat([sheet, sheet])], rows=2, columns=3,
                  find_gutters=True, inset=0))[1]
    assert list(two.branches) == [(0,), (1,)], "one branch per sheet"
    print("image nodes: OK")


def test_compare_and_video_grid():
    import tempfile
    from fractions import Fraction
    import av
    import folder_paths
    from comfy_api.latest import InputImpl, Types

    tone = lambda secs, ch=2: {"waveform": torch.sin(torch.linspace(0, 400 * secs, int(16000 * secs)))
                               .repeat(1, ch, 1) * 0.3, "sample_rate": 16000}
    clip = lambda n, fps=24, audio=None: InputImpl.VideoFromComponents(Types.VideoComponents(
        images=torch.rand(n, 32, 48, 3), audio=audio, frame_rate=Fraction(fps)))
    with tempfile.TemporaryDirectory() as d:
        old = folder_paths.get_temp_directory()
        folder_paths.set_temp_directory(d)
        try:
            # Compare Viewer: pictures, videos and sound in one tree
            mixed = T.DataTree({(0,): [torch.rand(2, 16, 24, 3), clip(12)], (1,): [tone(0.5)]},
                               {(0,): "Arrival", (1,): "Sound"})
            slides = run(nodes_image.ImageSlider, images={"image0": [mixed]}).ui["arbor_slider"][0]["slides"]
            assert [s["kind"] for s in slides] == ["image", "image", "video", "audio"]
            assert [s["label"] for s in slides] == ["Arrival · 1/3", "Arrival · 2/3", "Arrival · 3/3", "Sound"]
            assert (slides[2]["w"], slides[2]["h"]) == (48, 32) and abs(slides[2]["dur"] - 0.5) < 0.01
            assert abs(slides[3]["dur"] - 0.5) < 0.01 and max(slides[3]["peaks"]) == 1.0
            assert all(os.path.exists(os.path.join(d, s["subfolder"], s["filename"])) for s in slides)
            # a browser-playable file inside a ComfyUI folder is played where it is, not copied
            on_disk = os.path.join(d, "clip.mp4")
            clip(6).save_to(on_disk, format=Types.VideoContainer.MP4, codec=Types.VideoCodec.AUTO)
            ref = run(nodes_image.ImageSlider, images={"image0": [InputImpl.VideoFromFile(on_disk)]}).ui
            assert ref["arbor_slider"][0]["slides"][0]["filename"] == "clip.mp4"
            slot = nodes_image.ImageSlider.define_schema().inputs[0].template.input
            assert all(t in slot.get_io_type() for t in ("IMAGE", "VIDEO", "AUDIO", "ARBOR_TREE"))

            # Video Grid: 0.5 s at 24 fps, 0.5 s at 12 fps, and an image batch (3 frames) as a clip
            videos = T.DataTree({(0,): [clip(12, 24, tone(0.5)), clip(6, 12)], (1,): [torch.rand(3, 32, 48, 3)]},
                                {(0,): "two clips", (1,): "frames"})
            out = run(nodes_image.VideoGrid, videos=[videos], fit="fit", cell_size=64, gap=4, font_size=12,
                      theme="light", path_labels=False, fps=0.0, audio="mix")
            video = res(out)[0]
            w, h = video.get_dimensions()
            assert w % 2 == 0 and h % 2 == 0 and w > 2 * 64 and h > 2 * 40, (w, h)
            assert video.get_frame_count() == 12 and float(video.get_frame_rate()) == 24.0
            with av.open(video.get_stream_source()) as c:
                assert len(c.streams.audio) == 1, "audio=mix keeps the sound"
            assert out.ui["animated"] == [True] and out.ui["images"][0]["type"] == "temp"
            silent = res(run(nodes_image.VideoGrid, videos=[videos], fit="fit", cell_size=64, gap=4, font_size=12,
                             theme="dark", path_labels=False, fps=12.0, audio="none"))[0]
            assert silent.get_frame_count() == 6
            with av.open(silent.get_stream_source()) as c:
                assert not c.streams.audio
            # one column, cells filled, captions drawn into every frame
            tall = res(run(nodes_image.VideoGrid, videos=[videos], fit="fill", cell_size=64, gap=4, font_size=12,
                           theme="light", path_labels=False, fps=0.0, audio="none", columns=1,
                           captions=[["a", "b", "c"]], caption_style="overlay"))[0]
            tw, th = tall.get_dimensions()
            assert th > 1.4 * h and tw < w and tall.get_frame_count() == 12, "3 rows of one clip instead of 2 rows"
            top_bar = res(run(nodes_image.VideoGrid, videos=[videos], fit="fill", cell_size=64, gap=4, font_size=12,
                              theme="light", path_labels=False, fps=0.0, audio="none", columns=1,
                              captions=[["a", "b", "c"]], caption_style="overlay top"))[0]
            assert top_bar.get_dimensions() == (tw, th) and top_bar.get_frame_count() == 12
            first = lambda v: v.get_components().images[0]
            assert not torch.equal(first(top_bar), first(tall)), "the bar moves to the top"
            band = res(run(nodes_image.VideoGrid, videos=[videos], fit="fill", cell_size=64, gap=4, font_size=12,
                           theme="light", path_labels=False, fps=0.0, audio="none", columns=1,
                           captions=[["a", "b", "c"]], caption_style="above"))[0]
            assert band.get_dimensions()[1] > th, "captions above add height"
            raises(ValueError, run, nodes_image.VideoGrid, videos=[T.DataTree({(0,): ["text"]})], fit="fit",
                   cell_size=64, gap=4, font_size=12, theme="light", path_labels=False, fps=0.0, audio="none")
        finally:
            folder_paths.set_temp_directory(old)
    print("compare viewer / video grid: OK")


def test_load_media():
    import tempfile
    from fractions import Fraction
    from PIL import Image
    from comfy_api.latest import InputImpl, Types
    from arbor_pkg.arbor import load_media, media

    assert load_media.parse_list("# A\na.png\nb.png\n\nc.png\n# B\n\n# C\nd.wav") == [
        ("A", ["a.png", "b.png"]), ("", ["c.png"]), ("C", ["d.wav"])], "empty groups are dropped"
    LM = load_media.LoadMedia
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as elsewhere:
        os.makedirs(os.path.join(d, "shots"))
        for k in range(2):
            Image.new("RGB", (16 + k, 8)).save(os.path.join(d, "shots", f"s{k}.png"))
        InputImpl.VideoFromComponents(Types.VideoComponents(images=torch.rand(4, 16, 16, 3), audio=None,
                                                            frame_rate=Fraction(8))).save_to(
            os.path.join(d, "clip.mp4"), format=Types.VideoContainer.MP4, codec=Types.VideoCodec.AUTO)
        media.write_flac(torch.zeros(1, 800), 8000, os.path.join(d, "voice.flac"))
        far = os.path.join(elsewhere, "far.png")
        Image.new("RGB", (8, 8)).save(far)
        at = lambda *parts: os.path.join(d, *parts)
        text = (f"# Shots\n{at('shots', 's0.png')}\n{at('shots', 's1.png')}\n\n"
                f"# Mixed\n{at('clip.mp4')}\n{at('voice.flac')}\n{far}")
        files, names, images, videos, audio = res(LM.execute(files=text))
        assert files.names == {(0,): "Shots", (1,): "Mixed"} and [len(v) for v in files.branches.values()] == [2, 3]
        assert len(images) == 3 and images[1].shape == (1, 8, 17, 3), "every line is a full path; kinds are plain data"
        assert len(videos) == 1 and videos[0].get_frame_count() == 4 and audio[0]["sample_rate"] == 8000
        assert names.branches[(1,)] == ["clip", "voice", "far"]
        assert LM.fingerprint_inputs(text) != LM.fingerprint_inputs(text.replace("s1", "s0"))
        raises(ValueError, LM.execute, files="")
        raises(FileNotFoundError, LM.execute, files=at("missing.png"))
        raises(ValueError, LM.execute, files=at("notes.txt"))

        whole = load_media.tree_of(d)  # what Add folder… adds
        assert [g["name"] for g in whole] == [os.path.basename(d), "shots"] and len(whole[1]["files"]) == 2
        assert nodes_files.resolve_path(whole[1]["files"][0]) == os.path.realpath(at("shots", "s0.png"))
        for p in (os.path.join(d, "clip.mp4"), os.path.join(d, "shots", "s0.png")):
            assert load_media.thumbnail(p, 64)[:4] == b"RIFF", "webp thumbnails of pictures and videos"
    assert nodes_files.resolve_folder("arbor:storyboard").endswith(os.path.join("example_media", "storyboard"))
    from arbor_pkg.arbor import dialogs
    here = nodes_files.resolve_folder("arbor:storyboard")
    assert dialogs.folder_of(os.path.join(here, "(add this folder)"), "(add this folder)") == here, "OK inside a folder"
    assert dialogs.folder_of(os.path.join(here, "0 · Arrival"), "(add this folder)") is None
    samples = load_media.tree_of(nodes_files.resolve_folder("arbor:storyboard"))
    assert len(samples) == 3 and samples[0]["files"][0] == "arbor:storyboard/0 · Arrival/000.jpg", "written short"
    # paths are written the short way and read back the same
    import folder_paths
    out_file = os.path.join(folder_paths.get_output_directory(), "arbor", "x.png")
    in_file = os.path.join(folder_paths.get_input_directory(), "shots", "y.png")
    assert nodes_files.short_path(out_file) == "output/arbor/x.png"
    assert nodes_files.short_path(in_file) == "shots/y.png"
    for f in (out_file, in_file):
        assert nodes_files.resolve_path(nodes_files.short_path(f)) == os.path.realpath(f)
    print("load media: OK")


def test_files():
    import tempfile
    from fractions import Fraction
    import folder_paths
    from PIL import Image
    from comfy_api.latest import InputImpl, Types

    images = lambda pattern="*.png": {"kind": "images", "pattern": pattern}
    load = lambda folder, kind, limit=0: res(nodes_files.LoadFolder.execute(
        folder=folder, kind=kind, subfolders=True, sort="name", limit=limit))
    save = lambda tree, prefix, layout="subfolders", **kw: run(nodes_files.SaveByPath, tree=[tree],
                                                              filename_prefix=prefix, layout=layout, **kw)
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        for sub, n in (("a", 2), ("b10", 1), ("b2", 3)):
            os.makedirs(os.path.join(src, sub))
            for k in range(n):
                Image.new("RGB", (16 + k, 8), (k * 40, 0, 0)).save(os.path.join(src, sub, f"img{k}.png"))
        Image.new("RGB", (4, 4)).save(os.path.join(src, "root.png"))
        open(os.path.join(src, "notes.txt"), "w").close()
        imgs, names, folders, count = load(src, images())
        assert count == 7 and folders == ["src", "a", "b2", "b10"], folders  # plain data, one per branch
        assert list(imgs.names.values()) == folders and names.names == imgs.names, "branches named after folders"
        assert names.branches[(1,)] == ["img0", "img1"] and imgs.branches[(2,)][2].shape == (1, 8, 18, 3)
        assert nodes_files.LoadFolder.fingerprint_inputs(src, images(), True, "name", 0)
        assert load(src, images(), limit=3)[3] == 3

        out = os.path.join(d, "out")
        os.makedirs(out)
        old = folder_paths.get_output_directory()
        folder_paths.set_output_directory(out)
        try:
            saved = save(imgs, "xy/run", names=[names])
            paths = res(saved)[0]
            rel = lambda p: os.path.relpath(p, out).replace("\\", "/")
            assert os.path.basename(paths.branches[(1,)][1]) == "img1.png"
            assert rel(os.path.dirname(paths.branches[(2,)][0])) == "xy/run/2 · b2", "the prefix holds the tree"
            assert saved.ui["images"][0]["subfolder"].replace("\\", "/") == "xy/run/0 · src"
            # ... and Load Folder reads it back, names and all ('output/…' is the output folder)
            back, _, back_folders, back_count = load("output/xy/run", images())
            assert back_count == 7 and back_folders == folders and back.names == imgs.names
            plain = res(save(T.DataTree({(0, 1): [imgs.branches[(1,)][0]]}), "xy/plain"))[0]
            assert rel(plain.branches[(0, 1)][0]) == "xy/plain/0-1/000.png", "unnamed branches: just the path"
            one = [imgs.branches[(1,)][0], imgs.branches[(1,)][1]]
            listed = res(run(nodes_files.SaveByPath, tree=one, filename_prefix="xy/list", layout="subfolders",
                             names=["a → b", "b → c"]))[0]
            assert [rel(f) for f in listed.branches[(0,)]] == ["xy/list/a → b.png", "xy/list/b → c.png"],                 "a plain list goes straight under the prefix"
            again = res(save(imgs, "xy/run", layout="flat"))[0]
            assert os.path.basename(again.branches[(0,)][0]) == "run_0 · src_000.png"
            # a long name cut at a space must not leave a trailing space (Windows drops it from folder names)
            long_name = T.DataTree({(0,): [imgs.branches[(1,)][0]]}, {(0,): "word " * 30})
            cut = res(save(long_name, "xy/long"))[0]
            assert os.path.exists(cut.branches[(0,)][0]) and not os.path.basename(os.path.dirname(cut.branches[(0,)][0])).endswith(" ")
            assert nodes_files.folder_label("2 · Night market") == "Night market"
            assert nodes_files.folder_label("2024 photos") == "2024 photos", "only the saved tag is dropped"

            # videos, audio and text by tree, and back
            clip = lambda n: InputImpl.VideoFromComponents(Types.VideoComponents(
                images=torch.rand(n, 32, 48, 3), audio=None, frame_rate=Fraction(24)))
            tone = lambda secs, ch: {"waveform": torch.sin(torch.linspace(0, 400 * secs, int(16000 * secs)))
                                     .repeat(1, ch, 1) * 0.3, "sample_rate": 16000}
            media = T.DataTree({(0,): [clip(12), clip(6)], (1,): [tone(1.0, 2), "a caption"]},
                               {(0,): "Arrival", (1,): "Village"})
            saved = save(media, "media/run")
            files = res(saved)[0]
            assert [os.path.basename(f) for f in files.branches[(0,)]] == ["000.mp4", "001.mp4"]
            assert [os.path.basename(f) for f in files.branches[(1,)]] == ["000.flac", "001.txt"]
            assert rel(os.path.dirname(files.branches[(1,)][0])) == "media/run/1 · Village"
            assert saved.ui["images"] and saved.ui["animated"] == [True] and saved.ui["audio"], saved.ui
            vids, vnames, vfolders, vcount = load("output/media/run", {"kind": "videos", "pattern": "*.mp4"})
            assert vcount == 2 and vfolders == ["Arrival"] and vnames.branches[(0,)] == ["000", "001"]
            assert vids.branches[(0,)][1].get_frame_count() == 6 and vids.branches[(0,)][0].get_dimensions() == (48, 32)
            sounds = load("output/media/run", {"kind": "audio", "pattern": "*.flac"})[0]
            wav = sounds.branches[(0,)][0]
            assert sounds.names == {(0,): "Village"} and wav["sample_rate"] == 16000
            assert tuple(wav["waveform"].shape) == (1, 2, 16000) and wav["waveform"].abs().max() > 0.2
            with open(files.branches[(1,)][1], encoding="utf-8") as f:
                assert f.read() == "a caption"
            raises(ValueError, save, T.DataTree({(0,): [123]}), "media/none")  # nothing it can save

            # anywhere on disk: an absolute prefix, allowed while ComfyUI listens on this computer alone
            from comfy.cli_args import args
            assert nodes_files.save_root("arbor/run")[1:] == ("arbor/run", False)
            assert nodes_files.save_root("output/arbor/run")[1:] == ("arbor/run", False)
            assert nodes_files.save_root(os.path.join(out, "x", "run"))[1:] == (os.path.join("x", "run"), False)
            elsewhere = os.path.join(d, "renders")
            assert nodes_files.save_root(os.path.join(elsewhere, "run"))[2], "outside output"
            listen, env = args.listen, os.environ.pop("ARBOR_SAVE_ANYWHERE", None)
            try:
                args.listen = "127.0.0.1"
                far = save(imgs, os.path.join(elsewhere, "run"))
                first = res(far)[0].branches[(1,)][0]
                assert first.startswith(elsewhere) and os.path.exists(first), first
                assert far.ui["images"][0]["type"] == "temp", "previews of files outside output go through temp"
                args.listen = "0.0.0.0,::"
                raises(PermissionError, save, imgs, os.path.join(elsewhere, "lan"))
                os.environ["ARBOR_SAVE_ANYWHERE"] = "1"
                assert os.path.exists(res(save(imgs, os.path.join(elsewhere, "lan")))[0].branches[(0,)][0])
                assert res(save(imgs, "inside/run"))[0].branches[(0,)][0].startswith(out), "output still works"
            finally:
                args.listen = listen
                os.environ.pop("ARBOR_SAVE_ANYWHERE", None)
                if env is not None:
                    os.environ["ARBOR_SAVE_ANYWHERE"] = env
        finally:
            folder_paths.set_output_directory(old)
    print("load / save: OK")


# ====================================================================== live preview

def test_live_preview():
    mapping = {n.define_schema().node_id: n for n in pkg.NODES}
    live._mappings = lambda: mapping
    assert "Arbor_ImageSlider" not in live.safe_types() and "Arbor_Panel" in live.safe_types()
    panel = lambda **kw: {"class_type": "Arbor_Panel",
                          "inputs": {"text": "", "parse_numbers": True, "multiline": False} | kw}
    prompt = {
        "1": panel(text="a\nb\n\n3"),
        # the mode switch arrives as dotted keys, the way the front end sends a DynamicCombo
        "2": {"class_type": "Arbor_NumberSequence",
              "inputs": {"mode": "series", "mode.start": 1.0, "mode.step": 1.0, "mode.count": 2, "as_int": True}},
        "3": {"class_type": "Arbor_Merge", "inputs": {"trees.tree0": ["1", 1], "trees.tree1": ["2", 0], "mode": "merge"}},
        "4": panel(data=["3", 0]),
        "5": panel(data=["1", 0]),
        "6": {"class_type": "Arbor_NumberSequence",
              "inputs": {"mode": "range", "mode.start": 0.0, "mode.end": 10.0, "mode.steps": 2, "as_int": True}},
        "7": panel(data=["6", 0]),
        "10": {"class_type": "Arbor_ReshapeTree", "inputs": {"tree": ["3", 0], "mode": "flatten", "mode.path": "{2}"}},
        "11": panel(data=["10", 0]),
    }
    p = live.evaluate(prompt, "4")
    assert p["live"] and p["kind"] == "tree"
    assert [(b["path"], [i["v"] for i in b["items"]]) for b in p["branches"]] == [
        ("{0}", ["a", "b", "1", "2"]), ("{1}", ["3"])], p["branches"]
    flat = live.evaluate(prompt, "5")
    assert flat["kind"] == "list" and flat["stats"]["items"] == 3
    assert [i["v"] for i in live.evaluate(prompt, "7")["branches"][0]["items"]] == ["0", "5", "10"]
    reshaped = live.evaluate(prompt, "11")
    assert [b["path"] for b in reshaped["branches"]] == ["{2}"] and reshaped["stats"]["items"] == 5
    prompt["8"] = {"class_type": "KSampler", "inputs": {}}
    prompt["9"] = panel(data=["8", 0])
    try:
        live.evaluate(prompt, "9")
        raise AssertionError("KSampler must not run live")
    except live.Unsupported as e:
        assert e.class_type == "KSampler"
    print("live preview: OK")


# ====================================================================== package

def test_sampling():
    from comfy.utils import pack_latents, unpack_latents
    from comfy_extras.nodes_minimax_h3 import EmptyMiniMaxH3LatentAV, MiniMaxH3AddGuide
    S = nodes_sampling

    # Add Guide Frames: Batch Pick syntax, the same guides as one core Add Guide per frame
    gi = S.guide_indices
    assert gi("0, 17::17, -1", 124) == [0, 17, 34, 51, 68, 85, 102, 119, 123]
    assert gi("0, 5::17", 124) == [0, 5, 22, 39, 56, 73, 90, 107]
    assert gi("3-5, 4, -124", 124) == [3, 4, 5, 0], "ranges, repeats dropped, negatives"
    raises(IndexError, gi, "124", 124)
    raises(ValueError, gi, "x", 124)

    class FakeVAE:  # encodes each picture to something that depends on its pixels
        def encode(self, px):
            assert px.shape[0] == 1, "single frames only"
            return px.mean(dim=(1, 2, 3)).reshape(1, 1, 1, 1, 1).expand(1, 24, 1, 6, 4).clone()

    latent = EmptyMiniMaxH3LatentAV.execute(64, 96, 124).result[0]
    frames = torch.rand(124, 96, 64, 3)
    cond = [[torch.zeros(1, 4, 8), {}]]
    vae = FakeVAE()
    ours, count = res(run(S.H3AddGuideFrames, positive=cond, vae=vae, latent=latent, images=frames,
                          frames="0, 17::17, -1"))
    chain = cond
    for i in (0, 17, 34, 51, 68, 85, 102, 119, 123):
        chain = MiniMaxH3AddGuide.execute(chain, latent, i, vae=vae, image=frames[i:i + 1]).result[0]
    a, b = ours[0][1]["minimax_keyframes"], chain[0][1]["minimax_keyframes"]
    assert count == 9 and [k["resolved_frame_index"] for k in a] == [k["resolved_frame_index"] for k in b]
    assert all(torch.equal(x["latent"], y["latent"]) for x, y in zip(a, b)), "same guides as the core chain"
    pre = MiniMaxH3AddGuide.execute(cond, latent, 60, vae=vae, image=frames[60:61]).result[0]
    more = res(run(S.H3AddGuideFrames, positive=pre, vae=vae, latent=latent, images=frames, frames="0"))[0]
    assert [k["resolved_frame_index"] for k in more[0][1]["minimax_keyframes"]] == [60, 0], "earlier guides kept"

    # tiles cover the latent on the 2x2 patch grid and overlap; auto keeps them about H3's native size
    for h, w, ty, tx in ((84, 48, 2, 2), (68, 120, 2, 3), (84, 48, 1, 1), (42, 24, 3, 2), (160, 90, 0, 0)):
        boxes = S.plan_tiles(h, w, ty, tx, 8)
        cover = torch.zeros(h, w)
        for y0, y1, x0, x1 in boxes:
            assert y0 % 2 == x0 % 2 == (y1 - y0) % 2 == (x1 - x0) % 2 == 0, boxes
            cover[y0:y1, x0:x1] += 1
        assert cover.min() >= 1 and (len(boxes) == 1 or cover.max() >= 2), (h, w, ty, tx)
        assert all(S.tile_weights(b, h, w, 8).min() > 0 for b in boxes)
    auto = lambda W, H: len(S.plan_tiles(H // 16, W // 16, 0, 0, 8))
    assert (auto(768, 1344), auto(1088, 1920), auto(1440, 2560), auto(2048, 2048)) == (1, 2, 4, 6)
    for W, H in ((1440, 2560), (2048, 2048), (2160, 3840)):
        for y0, y1, x0, x1 in S.plan_tiles(H // 16, W // 16, 0, 0, 8):
            th, tw = y1 - y0, x1 - x0
            assert th * tw <= S.NATIVE_LATENT_AREA and max(th, tw) <= 2 * min(th, tw), (W, H, th, tw)

    # the wrapper: 1x1 passes through, a 2x2 blend equals untiled for a pixel-wise model
    T_, H, W = 3, 20, 16
    video, audio = torch.randn(1, 24, T_, H, W), torch.randn(1, 32, 2, 7)
    x, shapes = pack_latents([video, audio])
    guide = torch.randn(1, 24, 1, H, W)
    payload = {"keyframes": [{"resolved_frame_index": 0, "latent": guide}], "cond_video_latents": [guide],
               "layout": object(), "seed": 0}
    c = {"latent_shapes": shapes, "minimax_payload": payload, "denoise_mask": torch.rand(1, 1, T_, H, W),
         "transformer_options": {}}
    seen = []

    def fake_apply(x_, t_, latent_shapes=None, minimax_payload=None, denoise_mask=None, **kw):
        v, a_ = unpack_latents(x_, latent_shapes)
        h_, w_ = v.shape[-2:]
        g = minimax_payload["cond_video_latents"][0]
        assert g.shape[-2:] == (h_, w_) and denoise_mask.shape[-2:] == (h_, w_), "guide and mask cropped to the tile"
        assert "layout" not in minimax_payload or (h_, w_) == (H, W), "tile layout left to the model"
        seen.append((h_, w_))
        return pack_latents([v * 2 + g * denoise_mask, a_ * 3])[0]  # each position depends only on itself

    full = fake_apply(x, None, **c)
    seen.clear()
    assert torch.equal(S.make_wrapper(1, 1, 2, 2)(fake_apply, {"input": x, "timestep": None, "c": c}), full)
    assert seen == [(H, W)], "1x1 is a pass-through"
    seen.clear()
    out = S.make_wrapper(2, 2, 4, 4)(fake_apply, {"input": x, "timestep": None, "c": c})
    assert len(seen) == 4 and all(s != (H, W) for s in seen)
    assert torch.allclose(out, full, atol=1e-5), "blended tiles = untiled for a pixel-wise model"
    assert payload.get("layout") is not None, "the original payload is left untouched"
    # guide mask: only the guide tokens inside it go in
    from comfy.ldm.minimax.model import PackedLayout
    # which tokens: per latent frame (1, 4, 4.. pixel frames), 2x2 latent cells each, grown by a token
    g3 = torch.zeros(9, 8, 8, dtype=torch.uint8)
    g3[3, 0, 0] = 1  # pixel frame 3 = latent frame 1
    k = S.guide_keep(g3, torch.zeros(1, 24, 3, 8, 8), 0, (0, 8, 0, 8)).reshape(3, 4, 4)
    assert k[1].sum() == 4 and k[1, :2, :2].all() and not k[0].any() and not k[2].any(), k
    assert not S.guide_keep(g3, torch.zeros(1, 24, 3, 8, 8), 0, (0, 8, 0, 8), margin=0).reshape(3, 4, 4)[1, 1, 1]
    assert S.guide_keep(g3, torch.zeros(1, 24, 1, 8, 8), 3, (0, 8, 0, 8)).sum() == 4, "anchored at its frame"
    # the pruned layout: the kept guide rows keep their positions, the target is untouched
    kfs = [{"resolved_frame_index": 0, "latent": torch.zeros(1, 24, 2, 8, 8)}]
    lay = PackedLayout(5, 3, 8, 8, 7, keyframes=kfs)
    keep = torch.zeros(2 * 16, dtype=torch.bool)
    keep[[0, 5, 17]] = True
    new, left = S.repack(lay, [keep])
    assert new.seq_len == lay.seq_len - 29 and new.signature == lay.signature and left == [0]
    (ca, cb, _), = [s for s in lay.segments if s[2] == "cond"]
    (na, nb, _), = [s for s in new.segments if s[2] == "cond"]
    assert nb - na == 3 and torch.equal(new.position_ids[na:nb], lay.position_ids[ca:cb][keep])
    va, vb, _ = next(s for s in lay.segments if s[2] == "video")
    wa, wb, _ = next(s for s in new.segments if s[2] == "video")
    assert torch.equal(new.position_ids[wa:wb], lay.position_ids[va:vb])
    assert int((~new.img_update).sum()) == 3 and int(new.img_update.sum()) == int(lay.img_update.sum())
    assert torch.equal(new.position_ids[new.img_pos[~new.img_update]], lay.position_ids[ca:cb][keep])
    assert torch.equal(new.position_ids[new.audio_pos], lay.position_ids[lay.audio_pos])
    raises(ValueError, S.repack, lay, [keep[:-1]])
    assert S.repack(lay, [torch.zeros(32, dtype=torch.bool)])[1] == [], "a guide with no row left is left out"
    # with references: only the guide loses rows, and nothing asked for changes nothing
    img_ = {"kind": "image", "latent_h": 4, "latent_w": 4, "latent": torch.zeros(1, 24, 1, 4, 4)}
    vid_ = {"kind": "video", "latent_t": 3, "latent_h": 4, "latent_w": 4, "ref_audio_t": 0,
            "latent": torch.zeros(1, 24, 3, 4, 4)}
    lay2 = PackedLayout(5, 3, 8, 8, 7, keyframes=kfs, refs=[img_, vid_])
    assert [k for _, _, k in lay2.segments] == ["text", "cond", "ref_img", "ref_img", "audio", "video"]
    less, left = S.repack(lay2, [keep, None, None])
    assert left == [0, 1, 2] and less.seq_len == lay2.seq_len - 29
    assert less.img_update.tolist() == [False] * (3 + 4 + 12) + [True] * 48
    assert torch.equal(less.img_pos, torch.cat([torch.arange(a, b) for a, b, k in less.segments if k in S.PICTURES]))
    assert torch.equal(less.position_ids[less.audio_pos], lay2.position_ids[lay2.audio_pos]) and less.audio_update.all()
    assert S.repack(lay2, [torch.zeros(32, dtype=torch.bool), None, None])[1] == [1, 2]
    same, left = S.repack(lay2, [None] * 3)
    assert left == [0, 1, 2] and same.segments == lay2.segments and torch.equal(same.position_ids, lay2.position_ids)
    assert torch.equal(same.img_pos, lay2.img_pos) and torch.equal(same.img_update, lay2.img_update)
    assert torch.equal(same.audio_pos, lay2.audio_pos) and torch.equal(same.audio_update, lay2.audio_update)
    # what the text says of a same-framed reference video is cut to the tile: its blocks of picture tokens keep the
    # tokens over the tile, with the marker either side, and everything else stays
    assert [S.ref_frames(n) for n in (2, 7, 37, 72)] == [5, 22, 124, 243]
    rv8 = {"kind": "video", "latent_t": 7, "latent_h": 8, "latent_w": 12, "ref_audio_t": 0,
           "latent": torch.zeros(1, 24, 7, 8, 12)}  # 22 frames: two frames shown, one block of 4 x 6 tokens
    block = [0] * (4 * 6 + 2)
    tags = torch.tensor([1, 1] + [0] * 6 + [1] + block + [1, 1, 1])  # a picture's block, the video's, the prompt
    pic = {"kind": "image", "latent_h": 4, "latent_w": 4, "latent": torch.zeros(1, 24, 1, 4, 4)}
    tk = S.text_keep(tags, [pic, rv8], (0, 16, 0, 12), (7, 16, 24))  # the top left tile: all rows, half the columns
    assert tk is not None and int(tk.sum()) == tags.numel() - 12 and tk[:10].all() and tk[-4:].all()
    assert tk[10:34].reshape(4, 6).tolist() == [[True] * 3 + [False] * 3] * 4
    tk = S.text_keep(tags, [pic, rv8], (8, 16, 12, 24), (7, 16, 24))
    assert tk[10:34].reshape(4, 6).tolist() == [[False] * 6] * 2 + [[False] * 3 + [True] * 3] * 2
    assert S.text_keep(tags, [pic, rv8], (0, 16, 0, 24), (7, 16, 24)) is None, "the whole frame keeps every row"
    assert S.text_keep(tags, [rv8], (0, 16, 0, 12), (7, 16, 24)) is None, "blocks that don't match the references"
    assert S.text_keep(tags[:-5], [pic, rv8], (0, 16, 0, 12), (7, 16, 24)) is None, "a block of another size"
    assert S.text_keep(tags, [pic, {**rv8, "latent": torch.zeros(1, 24, 2, 8, 12), "latent_t": 2}],
                       (0, 16, 0, 12), (7, 16, 24)) is None, "a video of another length is not cropped"
    # a reference cut to a tile reaches a little past it, and gets the positions of where it lies: showing exactly
    # the canvas is H3's own layout, and anything else is spread over the same span
    assert S.ref_place(rv8, (0, 16, 0, 12), 16, 24) == (0.0, 1.0, 0.0, 1.0)
    wide = {**rv8, "latent": torch.zeros(1, 24, 7, 10, 8)}  # on a 20 x 16 video: 2 latents of the video each
    assert S.ref_place(wide, (0, 12, 0, 10), 20, 16) == (0.0, 1.0, 0.0, 1.2), "cut out to whole patches: 6 of 5 across"
    assert S.ref_place(wide, (8, 20, 6, 16), 20, 16) == (0.0, 1.0, -0.2, 1.0)
    lay3 = PackedLayout(5, 3, 8, 8, 7, refs=[vid_])
    stock = lay3.position_ids.clone()
    S.place(lay3, [vid_["latent"]], [(0.0, 1.0, 0.0, 1.0)], 8, 8)
    assert torch.allclose(lay3.position_ids, stock), "a reference that shows the canvas stays where H3 puts it"
    S.place(lay3, [vid_["latent"]], [(0.0, 1.25, -0.25, 1.0)], 8, 8)
    (ra, rb, _), = [s for s in lay3.segments if s[2] == "ref_img"]
    assert lay3.position_ids[ra:ra + 4, 1:].tolist() == [[0.0, -8.0], [0.0, 12.0], [20.0, -8.0], [20.0, 12.0]]
    assert torch.equal(lay3.position_ids[ra:rb, 1:], lay3.position_ids[ra:ra + 4, 1:].repeat(3, 1)), "every frame"
    assert torch.equal(lay3.position_ids[:, 0], stock[:, 0]) and torch.equal(lay3.position_ids[rb:], stock[rb:])
    raises(ValueError, S.place, lay3, [vid_["latent"][:, :, :2]], [(0.0, 1.0, 0.0, 1.0)], 8, 8)
    # the row filter picks the kept guide rows, and leaves payloads without a mask alone

    class FakeDM:
        def _cond_video_rows(self, payload, device):
            return torch.arange(6)[:, None].float()
    dm = FakeDM()
    assert S.install_row_filter(dm) and S.install_row_filter(dm)
    pick = torch.tensor([1, 0, 0, 1, 0, 1], dtype=torch.bool)
    assert dm._cond_video_rows({S.KEEP: pick}, "cpu")[:, 0].tolist() == [0, 3, 5]
    assert dm._cond_video_rows({}, "cpu").shape[0] == 6
    # through the wrapper: a corner mask gives the corner tile part of its guide and the other tiles none
    calls = []

    def count_guides(x_, t_, latent_shapes=None, minimax_payload=None, denoise_mask=None, **kw):
        keep_ = minimax_payload.get(S.KEEP)
        n = len(minimax_payload["cond_video_latents"])
        assert len(minimax_payload.get("keyframes") or []) == n, "keyframes and latents agree"
        calls.append((n, None if keep_ is None else int(keep_.sum())))
        if keep_ is not None:
            assert minimax_payload["layout"].seq_len < PackedLayout(
                5, T_, *unpack_latents(x_, latent_shapes)[0].shape[-2:], 7,
                keyframes=minimax_payload["keyframes"]).seq_len
        return x_
    cm = {**c, "c_crossattn": torch.zeros(1, 5, 8)}
    corner = torch.zeros(5, H * 16, W * 16)
    corner[0, :32, :32] = 1  # top left, the guide's frame
    S.make_wrapper(2, 2, 4, 4, guide_mask=corner)(count_guides, {"input": x, "timestep": None, "c": cm})
    assert calls == [(1, 4), (0, None), (0, None), (0, None)], calls
    calls.clear()
    S.make_wrapper(1, 1, 4, 4, guide_mask=torch.zeros(5, 32, 32))(count_guides, {"input": x, "timestep": None, "c": cm})
    assert calls == [(0, None)], "an empty mask drops the guide even untiled"
    calls.clear()
    S.make_wrapper(1, 1, 4, 4, guide_mask=torch.ones(1, 32, 32))(count_guides, {"input": x, "timestep": None, "c": cm})
    assert calls == [(1, None)] and cm["minimax_payload"] is payload, "a full mask changes nothing"
    calls.clear()
    S.make_wrapper(2, 2, 4, 4, guide_mask=corner)(count_guides, {"input": x, "timestep": None, "c": c})
    assert calls == [(1, None)] * 4, "no text to rebuild the layout from: the whole guide, no failure"
    assert len(payload["keyframes"]) == 1 and S.KEEP not in payload, "the original payload is left untouched"
    # a reference video framed like the video (the IC refiner's source) is cropped to each tile; others go in whole
    rv = {"kind": "video", "latent_t": T_, "latent_h": 10, "latent_w": 8, "ref_audio_t": 0,
          "latent": torch.randn(1, 24, T_, 10, 8)}
    other = {"kind": "video", "latent_t": 2, "latent_h": 10, "latent_w": 8, "ref_audio_t": 0,
             "latent": torch.randn(1, 24, 2, 10, 8)}
    img = {"kind": "image", "latent_h": 6, "latent_w": 6, "latent": torch.randn(1, 24, 1, 6, 6)}
    assert S.framed_like(rv, T_, H, W) and not S.framed_like(other, T_, H, W) and not S.framed_like(img, T_, H, W)
    rp = {**payload, "refs": [img, rv, other]}
    tile = S.crop_payload(rp, (0, 12, 0, 10), full=(T_, H, W))
    assert tile["refs"][1]["latent"].shape[-2:] == (6, 6) and tile["refs"][1]["latent_h"] == 6
    assert tile["refs"][0] is img and tile["refs"][2] is other and rp["refs"][1]["latent"].shape[-2:] == (10, 8)
    assert [z.shape[-3:] for z in tile["cond_video_latents"][1:]] == [(1, 6, 6), (T_, 6, 6), (2, 10, 8)]
    tl = PackedLayout(5, T_, 12, 10, 7, keyframes=tile["keyframes"], refs=tile["refs"])
    rows = sum(z.shape[2] * (z.shape[3] // 2) * (z.shape[4] // 2) for z in tile["cond_video_latents"])
    assert int((~tl.img_update).sum()) == rows, "the layout and the rows agree"
    assert S.crop_payload(rp, (0, 12, 0, 10))["refs"][1] is rv, "without the whole video's size, nothing is cropped"
    ref_sizes = []

    def see_refs(x_, t_, latent_shapes=None, minimax_payload=None, denoise_mask=None, **kw):
        ref_sizes.append(tuple(minimax_payload["refs"][1]["latent"].shape[-2:]))
        assert minimax_payload["refs"][0] is img and minimax_payload["refs"][2] is other
        return x_
    S.make_wrapper(2, 2, 4, 4)(see_refs, {"input": x, "timestep": None, "c": {**c, "minimax_payload": rp}})
    assert len(ref_sizes) == 4 and all(h_ < 10 and w_ < 8 for h_, w_ in ref_sizes), ref_sizes
    # with the text at hand a tile packs itself: what the text says of the reference is cut to the tile, and the
    # reference lies where its patches are
    packs = []

    def see_pack(x_, t_, latent_shapes=None, minimax_payload=None, c_crossattn=None, **kw):
        lay, v = minimax_payload.get("layout"), unpack_latents(x_, latent_shapes)[0]
        if lay is None:
            return x_
        assert lay.signature == (c_crossattn.shape[1], T_, *v.shape[-2:], 7), "the model takes this layout as its own"
        assert minimax_payload["text_token_tags"].numel() == c_crossattn.shape[1]
        assert int((~lay.img_update).sum()) == sum(S.rows_of(z) for z in minimax_payload["cond_video_latents"])
        (a, b), (va_, _) = (next((a, b) for a, b, k in lay.segments if k == kind) for kind in ("ref_img", "video"))
        frame = (v.shape[-2] // 2) * (v.shape[-1] // 2)
        packs.append(([k for _, _, k in lay.segments], c_crossattn[0, :, 0].tolist(), lay.position_ids[a:b, 1:],
                      lay.position_ids[va_:va_ + frame, 1:].reshape(v.shape[-2] // 2, v.shape[-1] // 2, 2)))
        return x_
    tags29 = torch.tensor([1] * 3 + [0] * 22 + [1] * 4)  # the 5-frame reference is one block of 5 x 4 tokens
    ct = {**c, "c_crossattn": torch.arange(29.0)[None, :, None].expand(1, 29, 8),
          "minimax_payload": {**payload, "refs": [rv], "text_token_tags": tags29}}
    S.make_wrapper(2, 2, 4, 4)(see_pack, {"input": x, "timestep": None, "c": ct})
    assert [p[0] for p in packs] == [["text", "cond", "ref_img", "audio", "video"]] * 4
    assert packs[0][1] == [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 13, 14, 24, 25, 26, 27, 28], "the top left 3 x 3 tokens"
    assert all(len(p[1]) == 18 for p in packs) and ct["c_crossattn"].shape[1] == 29
    stock = PackedLayout(18, T_, 12, 10, 7, keyframes=[{"resolved_frame_index": 0, "latent": guide[..., :12, :10]}],
                         refs=[S.crop_ref(rv, (0, 12, 0, 10), H, W)])
    sa, sb = next((a, b) for a, b, k in stock.segments if k == "ref_img")
    assert not torch.allclose(packs[0][2], stock.position_ids[sa:sb, 1:]), "not where H3 puts a 6 x 6 reference"
    # each of its tokens covers 2 x 2 of the tile's, and sits on the first of them
    assert torch.allclose(packs[0][2][:9].reshape(3, 3, 2), packs[0][3][::2, ::2])
    packs.clear()
    S.make_wrapper(2, 2, 4, 4, exact_refs=False, text_crop=False)(see_pack, {"input": x, "timestep": None, "c": ct})
    assert not packs, "nothing to pack: the payload goes in as it was, for the model to lay out"

    class NotH3:
        model = object()
    raises(ValueError, S.H3TiledRefine.execute, NotH3(), 0, 0, 128)
    print("sampling: OK  (guides = core chain, tiles exact on a pixel-wise model, auto grid)")


def test_region_redraw():
    import torch.nn.functional as F
    Fc = nodes_region
    H, W = 384, 672

    def mask(*spans, n=60, size=(96, 168)):
        """[n, h, w] mask from (frames, (x0, y0, x1, y1)) on a quarter-size grid."""
        m = torch.zeros(n, *size)
        for frames, box in spans:
            for f in frames:
                m[f, box[1]:box[3], box[0]:box[2]] = 1
        return m

    def faces(*spans, shots=(0,), **kw):
        return Fc.link_regions(Fc.split_regions(mask(*spans, **kw), H, W)[1], list(shots))

    # cuts
    assert Fc.shot_starts(torch.cat([torch.zeros(10, 64, 64, 3), torch.ones(10, 64, 64, 3)])) == [0, 10]

    # a mask comes apart into faces, in image pixels; a speck is not one, a face cut in two by a hair is one
    labels, regions = Fc.split_regions(mask((range(3), (10, 10, 20, 30)), (range(3), (60, 10, 70, 20)), (range(3), (100, 50, 101, 51))), H, W)
    assert labels.dtype == torch.uint8 and labels.shape == (60, 96, 168)
    assert sorted(b for _, b in regions[0]) == [(40.0, 40.0, 80.0, 120.0), (240.0, 40.0, 280.0, 80.0)]
    assert len(Fc.split_regions(mask((range(1), (10, 10, 20, 20)), (range(1), (21, 10, 30, 20))), H, W)[1][0]) == 1
    big = torch.zeros(2, 1440, 2560)
    big[:, 400:480, 800:880] = 1
    assert Fc.split_regions(big, 1440, 2560)[1][0][0][1] == (800.0, 400.0, 880.0, 480.0), "a large mask is split at a smaller size"

    # faces are followed by place and size: two stay two; hidden, a face comes back; a cut, a long gap or a jump is new
    two = faces((range(30), (10, 10, 20, 20)), (range(30), (60, 10, 70, 20)))
    assert [(r.number, r.first, r.last) for r in two] == [(1, 0, 29), (2, 0, 29)]
    hidden = faces((list(range(0, 20)) + list(range(30, 50)), (10, 10, 20, 20)))
    assert len(hidden) == 1 and 25 not in hidden[0].boxes
    assert [(r.first, r.last) for r in faces((range(40), (10, 10, 20, 20)), shots=(0, 20))] == [(0, 19), (20, 39)]
    assert len(faces((list(range(0, 10)) + list(range(40, 50)), (10, 10, 20, 20)))) == 2, "hidden too long"
    assert len(faces((range(0, 20), (10, 10, 20, 20)), (range(20, 40), (120, 60, 130, 70)))) == 2, "somewhere else"
    assert len(faces((range(0, 20), (10, 10, 20, 20)), (range(20, 40), (5, 5, 60, 60)))) == 2, "a jump in size is something else"
    assert faces((range(0, 3), (10, 10, 20, 20))) == [], "a blip"
    # faces that touch in the mask come and go as one piece: they stay one run, so nothing changes mid-shot
    apart = [(range(20, 40), (40, 40, 50, 50)), (range(20, 40), (56, 40, 66, 50))]
    together = [(list(range(0, 20)) + list(range(40, 60)), (40, 40, 66, 50))]
    joined_up = faces(*apart, *together)
    assert len(joined_up) == 1 and sorted(joined_up[0].boxes) == list(range(60)) and len(joined_up[0].parts[30]) == 2
    assert joined_up[0].boxes[30] == joined_up[0].boxes[5], "the box holds both"
    moving = [(range(f, f + 1), (10 + f, 20, 20 + f, 30)) for f in range(40)]
    assert len(faces(*moving)) == 1, "a face that moves"
    r = faces((range(10), (10, 10, 20, 30)))[0]
    assert r.boxes[0] == (40.0, 40.0, 80.0, 120.0) and r.size == 80

    # a push-in stays one face, smallest size decides, so it is redrawn whole
    push = [(range(f, f + 1), (60, 40, 68 + f // 3, 48 + f // 3)) for f in range(60)]
    grown = faces(*push)
    assert len(grown) == 1 and len(grown[0].boxes) == 60 and grown[0].least < 50 and max(grown[0].sides) > 100
    text = Fc.report(grown + faces((range(30), (10, 10, 60, 60))), 60)
    assert "redraw" in text.split("\n")[0] and "larger than max_size" in text.split("\n")[1]
    assert Fc.report([], 60) == "nothing in the masks"

    # neighbours share a crop when that is less work; faces far apart or at other times do not
    def box(x, y):
        return (x, y, x + 40, y + 40)

    a = Fc.Run({f: box(100, 100) for f in range(20)})
    b = Fc.Run({f: box(150, 100) for f in range(20)})
    c = Fc.Run({f: box(560, 300) for f in range(20)})
    d = Fc.Run({f: box(100, 100) for f in range(30, 50)})
    assert sorted(len(g) for g in Fc.group_runs([a, b, c, d])) == [1, 1, 2]
    assert sorted(len(g) for g in Fc.group_runs([a, b, c, d], 0)) == [1, 1, 1, 1], "0 keeps every face alone"
    assert len(Fc.group_runs([a, c], 2048)) == 2, "far apart, one crop is more work than two"
    row = [Fc.Run({f: box(i * 120, 100) for f in range(20)}) for i in range(5)]
    assert all(Fc._work(g, 512, Fc.CONTEXT, 77)[2] <= Fc.GROUP_SIZE and Fc._work(g, 512, Fc.CONTEXT, 77)[1] <= Fc.MAX_CANVAS for g in Fc.group_runs(row))
    assert len(Fc.group_runs(row)) < 5, "a row of faces shares crops"
    # a face sharing a crop is enlarged as much as it would be alone, and has as much room around it
    _, gpos, gshape = Fc.crop_window([a, b], 1440, 2560, 512)
    _, spos, sshape = Fc.crop_window([a], 1440, 2560, 512)
    assert abs(gshape[0] / gpos[5][3] - sshape[0] / spos[5][3]) < 0.1 * sshape[0] / spos[5][3]
    assert gpos[5][2] - 90 >= spos[5][2] - 77 - 2 and max(gshape) > max(sshape), "a 40 px face counts as 77 px"

    # a lone face is square, others longer, never past 2:1; the crop has the canvas's shape; context reaches small faces
    assert Fc.fit_crop(40, 50, 768, 4.0) == (308, 308, (768, 768)) and Fc.fit_crop(90, 120, 768, 4.0)[2] == (768, 768)
    assert Fc.fit_crop(40, 50, 480, 4.0)[2] == (480, 480)
    assert Fc.fit_crop(400, 40, 768, 4.0) == (1600, 800, (768, 1536)) and Fc.fit_crop(40, 400, 768, 4.0) == (800, 1600, (1536, 768))
    cw, ch, shape = Fc.fit_crop(150, 90, 768, 4.0)
    assert shape[1] > shape[0] and abs(cw / ch - shape[1] / shape[0]) < 1e-6 and cw >= 600 and ch >= 360
    assert Fc.fit_crop(40, 50, 768, 2.0)[:2] == (154, 154) and Fc.fit_crop(100, 100, 768, 3.0)[:2] == (300, 300)
    assert Fc.fit_crop(90, 40, 512, 4.0, 77, (40, 40))[2][0] > 512, "a shared crop has a larger canvas"

    # the crop stays inside the frame and follows the face; a steady face keeps one size; a growing one grows it smoothly
    walking = Fc.Run({f: (f * 8.0, 100.0, f * 8.0 + 40, 140.0) for f in range(60)})
    frames, pos, shape = Fc.crop_window([walking], H, W, 768, 4.0)
    assert shape == (768, 768) and frames == list(range(60))
    assert len({p[2:] for p in pos.values()}) == 1 and pos[0][2] == pos[0][3] >= 160
    assert all(0 <= p[0] <= W - p[2] and 0 <= p[1] <= H - p[3] for p in pos.values()) and pos[59][0] > pos[0][0]
    tall = Fc.Run({f: (100, 100, 140, 300) for f in range(10)})
    window = Fc.crop_window([tall], H * 2, W, 768, 4.0)
    assert window[1][5][3] > window[1][5][2] and window[2] == (1536, 768)
    big_h, big_w = 720, 1280
    ones = torch.ones(60, 90, 160, dtype=torch.uint8)
    wide_run = Fc.Run({f: (500 - f * 2, 340 - f * 2, 520 + f * 2, 360 + f * 2) for f in range(60)}, {f: [1] for f in range(60)}, labels=ones)
    _, wpos, wshape = Fc.crop_window([wide_run], big_h, big_w, 768, 4.0)
    assert wshape == (768, 768) and wpos[59][3] > 2 * wpos[0][3]
    assert max(abs(wpos[f + 1][3] - wpos[f][3]) for f in range(59)) < 40
    x = torch.zeros(1, 1, 40, 40)
    x[0, 0, 20, 20] = 1
    assert torch.equal(Fc._dilate(x, 9), F.max_pool2d(x, 9, stride=1, padding=4)), "same as the square kernel"

    # a growing face: the paste follows it, on one grid
    grid = Fc.paste_mask([wide_run], list(range(60)), wpos, big_h, big_w)
    assert grid.shape == (60, max(p[3] for p in wpos.values()), max(p[2] for p in wpos.values()))
    zoomed = torch.full((60, big_h, big_w, 3), 0.25)
    sizes, areas = [], []

    def fake(crops, area):
        sizes.append(tuple(crops.shape))
        assert area.shape == crops.shape[:3] and area.dtype == torch.bool and area.any()
        areas.append(float(area.float().mean()))
        out = crops.clone()
        out = out + 0.1  # what the VAE might do to everything
        out[area] += 0.4
        return out

    crop2, comp2 = Fc.refine_group(zoomed, [wide_run], big_h, big_w, fake, context=4.0)
    assert sizes == [(60, 768, 768, 3)] and comp2.shape == (60, 768 * 2 + 4, 768, 3) and "enlarged" in crop2.text
    assert (zoomed[59] - 0.25).abs().sum() > (zoomed[0] - 0.25).abs().sum(), "more is pasted as the face grows"

    # only the region's frames and pixels change; drift outside it is taken out
    source = mask((range(10, 30), (40, 40, 50, 50)), (range(0, 60), (130, 60, 140, 70)))
    labels, regions = Fc.split_regions(source, H, W)
    runs = Fc.link_regions(regions, [0])
    run0 = next(r for r in runs if r.first == 10)
    run0.labels = labels
    images = torch.full((60, H, W, 3), 0.25)
    sizes.clear()
    before = images.clone()
    crop, comp = Fc.refine_group(images, [run0], H, W, fake, context=4.0)
    assert sizes == [(20, 768, 768, 3)], sizes
    assert areas[-1] < 0.5, "only around the face is redrawn"
    assert "frames 10-29" in crop.text, crop.text
    assert comp.shape == (20, 768 * 2 + 4, 768, 3) and float(comp[5, :768].mean()) < float(comp[5, 772:].mean()), \
        "before above, after below, at the canvas size"
    flat_frames = torch.full_like(images[:10], 0.25)
    assert torch.equal(images[:10], flat_frames) and torch.equal(images[30:40], flat_frames)
    changed = (images[20] - 0.25).abs().sum(-1) > 1e-4
    assert changed.any() and int(changed.nonzero()[:, 0].min()) > 100, "the change stays around the face"
    assert not changed[240:280, 520:560].any(), "another face in the mask is not touched by this crop"
    assert abs(float(images[20][changed].max()) - 0.65) < 0.02, "a real change keeps its colour, the VAE's drift goes"

    # refine_size sets the canvas
    other = torch.full((60, H, W, 3), 0.25)
    sizes.clear()
    Fc.refine_group(other, [run0], H, W, fake, 640, context=4.0)
    assert sizes == [(20, 640, 640, 3)], sizes

    # bbox: a steady box with no holes for a dropout, none where a face is hidden; grow and feather reach further
    shaky = Fc.Run({f: (100.0 + (f % 2) * 6, 100.0, 140.0 + (f % 2) * 6, 140.0) for f in range(30) if f != 12})
    steady = Fc.steady_boxes(shaky)
    assert sorted(steady) == list(range(30)) and max(abs(steady[f][0] - steady[f + 1][0]) for f in range(5, 25)) < 1
    gap = Fc.Run({f: (100, 100, 140, 140) for f in list(range(10)) + list(range(30, 40))})
    assert 11 in Fc.steady_boxes(gap) and 20 not in Fc.steady_boxes(gap), "a hidden face is not pasted over"
    win = Fc.crop_window([run0], H, W, 768, 4.0)[:2]
    area = {}
    for paste, grow, feather in (("mask", 0.35, 0.12), ("bbox", 0.35, 0.12), ("mask", 0.8, 0.12), ("mask", 0.35, 0.4)):
        w = Fc.paste_mask([run0], *win, H, W, paste, grow, feather)
        assert w.shape == (20, round(win[1][10][3]), round(win[1][10][2])) and 0 <= float(w.min()) and float(w.max()) <= 1
        area[paste, grow, feather] = int((w[10] > 0.01).sum())
    assert area["mask", 0.8, 0.12] > area["mask", 0.35, 0.12] and area["mask", 0.35, 0.4] > area["mask", 0.35, 0.12]
    assert area["bbox", 0.35, 0.12] > 0

    # what is kept stays out of the paste, however near
    nearby = torch.zeros(60, H, W, dtype=torch.bool)
    nearby[:, 160:200, 200:230] = True
    w = Fc.paste_mask([run0], *win, H, W, keep=nearby)
    x0, y0 = win[1][20][:2]
    assert float(w[10, round(170 - y0), round(215 - x0)]) == 0, "a lead is not pasted over"

    # crops keep their fraction of a pixel: a crop that grows smoothly in a push-in is cut and pasted where it is, so the
    # redrawn region does not wobble against the rest by each frame's rounding
    sp_run = Fc.Run({f: (300 - 2.3 * f, 200 - 1.3 * f, 340 + 2.3 * f, 240 + 1.3 * f) for f in range(40)})
    sp_pos = Fc.crop_window([sp_run], 1000, 1000, 512, 2.0)[1]
    assert any(p[2] != round(p[2]) for p in sp_pos.values()), "sizes are not rounded to whole pixels"
    sp_ramp = torch.arange(1000, dtype=torch.float32)[None, :, None].expand(1000, 1000, 3) / 1000
    sp_box = (100.25, 50.5, 80.5, 80.5)
    sp_cut = Fc.window(sp_ramp, sp_box, (161, 161))  # 2x
    sp_want = (sp_box[0] + (torch.arange(161) + 0.5) * sp_box[2] / 161) / 1000
    assert float((sp_cut[80, :, 0] - sp_want).abs()[2:-2].max()) < 1e-3, "a window samples exactly the fractional box"
    sp_frame = torch.zeros(1, 1000, 1000, 3)
    sp_crop = Fc.Crop([0], {0: sp_box}, (161, 161), torch.full((1, 161, 161), 255, dtype=torch.uint8), [(0, 1, torch.zeros(3))],
                   height=1000, width=1000)
    Fc.paste_crop(sp_frame, sp_crop, sp_cut[None])
    sp_in = sp_frame[0, 52:129, 102:179, 0]
    assert float((sp_in - sp_ramp[52:129, 102:179, 0]).abs().max()) < 2e-3, "pasted back where it came from"
    assert float(sp_frame[0, 140:, :, 0].abs().max()) == 0 and float(sp_frame[0, :, 190:, 0].abs().max()) == 0
    # a redraw that comes out a little off is moved back over where it was, a fraction of a pixel too; one in place stays
    torch.manual_seed(0)
    al_before = Fc._gaussian(torch.rand(3, 1, 128, 128), 3.0).expand(3, 3, 128, 128).movedim(1, -1).contiguous()
    al_true = torch.tensor([[1.6, -2.3], [0.0, 0.0], [-0.4, 0.7]])
    al_after = Fc._moved(al_before.movedim(-1, 1), al_true[:, 0], al_true[:, 1]).movedim(1, -1)
    al_area = torch.zeros(3, 128, 128, dtype=torch.bool)
    al_area[:, 32:96, 32:96] = True
    al_fixed, al_most = Fc.align(al_before, al_after, [al_area])
    al_err = (al_fixed - al_before)[:, 40:88, 40:88].abs().amax((1, 2, 3))
    assert float(al_err.max()) < 0.01 and 2.0 < al_most < 2.5, (al_err, al_most)
    assert torch.equal(al_fixed[1], al_after[1]), "a frame in place is not resampled"
    # one redrawn a little larger or smaller is put back at its size too
    al_p = torch.tensor([[0.8, -1.2, 0.03], [0.0, 0.0, -0.025], [-0.5, 0.4, 0.0]])
    al_sized = Fc._warped(al_before.movedim(-1, 1), al_p, torch.full((3, 2), 64.0)).movedim(1, -1)
    al_back, al_edge = Fc.align(al_before, al_sized, [al_area])
    al_err3 = (al_back - al_before)[:, 40:88, 40:88].abs().amax((1, 2, 3))
    assert float(al_err3.max()) < 0.01 and al_edge > 1.5, (al_err3, al_edge)
    # two regions in one crop, off in different ways: each is moved back on its own
    al_two = al_before.clone()
    al_two[:, :, 64:] = Fc._moved(al_before.movedim(-1, 1), al_true[:, 1], al_true[:, 0]).movedim(1, -1)[:, :, 64:]
    al_left, al_right = torch.zeros(3, 128, 128, dtype=torch.bool), torch.zeros(3, 128, 128, dtype=torch.bool)
    al_left[:, 32:96, 8:52] = True
    al_right[:, 32:96, 76:120] = True
    al_mixed = al_after.clone()
    al_mixed[:, :, 64:] = al_two[:, :, 64:]
    al_both, _ = Fc.align(al_before, al_mixed, [al_left, al_right])
    al_err2 = (al_both - al_before)[:, 40:88].abs()
    assert float(al_err2[:, :, 14:46].max()) < 0.01 and float(al_err2[:, :, 82:114].max()) < 0.01, al_err2.amax((1, 3))

    # the crop holds still while the mask wobbles, and moves only when the region would near its edge
    wobble = Fc.Run({f: (200.0 + 6 * (f % 3), 120.0 + 5 * (f % 2), 260.0 + 6 * (f % 3), 180.0 + 5 * (f % 2)) for f in range(60)})
    assert len({p[:2] for p in Fc.crop_window([wobble], 2000, 2000, 768, 4.0)[1].values()}) == 1, "a mask's jitter is no reason to move"
    assert Fc._hold([0, 5, -5, 5], [10] * 4) == [0, 0, 0, 0] and Fc._hold([0, 40, 80], [10] * 3) == [10, 50, 70]
    frames, pos, shape = Fc.crop_window([walking], 2000, 2000, 768, 4.0)
    assert all(p[0] <= walking.boxes[f][0] and walking.boxes[f][2] <= p[0] + p[2] for f, p in pos.items()), "it stays in the crop"
    # latents take the frames the VAE gives them
    from types import SimpleNamespace as NS
    coder = NS(first_stage_model=NS(vae_ratio_t=4, tokens_chunk_size=5, frame_pre_padding=3))
    only = torch.zeros(22, 32, 32)
    only[5] = 1
    assert Fc.latent_area(only, (7, 2, 2), coder).amax((1, 2)).tolist() == [0, 0, 1, 0, 0, 0, 0], "frames 5-8 are the third latent"
    only[:] = 0
    only[21] = 1
    assert Fc.latent_area(only, (7, 2, 2), coder).amax((1, 2)).tolist() == [0, 0, 0, 0, 0, 0, 1], "the last takes what is left"
    assert tuple(Fc.latent_area(only, (7, 2, 2), None).shape) == (7, 2, 2)
    # a region too large for the frame still has its surroundings on the free axis, not a square slice
    huge = Fc.Run({f: (150, 10, 520, 370) for f in range(20)})
    _, hpos, hshape = Fc.crop_window([huge], H, W, 768, 1.3)
    assert hshape[1] > hshape[0] and hpos[5][3] >= H - 2 and hpos[5][2] > hpos[5][3] + 60
    # a flash is not a shot of its own, or what is in it would be left out
    flash = torch.zeros(40, 32, 32, 3)
    flash[20:] = 0.5
    flash[23:] = 0.0
    assert Fc.shot_starts(flash) == [0, 20]
    # light sweeping over a shot is no cut, though a new picture is
    scene = torch.rand(40, 32 * 8, 32 * 8, 1).expand(-1, -1, -1, 3).clone()
    scene[:] = scene[0]
    scene[20:] = (scene[20:] * 0.6 + 0.3)
    assert Fc.shot_starts(scene) == [0]
    scene[30:] = torch.rand(32 * 8, 32 * 8, 1)
    assert Fc.shot_starts(scene) == [0, 30]
    # a subject cut up by what stands in front of it is one piece, but something far off is not part of it
    cut = mask((range(20), (10, 10, 30, 40)), (range(20), (36, 10, 50, 40)), (range(20), (140, 10, 150, 20)))
    assert len(Fc.split_regions(cut, H, W)[1][5]) == 3
    labels, regions = Fc.split_regions(cut, H, W, subject=True)
    assert len(regions[5]) == 2 and len(labels[5].unique()) == 3 and len(Fc.link_regions(regions, [0])) == 2
    assert regions[5][0][1] == (40.0, 40.0, 200.0, 160.0)
    # a subject never shares a crop
    subject = Fc.Run({f: box(120, 100) for f in range(20)}, subject=1)
    assert sorted(len(g) for g in Fc.group_runs([a, b, subject])) == [1, 2]
    assert Fc.numbered({"subject_mask_2": 1, "subject_mask_1": None}) == {2: 1} and Fc.numbered(None) == {}
    text = Fc.report([subject], 16)
    assert text.startswith("subject 1:") and "redraw" in text, "a subject is redrawn whatever its size"

    # before and after: one above the other for a wide crop, side by side for a tall one, never larger than needed
    wide_, tall_ = torch.zeros(3, 8, 16, 3), torch.ones(3, 16, 8, 3)
    assert Fc.compare(wide_, wide_).shape == (3, 20, 16, 3) and Fc.compare(tall_, tall_).shape == (3, 16, 20, 3)
    # denoise takes the last steps of the sigmas, as Split Sigmas Denoise does
    sig = torch.tensor([1.0, 0.9, 0.5, 0.0])
    assert torch.equal(Fc.denoised(sig, 1.0), sig) and torch.equal(Fc.denoised(sig, 0.5), sig[1:])
    assert Fc.denoised(sig, 0.0).tolist() == [0.0], "nothing left to do"

    # node: an empty mask returns the frames untouched; a wrong mask count is an error
    frames_in = torch.zeros(60, H, W, 3)
    args = (None, None, None, frames_in, None, torch.tensor([0.7, 0.5, 0.0]), 1.0, "p", 0, 768, 4.0, 128, 0, "mask", 0.35, 0.12)
    none = Fc.H3RegionRedraw.execute(*args, masks=torch.zeros(60, 96, 168)).result
    assert none[0] is frames_in and none[1] == [] and none[2] == "nothing in the masks"
    assert Fc.H3RegionRedraw.execute(*args).result[2] == "nothing in the masks", "nothing connected is fine"
    raises(ValueError, Fc.H3RegionRedraw.execute, *args, masks=torch.zeros(9, 96, 168))
    raises(ValueError, Fc.H3RegionRedraw.execute, *args, subject_masks={"subject_mask_1": torch.zeros(9, 96, 168)})
    spare = Fc.H3RegionRedraw.execute(*args, subject_references={"subject_reference_2": torch.zeros(1, 8, 8, 3)}).result[2]
    assert "subject reference 2 has no subject mask" in spare
    print("region redraw: OK  (mask to regions, following, groups, crop window, paste, compare)")


def test_docs_and_locales():
    import json
    import re
    sys.path.insert(0, os.path.join(PKG_DIR, "tools"))
    import build_locales
    build_locales.check(pkg.NODES)  # every node / input / output documented in en + zh
    ids = {n.define_schema().node_id for n in pkg.NODES}
    for lang in ("en", "zh"):
        with open(os.path.join(PKG_DIR, "locales", lang, "nodeDefs.json"), encoding="utf-8") as f:
            defs = json.load(f)
        assert set(defs) == ids, f"{lang} nodeDefs out of date — run tools/build_locales.py"
        for nid in ids:
            assert os.path.exists(os.path.join(PKG_DIR, "web", "docs", nid, f"{lang}.md")), f"no help page {nid}"
            assert defs[nid]["description"]
    stale = {os.path.splitext(n)[0] for n in os.listdir(os.path.join(PKG_DIR, "web", "docs"))} - ids
    assert not stale, f"help pages of removed nodes: {sorted(stale)}"
    # every UI string has a Chinese version
    with open(os.path.join(PKG_DIR, "web", "arbor_common.js"), encoding="utf-8") as f:
        js = f.read()
    keys_en = set(re.findall(r'(\w+): "', js[js.index("  en: {"):js.index("  zh: {")]))
    keys_zh = set(re.findall(r'(\w+): "', js[js.index("  zh: {"):js.index("export function lang")]))
    assert keys_en - keys_zh == set(), f"untranslated UI strings: {sorted(keys_en - keys_zh)}"
    print(f"docs / locales: OK ({len(ids)} nodes × en, zh; {len(keys_en)} UI strings)")


def test_example_workflows():
    import json
    ids = {n.define_schema().node_id for n in pkg.NODES}
    folder = os.path.join(PKG_DIR, "example_workflows")
    for name in os.listdir(folder):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            w = json.load(f)
        arbor = {n["type"] for n in w["nodes"] if n["type"].startswith("Arbor_")}
        assert arbor <= ids, f"{name} uses unknown nodes {sorted(arbor - ids)}"
    print("example workflows: OK")


def test_registration():
    ids = [n.define_schema().node_id for n in pkg.NODES]
    assert len(ids) == len(set(ids)) == 34, (len(ids), len(set(ids)))
    cats = {}
    for n in pkg.NODES:
        s = n.define_schema()
        s.finalize()
        s.validate()
        assert s.node_id == f"Arbor_{n.__name__}", f"{s.node_id} is defined by class {n.__name__}"
        assert not s.is_deprecated
        cats[s.node_id] = s.category
    assert set(cats.values()) == {"Arbor/Media", "Arbor/Data", "Arbor/Tree", "Arbor/List", "Arbor/Sampling"}, set(cats.values())
    assert cats["Arbor_IndexSwitch"] == "Arbor/Data" and cats["Arbor_ConstructTree"] == "Arbor/Tree"
    print(f"registration: OK ({len(ids)} nodes)")


if __name__ == "__main__":
    for test in [test_tree_algebra, test_cross_and_rebuild, test_data_nodes, test_number_slider, test_panel,
                 test_tree_nodes, test_list_nodes, test_grasshopper_matching, test_nested_trees, test_xy_lists, test_image_grid, test_grid_layout, test_image_nodes,
                 test_compare_and_video_grid, test_load_media, test_files, test_sampling, test_region_redraw,
                 test_live_preview, test_docs_and_locales, test_example_workflows, test_registration]:
        test()
    print("ALL OK")
