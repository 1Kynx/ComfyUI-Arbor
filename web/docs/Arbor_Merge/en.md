# Merge

Combine trees — Grasshopper's Merge and Entwine in one node.

## Inputs

- **trees** · *any × N, grows as you connect*  
  Trees to combine. Every connection adds a slot.
- **mode** · *COMBO (merge · entwine)*  
  merge: items on the same path are appended in input order · entwine: input i is placed under {i;…}, so the inputs stay apart.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`{0}: a` and `{0}: b · {1}: c`:
- merge → `{0}: a, b · {1}: c`
- entwine → `{0;0}: a · {1;0}: b · {1;1}: c`
