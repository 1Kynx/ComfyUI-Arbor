# Shift Paths

Drop path indices: +1 removes the first, −1 the last; branches that end up on the same path are joined (Grasshopper's Shift Paths).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **offset** · *INT*  
  Positive drops leading indices, negative drops trailing ones.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
offset −1: `{0;0}: a · {0;1}: b · {1;0}: c` → `{0}: a, b · {1}: c` (undoes Graft).
