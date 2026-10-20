# Collect

Gather any values — pictures, masks, latents, audio, video, text — into data: one branch per input, named, or all in one list.

## Inputs

- **inputs** · *any × N, grows as you connect*  
  Anything. Every connection adds a slot. A list fills its branch with all its items; a tree keeps its own branches under {i;…}.
- **mode** · *COMBO (branch per input · one list)*  
  branch per input: input 1 → {0}, input 2 → {1}, … (only connected slots count) · one list: everything in {0}, like ComfyUI's Create List.
- **names** · *STRING*  
  One name per line, for the branches in input order. The names label Image Grid rows, Panel branches and Image Slider slides, and name the folders of Save by Path. In one-list mode the first line names the list.
- **split_batch** · *BOOLEAN*  
  Split IMAGE / MASK / LATENT batches into one item per frame.

## Outputs

- **data** · *any ×N*  
  Every collected item as plain data — ordinary nodes run once per item.
- **tree** · *TREE*  
  The collected items as a tree, one named branch per input.

## Compare pipelines
```
Qwen   ─► input0 ┐
Flux   ─► input1 ├─ Collect (names: Qwen / Flux / original) ─ tree ─► Image Grid
LoadImage ► input2 ┘
```
Every pipeline becomes a row of the sheet, labelled with its name.

## Reference sets per scene
Connect one batch of reference pictures per scene, turn on *split_batch*, write the scene names: `{0} Arrival: 3 pictures · {1} Village: 2 pictures` — ready for **List Item**, **Cross Reference** or a reference-to-video run.

## Tips
- Text typed by hand is easier in a **Panel**; this node is for values that come from other nodes.
- Only connected slots count, so `{0}`, `{1}`, … have no gaps.
