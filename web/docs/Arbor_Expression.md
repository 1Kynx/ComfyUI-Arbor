# Expression

Evaluate a formula for every item of x (y matched by path, then longest-list), like Grasshopper's Expression.

## Inputs

- **expression** · *STRING*  
  Python-style formula, e.g. x * 2 + 1, x > 3, upper(x), x if i % 2 else -x.
- **x** · *any, optional*  
  Main input — the result has the same tree layout. Leave empty for a single constant result.
- **y** · *any, optional*  
  Optional second value. Matched by path: the same branch, or the nearest parent — a y on {0} goes with every {0;…} of x — otherwise branch by branch in order; item by item, the last item repeats.

## Outputs

- **data** · *any ×N*  
  Every result as plain data.
- **tree** · *TREE*  
  Results in x's tree layout. Comparisons give booleans — ready for Dispatch.

## Names
| name | meaning |
|---|---|
| `x`, `y` | the current items |
| `i` | item index in the branch |
| `b` | branch index |
| `n` | branch length |
| `name` | the branch's name (`Mira`, `Mira · lab coat`), or empty |
| `pi`, `e` | constants |

## Parent branches
x = outfits on `{0;0}`, `{0;1}`, `{1;0}`; y = one description per character on `{0}`, `{1}`.
`y + " wearing " + x` gives every outfit its own character's description — the parent `{0}` goes with all of `{0;…}`. Template: *arbor_qwen_character_sheet*.

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
