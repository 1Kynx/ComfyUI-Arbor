# Repeat

Repeat items: each gives aabbcc, whole gives abcabc. With a shape connected, every branch is stretched to the item count of its matching branch instead — Grasshopper's Longest List.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **count** · *INT*  
  How many times (ignored while a shape is connected).
- **mode** · *COMBO (each · whole)*  
  each: repeat every item in place · whole: repeat the whole list. With a shape: each spreads the items evenly (a a b b), whole cycles them (a b a b).
- **shape** · *any, optional*  
  Optional tree to match. Branches pair in order (the last one repeats); each branch gets as many items as its partner and takes its path, so the result lines up with the shape item by item.

## Outputs

- **tree** · *TREE*  
  The resulting tree.

## Example
count 2: `a, b` → each `a, a, b, b` · whole `a, b, a, b`

## Match a shape
One location per scene, two shots per scene:
```
tree  = {0}: tea house · {1}: bamboo · {2}: rooftop
shape = {0}: shot 1, shot 2 · {1}: shot 1, shot 2 · {2}: shot 1, shot 2
→ {0}: tea house, tea house · {1}: bamboo, bamboo · {2}: rooftop, rooftop
```
**Tree to Data** on both now gives two lists of six that line up — every shot gets its own scene's location as a reference picture.
