"""Offline tests: tree algebra + every node's execute(), no GPU or models.

Run with ComfyUI's embedded python so comfy_api / folder_paths import:

    python_embeded\\python.exe tests\\test_offline.py <path-to-ComfyUI>
"""

import importlib.util
import os
import sys
import types

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

from arbor_pkg.arbor import tree as T  # noqa: E402
from arbor_pkg.arbor import nodes_grid, nodes_image, nodes_list, nodes_panel, nodes_tree  # noqa: E402

P = T.format_path


def run(node, **kw):
    """Call execute the way ComfyUI does for is_input_list nodes."""
    schema = node.define_schema()
    if schema.is_input_list:
        kw = {k: v if isinstance(v, (list, dict)) else [v] for k, v in kw.items()}
    out = node.execute(**kw)
    return out


def res(out):
    return out.result if hasattr(out, "result") else out.args


def test_tree_algebra():
    t = T.DataTree({(0,): [1, 2, 3], (1,): [4, 5]})
    g = T.graft(t)
    assert [P(p) for p in g.paths()] == ["{0;0}", "{0;1}", "{0;2}", "{1;0}", "{1;1}"]
    assert T.shift_paths(g, -1).branches == t.branches, "shift -1 undoes graft"
    assert T.flatten(t).branches == {(0,): [1, 2, 3, 4, 5]}
    assert T.flip_matrix(t).branches == {(0,): [1, 4], (1,): [2, 5], (2,): [3]}
    s = T.simplify(T.DataTree({(0, 0, 1): ["a"], (0, 0, 2): ["b"]}))
    assert s.branches == {(1,): ["a"], (2,): ["b"]}, s.branches
    assert T.parse_path("{0; 2}") == (0, 2) and T.parse_path("") == (0,)
    assert T.parse_pattern("TFT") == [True, False, True]
    assert T.parse_pattern("true, 0") == [True, False]
    assert T.cull_pattern(t, [True, False]).branches == {(0,): [1, 3], (1,): [4]}
    assert T.partition(T.DataTree({(0,): list(range(5))}), 2).branches == {
        (0, 0): [0, 1], (0, 1): [2, 3], (0, 2): [4]}
    assert T.repeat(t, 2, "whole").branches[(1,)] == [4, 5, 4, 5]
    assert T.list_item(t, -1).branches == {(0,): [3], (1,): [5]}
    m = T.merge([t, T.DataTree({(1,): [9], (2,): [8]})])
    assert m.branches == {(0,): [1, 2, 3], (1,): [4, 5, 9], (2,): [8]}
    assert T.entwine([t, t]).paths()[2] == (1, 0)
    assert T.to_tree([1, 2]).branches == {(0,): [1, 2]}
    assert T.to_tree([t]) is t
    print("tree algebra: OK")


def test_cross_and_rebuild():
    a = T.DataTree({(0,): [3, 5]})
    b = T.DataTree({(0,): ["x", "y", "z"]})
    ca, cb = T.cross_reference(a, b)
    assert ca.branches == {(0, 0): [3, 3, 3], (0, 1): [5, 5, 5]}
    assert cb.branches == {(0, 0): ["x", "y", "z"], (0, 1): ["x", "y", "z"]}
    flat = ca.flat()
    back = T.rebuild([f"img{i}" for i in range(len(flat))], ca)
    assert back.branches[(0, 1)] == ["img3", "img4", "img5"]
    try:
        T.rebuild([1], ca)
        raise AssertionError("mismatch should raise")
    except ValueError:
        pass
    print("cross reference / rebuild: OK")


