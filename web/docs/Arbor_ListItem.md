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

## Examples
`{0}: a, b, c, d · {1}: e, f`:

| index | result |
|---|---|
| `1` | `{0}: b · {1}: f` |
| `-1` | `{0}: d · {1}: f` |
| `0, 2` | `{0}: a, c · {1}: e, e` (wrap) |
| `1:` | `{0}: b, c, d · {1}: f` |
| `::2` | `{0}: a, c · {1}: e` |

`:-1` and `1:` pair every item with the next one (a → b, b → c, c → d): *arbor_h3_continuous_shots* takes its first and last frames this way. The same syntax picks frames in **Batch Pick**.

## One pick per branch
Connect a tree of indices to *index*: `{0}: 2 · {1}: 0 · {2}: 1, 3` takes item 2 of the first branch, item 0 of the second and items 1 and 3 of the third. Type the picks in a **Panel** one line per branch and **Reshape Tree** *graft* them — *arbor_qwen_pick_takes* chooses the best take of every shot this way.
