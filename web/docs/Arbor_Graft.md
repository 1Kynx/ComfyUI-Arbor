# Graft

Every item gets its own branch: {p} → {p;i} (Grasshopper's Graft).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`{0}: a, b, c` → `{0;0}: a · {0;1}: b · {0;2}: c`

Undo it with **Shift Paths** (offset −1).