def test_nodes():
    tr = res(run(nodes_tree.NumberSeries, start=1.0, step=0.5, count=4, as_int=False))[0]
    assert tr.branches == {(0,): [1.0, 1.5, 2.0, 2.5]}
    rg = res(run(nodes_tree.NumberRange, start=0.0, end=10.0, steps=2, as_int=True))[0]
    assert rg.branches == {(0,): [0, 5, 10]}
    st = res(run(nodes_tree.SplitText, text="cat\ndog\n\nred, blue", separator="newline",
                 blank_line_branches=True, strip=True))[0]
    assert st.branches == {(0,): ["cat", "dog"], (1,): ["red, blue"]}
    st2 = res(run(nodes_tree.SplitText, text="red, blue", separator=",",
                  blank_line_branches=True, strip=True))[0]
    assert st2.branches == {(0,): ["red", "blue"]}

    items, count = res(run(nodes_tree.TreeToList, tree=[tr]))
    assert items == [1.0, 1.5, 2.0, 2.5] and count == 4
    assert nodes_tree.TreeToList.define_schema().outputs[0].is_output_list
    back = res(run(nodes_tree.ListToTree, list=["a", "b", "c", "d"], shape=[T.partition(tr, 2)],
                   split_batch=False))[0]
    assert back.branches == {(0, 0): ["a", "b"], (0, 1): ["c", "d"]}

    g = res(run(nodes_tree.Graft, tree=[tr]))[0]
    assert g.branch_count == 4
    f = res(run(nodes_tree.Flatten, tree=[g], path="{3}"))[0]
    assert f.paths() == [(3,)]
    sp = res(run(nodes_tree.ShiftPaths, tree=[g], offset=-1))[0]
    assert sp.branches == tr.branches
    br = res(run(nodes_tree.TreeBranch, tree=[g], path="{0;2}", index=0))[0]
    assert br.branches == {(0, 2): [2.0]}
    br2 = res(run(nodes_tree.TreeBranch, tree=[g], path="", index=-1))[0]
    assert br2.paths() == [(0, 3)]
    mg = res(run(nodes_tree.MergeTrees, trees={"tree0": [tr], "tree1": [5, 6]}))[0]
    assert mg.branches == {(0,): [1.0, 1.5, 2.0, 2.5, 5, 6]}
    ew = res(run(nodes_tree.Entwine, trees={"tree0": [tr], "tree1": [5, 6]}))[0]
    assert ew.paths() == [(0, 0), (1, 0)]
    info = res(run(nodes_tree.TreeInfo, tree=[g]))
    assert info[:3] == (4, 4, 2) or list(info[:3]) == [4, 4, 2]
    ct = res(run(nodes_tree.ConstructTree, data=[torch.zeros(3, 8, 8, 3)], path="{1}", split_batch=True))[0]
    assert ct.paths() == [(1,)] and len(ct.branches[(1,)]) == 3

    a, b = res(run(nodes_list.Dispatch, tree=[tr], pattern="T F"))
    assert a.branches[(0,)] == [1.0, 2.0] and b.branches[(0,)] == [1.5, 2.5]
    cx, cy = res(run(nodes_list.CrossReference, A=[tr], B=[st2], group=True))
    assert cx.branch_count == 4 and cy.item_count == 8
    sl = res(run(nodes_list.SubList, tree=[tr], start=1, end=-1))[0]
    assert sl.branches[(0,)] == [1.5, 2.0, 2.5]
    so = res(run(nodes_list.Sort, tree=[T.DataTree({(0,): [3, "b", 1, "a"]})], descending=False))[0]
    assert so.branches[(0,)] == [1, 3, "a", "b"]
    for node in (nodes_list.ListItem, nodes_list.CullPattern, nodes_list.Partition,
                 nodes_list.Repeat, nodes_list.Reverse):
        node.define_schema()
    print("tree / list nodes: OK")


