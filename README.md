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

### Nesting

Branches can hold branches — `{scene;shot}`, `{character;outfit}` — and the operations understand it:

- **Parents pair with their children.** Expression and Dispatch match a second tree by path: a value on
  `{0}` (Mira's description, a scene's sound) goes with every `{0;…}` (her outfits, the scene's shots).
- **Names ride along.** A branch can carry a name (`# Arrival` in a Panel, a folder in Load Folder,
  an x value in XY Lists). After Graft or Cross Reference it names the group, labels read `Mira · lab coat`,
  Shift Paths −1 folds back to `Mira`, and grids, Panels, sliders and saved folders show them.
  Expression sees it as `name`.
- **Uneven is fine.** Three outfits for one character, two for the next; two edits for one scene, one for
  another — counts per branch never have to line up.

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

**Image Slider** — connect any number of images (inputs grow as you connect) of any size — single
images, batches or whole image trees; slides from a named branch are labelled with its name.
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
a list of BOOLEANs, or a boolean tree such as Expression `x > 2` (matched by path: a value on a
parent branch covers all of its children).
Index Switch takes a BOOLEAN as its index (False = 0, True = 1).

**Prompt Template** — `a photo of {a}, {b}` filled from trees. *Cross* builds every combination as a
grid-ready tree (rows = `{a}`, columns = the last variable); *zip* pairs items one by one.

**Expression** — per-item formula like `x * 2 + i` or `upper(x) if len(x) > 2 else x`.
Names: `x`, `y` (matched by path — a parent branch goes with all of its children — then in order),
`i` item index, `b` branch index, `n` branch length, `name` the branch's name.
A safe evaluator: no attribute access or imports.

**Load Folder / Save Images by Path** — subfolders become branches on the way in, named after the folder;
branches become subfolders (or filename parts) on the way out — `prefix/0-1/000.png`, or `prefix/0 · Arrival/…`
for a named branch — with optional names per file. Saved trees load back with their names; `output/…` paths
read from ComfyUI's output folder.

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

*Templates → ComfyUI-Arbor*. Each one has a note explaining what the nodes are doing. Times are for a 16 GB card.

**Trees of pictures, video and sound** — where branches pay off:

| Workflow | Shows | Run |
|---|---|---|
| `arbor_qwen_storyboard` | A **Panel** storyboard (`# scene` lines, one shot per line) → **Expression** adds the style → **XY Lists** flattens it for the sampler → **Image Grid** with one row per scene; **Construct Tree** + **Save Images by Path** write one folder per scene. Start here — the next three use its output. | 6 images, 30 s |
| `arbor_qwen_edit_by_scene` | Pictures × instructions as one tree: **Load Folder** gives the frames per scene, a **Panel** gives each scene its *own* edits (2 / 1 / 2). **Cross Reference** pairs them per shot, two **XY Lists** flatten both side by side for the edit model, **Construct Tree** + **Merge** put each original in front of its edits. | 10 edits, 75 s |
| `arbor_h3_storyboard_video` | Keyframes (images), a motion line per shot and a sound line per scene (text) drive MiniMax H3 image-to-video **with audio**. The sound line reaches every shot of its scene by path; **Expression** `name` files each clip under its scene; **Batch Pick** + **Construct Tree** make a contact sheet per scene. | 6 clips, 110 s |
| `arbor_folder_review` | No model: **Load Folder** reads the folders back as a named tree; contact sheet, **List Item** picks, **Reshape Tree** (flip matrix) compares shot by shot, **Image Slider** flips through. | — |
| `arbor_qwen_character_sheet` | Three uneven levels — character → outfit → pose (Mira 3 outfits, Theo 2). **List Item** splits description from outfits per branch, **Cross Reference** nests the poses, **Expression** pairs each outfit with its *parent's* description, **Reshape Tree** *shift paths −1* folds outfits back into one row per character. | 15 images, 65 s |

**Grids and sweeps:**

| Workflow | Shows | Run |
|---|---|---|
| `arbor_qwen_prompt_matrix` | **Prompt Template** crosses 3 subjects × 3 styles; **Image Grid** lays the results out with the template's tree — rows named after the subjects. | 9 images, 50 s |
| `arbor_qwen_lora_sweep` | **XY Lists** drives LoRA strength (from **Number Sequence**) against subjects (expanded by **Prompt Template** in zip mode); the seed is a **Number Slider**. | 9 images, 35 s |
| `arbor_xy_demo` | No model: the XY idea with plain coloured images. | — |
| `arbor_xy_sampler` | A classic XY plot for any SD-style checkpoint. | — |

Models used:
- **Qwen Image 2.1 Turbo** (`arbor_qwen_*`): `qwen_image_2.1_turbo_int8_convrot.safetensors` (diffusion_models), `qwen3vl_8b_int8_convrot.safetensors` (text_encoders), `texture_fix_vae_for_qwen_image_2.1_bf16.safetensors` for generating and `qwen_image_2.1_vae_bf16.safetensors` for editing (vae); text to image uses 8 steps, editing 6. The sweep uses the LoRA `Qwen-2.1\mj_aesthetic_qwen21_turbo_v2_632_r32.safetensors` — swap in any LoRA you have. Editing works best with concrete, local instructions (add, remove or recolor something).
- **MiniMax H3** (`arbor_h3_*`): `minimax_h3_fl2va_pruned_int8_convrot.safetensors` (diffusion_models) + the LoRA `minimax h3\minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors` (6 steps), `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (text_encoders, type *minimax*), `minimax_h3_video_vae_int8_convrot.safetensors` and `minimax_h3_audio_vae_fp32.safetensors` (vae). The demo renders 56 frames at 0.3 MP; raise both for real shots.

## Install

Clone into `ComfyUI/custom_nodes/` and restart. No extra dependencies.

## Tests

```
python_embeded\python.exe tests\test_offline.py <path-to-ComfyUI>
```
