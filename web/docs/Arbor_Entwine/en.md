# Entwine

Stack trees side by side: input i is placed under {i;…} (Grasshopper's Entwine).

## Inputs

- **trees** · *any × N, grows as you connect*  
  Trees to stack. Every connection adds a slot.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
`{0}: a, b` + `{0}: c` → `{0;0}: a, b · {1;0}: c`
