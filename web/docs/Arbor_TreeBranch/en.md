# Tree Branch

Pick branches by path (e.g. {0;1}) or by name — several separated by commas — or, when path is empty, one by index (Grasshopper's Tree Branch).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **path** · *STRING*  
  Paths such as {0;1} or branch names such as Mei, separated by commas (Mei, Kai); leave empty to pick by index.
- **index** · *INT*  
  Branch index when path is empty; wraps around, −1 = last branch.

## Outputs

- **tree** · *TREE*  
  A tree with only those branches, paths and names kept.
- **data** · *any ×N*  
  Their items as plain data, branch after branch — straight into a node that runs once per item.

## Example
**Load Media** with the groups `# Mei`, `# Kai` and `# Places`: one **Tree Branch** with path *Mei, Kai* and one with *Places* split them, and **Cross Reference** pairs every character with every place — `{0} Mei` and `{1} Kai`, three places each.

## Tips
- A path or name that doesn't exist is an error listing the paths that do.
