# Repeat

Repeat items: each gives aabbcc, whole gives abcabc.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **count** · *INT*  
  How many times.
- **mode** · *COMBO (each · whole)*  
  each: repeat every item in place · whole: repeat the whole list.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
count 2: `a, b` → each `a, a, b, b` · whole `a, b, a, b`
