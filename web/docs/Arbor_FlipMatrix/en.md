# Flip Matrix

Swap rows and columns: item j of every branch goes to {j} (Grasshopper's Flip Matrix).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`{0}: a, b · {1}: c, d` → `{0}: a, c · {1}: b, d`

Put it before **Tree → Grid** to swap the axes of a sheet.
