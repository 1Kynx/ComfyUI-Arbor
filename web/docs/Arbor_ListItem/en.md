# List Item

Pick items from every branch by index, list, range or slice — Grasshopper's List Item and Sub List in one node.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **index** · *STRING / INT / TREE*  
  Which items: `0` · `-1` (last) · `0, 2` · `1:4` (slice, end excluded) · `2-5` (range, end included) · `::2` (every other). A connected number works too, or a tree of indices: its branches pair with the list's in order, so every branch picks its own items.
- **wrap** · *BOOLEAN*  
  Out-of-range indices wrap around the branch length. Off: they give an empty value, so branches stay aligned.

## Outputs

- **tree** · *TREE*  
  The picked items, branch by branch.
- **data** · *any ×N*  
  The picked items as plain data, branch after branch: index k on a tree of sheets gives frame k of every sheet as one list — straight into a node that runs once per item.

## Examples
`{0}: a, b, c, d · {1}: e, f`:

| index | result |
|---|---|
| `1` | `{0}: b · {1}: f` |
| `-1` | `{0}: d · {1}: f` |
| `0, 2` | `{0}: a, c · {1}: e, e` (wrap) |
| `1:` | `{0}: b, c, d · {1}: f` |
| `::2` | `{0}: a, c · {1}: e` |

`:-1` and `1:` pair every item with the next one (a → b, b → c, c → d) — first and last frames for clip after clip. The same syntax picks frames in **Batch Pick**.

## Item k of every branch
The *data* output lists the picks branch after branch. On a tree with one branch per storyboard sheet, index `2` gives the third frame of **every** sheet as one plain list — one item per scene, straight into a node that then runs once per scene. *arbor_h3_long_takes* feeds six of these lists (index 0 … 5) into the six reference pictures and keyframe guides of its long takes.

## One pick per branch
Connect a tree of indices to *index*: `{0}: 2 · {1}: 0 · {2}: 1, 3` takes item 2 of the first branch, item 0 of the second and items 1 and 3 of the third. Type the picks in a **Panel** one line per branch and **Reshape Tree** *graft* them — *arbor_qwen_pick_takes* chooses the best take of every shot this way.
