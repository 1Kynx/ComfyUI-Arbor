# List → Tree

Collect a native list back into a tree. Connect the tree you fed into Tree → List (or XY Lists' shape) as shape to restore its branches.

## Inputs

- **list** · *any*  
  Native list, e.g. the per-item results of a batch run.
- **shape** · *any, optional*  
  Tree whose branch layout to copy. Its item count must match the list. Without it everything goes into {0}.
- **split_batch** · *BOOLEAN*  
  Split batches into single frames before rebuilding.

## Outputs

- **tree** · *TREE*  
  The values arranged like shape.

## Example
shape `{0}: a, b · {1}: c, d`, list `1, 2, 3, 4` → `{0}: 1, 2 · {1}: 3, 4`.

## Tips
- A count mismatch is an error with both counts in the message — usually the shape is from a different tree than the one that was flattened.
- With a batch size above 1 every result is a batch; that is fine, the batch stays one item.
