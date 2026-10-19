# Series

Arithmetic sequence: start, start + step, … — count numbers (Grasshopper's Series).

## Inputs

- **start** · *FLOAT*  
  First number.
- **step** · *FLOAT*  
  Difference between neighbours (negative counts down).
- **count** · *INT*  
  How many numbers.
- **as_int** · *BOOLEAN*  
  Output whole numbers — for seeds, steps, sizes.

## Outputs

- **tree** · *TREE*  
  The numbers in branch {0}.

## Examples
| start | step | count | result |
|---|---|---|---|
| 0 | 1 | 5 | 0, 1, 2, 3, 4 |
| 3 | 2 | 4 | 3, 5, 7, 9 |
| 1000 | 1 | 4 (as_int) | four consecutive seeds |
