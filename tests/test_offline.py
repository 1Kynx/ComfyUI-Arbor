"""Offline tests: tree algebra + every node's execute(), no GPU or models.

Run with ComfyUI's embedded python so comfy_api / folder_paths import:

    python_embeded\\python.exe tests\\test_offline.py <path-to-ComfyUI>
"""

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

from arbor_pkg.arbor import grid, live, nodes_data, nodes_files, nodes_image, nodes_list, nodes_panel, \
    nodes_tree  # noqa: E402
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
    one = res(run(nodes_data.PromptTemplate, template="{a}!", mode="cross", vars={"a": [7, 8]}))[1]
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

def test_nested_trees():
    """character -> outfit -> pose: parents name their groups and pair with their children."""
    chars = res(run(nodes_panel.Panel, text="# Mira\nbotanist\nraincoat\nlab coat\n\n# Theo\nbaker\njacket",
                    parse_numbers=False, multiline=False))[1]
    first = lambda spec: res(run(nodes_list.ListItem, tree=[chars], index=spec, wrap=True))[0]
    desc, outfits = first("0"), first("1:")
    assert outfits.branches == {(0,): ["raincoat", "lab coat"], (1,): ["jacket"]} and outfits.names == chars.names
    ca, cb = res(run(nodes_list.CrossReference, A=[outfits], B=["front", "side"], group=True))
    assert ca.paths() == [(0, 0), (0, 1), (1, 0)]
    assert ca.label((0, 1)) == "Mira · lab coat", "the parent keeps its name, the sub-branch is named after A"
    # {0} Mira's description goes with every {0;i} of Mira's outfits — matched by path, not by index
    who = res(run(nodes_data.Expression, expression='y + " in " + x', x=[ca], y=[desc]))[1]
    assert who.branches[(1, 0)] == ["baker in jacket"] * 2, who.branches
    full = res(run(nodes_data.Expression, expression='x + ", " + y', x=[who], y=[cb]))[1]
    assert full.branches[(0, 1)] == ["botanist in lab coat, front", "botanist in lab coat, side"]
    # flatten for the sampler, then put the results back and regroup per character
    x, *_, shape, n = res(run(nodes_tree.XYLists, x=[full], mode="cross"))
    assert n == 6 and shape.label((0, 0)) == "Mira · raincoat"
    imgs = res(run(nodes_tree.ConstructTree, data=[f"img{k}" for k in range(n)], path="{0}", split_batch=False,
                   shape=[shape]))[0]
    per_char = res(run(nodes_tree.ReshapeTree, tree=[imgs], mode={"mode": ["shift paths"], "offset": [-1]}))[0]
    assert per_char.branches == {(0,): ["img0", "img1", "img2", "img3"], (1,): ["img4", "img5"]}
    assert per_char.names == {(0,): "Mira", (1,): "Theo"}, "shifting back up lands on the named parents"
    # graft / entwine / renumber carry names too
    assert T.graft(chars).label((1, 0)) == "Theo"
    assert T.entwine([outfits, outfits]).label((1, 0)) == "Mira"
    assert T.renumber(ca).names[(1,)] == "Mira · lab coat"
    # a boolean tree on the parent masks all of its children (Dispatch)
    keep, _ = res(run(nodes_list.Dispatch, tree=[ca], pattern=[T.DataTree({(0,): [True], (1,): [False]})]))
    assert keep.item_count == 4 and keep.branches[(1, 0)] == []
    # Image Grid rows read "Mira · raincoat"; row labels from another tree use its branch names
    assert grid.row_labels_for([desc], 2) == ["Mira", "Theo"]
    # Expression knows the branch name: per-shot file names from the structure
    files = res(run(nodes_data.Expression, expression='name + "/shot_" + str(i + 1)', x=[outfits]))[0]
    assert files == ["Mira/shot_1", "Mira/shot_2", "Theo/shot_1"], files
    # pictures cross-referenced with edits: sub-branches are numbered, not named "Image 8×8"
    pics = T.DataTree({(0,): [torch.rand(1, 8, 8, 3), torch.rand(1, 8, 8, 3)]}, {(0,): "Arrival"})
    pa, pb = res(run(nodes_list.CrossReference, A=[pics], B=["snow", "ink"], group=True))
    assert [pa.label(p) for p in pa.paths()] == ["Arrival · 1", "Arrival · 2"] and pb.branches[(0, 1)] == ["snow", "ink"]
    # Cross Reference pairs branches by path too: B's {2} goes with A's {2}, not with A's 2nd branch
    shots = T.DataTree({(0,): ["s0"], (2,): ["s2"]})
    edits = T.DataTree({(0,): ["e0"], (1,): ["e1"], (2,): ["e2a", "e2b"]})
    sa, sb = res(run(nodes_list.CrossReference, A=[shots], B=[edits], group=False))
    assert sb.branches == {(0,): ["e0"], (1,): ["e1"], (2,): ["e2a", "e2b"]} and sa.branches[(2,)] == ["s2", "s2"]
    sa, sb = res(run(nodes_list.CrossReference, A=[edits], B=[shots], group=False))
    assert sb.branches[(1,)] == ["s2"] and sb.branches[(2,)] == ["s2", "s2"], "an unmatched path falls back to order"
    # an unconnected x that arrives as [None] still gives one constant result
    assert res(run(nodes_data.Expression, expression="1 + 1", x=[None]))[0] == [2]
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
    print("image nodes: OK")


