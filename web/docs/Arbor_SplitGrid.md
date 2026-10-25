# Split Grid

Cut a grid picture — a storyboard sheet, a contact sheet, a sprite sheet — into its panels, row by row. Gutters and margins are found and left out; without them the picture is cut evenly.

## Inputs

- **image** · *IMAGE*  
  One sheet, or a batch / list of sheets — each sheet becomes one branch.
- **rows** · *INT*  
  How many rows of panels the sheet has.
- **columns** · *INT*  
  How many panels per row.
- **find_gutters** · *BOOLEAN*  
  Look for gutters and margins — lines of one flat colour — near every cut and leave them out, so panels that are not quite even still come out clean. Off: cut into even parts.
- **inset** · *INT*  
  Pixels shaved off every panel edge, to drop the soft edge of a gutter.

## Outputs

- **data** · *IMAGE ×N*  
  Every panel as plain data, in reading order (left to right, top to bottom) — panels may differ by a few pixels in size.
- **tree** · *TREE*  
  One branch per sheet, its panels in reading order.

## Why a whole sheet
An image model that draws all the frames of a storyboard in one picture keeps the character, the light and the palette far more consistent than separate renders do. Ask for the grid in the prompt (*six panels, three columns and two rows, thin white gutters, no text*), give the sheet the panels' combined aspect (3 × 16:9 by 2 rows ≈ 8:3, e.g. 3264 × 1216), and cut it here.

Template: *arbor_h3_continuous_shots* draws a 3 × 2 sheet with MOSS-Image, cuts it into six keyframes and animates from each one to the next.

## Checking the cuts
After a run the node shows the sheet with everything that was cut away shaded red and every panel outlined and numbered (0, 1, 2 … — the numbers **List Item** uses). A panel that swallowed a gutter, or two panels merged into one, shows at a glance.

## Tips
- The gutters only need to be roughly where an even split would cut; drawn grids are rarely exact and the found gutter wins.
- Panels come out a few pixels apart in size; video and image models resize them anyway, **Smart Resize** evens them out.
- The inverse of **Image Grid**.
