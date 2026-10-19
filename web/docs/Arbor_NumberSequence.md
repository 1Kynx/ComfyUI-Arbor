# Number Sequence

A list of numbers, defined by a step (series) or by both ends (range).

## Inputs

- **mode** · *COMBO*  
  series: start, start + step, … · range: start → end split evenly. Only that mode's fields are shown.
  - **mode.start** `start` · *FLOAT*  
    First number.
  - **mode.step** `step` · *FLOAT*  
    series: difference between neighbours (negative counts down).
  - **mode.count** `count` · *INT*  
    series: how many numbers.
  - **mode.end** `end` · *FLOAT*  
    range: last number (included).
  - **mode.steps** `steps` · *INT*  
    range: number of equal parts — you get steps + 1 numbers.
- **as_int** · *BOOLEAN*  
  Round to whole numbers — for seeds, steps, sizes.

## Outputs

- **data** · *FLOAT / INT ×N*  
  The numbers as plain data — connect straight to cfg, steps, seed… (the node runs once per number) or to any Arbor input.

## Examples
| mode | values | result |
|---|---|---|
| series | start 3 · step 2 · count 4 | 3, 5, 7, 9 |
| series | start 1000 · step 1 · count 4 · as_int | four consecutive seeds |
| range | start 0 · end 1 · steps 4 | 0, 0.25, 0.5, 0.75, 1 |
| range | start 3 · end 9 · steps 3 | 3, 5, 7, 9 |

Use **series** when you know the step, **range** when you know both ends (e.g. cfg 3 → 9).

## Tips
- Connect the output straight to a widget (cfg, steps, width…): the node it feeds runs once per number.
- For a parameter sweep against a second value, connect it to **XY Lists**.
