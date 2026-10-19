# Tree Branch

Pick one branch by path (e.g. {0;1}) or, when path is empty, by index (Grasshopper's Tree Branch).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **path** · *STRING*  
  Exact path such as {0;1}; leave empty to pick by index.
- **index** · *INT*  
  Branch index when path is empty; wraps around, −1 = last branch.

## Outputs

- **tree** · *TREE*  
  A tree with only that branch.

## Tips
- A path that doesn't exist is an error listing the paths that do.
