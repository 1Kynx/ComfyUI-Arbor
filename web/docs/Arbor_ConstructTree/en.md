# Construct Tree

Wrap any value, native list or batch into one branch of a data tree.

## Inputs

- **data** · *any*  
  Any value or native list.
- **path** · *STRING*  
  Branch path for the items, e.g. {0} or {0;2}.
- **split_batch** · *BOOLEAN*  
  Split IMAGE / MASK / LATENT batches into one item per frame.

## Outputs

- **tree** · *TREE*  
  A tree with a single branch at path.

## Tips
- Every Arbor tree input already accepts plain values and lists (they become `{0}`); use this node when you need a specific path or want batches split.
- Combine several with **Merge** (same paths join) or **Entwine** (each input gets its own branch).
