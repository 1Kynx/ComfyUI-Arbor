# Tree to Data

Every item of a tree as plain data, so ordinary nodes run once per item — plus its shape, to put the results back.

## Inputs

- **tree** · *any*  
  The tree to run over — every item becomes one run of the nodes it feeds.

## Outputs

- **data** · *any ×N*  
  Every item as plain data, in branch order: connect to any ordinary node (a text encoder, a sampler input…) and it runs once per item.
- **shape** · *TREE*  
  The tree itself: connect to Construct Tree or Image Grid to put the results back into the same branches, with their names.

## Round trip
```
tree ─► Tree to Data ─ data ─► ordinary nodes (run once per item) ─┐
                    └─ shape ───────────────────────────────────► Construct Tree / Image Grid
```
`{0} Arrival: a, b · {1} Village: c` → *data* `a, b, c` → three runs → back as `{0} Arrival: A, B · {1} Village: C`.

## Tips
- A small node on purpose: for one tree it does what **XY Lists** does with only *x* connected.
- Two or three trees of the same layout (pictures and their edit instructions, say) flatten side by side with **XY Lists** in *zip* mode.
- The data nodes (Panel, Split Text, Prompt Template, Expression, Random, Collect) already have a *data* output; this is for every other tree.
