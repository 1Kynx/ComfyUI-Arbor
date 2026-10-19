# List Item

Pick item i from every branch (Grasshopper's List Item).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **index** · *INT*  
  Item index; negative counts from the end (−1 = last).
- **wrap** · *BOOLEAN*  
  Wrap the index around the branch length. Off: out-of-range gives an empty value.

## Outputs

- **item** · *TREE*  
  One item per branch.

## Example
index 1: `{0}: a, b, c · {1}: d, e` → `{0}: b · {1}: e`
