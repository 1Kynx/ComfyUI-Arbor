# Split Text

Split text into items — one per line or separator; an empty line starts a new branch. table reads a pasted spreadsheet: one branch per column.

## Inputs

- **text** · *STRING*  
  The text. Can be typed or connected from any STRING output.
- **separator** · *COMBO (newline · , · ; · | · table)*  
  What separates items inside a paragraph: newline, comma, semicolon or |. table: rows copied from a spreadsheet or a CSV — cells split by tabs (or commas when there are none, quotes allowed), the first row names the columns, every column becomes a branch.
- **blank_line_branches** · *BOOLEAN*  
  Paragraphs separated by an empty line become branches {0}, {1}, …
- **strip** · *BOOLEAN*  
  Trim spaces around every item.

## Outputs

- **data** · *STRING ×N*  
  Every item as plain text data (paragraphs one after another).
- **tree** · *TREE*  
  The items as a tree: one branch per paragraph.

## Example
`red, green` ⏎ ⏎ `cat, dog` with separator `,` → `{0}: red, green` · `{1}: cat, dog`.

## Tables
Copy a shot list out of Excel or Google Sheets and paste it, separator `table`:
```
scene     motion                  sound
Arrival   the train pulls away    a distant horn
Village   mist drifts             birdsong
```
→ `{0} scene: Arrival, Village` · `{1} motion: …` · `{2} sound: …`. **Tree Branch** (index 1) takes the motion column for **Prompt Template**; **Reshape Tree** *flip matrix* turns it into one branch per row.

## Tips
- For typing, a **Panel** does the same with a live preview; use this node when the text comes from another node (a file loader, an LLM…).
