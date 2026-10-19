# Index Switch

Pass through input N (counting connected inputs, wrapping around). Unselected inputs are lazy and never execute.

## Inputs

- **index** · *INT / BOOLEAN*  
  0 = first connected input; negative counts from the end; wraps around. A BOOLEAN works too: False = 0, True = 1.
- **inputs** · *any × N, grows as you connect*  
  Candidates of any type. Every connection adds a slot; only the selected one is computed.

## Outputs

- **data** · *any*  
  The selected input.
- **count** · *INT*  
  Number of connected inputs.

## Tips
- Switch between whole branches of a workflow (models, prompts, image sources) without computing the others.
- Drive *index* with a **Number Slider** (*int* output) or a Boolean for an if / else.
- ComfyUI's own *If/Else Switch* takes exactly two inputs; this one takes up to 32.
