# Panel

Inspect anything, or type data in. Connected: shows the input and passes it through. Unconnected: each line you type is an item, an empty line starts a new branch and a `# title` line names it.

## Inputs

- **data** · *any, optional*  
  Anything — a data tree, a native list, an image, a number… Leave it unconnected to type data instead.
- **text** · *STRING*  
  The typed data (used when nothing is connected). Edited in the panel itself.
- **parse_numbers** · *BOOLEAN*  
  Typed values: lines like 7 / 3.5 / true become INT / FLOAT / BOOLEAN. The 123 / abc button in the panel.
- **multiline** · *BOOLEAN*  
  Text mode: the whole text is one item. The Lines / Text switch in the panel.

## Outputs

- **data** · *any ×N*  
  The data as a native list: downstream nodes run once per item (a single item runs once).
- **tree** · *TREE*  
  The data as a tree — for Arbor nodes, keeps the branches.

## Viewing (input connected)
- Trees show as collapsible branches with their path, name and count (`{1} 7 N=3` — XY Lists names each row after its x value); images as thumbnails.
- Long text folds to four lines — *more* unfolds it. Hover an item to copy it; the toolbar copies everything.
- **Live**: when everything upstream is a lightweight data node (Arbor data / tree / list nodes, primitives, string and math nodes) the view updates as you edit — no run needed (green dot). Anything heavier upstream (samplers, loaders) never runs on its own; the panel then shows the last run.
- ⤢ opens a large view.

## Typing (input unconnected)
- **Lines**: one item per line, an empty line starts a new branch. A line `# title` names its branch instead of being an item — the name shows up as the row label in **Image Grid**, as the folder name in **Save Images by Path**, and in every Panel downstream. The gutter shows each line's branch path and index, coloured by type (blue = number, purple = boolean).
- **Text**: the whole text is one item — for long prompts.
- **123 / abc**: read numbers and true / false, or keep everything as text.
- ⤢ opens a large editor. Ctrl+Enter still queues the workflow.

## Example
```
3
5
7

a cat
a dog
```
→ tree `{0}: [3, 5, 7]`, `{1}: ["a cat", "a dog"]`.

```
# Arrival
night train
paper map

# The village
misty roofs
```
→ `{0} Arrival: [night train, paper map]`, `{1} The village: [misty roofs]` — a storyboard (template *arbor_qwen_storyboard*).