def test_files():
    import tempfile
    import folder_paths
    from PIL import Image

    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src")
        for sub, n in (("a", 2), ("b10", 1), ("b2", 3)):
            os.makedirs(os.path.join(src, sub))
            for k in range(n):
                Image.new("RGB", (16 + k, 8), (k * 40, 0, 0)).save(os.path.join(src, sub, f"img{k}.png"))
        Image.new("RGB", (4, 4)).save(os.path.join(src, "root.png"))
        open(os.path.join(src, "notes.txt"), "w").close()
        imgs, names, folders, count = res(nodes_files.LoadFolder.execute(
            folder=src, pattern="*.png", subfolders=True, sort="name", limit=0))
        assert count == 7 and folders == ["src", "a", "b2", "b10"], folders  # plain data, one per branch
        assert list(imgs.names.values()) == folders and names.names == imgs.names, "branches named after folders"
        assert names.branches[(1,)] == ["img0", "img1"] and imgs.branches[(2,)][2].shape == (1, 8, 18, 3)
        assert nodes_files.LoadFolder.fingerprint_inputs(src, "*.png", True, "name", 0)
        assert res(nodes_files.LoadFolder.execute(folder=src, pattern="*.png", subfolders=True,
                                                  sort="name", limit=3))[3] == 3

        out = os.path.join(d, "out")
        os.makedirs(out)
        old = folder_paths.get_output_directory()
        folder_paths.set_output_directory(out)
        try:
            saved = run(nodes_files.SaveImagesByPath, images=[imgs], filename_prefix="xy/run",
                        layout="subfolders", names=[names])
            paths = res(saved)[0]
            rel = lambda p: os.path.relpath(p, out).replace("\\", "/")
            assert os.path.basename(paths.branches[(1,)][1]) == "img1.png"
            assert rel(os.path.dirname(paths.branches[(2,)][0])) == "xy/run/2 · b2", "the prefix holds the tree"
            assert saved.ui["images"][0]["subfolder"].replace("\\", "/") == "xy/run/0 · src"
            # ... and Load Folder reads it back, names and all ('output/…' is the output folder)
            back, _, back_folders, back_count = res(nodes_files.LoadFolder.execute(
                folder="output/xy/run", pattern="*.png", subfolders=True, sort="name", limit=0))
            assert back_count == 7 and back_folders == folders and back.names == imgs.names
            plain = res(run(nodes_files.SaveImagesByPath, images=[T.DataTree({(0, 1): [imgs.branches[(1,)][0]]})],
                            filename_prefix="xy/plain", layout="subfolders"))[0]
            assert rel(plain.branches[(0, 1)][0]) == "xy/plain/0-1/000.png", "unnamed branches: just the path"
            again = res(run(nodes_files.SaveImagesByPath, images=[imgs], filename_prefix="xy/run",
                            layout="flat"))[0]
            assert os.path.basename(again.branches[(0,)][0]) == "run_0 · src_000.png"
            assert nodes_files.folder_label("2 · Night market") == "Night market"
            assert nodes_files.folder_label("2024 photos") == "2024 photos", "only the saved tag is dropped"
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
    assert len(ids) == len(set(ids)) == 26, (len(ids), len(set(ids)))
    cats = {}
    for n in pkg.NODES:
        s = n.define_schema()
        s.finalize()
        s.validate()
        assert s.node_id == f"Arbor_{n.__name__}", f"{s.node_id} is defined by class {n.__name__}"
        assert not s.is_deprecated
        cats[s.node_id] = s.category
    assert set(cats.values()) == {"Arbor/Image", "Arbor/Data", "Arbor/Tree", "Arbor/List"}, set(cats.values())
    assert cats["Arbor_IndexSwitch"] == "Arbor/Data" and cats["Arbor_ConstructTree"] == "Arbor/Tree"
    print(f"registration: OK ({len(ids)} nodes)")


if __name__ == "__main__":
    for test in [test_tree_algebra, test_cross_and_rebuild, test_data_nodes, test_number_slider, test_panel,
                 test_tree_nodes, test_list_nodes, test_nested_trees, test_xy_lists, test_image_grid, test_image_nodes, test_files,
                 test_live_preview, test_docs_and_locales, test_example_workflows, test_registration]:
        test()
    print("ALL OK")