def test_panel_slider_grid():
    img = torch.rand(2, 32, 48, 3)
    tree = T.DataTree({(0, 0): [1, 2.5, "hi"], (0, 1): [img, None, True]})
    out = run(nodes_panel.Panel, data=[tree])
    payload = out.ui["arbor_panel"][0]
    assert payload["kind"] == "tree" and payload["stats"]["items"] == 6
    br1 = payload["branches"][1]
    assert br1["path"] == "{0;1}" and br1["items"][0]["t"] == "image" and "img" in br1["items"][0]
    assert br1["items"][0]["v"] == "Image 48×32 ×2"
    assert res(out)[0] == [tree], "panel passes data through"
    flat = run(nodes_panel.Panel, data=[1, 2, 3]).ui["arbor_panel"][0]
    assert flat["kind"] == "list" and flat["stats"]["items"] == 3
    assert res(out)[1] is tree, "tree output is the input tree"

    # unconnected: typed text, Grasshopper style
    typed = run(nodes_panel.Panel, text="a cat\n7\n3.5\n\n  \n-2\nnot 1", parse_numbers=True, multiline=False)
    values, ttree = res(typed)
    assert ttree.branches == {(0,): ["a cat", 7, 3.5], (1,): [-2, "not 1"]}, ttree.branches
    assert values == ["a cat", 7, 3.5, -2, "not 1"]
    assert typed.ui["arbor_panel"][0]["source"] == "text"
    raw = res(run(nodes_panel.Panel, text="7\n8", parse_numbers=False, multiline=False))[1]
    assert raw.branches == {(0,): ["7", "8"]}
    one = res(run(nodes_panel.Panel, text="line 1\n\nline 2", parse_numbers=True, multiline=True))
    assert one[0] == ["line 1\n\nline 2"]
    empty = res(run(nodes_panel.Panel, text="", parse_numbers=True, multiline=False))
    assert empty[0] == [""], "empty panel still emits one item"

    cmp_ = run(nodes_image.ImageSlider,
               images={"image0": [img], "image1": [torch.rand(1, 64, 64, 3)]}).ui["arbor_slider"][0]
    assert [s["label"] for s in cmp_["slides"]] == ["image0 · 1/2", "image0 · 2/2", "image1"]
    assert cmp_["slides"][2]["w"] == 64

    a = T.DataTree({(0,): [3, 5]})
    b = T.DataTree({(0,): ["cat", "一只猫在雨中"]})
    ca, cb = T.cross_reference(a, b)
    imgs = T.rebuild([torch.rand(1, 40 + 8 * i, 60, 3) for i in range(4)], ca)
    grid = res(run(nodes_grid.TreeToGrid, images=[imgs], row_labels=[a], col_labels=[b], fit="fit",
                   cell_size=0, gap=8, font_size=16, theme="light", path_labels=False))[0]
    assert grid.dim() == 4 and grid.shape[0] == 1 and grid.shape[-1] == 3
    # 2 rows x 2 cols of 56x60 cells + labels
    assert grid.shape[2] > 2 * 60 and grid.shape[1] > 2 * 56, grid.shape
    plain = res(run(nodes_grid.TreeToGrid, images=[torch.rand(1, 16, 16, 3), torch.rand(3, 16, 16, 3)],
                    fit="original", cell_size=0, gap=0, font_size=12, theme="dark", path_labels=False))[0]
    assert plain.shape[2] == 4 * 16, plain.shape  # one row, batch expanded to columns
    print("panel / slider / grid: OK")


def test_live_preview():
    from arbor_pkg.arbor import live
    mapping = {n.define_schema().node_id: n for n in pkg.NODES}
    live._mappings = lambda: mapping
    assert "Arbor_ImageSlider" not in live.safe_types() and "Arbor_Panel" in live.safe_types()
    prompt = {
        "1": {"class_type": "Arbor_Panel", "inputs": {"text": "a\nb\n\n3", "parse_numbers": True,
                                                       "multiline": False}},
        "2": {"class_type": "Arbor_Series", "inputs": {"start": 1.0, "step": 1.0, "count": 2, "as_int": True,
                                                        "control_after_generate": "fixed"}},
        "3": {"class_type": "Arbor_Merge", "inputs": {"trees.tree0": ["1", 1], "trees.tree1": ["2", 0]}},
        "4": {"class_type": "Arbor_Panel", "inputs": {"data": ["3", 0], "text": "", "parse_numbers": True,
                                                       "multiline": False}},
        "5": {"class_type": "Arbor_Panel", "inputs": {"data": ["1", 0], "text": "", "parse_numbers": True,
                                                       "multiline": False}},
    }
    p = live.evaluate(prompt, "4")
    assert p["live"] and p["kind"] == "tree"
    assert [(b["path"], [i["v"] for i in b["items"]]) for b in p["branches"]] == [
        ("{0}", ["a", "b", "1", "2"]), ("{1}", ["3"])], p["branches"]
    flat = live.evaluate(prompt, "5")
    assert flat["kind"] == "list" and flat["stats"]["items"] == 3
    prompt["6"] = {"class_type": "KSampler", "inputs": {}}
    prompt["7"] = {"class_type": "Arbor_Panel", "inputs": {"data": ["6", 0]}}
    try:
        live.evaluate(prompt, "7")
        raise AssertionError("KSampler must not run live")
    except live.Unsupported as e:
        assert e.class_type == "KSampler"
    print("live preview: OK")


