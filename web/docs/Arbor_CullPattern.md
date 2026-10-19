# Cull Pattern

Deprecated — use Dispatch: its A output is exactly this. Keeps the items where the pattern is true.

## Inputs

- **tree** · *any*  
  A data tree, or any value / list (becomes branch {0}).
- **pattern** · *STRING / BOOLEAN / TREE*  
  Typed repeating pattern ('T F', 'true,false', '1 0 1', 'TFT'), or connect BOOLEAN values / a boolean tree (e.g. Expression 'x > 2'), matched branch by branch.

## Outputs

- **tree** · *TREE*  
  The kept items.

## Examples
| pattern | `a, b, c, d` |
|---|---|
| `T F` | a, c |
| `F F T` | c |
| Expression `i % 2 == 1` | b, d |
| a native Boolean = False | (nothing) |
