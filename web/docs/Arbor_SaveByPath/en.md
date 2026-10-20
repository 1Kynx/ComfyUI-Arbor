# Save by Path

Save a tree keeping its structure — pictures as PNG, videos as MP4, audio as FLAC, text as TXT: one subfolder (or filename part) per branch, named after the branch when it has a name, with optional names per file.

## Inputs

- **tree** · *any*  
  What to save — a tree, a list or a single value. Picture batches are saved frame by frame, audio batches clip by clip; other values are skipped.
- **filename_prefix** · *STRING*  
  Folder / prefix inside ComfyUI's output folder (saving outside it is not allowed, as with Save Image). Supports %date%-style variables.
- **layout** · *COMBO (subfolders · flat)*  
  subfolders: prefix/0-1/000.png (a named branch: prefix/0-1 · name/000.png) · flat: prefix_0-1_000.png
- **names** · *any, optional*  
  Optional file names, matched to the files item by item (e.g. Load Folder's names or a Prompt Template).

## Outputs

- **paths** · *TREE*  
  Saved file paths, in the same tree layout (and with the same names).

## Example
Tree `{0} Arrival: 2 clips · {1} Village: 1 clip`, prefix `arbor/h3`, layout *subfolders*:
```
output/arbor/h3/0 · Arrival/000.mp4  001.mp4
output/arbor/h3/1 · Village/000.mp4
```
Pictures become `000.png …`, audio `000.flac …`, text `000.txt …` — a branch may mix them. **Load Folder** with `output/arbor/h3` (kind *videos*) reads the tree back, names included. Template: *arbor_h3_storyboard_video*.

With *names* connected the files are called after the names instead (`cat.png`, `dog.png`, …).

## Tips
- Existing files are never overwritten: a `_2`, `_3`, … suffix is added.
- The workflow is embedded in every PNG, MP4 and FLAC, like ComfyUI's own save nodes.
