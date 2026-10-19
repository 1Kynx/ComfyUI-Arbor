# Merge

Combine trees; items on the same path are appended in input order (Grasshopper's Merge).

## Inputs

- **trees** · *any × N, grows as you connect*  
  Trees to combine. Every connection adds a slot.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`{0}: a` + `{0}: b · {1}: c` → `{0}: a, b · {1}: c`

To keep inputs apart instead, use **Entwine**.
