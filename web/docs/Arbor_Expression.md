# Expression

Evaluate a formula for every item, like Grasshopper's Expression: x and y are matched branch by branch in order and item by item (longest list).

## Inputs

- **expression** · *STRING*  
  Python-style formula, e.g. x * 2 + 1, x > 3, upper(x), x if i % 2 else -x.
- **x** · *any, optional*  
  First value — a tree, a list or a single value. Leave both empty for a single constant result.
- **y** · *any, optional*  
  Optional second value, matched to x branch by branch in order and item by item; whichever is shorter repeats its last branch / item.

## Outputs

- **data** · *any ×N*  
  Every result as plain data.
- **tree** · *TREE*  
  Results as a tree, with the paths of the input whose paths are longest (x on a tie). Comparisons give booleans — ready for Dispatch.

## Names
| name | meaning |
|---|---|
| `x`, `y` | the current items |
| `i` | item index in the branch |
| `b` | branch index |
| `n` | branch length |
| `name` | the branch's name (`Mira`, `Mira · lab coat`), or empty |
| `pi`, `e` | constants |

## Data matching (as in Grasshopper)
- Branches pair **in order**, not by path: x's 1st branch with y's 1st, 2nd with 2nd…; the input with fewer branches repeats its last one.
- Items pair **longest-list**: the shorter list repeats its last item, so a single y works with every x.
- The result takes the paths of the input with the **longest paths** (x on a tie); if that input runs out of branches, its last path counts on (`{0;1;0}`, `{0;1;1}`, …).

So combine data where the branches line up: one description per character with the outfits per character (same branches, same order) — then go deeper. Template: *arbor_qwen_character_sheet*.

## Functions
`abs min max round int float str bool len sum sqrt sin cos tan atan2 floor ceil log exp clamp(v, lo, hi) lerp(a, b, t) upper lower strip replace(s, a, b) join(sep, …)`

## Examples
| expression | x = 1, 2, 3 |
|---|---|
| `x * 2 + i` | 2, 5, 8 |
| `x > 1` | False, True, True |
| `lerp(0, 10, i / (n - 1))` | 0, 5, 10 |
| `"shots/" + name + "/" + str(i + 1)` | shots/Arrival/1, … — a file name per item from the tree |

## Safety
Attribute access, imports, lambdas and comprehensions are rejected, and results that would be huge (e.g. `9 ** 9 ** 9`) stop with an error.
