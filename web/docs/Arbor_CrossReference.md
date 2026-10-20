# Cross Reference

Every combination of A × B, branch by branch, like Grasshopper's Cross Reference: branches pair in order (the shorter tree repeats its last branch) and the result takes the paths of the input with the longest paths. With group on: rows = A, columns = B.

## Inputs

- **A** · *any*  
  First set of values.
- **B** · *any*  
  Second set of values.
- **group** · *BOOLEAN*  
  Off (default): Grasshopper's Cross Reference — all combinations stay in the branch. On: one sub-branch per A item, the same as grafting A first — grid-ready (rows = A, columns = B).

## Outputs

- **A** · *TREE*  
  A repeated for every B.
- **B** · *TREE*  
  B cycled for every A.

## Example
A `3, 5`, B `x, y, z`:
- group off → A `{0}: 3, 3, 3, 5, 5, 5` · B `{0}: x, y, z, x, y, z`
- group on → A `{0;0}: 3, 3, 3 · {0;1}: 5, 5, 5` · B `{0;0}: x, y, z · {0;1}: x, y, z`

## Tips
- For an XY plot, **XY Lists** does this and the flattening in one node.
- With group on, each sub-branch is named after its A value (pictures and other non-text values get their number), and the branch it came from becomes the parent and keeps its name: `Mira · lab coat`, `Arrival · 2`. **Image Grid** labels its rows with these; B works as column labels.
