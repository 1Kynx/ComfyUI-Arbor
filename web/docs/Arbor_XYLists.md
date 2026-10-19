# XY Lists

One step from parameter values to a batch run: every combination of x, y (and z) as aligned native lists, plus the grid shape for List → Tree.

## Inputs

- **x** · *any*  
  Values for the rows: a tree, a list or a single value (e.g. a Panel with 3 / 5 / 7).
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
  Grid layout of the runs — connect to List → Tree's shape. Its items are the column values, so it also works as Image Grid's col_labels.
- **count** · *INT*  
  Number of runs.

## XY plot in five nodes
```
Panel (cfg) ─x─┐               ┌─ x ─► KSampler.cfg ─┐
               ├─ XY Lists ────┤─ y ─► CLIP Text ────┴─► VAE Decode ─► List → Tree ─► Image Grid
Panel (text)─y─┘               └─ shape ──────────────────────────────┘
```
1. Type the x values and the y values in two **Panels** (or use **Series** / **Range**) and connect them.
2. Connect XY Lists' *x* / *y* to the inputs you want to vary — ordinary nodes run once per combination.
3. Collect the images with **List → Tree** (*shape* from this node), then **Image Grid** (row labels = the x Panel, column labels = *shape*).

Example template: *Templates → ComfyUI-Arbor → arbor_xy_sampler*.

## Tips
- 3 × 4 values = 12 runs; the limit is 10 000.
- Any widget accepts these outputs: drag from *x* onto a widget to turn it into an input.
