# Simplify

Remove path indices that every branch shares (Grasshopper's Simplify).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`{0;0;1}: a · {0;0;2}: b` → `{1}: a · {2}: b`
