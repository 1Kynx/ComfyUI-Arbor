# Batch Pick

Pick frames from an image batch or a video by index, inclusive range or slice. Order and repeats are kept.

## Inputs

- **images** · *IMAGE / VIDEO*  
  Image batch — or a video, whose frames are picked from.
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

## Videos
Connect a video (Create Video, Load Video, a generated clip) and pick its frames as pictures: `0, -1` for a contact sheet of first and last frames, `-1` for the last frame to start the next shot from. A batch run of clips gives one picked batch per clip.

## Tips
- An index outside the batch is an error rather than being skipped, so typos don't go unnoticed.
