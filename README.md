# ComfyUI-Arbor

Grasshopper-style **data trees**, a data **Panel**, **multi-image compare** and **XY grids** for ComfyUI.
Built on the v3 node schema; the custom widgets work in both the classic canvas and Nodes 2.0 (Vue).

> Inspired by Grasshopper. Not affiliated with Robert McNeel & Associates.

## Why trees

ComfyUI natively only has flat lists. A data tree keeps *structure*: every item lives on a path like `{0;2}`,
so "6 images" can stay "3 rows × 2 columns" all the way to your comparison sheet.

### XY plot in four nodes

```
Panel (cfg: 3 5 7) ──x─┐                ┌─ x ──► KSampler.cfg ─┐
                       ├─ XY Lists ─────┤                       ├─► VAE Decode ─► Image Grid
Panel (prompts) ────y──┘                ├─ y ──► CLIP Text ─────┘                    ▲ shape
                                        └─ shape ────────────────────────────────────┘
```

**XY Lists** turns parameter values into every combination as aligned plain data — ordinary nodes run once
per combination — plus the **shape** of the runs. **Image Grid** takes the decoded images and that shape and
draws the sheet as rows × columns, already labelled: the shape names every row after its x value and holds
the y values as columns.
Open *Templates → ComfyUI-Arbor → arbor_xy_sampler* and pick your checkpoint.

### Trees and plain data

There are no conversion nodes to remember. Every tree input accepts plain values and native lists (they
become branch `{0}`); nodes that produce trees also output their items as plain `data`, so ordinary
nodes run once per item. To run something per item and keep the branches: **XY Lists** with only *x*
connected flattens a tree and outputs its shape, and **Construct Tree** (or **Image Grid**) with that
*shape* puts the results back into the same branches.

## Nodes

| Category | Nodes |
|---|---|
| **Arbor/Image** | Image Slider · Image Grid · Load Folder · Save Images by Path · Smart Resize · Batch Pick |
| **Arbor/Data** | Panel · Number Slider · Number Sequence · Split Text · Prompt Template · Expression · Random · Index Switch |
| **Arbor/Tree** | XY Lists · Construct Tree · Reshape Tree · Tree Branch · Merge · Tree Statistics |
| **Arbor/List** | List Item · Dispatch · Partition · Repeat · Sort List · Cross Reference |

*Image*: viewing, gridding, loading, saving and resizing images. *Data*: where values come from (typed,
slid, generated, computed) and which one goes on. *Tree*: building, reshaping and flattening trees. *List*: the same operation on every branch.

Grasshopper's tree operations are grouped by what they do instead of one node each: **Reshape Tree** is Graft,
Flatten, Simplify, Flip Matrix, Shift Paths and Renumber (pick the mode); **Merge** also entwines; **List Item**
takes `0`, `-1`, `0, 2`, `1:4`, `2-5` or `::2`, so it covers Sub List; **Sort List** also reverses.
Searching for any of the Grasshopper names finds the right node.

**Image Slider** — connect any number of images (inputs grow as you connect) of any size.
*Flip*: drag the scrubber or press ← → to step through them. *Wipe*: A/B split that follows the pointer.
*Real* keeps relative sizes, *Fit* fills the stage. Double-click opens the full image.

**Panel** — works both ways, like Grasshopper's panel.
*Connected*: a viewer. Trees show collapsible branches with paths, names and counts, images show thumbnails,
long text folds to four lines (*more* unfolds it), every item has its own copy button, and ⤢ opens a
large view. Data passes through unchanged.
When everything upstream is a lightweight data node (Arbor data/tree/list nodes, core primitives,
string and math nodes) the view updates **live** as you edit — no run needed (green dot).
Anything heavier upstream (samplers, loaders, …) never runs on its own; the Panel then shows the last run.
*Unconnected*: type data in. **Lines** mode: each line is an item, an empty line starts a new branch,
a `# title` line names its branch (the name becomes a grid row label and a folder name downstream),
and a gutter shows every line's branch path and index (coloured by type). **Text** mode: the whole text
is one item. **123 / abc** toggles reading values (`7` → INT, `3.5` → FLOAT, `true` → BOOLEAN).
Long lines wrap; ⤢ opens a large editor; Ctrl+Enter still queues. Outputs `data` (every item, flattened) and `tree`.

