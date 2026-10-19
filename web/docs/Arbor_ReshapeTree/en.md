# Reshape Tree

Change how items are grouped into branches — Grasshopper's Graft, Flatten, Simplify, Flip Matrix, Shift Paths and Renumber in one node.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **mode** · *COMBO*  
  graft: every item its own branch · flatten: everything in one branch · simplify: drop path indices all branches share · flip matrix: swap rows and columns · shift paths: drop path indices, joining branches that meet · renumber: {0}, {1}, {2}, … in order.
  - **mode.path** `path` · *STRING*  
    flatten: path of the single output branch, e.g. {0}.
  - **mode.offset** `offset` · *INT*  
    shift paths: −1 drops the last index (undoes graft), +1 the first.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Modes
| mode | example |
|---|---|
| graft | `{0}: a, b, c` → `{0;0}: a · {0;1}: b · {0;2}: c` |
| flatten | `{0}: a, b · {1}: c` → `{0}: a, b, c` |
| simplify | `{0;0;1}: a · {0;0;2}: b` → `{1}: a · {2}: b` |
| flip matrix | `{0}: a, b · {1}: c, d` → `{0}: a, c · {1}: b, d` |
| shift paths (−1) | `{0;0}: a · {0;1}: b · {1;0}: c` → `{0}: a, b · {1}: c` |
| renumber | `{0;3}: a · {2;1}: b` → `{0}: a · {1}: b` |

## Tips
- *flip matrix* before **Image Grid** swaps the axes of a sheet.
- *graft* then a per-item operation, then *shift paths −1*, groups the results back.
- Search for graft, flatten, flip matrix… — they all find this node.
