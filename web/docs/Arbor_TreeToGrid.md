# Tree → Grid

Lay an image tree out as an XY comparison sheet: each branch is a row, each item a column.

## Inputs

- **images** · *any*  
  Image tree — one branch per row. A plain image list becomes a single row; batches add columns.
- **row_labels** · *any, optional*  
  One label per row: a list, or a tree with one branch per row (XY Lists' x input or Cross Reference A work directly).
- **col_labels** · *any, optional*  
  One label per column: a list, or a tree whose branches hold the column values (XY Lists' shape or Cross Reference B work directly).
- **fit** · *COMBO (fit · original · stretch)*  
  How images of different sizes fill a cell: fit (scale to fit), original (no scaling), stretch.
- **cell_size** · *INT*  
  Longest side of a cell in pixels; 0 = the largest image's size.
- **gap** · *INT*  
  Space between cells and around the sheet, in pixels.
- **font_size** · *INT*  
  Label font size. Chinese labels render with a CJK font when one is installed.
- **theme** · *COMBO (light · dark)*  
  Light or dark sheet background.
- **path_labels** · *BOOLEAN*  
  Label rows with their branch path when no row labels are connected.

## Outputs

- **image** · *IMAGE*  
  The comparison sheet as one image.

## How to use
1. Get the images into a tree whose branches are rows — e.g. **List → Tree** with the *shape* from **XY Lists**.
2. Connect the x values to *row_labels* and the shape (or y values) to *col_labels*.
3. Use **Flip Matrix** before this node to swap rows and columns.

## Tips
- Long labels wrap to three lines and are cut with "…".
- Save the sheet with Save Image, or every cell separately with **Save by Path**.
