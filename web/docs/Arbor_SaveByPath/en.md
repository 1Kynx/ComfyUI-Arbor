# Save by Path

Save a tree keeping its structure — pictures as PNG, videos as MP4, audio as FLAC, text as TXT: one subfolder (or filename part) per branch, named after the branch when it has a name, with optional names per file.

## Inputs

- **tree** · *any*  
  What to save — a tree, a list or a single value. Picture batches are saved frame by frame, audio batches clip by clip; other values are skipped.
- **filename_prefix** · *STRING*  
  Where to save: a folder / prefix inside ComfyUI's output folder (arbor/run), output/…, or an absolute path such as D:/renders/run — the folder icon at the end of the box picks the folder. Outside the output folder only while ComfyUI listens on this computer alone. Supports %date%-style variables.
- **layout** · *COMBO (subfolders · flat)*  
  subfolders: prefix/0-1/000.png (a named branch: prefix/0-1 · name/000.png) · flat: prefix_0-1_000.png. A plain list (one unnamed branch {0}) goes straight under the prefix: prefix/000.png · prefix_000.png
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
Pictures become `000.png …`, audio `000.flac …`, text `000.txt …` — a branch may mix them. **Load Folder** with `output/arbor/h3_orbit` (kind *videos*) reads the tree back, names included. Template: *arbor_h3_orbit*.

With *names* connected the files are called after the names instead (`cat.png`, `dog.png`, …).

## Saving anywhere
Click the **folder icon** at the end of the prefix box to pick the destination with the system's folder dialog — the last part of the prefix (`run`, `batch`) is kept as the file name part. An absolute prefix (`D:/renders/run`) saves outside ComfyUI's output folder:
- allowed while ComfyUI listens on this computer alone (the default, no `--listen`);
- refused when ComfyUI is opened to the network (`--listen`), because anyone who can queue a workflow could then write anywhere on your disk — set the environment variable `ARBOR_SAVE_ANYWHERE=1` to allow it anyway.

Previews of files saved outside the output folder are shown from a copy in the temp folder.

## Tips
- Existing files are never overwritten: a `_2`, `_3`, … suffix is added.
- The workflow is embedded in every PNG, MP4 and FLAC, like ComfyUI's own save nodes.
