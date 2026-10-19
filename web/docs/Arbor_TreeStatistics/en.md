# Tree Statistics

Branch count, item count, depth and the list of paths.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).

## Outputs

- **branches** · *INT*  
  Number of branches.
- **items** · *INT*  
  Total number of items.
- **depth** · *INT*  
  Longest path length.
- **paths** · *STRING*  
  One line per branch: path and item count.

## Tips
- For a quick look a **Panel** shows the same, live; use this node when you need the numbers downstream (e.g. as the count of a Number Sequence).
