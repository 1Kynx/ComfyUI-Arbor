# Partition

Chop every branch into chunks of size items: {p} → {p;k} (Grasshopper's Partition).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **size** · *INT*  
  Items per chunk; the last chunk may be shorter.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
size 2: `{0}: a, b, c, d, e` → `{0;0}: a, b · {0;1}: c, d · {0;2}: e`

Handy for turning a flat list of images into grid rows.
