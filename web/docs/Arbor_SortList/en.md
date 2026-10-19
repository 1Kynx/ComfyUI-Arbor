# Sort List

Sort every branch — numbers first (by value), then text (alphabetically) — or reverse it.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **order** · *COMBO (ascending · descending · reverse)*  
  ascending · descending · reverse (keep the items, flip their order).

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`3, b, 1, a` → ascending `1, 3, a, b` · descending `b, a, 3, 1` · reverse `a, 1, b, 3`