def test_v02_nodes():
    import tempfile
    import folder_paths
    from PIL import Image
    from arbor_pkg.arbor import expr as E, nodes_data, nodes_files, nodes_util

    # Prompt Template
    a = T.DataTree({(0,): ["cat", "dog"]})
    b = T.DataTree({(0,): ["oil", "ink", "pixel"]})
    cross = res(run(nodes_data.PromptTemplate, template="{a} in {b} style", mode="cross",
                    vars={"a": [a], "b": [b]}))[0]
    assert cross.branches == {(0,): ["cat in oil style", "cat in ink style", "cat in pixel style"],
                              (1,): ["dog in oil style", "dog in ink style", "dog in pixel style"]}
    z = res(run(nodes_data.PromptTemplate, template="{a}/{b}/{c}", mode="zip",
                vars={"a": [a], "b": [b]}))[0]
    assert z.branches == {(0,): ["cat/oil/{c}", "dog/ink/{c}", "dog/pixel/{c}"]}, z.branches
    one = res(run(nodes_data.PromptTemplate, template="{a}!", mode="cross", vars={"a": [7, 8]}))[0]
    assert one.branches == {(0,): ["7!", "8!"]}

    # Expression
    xs = T.DataTree({(0,): [1, 2, 3], (1,): [10]})
    r = res(run(nodes_data.Expression, expression="x * 2 + i", x=[xs]))[0]
    assert r.branches == {(0,): [2, 5, 8], (1,): [20]}
    r = res(run(nodes_data.Expression, expression="x + y", x=[xs], y=[T.DataTree({(0,): [100]})]))[0]
    assert r.branches == {(0,): [101, 102, 103], (1,): [110]}, "longest-list matching"
    r = res(run(nodes_data.Expression, expression="upper(x) if len(x) > 2 else x", x=["ab", "cat"]))[0]
    assert r.branches == {(0,): ["ab", "CAT"]}
    for bad in ["__import__('os')", "x.__class__", "(lambda: 1)()", "9 ** 9 ** 9", "'a' * 10**7"]:
        try:
            res(run(nodes_data.Expression, expression=bad, x=[1]))
            raise AssertionError(f"should reject {bad}")
        except E.ExprError:
            pass

    # Random: deterministic per seed
    t = T.DataTree({(0,): list(range(20))})
    r1 = res(run(nodes_data.RandomPick, tree=[t], mode="pick", count=5, seed=42, per_branch=True))[0]
    r2 = res(run(nodes_data.RandomPick, tree=[t], mode="pick", count=5, seed=42, per_branch=True))[0]
    assert r1.branches == r2.branches and len(r1.branches[(0,)]) == 5
    sh = res(run(nodes_data.RandomPick, tree=[t], mode="shuffle", count=1, seed=1, per_branch=True))[0]
    assert sorted(sh.branches[(0,)]) == list(range(20))

    # Load Folder / Save by Path round trip in a temp dir
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
        assert count == 7 and folders.branches[(0,)] == ["src", "a", "b2", "b10"], folders.branches
        assert names.branches[(1,)] == ["img0", "img1"] and imgs.branches[(2,)][2].shape == (1, 8, 18, 3)
        assert nodes_files.LoadFolder.fingerprint_inputs(src, "*.png", True, "name", 0)
        lim = res(nodes_files.LoadFolder.execute(folder=src, pattern="*.png", subfolders=True,
                                                 sort="name", limit=3))[3]
        assert lim == 3

        out = os.path.join(d, "out")
        os.makedirs(out)
        old = folder_paths.get_output_directory()
        folder_paths.set_output_directory(out)
        try:
            saved = run(nodes_files.SaveByPath, images=[imgs], filename_prefix="xy/run",
                        layout="subfolders", names=[names])
            paths = res(saved)[0]
            assert os.path.basename(paths.branches[(1,)][1]) == "img1.png"
            assert os.path.basename(os.path.dirname(paths.branches[(2,)][0])) == "run_2"
            again = res(run(nodes_files.SaveByPath, images=[imgs], filename_prefix="xy/run",
                            layout="flat"))[0]
            assert os.path.basename(again.branches[(0,)][0]) == "run_0_000.png"
            assert saved.ui["images"][0]["subfolder"].replace("\\", "/") == "xy/run_0"
        finally:
            folder_paths.set_output_directory(old)

    # Smart Resize / Batch Pick
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

    # Index Switch: lazy status asks only for the chosen, connected input
    ins = {"input0": (None, "inputs.input0"), "input1": (None, "inputs.input1"), "input2": (None, "inputs.input2")}
    assert nodes_util.IndexSwitch.check_lazy_status(1, ins) == ["inputs.input1"]
    assert nodes_util.IndexSwitch.check_lazy_status(-1, ins) == ["inputs.input2"]
    o = res(nodes_util.IndexSwitch.execute(4, {"input0": "a", "input1": "b"}))
    assert o == ("a", 2) or list(o) == ["a", 2]
    print("v0.2 nodes: OK")


