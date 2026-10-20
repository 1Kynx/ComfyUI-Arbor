# Video Grid

Image Grid for video: each branch is a row, each clip a column, all playing in sync in one labelled video.

## Inputs

- **videos** · *any*  
  A video tree — or the plain videos of a batch run, together with shape. An image batch counts as one clip (its frames played at the grid's frame rate).
- **shape** · *any, optional*  
  XY Lists' shape: pours plain videos into rows × columns and labels them (rows by x, columns by y).
- **row_labels** · *any, optional*  
  One label per row — a list, or a tree with one branch per row. Not needed when the tree or shape names its rows.
- **col_labels** · *any, optional*  
  One label per column — overrides the labels taken from shape.
- **fit** · *COMBO (fit · original · stretch)*  
  How clips of different sizes fill a cell: fit (scale to fit), original (no scaling), stretch.
- **cell_size** · *INT*  
  Longest side of a cell in pixels; 0 = the largest clip's size. Keep it modest — the grid video is width × height of all cells.
- **gap** · *INT*  
  Space between cells and around the grid, in pixels.
- **font_size** · *INT*  
  Label font size. Chinese labels render with a CJK font when one is installed.
- **theme** · *COMBO (light · dark)*  
  Light or dark background.
- **path_labels** · *BOOLEAN*  
  Label rows with their branch path when there are no row labels or row names.
- **fps** · *FLOAT*  
  Frame rate of the grid video; 0 = the highest frame rate among the clips. Every clip keeps its own speed.
- **audio** · *COMBO (none · mix)*  
  none: a silent grid · mix: every clip's sound mixed together (loudness kept below clipping).

## Outputs

- **video** · *VIDEO*  
  The grid as one VIDEO (H.264 MP4 in the temp folder) — save it with Save by Path or Save Video, or compare it in the Compare Viewer.

## How to use
- **From a tree**: connect any video tree, e.g. *arbor_h3_storyboard_video*'s clips through **Construct Tree** (one row per scene), or **Load Folder** with kind *videos* (one row per folder).
- **After a batch run**: connect the plain videos to *videos* and **XY Lists'** *shape* to *shape* — rows and columns are laid out and labelled like **Image Grid**.
- The node shows the grid video when it runs; it also works on its own, nothing needs to follow it.

## Timing
- All clips start together. Each plays at its own frame rate; shorter clips hold their last frame until the longest one ends.
- Clips are decoded straight at cell size, frame by frame, so long or large videos do not need much memory.

## Tips
- Use **Reshape Tree** (*flip matrix*) first to swap rows and columns.
- For a single pair, the **Compare Viewer** is quicker: it plays both in sync with a wipe divider.
