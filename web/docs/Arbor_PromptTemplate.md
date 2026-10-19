# Prompt Template

Fill {a} {b} … in a template from trees. Cross builds every combination as a grid-ready tree; zip pairs items one by one.

## Inputs

- **template** · *STRING*  
  Text with placeholders {a} … {f}. Placeholders without a connected value stay as they are.
- **mode** · *COMBO (cross · zip)*  
  cross: every combination — rows = {a}, columns = the last variable used. zip: item by item (longest list).
- **vars** · *any × N, optional, grows as you connect*  
  Values for {a}, {b}, … — a tree, a list or a single value. Each connection adds the next letter.

## Outputs

- **data** · *STRING ×N*  
  Every filled prompt as plain data — connect straight to a text encoder (it runs once per prompt).
- **tree** · *TREE*  
  The prompts as a tree (cross: one branch per combination of the outer variables — ready for Image Grid).

## Example
Template `a photo of {a}, {b} style`, a = `cat, dog`, b = `oil, ink`:

| mode | result |
|---|---|
| cross | `{0}: cat·oil, cat·ink` · `{1}: dog·oil, dog·ink` |
| zip | `{0}: cat·oil, dog·ink` |

## Tips
- Type the values in **Panels** (one per line) and connect their *data* output (or *tree*, to keep branches).
- Feed the result to **XY Lists** or **Tree → List** to run a sampler once per prompt. Up to 10 000 combinations.