**Number Slider** — one bar: drag across it to set the value (Shift = fine), click it to type
(a value outside the range widens the range), scroll or ← → to step. Click *min*, *step* or *max* under
the bar to edit them; step 1 gives whole numbers, 0 is continuous. A single output connects to INT and FLOAT inputs alike; live Panels
follow while you drag.

**True / false** — Dispatch's pattern input takes typed text (`T F`), a native BOOLEAN,
a list of BOOLEANs, or a boolean tree such as Expression `x > 2` (matched branch by branch).
Index Switch takes a BOOLEAN as its index (False = 0, True = 1).

**Prompt Template** — `a photo of {a}, {b}` filled from trees. *Cross* builds every combination as a
grid-ready tree (rows = `{a}`, columns = the last variable); *zip* pairs items one by one.

**Expression** — per-item formula like `x * 2 + i` or `upper(x) if len(x) > 2 else x`.
Names: `x`, `y` (matched longest-list), `i` item index, `b` branch index, `n` branch length.
A safe evaluator: no attribute access or imports.

**Load Folder / Save Images by Path** — subfolders become branches on the way in; branch paths become
subfolders (or filename parts) on the way out, with optional names per file.

**Smart Resize** — longest / shortest side, megapixels, fit, fill & crop or scale; snaps to multiples of
8/16/32/64. Only the fields for the chosen mode are shown.

**Index Switch** — pick input N; unselected inputs are lazy and never execute.


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

## Example workflows

*Templates → ComfyUI-Arbor*. Each one has a note explaining what the nodes are doing.

| Workflow | Shows |
|---|---|
| `arbor_qwen_prompt_matrix` | **Prompt Template** crosses 3 subjects × 3 styles into 9 prompts; the sampler runs once per prompt; **Image Grid** lays the results out with the template's tree — rows named after the subjects, columns after the styles. |
| `arbor_qwen_lora_sweep` | **XY Lists** drives LoRA strength (from **Number Sequence**) against subjects (expanded by **Prompt Template** in zip mode); the seed is a **Number Slider**; the sheet labels itself from XY Lists' shape. |
| `arbor_qwen_storyboard` | A nested structure through a batch run: a **Panel** storyboard (`# scene title` lines, one shot per line) → **Expression** adds the style → **XY Lists** flattens it for the sampler → **Image Grid** with one row per scene, **Construct Tree** + **Save Images by Path** write one folder per scene. |
| `arbor_folder_review` | No model: **Load Folder** reads the storyboard folders back as a named tree; contact sheet, **List Item** picks, **Reshape Tree** (flip matrix) compares shot by shot, **Image Slider** flips through. |
| `arbor_xy_demo` | No model: the XY idea with plain coloured images. |
| `arbor_xy_sampler` | A classic XY plot for any SD-style checkpoint. |

The `arbor_qwen_*` workflows use Qwen Image 2.1 Turbo (8 steps, cfg 1): `qwen_image_2.1_turbo_int8_convrot.safetensors`
(diffusion_models), `qwen3vl_8b_int8_convrot.safetensors` (text_encoders), `texture_fix_vae_for_qwen_image_2.1_bf16.safetensors`
(vae), and for the sweep the LoRA `Qwen-2.1\mj_aesthetic_qwen21_turbo_v2_632_r32.safetensors` — swap in any LoRA you have.
On a 16 GB card a 9-image sheet takes about a minute.

## Install

Clone into `ComfyUI/custom_nodes/` and restart. No extra dependencies.

## Tests

```
python_embeded\python.exe tests\test_offline.py <path-to-ComfyUI>
```
