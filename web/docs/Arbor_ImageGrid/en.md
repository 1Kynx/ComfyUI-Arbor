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
  Label rows with their branch path when there are no row labels or row names.

## Outputs

- **image** · *IMAGE*  
  The comparison sheet as one image.

## How to use
- **After a batch run**: connect the decoded images to *images* and **XY Lists'** *shape* to *shape*. Rows and columns come out right and are labelled — rows with the x values, columns with the y values. Nothing else to connect.
- **From a tree**: connect any image tree — each branch becomes a row. Use **Reshape Tree** (*flip matrix*) first to swap rows and columns.

## Tips
- Long labels wrap to three lines and are cut with "…".
- Save the sheet with Save Image, or every image separately with **Save Images by Path**.