def test_v03_booleans_slider_text():
    from arbor_pkg.arbor import nodes_data, nodes_util
    from arbor_pkg.arbor.preview import PANEL_MAX_CHARS

    t = T.DataTree({(0,): [1, 2, 3, 4], (1,): [5, 6]})
    # typed text still works
    assert res(run(nodes_list.CullPattern, tree=[t], pattern="T F"))[0].branches == {(0,): [1, 3], (1,): [5]}
    # a single native BOOLEAN
    assert res(run(nodes_list.CullPattern, tree=[t], pattern=[False]))[0].branches == {(0,): [], (1,): []}
    # a native list of BOOLEANs repeats like a typed pattern
    assert res(run(nodes_list.CullPattern, tree=[t], pattern=[True, True, False]))[0].branches == {
        (0,): [1, 2, 4], (1,): [5, 6]}
    # a boolean tree is matched branch by branch (e.g. from Expression "x > 2")
    mask = res(run(nodes_data.Expression, expression="x > 2", x=[t]))[0]
    a, b = res(run(nodes_list.Dispatch, tree=[t], pattern=[mask]))
    assert a.branches == {(0,): [3, 4], (1,): [5, 6]} and b.branches == {(0,): [1, 2], (1,): []}
    assert T.to_bool("TRUE") and not T.to_bool(0) and not T.to_bool("off")
    try:
        T.to_bool("maybe")
        raise AssertionError("non-boolean text must fail")
    except ValueError:
        pass
    sch = nodes_list.CullPattern.define_schema()
    pat = [i for i in sch.inputs if i.id == "pattern"][0]
    assert "BOOLEAN" in pat.get_io_type() and "STRING" in pat.get_io_type()
    # Index Switch takes a BOOLEAN as index
    assert res(nodes_util.IndexSwitch.execute(True, {"input0": "off", "input1": "on"}))[0] == "on"

    # Panel typed true / false
    tt = res(run(nodes_panel.Panel, text="true\nFalse\nTRUE\ntrue-ish", parse_numbers=True, multiline=False))[1]
    assert tt.branches == {(0,): [True, False, True, "true-ish"]}, tt.branches

    # Number Slider clamps, rounds and swaps a reversed range
    v, i = res(nodes_data.NumberSlider.execute(value=7.3456, min=0.0, max=5.0, decimals=2))
    assert (v, i) == (5.0, 5)
    v, i = res(nodes_data.NumberSlider.execute(value=0.3456, min=1.0, max=0.0, decimals=2))
    assert (v, i) == (0.35, 0)
    v, i = res(nodes_data.NumberSlider.execute(value=2.6, min=0.0, max=10.0, decimals=0))
    assert (v, i) == (3.0, 3)

    # long text reaches the Panel in full up to the limit, and is flagged when cut
    long = "x" * (PANEL_MAX_CHARS + 50)
    p = run(nodes_panel.Panel, data=["short", long]).ui["arbor_panel"][0]
    rows = p["branches"][0]["items"]
    assert rows[0]["v"] == "short" and "len" not in rows[0]
    assert len(rows[1]["v"]) == PANEL_MAX_CHARS and rows[1]["len"] == PANEL_MAX_CHARS + 50
    print("v0.3 booleans / slider / long text: OK")


