# Number Slider

Grasshopper-style number slider: drag the bar to set a value between min and max, click it to type. A step of 1 gives whole numbers.

## Inputs

- **value** · *FLOAT*  
  Current value — set it on the bar.
- **min** · *FLOAT*  
  Lower end of the range (click the left number under the bar).
- **max** · *FLOAT*  
  Upper end of the range (click the right number under the bar).
- **step** · *FLOAT*  
  Values snap to min + k × step: 1 = whole numbers, 0.05 = steps of 0.05, 0 = continuous. Also sets how many decimals are shown.

## Outputs

- **value** · *FLOAT / INT*  
  One output for every number input: connects to INT inputs (steps, seed) and FLOAT inputs (cfg, denoise) alike. Whole numbers come out as INT, others as FLOAT.

## How to use
- **Drag** across the bar — the value follows the pointer. Hold **Shift** while dragging for 10× finer control.
- **Click** the bar (without dragging) to type a value; Enter confirms, Esc cancels. A value outside the range widens the range.
- **Scroll** over the bar or press **← / →** to move by one step (Shift: 10 steps).
- Under the bar: click **min**, **step** or **max** to edit them.

## Examples
| min · step · max | values |
|---|---|
| 0 · 0.05 · 1 | 0, 0.05, 0.10, … 1 |
| 1 · 1 · 50 | whole numbers — steps, batch sizes |
| 0 · 0 · 1 | any value (shown with up to 4 decimals) |

## Tips
- The single *value* output connects to any number input — FLOAT (cfg, denoise, LoRA strength) or INT (steps, seed, batch size). Drag it onto a widget to turn the widget into an input.
- For INT inputs use a whole-number slider (step 1): a value like 7.5 would be passed as FLOAT.
- Live Panels downstream follow the slider while you drag.
