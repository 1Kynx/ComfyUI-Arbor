# Construct Tree

Build a tree from plain data: put every item on one path, or — with shape connected — pour the items back into another tree's branches.

## Inputs

- **data** · *any*  
  Any value or plain data (a native list), e.g. the results of a batch run.
- **path** · *STRING*  
  Branch path for the items when no shape is connected, e.g. {0} or {0;2}.
- **shape** · *any, optional*  
  A tree whose branch layout to copy — XY Lists' shape, or the tree you flattened. The item counts must match.
- **split_batch** · *BOOLEAN*  
  Split IMAGE / MASK / LATENT batches into one item per frame first.

## Outputs

- **tree** · *TREE*  
  The tree.

## Two ways
| connected | result |
|---|---|
| data only | every item on *path*: `{0}: a, b, c` |
| data + shape | the items poured into shape's branches: shape `{0}: ·, · · {1}: ·, ·` + `a b c d` → `{0}: a, b · {1}: c, d` |

## Round trip
Tree → **XY Lists** (x only) → ordinary nodes run per item → **Construct Tree** with *shape* = XY Lists' shape → the results are back in the original branches.

## Tips
- A count mismatch is an error with both counts in the message — usually the shape is from a different tree than the one that was flattened.
- Every Arbor tree input already accepts plain data (as `{0}`); use this node for a specific path, a shape or split batches.
