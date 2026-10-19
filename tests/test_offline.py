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


def test_panel_compare_grid():
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

    cmp_ = run(nodes_image.ImageCompare,
               images={"image0": [img], "image1": [torch.rand(1, 64, 64, 3)]}).ui["arbor_compare"][0]
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
    print("panel / compare / grid: OK")


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
    test_panel_compare_grid()
    test_registration()
    print("ALL OK")
