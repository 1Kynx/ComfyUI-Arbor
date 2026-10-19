# Random

Seeded shuffle, or pick a number of items (with or without repeats). Same seed, same result.

## Inputs

- **tree** · *any*  
  Items to shuffle or pick from.
- **mode** · *COMBO (shuffle · pick · pick (repeats))*  
  shuffle: reorder everything · pick: choose count different items · pick (repeats): choose count items, repeats allowed.
- **count** · *INT*  
  Items to pick per branch (ignored by shuffle).
- **seed** · *INT*  
  Random seed — the same seed always gives the same result.
- **per_branch** · *BOOLEAN*  
  On: every branch separately. Off: all items as one list.

## Outputs

- **tree** · *TREE*  
  The shuffled / picked items.

## Tips
- Pick random prompts or styles for a batch: Panel (one per line) → **Random** (pick 4) → XY Lists / Tree → List.
- Set the seed's *control after generate* to *randomize* for a new pick on every run.
