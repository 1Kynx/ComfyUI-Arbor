# Sub List

Slice items [start, end) from every branch.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **start** · *INT*  
  First item to keep (negative counts from the end).
- **end** · *INT*  
  Stop before this item; −1 keeps through the last item.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
start 1, end −1: `a, b, c, d` → `b, c, d`
