# List Item

Pick items from every branch by index, list, range or slice — Grasshopper's List Item and Sub List in one node.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **index** · *STRING / INT*  
  Which items: `0` · `-1` (last) · `0, 2` · `1:4` (slice, end excluded) · `2-5` (range, end included) · `::2` (every other). A connected number works too.
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
