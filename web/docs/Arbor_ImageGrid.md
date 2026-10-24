# Image Grid

Lay images out as an XY comparison sheet: each branch is a row, each item a column.

## Inputs

- **images** · *any*  
  An image tree — or the plain images of a batch run, together with shape.
- **shape** · *any, optional*  
  XY Lists' shape: pours plain images into rows × columns and labels them (rows by x, columns by y).
- **row_labels** · *any, optional*  
  One label per row — a list, or a tree with one branch per row. Not needed when the tree or shape names its rows (XY Lists, Prompt Template, Cross Reference).
- **col_labels** · *any, optional*  
  One label per column — overrides the labels taken from shape (which labels the columns when every row holds the same values, as in XY Lists).
- **captions** · *any, optional*  
  One caption per cell — e.g. the prompts or seeds of a batch run: a tree shaped like the grid (item by item, branch by branch) or a flat list read cell by cell. Long captions wrap to three lines.
- **fit** · *COMBO (fit · fill · original · stretch)*  
  How pictures of different sizes fill a cell: fit (whole picture, bars around) · fill (covers the cell, edges cut) · original (no scaling) · stretch (fills the cell, distorted).
- **cell_size** · *INT*  
  Longest side of a cell in pixels; 0 = the largest image's size.
- **gap** · *INT*  
  Space between cells and around the sheet, in pixels.
- **font_size** · *INT*  
  Label font size. Chinese labels render with a CJK font when one is installed.
- **theme** · *COMBO (light · dark)*  
  Light or dark sheet background.
- **path_labels** · *BOOLEAN*  
  Label rows with their branch path when there are no row labels or row names.
- **columns** · *INT*  
  0: one row per branch. N: every branch wraps after N cells — a flat list of 20 becomes 4 rows of 5; a branch's label spans all its rows. Column labels are left out when wrapping.
- **label_direction** · *COMBO (auto · horizontal · vertical)*  
  Row labels: auto (horizontal while they fit in two lines, otherwise standing up) · horizontal · vertical. Standing up, Chinese stacks upright; other text reads bottom to top.
- **caption_style** · *COMBO (below · overlay)*  
  below: under each cell (the sheet grows to fit) · overlay: on a dark bar across the bottom of the picture.

## Outputs

- **image** · *IMAGE*  
  The comparison sheet as one image.

## How to use
- **After a batch run**: connect the decoded images to *images* and **XY Lists'** *shape* to *shape*. Rows and columns come out right and are labelled — rows with the x values, columns with the y values. Nothing else to connect.
- **From a tree**: connect any image tree — each branch becomes a row. Use **Reshape Tree** (*flip matrix*) first to swap rows and columns.

## Captions and layout
- **captions**: one text per cell — connect a Prompt Template, the seeds of an XY run or Load Media's *names*. *caption_style* puts them under the cells or on a bar over the picture.
- **columns**: wrap long branches (or a flat list) after N cells instead of one very long row.
- **fit = fill** crops every picture to the cell, so mixed sizes still make an even grid.
- Long row labels stand up by themselves (*label_direction* auto).

## Tips
- Long labels wrap to three lines and are cut with "…".
- Save the sheet with Save Image, or every image separately with **Save by Path**.
