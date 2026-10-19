# Dispatch

Split items by a true / false pattern: A keeps the true ones, B the false ones — use A alone to cull a list (Grasshopper's Dispatch and Cull Pattern).

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **pattern** · *STRING / BOOLEAN / TREE*  
  Typed repeating pattern ('T F', 'true,false', '1 0 1', 'TFT'), or connect BOOLEAN values / a boolean tree (e.g. Expression 'x > 2'), matched by path — a value on a parent branch covers all of its children.

## Outputs

- **A** · *TREE*  
  Items where the pattern is true — the kept items when culling.
- **B** · *TREE*  
  Items where the pattern is false.

## Examples
| pattern | `a, b, c, d` → A | B |
|---|---|---|
| `T F` | a, c | b, d |
| `F F T` | c | a, b, d |
| Expression `i % 2 == 1` | b, d | a, c |
| a native Boolean = False | (nothing) | everything |

To cull a list, use A and leave B unconnected.
