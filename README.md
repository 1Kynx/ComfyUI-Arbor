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
| **Arbor/Image** | Image Slider · Tree → Grid |
| **Arbor/Data** | Panel · Construct Tree · Series · Range · Split Text |
| **Arbor/Tree** | Tree → List · List → Tree · Graft · Flatten · Simplify · Flip Matrix · Shift Paths · Renumber · Tree Branch · Merge · Entwine · Tree Statistics |
| **Arbor/List** | List Item · Sub List · Cull Pattern · Dispatch · Partition · Repeat · Reverse List · Sort List · Cross Reference |

**Image Slider** — connect any number of images (inputs grow as you connect) of any size.
*Flip*: drag the scrubber or press ← → to step through them. *Wipe*: A/B split that follows the pointer.
*Real* keeps relative sizes, *Fit* fills the stage. Double-click opens the full image.

**Panel** — works both ways, like Grasshopper's panel.
*Connected*: a viewer. Trees show collapsible branches with paths and counts, images show thumbnails,
the copy button exports the whole structure as text, and the data passes through unchanged.
*Unconnected*: type data in. Each line is an item, an empty line starts a new branch; `1.0` turns
number parsing on/off, `¶` makes the whole text one item. Outputs `data` (native list) and `tree`.

Every tree input also accepts plain values or native lists (they become branch `{0}`).

## Install

Clone into `ComfyUI/custom_nodes/` and restart. No extra dependencies.
An example workflow ships in `example_workflows/` (Templates → ComfyUI-Arbor).

## Tests

```
python_embeded\python.exe tests\test_offline.py <path-to-ComfyUI>
```
