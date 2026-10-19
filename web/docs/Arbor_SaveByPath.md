# Save by Path

Save an image tree keeping its structure: one subfolder (or filename part) per branch path, with optional names per file.

## Inputs

- **images** · *any*  
  Image tree to save. Batches are saved frame by frame.
- **filename_prefix** · *STRING*  
  Folder / prefix inside ComfyUI's output folder. Supports %date%-style variables like Save Image.
- **layout** · *COMBO (subfolders · flat)*  
  subfolders: prefix_0-1/000.png · flat: prefix_0-1_000.png
- **names** · *any, optional*  
  Optional file names, matched to the images item by item (e.g. Load Folder's names or a Prompt Template).

## Outputs

- **paths** · *TREE*  
  Saved file paths, in the same tree layout.

## Example
Tree `{0}: 2 images, {1}: 3 images`, prefix `arbor/run`, layout *subfolders*:
```
output/arbor/run_0/000.png  001.png
output/arbor/run_1/000.png  001.png  002.png
```
With *names* connected the files are called after the names instead (`cat.png`, `dog.png`, …).

## Tips
- Existing files are never overwritten: a `_2`, `_3`, … suffix is added.
- The workflow is embedded in every PNG, like Save Image.
