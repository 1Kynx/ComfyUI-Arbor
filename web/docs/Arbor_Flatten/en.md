# Flatten

Put every item into one branch (Grasshopper's Flatten).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **path** · *STRING*  
  Path of the single output branch, e.g. {0}.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`{0}: a, b · {1}: c` → `{0}: a, b, c`
