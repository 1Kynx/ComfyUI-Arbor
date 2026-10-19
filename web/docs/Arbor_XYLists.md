# XY Lists

From values to a batch run: every combination of x, y (and z) as aligned plain data — wire them into ordinary nodes and they run once per combination — plus the shape of the runs. With only x connected it flattens any tree into plain data.

## Inputs

- **x** · *any*  
  Values for the rows — or any tree to flatten into plain data.
- **y** · *any, optional*  
  Values for the columns (optional).
- **z** · *any, optional*  
  Optional third parameter: becomes the columns, rows become x × y.
- **mode** · *COMBO (cross · zip)*  
  cross: every combination · zip: item by item (longest list, the last item repeats).

## Outputs

- **x** · *any ×N*  
  x of every run — connect to any widget input (cfg, steps, seed…). The node it feeds runs once per combination.
- **y** · *any ×N*  
  y of every run.
- **z** · *any ×N*  
  z of every run (empty values when z is not connected).
- **shape** · *TREE*  
  Layout of the runs: connect to Image Grid (rows × columns) or Construct Tree (back into a tree). Its items are the column values, so Image Grid labels its columns from it. With only x, it is x's own tree.
- **count** · *INT*  
  Number of runs.

## XY plot in four nodes
```
Panel (cfg) ─x─┐               ┌─ x ─► KSampler.cfg ─┐
               ├─ XY Lists ────┤─ y ─► CLIP Text ────┴─► VAE Decode ─► Image Grid
Panel (text)─y─┘               └─ shape ─────────────────────────────────┘
```
1. Type the x values and the y values in two **Panels** (or use **Number Sequence**) and connect them.
2. Connect *x* / *y* to the inputs you want to vary — ordinary nodes run once per combination.
3. Connect the decoded images and *shape* to **Image Grid**. It lays them out as rows × columns and labels the columns; connect the x Panel to its *row_labels*.

Example template: *Templates → ComfyUI-Arbor → arbor_xy_sampler*.

## Flatten any tree
Connect a tree to *x* only: *x* becomes its items as plain data (ordinary nodes run once per item) and *shape* is the tree itself. Run something per item, then put the results back with **Construct Tree** (*shape* = this shape).

## Tips
- 3 × 4 values = 12 runs; the limit is 10 000.
- Any widget accepts these outputs: drag from *x* onto a widget to turn it into an input.
