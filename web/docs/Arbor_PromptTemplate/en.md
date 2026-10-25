# Prompt Template

Fill {a} {b} … in a template from trees. Cross builds every combination as a grid-ready tree; zip pairs them branch by branch and item by item, like Grasshopper.

## Inputs

- **template** · *STRING*  
  Text with placeholders {a} … {f} (and, in zip mode, {name} — the branch's name). Placeholders without a connected value stay as they are. Several lines are fine.
- **mode** · *COMBO (cross · zip)*  
  cross: every combination — rows = {a}, columns = the last variable used. zip: branches paired in order, items one by one (longest list), the tree keeps its branches and names.
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

## Zip with branches
Zip matches like **Expression**: branch by branch in order, item by item, the shorter list repeating its last item. Two shots per scene against one sound line per scene:
```
a = {0} Arrival: door, map · {1} Village: mist, steps
b = {0}: horn · {1}: bells          template "{name}: {a} + {b}"
→ {0} Arrival: "Arrival: door + horn", "Arrival: map + horn"
  {1} Village: "Village: mist + bells", "Village: steps + bells"
```
`{name}` is the branch's name (a scene, a page). Template: *arbor_h3_two_characters* writes a structured video prompt per scene this way, *arbor_h3_continuous_shots* one per transition.

## Tips
- Type the values in **Panels** (one per line) and connect their *data* output (or *tree*, to keep branches).
- Connect *data* to a text encoder: the sampler runs once per prompt. Connect *tree* to **Image Grid**'s *shape* to lay the images out in the same rows. Up to 10 000 combinations.
