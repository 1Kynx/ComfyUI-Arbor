# Split Text

Split text into items — one per line or separator; an empty line starts a new branch.

## Inputs

- **text** · *STRING*  
  The text. Can be typed or connected from any STRING output.
- **separator** · *COMBO (newline · , · ; · |)*  
  What separates items inside a paragraph: newline, comma, semicolon or |.
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

## Tips
- For typing, a **Panel** does the same with a live preview; use this node when the text comes from another node (a file loader, an LLM…).
