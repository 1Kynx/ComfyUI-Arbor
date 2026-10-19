# Random

Seeded shuffle, or pick a number of items (with or without repeats). Same seed, same result.

## Inputs

- **data** `tree` · *any*  
  Items to shuffle or pick from — plain data or a tree (handled branch by branch).
- **mode** · *COMBO (shuffle · pick · pick (repeats))*  
  shuffle: reorder everything · pick: choose count different items · pick (repeats): choose count items, repeats allowed.
- **count** · *INT*  
  Items to pick per branch (ignored by shuffle).
- **seed** · *INT*  
  Random seed — the same seed always gives the same result.
- **per_branch** · *BOOLEAN*  
  On: every branch separately. Off: all items as one list.

## Outputs

- **data** · *any ×N*  
  The shuffled / picked items as plain data.
- **tree** · *TREE*  
  The shuffled / picked items, branch by branch.

## Tips
- Pick random prompts or styles for a batch: Panel (one per line) → **Random** (pick 4) → *data* to a text encoder.
- Set the seed's *control after generate* to *randomize* for a new pick on every run.
