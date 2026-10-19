# Expression

Evaluate a formula for every item of x (y matched longest-list), like Grasshopper's Expression.

## Inputs

- **expression** · *STRING*  
  Python-style formula, e.g. x * 2 + 1, x > 3, upper(x), x if i % 2 else -x.
- **x** · *any, optional*  
  Main input — the result has the same tree layout. Leave empty for a single constant result.
- **y** · *any, optional*  
  Optional second value, matched to x branch by branch, item by item (the last item repeats).

## Outputs

- **result** · *TREE*  
  Results, in x's tree layout. Comparisons give booleans — ready for Cull Pattern / Dispatch.

## Names
| name | meaning |
|---|---|
| `x`, `y` | the current items |
| `i` | item index in the branch |
| `b` | branch index |
| `n` | branch length |
| `pi`, `e` | constants |

## Functions
`abs min max round int float str bool len sum sqrt sin cos tan atan2 floor ceil log exp clamp(v, lo, hi) lerp(a, b, t) upper lower strip replace(s, a, b) join(sep, …)`

## Examples
| expression | x = 1, 2, 3 |
|---|---|
| `x * 2 + i` | 2, 5, 8 |
| `x > 1` | False, True, True |
| `lerp(0, 10, i / (n - 1))` | 0, 5, 10 |

## Safety
Attribute access, imports, lambdas and comprehensions are rejected, and results that would be huge (e.g. `9 ** 9 ** 9`) stop with an error.
