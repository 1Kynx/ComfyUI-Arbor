# Dispatch

Split items into A (pattern true) and B (pattern false) (Grasshopper's Dispatch).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **pattern** · *STRING / BOOLEAN / TREE*  
  Typed repeating pattern ('T F', 'true,false', '1 0 1', 'TFT'), or connect BOOLEAN values / a boolean tree (e.g. Expression 'x > 2'), matched branch by branch.

## Outputs

- **A** · *TREE*  
  Items where the pattern is true.
- **B** · *TREE*  
  Items where the pattern is false.

## Example
pattern `T F`: `a, b, c, d` → A `a, c` · B `b, d`
