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
- **captions** · *any, optional*  
  One caption per cell — e.g. the prompts or seeds of a batch run: a tree shaped like the grid (item by item, branch by branch) or a flat list read cell by cell. Long captions wrap to three lines.
- **fit** · *COMBO (fit · fill · original · stretch)*  
  How clips of different sizes fill a cell: fit (whole clip, bars around) · fill (covers the cell, edges cut) · original (no scaling) · stretch (fills the cell, distorted).
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
- **columns** · *INT*  
  0: one row per branch. N: every branch wraps after N cells — a flat list of 20 becomes 4 rows of 5; a branch's label spans all its rows. Column labels are left out when wrapping.
- **label_direction** · *COMBO (auto · horizontal · vertical)*  
  Row labels: auto (horizontal while they fit in two lines, otherwise standing up) · horizontal · vertical. Standing up, Chinese stacks upright; other text reads bottom to top.
- **caption_style** · *COMBO (below · overlay)*  
  below: under each cell (the sheet grows to fit) · overlay: on a dark bar across the bottom of the picture.

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

## Captions and layout
- **captions**: one text per cell — connect a Prompt Template, the seeds of an XY run or Load Media's *names*. *caption_style* puts them under the cells or on a bar over the clip (drawn into every frame).
- **columns**: wrap long branches (or a flat list) after N cells instead of one very long row.
- **fit = fill** crops every picture to the cell, so mixed sizes still make an even grid.
- Long row labels stand up by themselves (*label_direction* auto).

## Tips
- Use **Reshape Tree** (*flip matrix*) first to swap rows and columns.
- For a single pair, the **Compare Viewer** is quicker: it plays both in sync with a wipe divider.
