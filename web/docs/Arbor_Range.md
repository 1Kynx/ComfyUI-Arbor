# Range

Deprecated — use Number Sequence (mode: range). Evenly divide [start, end] into steps parts — steps + 1 numbers.

## Inputs

- **start** · *FLOAT*  
  First number.
- **end** · *FLOAT*  
  Last number (included).
- **steps** · *INT*  
  Number of equal parts; you get steps + 1 numbers.
- **as_int** · *BOOLEAN*  
  Round to whole numbers (duplicates are possible for small ranges).

## Outputs

- **data** · *FLOAT / INT ×N*  
  The numbers as plain data — connect straight to cfg, steps, seed… (the node runs once per number) or to any Arbor input.

## Examples
| start | end | steps | result |
|---|---|---|---|
| 0 | 1 | 4 | 0, 0.25, 0.5, 0.75, 1 |
| 3 | 9 | 3 | 3, 5, 7, 9 |

Use **Range** when you know both ends (e.g. cfg 3 → 9), **Series** when you know the step.
