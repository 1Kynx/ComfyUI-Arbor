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
- With group on, each sub-branch is named after its A value (pictures and other non-text values get their number), and the branch it came from becomes the parent and keeps its name: `Mira · lab coat`, `Arrival · 2`. **Image Grid** labels its rows with these; B works as column labels.
