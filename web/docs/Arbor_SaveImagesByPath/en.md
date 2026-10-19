# Save Images by Path

Save an image tree keeping its structure: one subfolder (or filename part) per branch, named after the branch when it has a name, with optional names per file.

## Inputs

- **images** · *any*  
  Image tree to save. Batches are saved frame by frame.
- **filename_prefix** · *STRING*  
  Folder / prefix inside ComfyUI's output folder. Supports %date%-style variables like Save Image.
- **layout** · *COMBO (subfolders · flat)*  
  subfolders: prefix/0-1/000.png (a named branch: prefix/0-1 · name/000.png) · flat: prefix_0-1_000.png
- **names** · *any, optional*  
  Optional file names, matched to the images item by item (e.g. Load Folder's names or a Prompt Template).

## Outputs

- **paths** · *TREE*  
  Saved file paths, in the same tree layout.

## Example
Tree `{0}: 2 images, {1}: 3 images`, prefix `arbor/run`, layout *subfolders*:
```
output/arbor/run/0/000.png  001.png
output/arbor/run/1/000.png  001.png  002.png
```
Named branches (storyboard scenes from a Panel's `# title` lines, Load Folder folders) keep their names: `output/arbor/run/0 · Arrival/000.png`. **Load Folder** with `output/arbor/run` reads the tree back, names included.

With *names* connected the files are called after the names instead (`cat.png`, `dog.png`, …).

## Tips
- Existing files are never overwritten: a `_2`, `_3`, … suffix is added.
- The workflow is embedded in every PNG, like Save Image.
