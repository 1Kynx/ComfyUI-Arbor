# Number Slider

Grasshopper-style number slider: drag to set a value between min and max. decimals = 0 gives whole numbers.

## Inputs

- **value** · *FLOAT*  
  Current value (set by the slider).
- **min** · *FLOAT*  
  Lower end of the range (click the left number to edit).
- **max** · *FLOAT*  
  Upper end of the range (click the right number to edit).
- **decimals** · *INT*  
  Precision: 0 = whole numbers, 2 = steps of 0.01 (click the step chip to change).

## Outputs

- **value** · *FLOAT*  
  The value as FLOAT.
- **int** · *INT*  
  The value rounded to INT — for steps, seeds, counts.

## How to use
- **Drag** the track to set the value; hold **Shift** for 10× finer control.
- **Scroll** over the track or press **← / →** (with Shift: ×10) to step.
- **Double-click** the big number to type an exact value.
- Click the **min / max** numbers to change the range, the **step** chip to change precision.

## Tips
- Connect *value* to any FLOAT widget (cfg, denoise, LoRA strength) or *int* to INT widgets (steps, seed).
- Live Panels downstream follow the slider while you drag.
