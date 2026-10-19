# Tree → List

Flatten a tree into a native ComfyUI list: downstream nodes then run once per item. Collect the results with List → Tree.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).

## Outputs

- **data** · *any ×N*  
  Every item as plain data, branch order then item order — downstream nodes run once per item.
- **count** · *INT*  
  Number of items.

## How it works
ComfyUI runs a node once per item when it receives a list. **Tree → List** turns a tree into such a list, so an ordinary node (a sampler, a text encoder…) processes every item. Afterwards **List → Tree** with the same tree as *shape* restores the branches.

## Tips
- For an XY plot, **XY Lists** does the combining and flattening in one node.
- Feeding several lists into one node pairs them by index; the shorter list repeats its last item.
