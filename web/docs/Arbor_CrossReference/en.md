# Cross Reference

Every combination of A × B, branch by branch (Grasshopper's Cross Reference). With group on: rows = A, columns = B.

## Inputs

- **A** · *any*  
  First set of values.
- **B** · *any*  
  Second set of values.
- **group** · *BOOLEAN*  
  One branch per A item — the result is grid-ready (rows = A, columns = B).

## Outputs

- **A** · *TREE*  
  A repeated for every B.
- **B** · *TREE*  
  B cycled for every A.

## Example
A `3, 5`, B `x, y, z`, group on:
- A → `{0;0}: 3, 3, 3 · {0;1}: 5, 5, 5`
- B → `{0;0}: x, y, z · {0;1}: x, y, z`

## Tips
- For an XY plot, **XY Lists** does this and the flattening in one node.
- Both outputs work directly as **Tree → Grid** labels.
