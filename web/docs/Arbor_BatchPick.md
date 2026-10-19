# Batch Pick

Pick frames from an image batch by index, inclusive range or slice. Order and repeats are kept.

## Inputs

- **images** · *IMAGE*  
  Image batch to pick from.
- **indices** · *STRING*  
  Comma / space separated: 0, 2, -1 (from the end), 3-5 (inclusive range), 1:8:2 or ::2 (Python slices).

## Outputs

- **images** · *IMAGE*  
  The picked frames, as one batch.
- **count** · *INT*  
  How many frames were picked.

## Examples (batch of 6)
| indices | frames |
|---|---|
| `0, -1` | first and last |
| `2-4` | 2, 3, 4 |
| `::2` | 0, 2, 4 |
| `1, 1, 1` | frame 1 three times |

## Tips
- An index outside the batch is an error rather than being skipped, so typos don't go unnoticed.