def test_review_fixes():
    from arbor_pkg.arbor import nodes_data
    t = T.DataTree({(0,): [1, 2]})
    # the trailing empty Autogrow slot arrives as [None] in a real run
    m = res(run(nodes_tree.MergeTrees, trees={"tree0": [t], "tree1": [5], "tree2": [None]}))[0]
    assert m.branches == {(0,): [1, 2, 5]}, m.branches
    e = res(run(nodes_tree.Entwine, trees={"tree0": [t], "tree1": [t], "tree2": [None]}))[0]
    assert e.paths() == [(0, 0), (1, 0)], e.paths()
    pt = res(run(nodes_data.PromptTemplate, template="{a}-{b}", mode="cross",
                 vars={"a": ["x"], "b": [None], "c": [None]}))[0]
    assert pt.branches == {(0,): ["x-{b}"]}, pt.branches

    # grid labels straight from Cross Reference outputs
    a = T.DataTree({(0,): [256, 384, 512]})
    b = T.DataTree({(0,): ["red", "blue"]})
    ca, cb = T.cross_reference(a, b)
    assert nodes_grid.row_labels_for([ca], 3) == ["256", "384", "512"]
    assert nodes_grid.col_labels_for([cb], 2) == ["red", "blue"]
    assert nodes_grid.row_labels_for([a], 3) == ["256", "384", "512"], "plain list still works"
    assert nodes_grid.col_labels_for([b], 2) == ["red", "blue"]
    imgs = T.rebuild([torch.rand(1, 8, 8, 3) for _ in range(6)], ca)
    g1 = res(run(nodes_grid.TreeToGrid, images=[imgs], row_labels=[ca], col_labels=[cb], fit="fit",
                 cell_size=0, gap=2, font_size=10, theme="light", path_labels=False))[0]
    g2 = res(run(nodes_grid.TreeToGrid, images=[imgs], row_labels=[a], col_labels=[b], fit="fit",
                 cell_size=0, gap=2, font_size=10, theme="light", path_labels=False))[0]
    assert torch.equal(g1, g2), "cross-reference labels render exactly like the originals"
    print("review fixes: OK")


def test_registration():
    ids = [n.define_schema().node_id for n in pkg.NODES]
    assert len(ids) == len(set(ids)), "duplicate node ids"
    assert all(i.startswith("Arbor_") for i in ids)
    for n in pkg.NODES:
        s = n.define_schema()
        s.finalize()
        s.validate()
    print(f"registration: OK ({len(ids)} nodes)")


if __name__ == "__main__":
    test_tree_algebra()
    test_cross_and_rebuild()
    test_nodes()
    test_panel_slider_grid()
    test_live_preview()
    test_v02_nodes()
    test_v03_booleans_slider_text()
    test_review_fixes()
    test_registration()
    print("ALL OK")
