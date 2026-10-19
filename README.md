# ComfyUI-Arbor

Grasshopper-style **data trees**, a data **Panel**, **multi-image compare** and **XY grids** for ComfyUI.
Built on the v3 node schema; the custom widgets work in both the classic canvas and Nodes 2.0 (Vue).

> Inspired by Grasshopper. Not affiliated with Robert McNeel & Associates.

## Why trees

ComfyUI natively only has flat lists. A data tree keeps *structure*: every item lives on a path like `{0;2}`,
so "6 images" can stay "3 rows × 2 columns" all the way to your comparison sheet.

```
Series (cfg) ─┐                     ┌─ Tree → List ─► KSampler.cfg ─┐
              ├─ Cross Reference ──┤                                ├─► VAE Decode ─► List → Tree ─► Tree → Grid
Split Text ───┘   (rows = A)        └─ Tree → List ─► CLIP Text ────┘        (shape = A)       (rows × cols)
```

`Tree → List` hands a native list to ordinary nodes (they run once per item);
`List → Tree` pours the results back into the original branches.

## Nodes

| Category | Nodes |
|---|---|
| **Arbor/Image** | Image Slider · Tree → Grid · Load Folder as Tree · Save by Path · Smart Resize · Batch Pick |
| **Arbor/Data** | Panel · Number Slider · Construct Tree · Series · Range · Split Text · Prompt Template · Expression · Random |
| **Arbor/Tree** | Tree → List · List → Tree · Graft · Flatten · Simplify · Flip Matrix · Shift Paths · Renumber · Tree Branch · Merge · Entwine · Tree Statistics |
| **Arbor/List** | List Item · Sub List · Cull Pattern · Dispatch · Partition · Repeat · Reverse List · Sort List · Cross Reference |
| **Arbor/Util** | Index Switch |

**Image Slider** — connect any number of images (inputs grow as you connect) of any size.
*Flip*: drag the scrubber or press ← → to step through them. *Wipe*: A/B split that follows the pointer.
*Real* keeps relative sizes, *Fit* fills the stage. Double-click opens the full image.

**Panel** — works both ways, like Grasshopper's panel.
*Connected*: a viewer. Trees show collapsible branches with paths and counts, images show thumbnails,
long text folds to four lines (*more* unfolds it), every item has its own copy button, and ⤢ opens a
large view. Data passes through unchanged.
When everything upstream is a lightweight data node (Arbor data/tree/list nodes, core primitives,
string and math nodes) the view updates **live** as you edit — no run needed (green dot).
Anything heavier upstream (samplers, loaders, …) never runs on its own; the Panel then shows the last run.
*Unconnected*: type data in. **Lines** mode: each line is an item, an empty line starts a new branch,
and a gutter shows every line's branch path and index (coloured by type). **Text** mode: the whole text
is one item. **123 / abc** toggles reading values (`7` → INT, `3.5` → FLOAT, `true` → BOOLEAN).
Long lines wrap; ⤢ opens a large editor; Ctrl+Enter still queues. Outputs `data` (native list) and `tree`.

**Number Slider** — drag between min and max (Shift = fine, scroll or ← → to step). Double-click the
value to type it, click min / max to change the range, click *step* to change precision.
Outputs FLOAT and INT; live Panels follow while you drag.

**True / false** — pattern inputs (Cull Pattern, Dispatch) take typed text (`T F`), a native BOOLEAN,
a list of BOOLEANs, or a boolean tree such as Expression `x > 2` (matched branch by branch).
Index Switch takes a BOOLEAN as its index (False = 0, True = 1).

**Prompt Template** — `a photo of {a}, {b}` filled from trees. *Cross* builds every combination as a
grid-ready tree (rows = `{a}`, columns = the last variable); *zip* pairs items one by one.

**Expression** — per-item formula like `x * 2 + i` or `upper(x) if len(x) > 2 else x`.
Names: `x`, `y` (matched longest-list), `i` item index, `b` branch index, `n` branch length.
A safe evaluator: no attribute access or imports.

**Load Folder as Tree / Save by Path** — subfolders become branches on the way in; branch paths become
subfolders (or filename parts) on the way out, with optional names per file.

**Smart Resize** — longest / shortest side, megapixels, fit, fill & crop or scale; snaps to multiples of
8/16/32/64. Only the fields for the chosen mode are shown.

**Index Switch** — pick input N; unselected inputs are lazy and never execute.

Every tree input also accepts plain values or native lists (they become branch `{0}`).

## Install

Clone into `ComfyUI/custom_nodes/` and restart. No extra dependencies.
An example workflow ships in `example_workflows/` (Templates → ComfyUI-Arbor).

## Tests

```
python_embeded\python.exe tests\test_offline.py <path-to-ComfyUI>
```
