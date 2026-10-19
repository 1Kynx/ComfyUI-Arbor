# ComfyUI-Arbor

Grasshopper-style **data trees**, a data **Panel**, **multi-image compare** and **XY grids** for ComfyUI.
Built on the v3 node schema; the custom widgets work in both the classic canvas and Nodes 2.0 (Vue).

> Inspired by Grasshopper. Not affiliated with Robert McNeel & Associates.

## Why trees

ComfyUI natively only has flat lists. A data tree keeps *structure*: every item lives on a path like `{0;2}`,
so "6 images" can stay "3 rows × 2 columns" all the way to your comparison sheet.

### XY plot in five nodes

```
Panel (cfg: 3 5 7) ──x─┐                ┌─ x ──► KSampler.cfg ─┐
                       ├─ XY Lists ─────┤                       ├─► VAE Decode ─► List → Tree ─► Tree → Grid
Panel (prompts) ────y──┘                ├─ y ──► CLIP Text ─────┘          ▲ shape        ▲ row / col labels
                                        └─ shape ──────────────────────────┘
```

**XY Lists** turns parameter values into every combination as aligned native lists — ordinary nodes run once
per combination — plus the grid **shape**. **List → Tree** pours the results back into rows × columns and
**Tree → Grid** draws the sheet (row labels = the x Panel, column labels = the shape).
Open *Templates → ComfyUI-Arbor → arbor_xy_sampler* and pick your checkpoint.

For finer control use the building blocks: `Tree → List` hands any tree to ordinary nodes,
`List → Tree` collects the results, `Cross Reference` builds combinations per branch.

## Nodes

| Category | Nodes |
|---|---|
| **Arbor/Image** | Image Slider · Tree → Grid · Load Folder as Tree · Save by Path · Smart Resize · Batch Pick |
| **Arbor/Data** | Panel · Number Slider · Construct Tree · Series · Range · Split Text · Prompt Template · Expression · Random |
| **Arbor/Tree** | XY Lists · Tree → List · List → Tree · Graft · Flatten · Simplify · Flip Matrix · Shift Paths · Renumber · Tree Branch · Merge · Entwine · Tree Statistics |
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

**Number Slider** — one bar: drag across it to set the value (Shift = fine), click it to type
(a value outside the range widens the range), scroll or ← → to step. Click *min*, *step* or *max* under
the bar to edit them; step 1 gives whole numbers, 0 is continuous. Outputs FLOAT and INT; live Panels
follow while you drag.

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

## Languages and help

Node names, descriptions, inputs, outputs, tooltips and the widgets' own UI text follow ComfyUI's
language setting (*Settings → Comfy → Locale*) — English and Simplified Chinese are included, other
languages fall back to English. Every node has a help page (inputs, outputs, how to use, examples)
in the **Info** tab of ComfyUI's right-side panel.

All of it is generated from `tools/node_info.py` + `tools/node_info_tree.py`:

```
python_embeded\python.exe tools\build_locales.py <path-to-ComfyUI>
```

writes `locales/<lang>/nodeDefs.json` and `web/docs/<node>/<lang>.md`; the offline tests fail when a node,
input or output is undocumented.

## Install

Clone into `ComfyUI/custom_nodes/` and restart. No extra dependencies.
Example workflows ship in `example_workflows/` (Templates → ComfyUI-Arbor): `arbor_xy_sampler` (a real XY plot — pick your checkpoint) and `arbor_xy_demo` (no model needed).

## Tests

```
python_embeded\python.exe tests\test_offline.py <path-to-ComfyUI>
```
