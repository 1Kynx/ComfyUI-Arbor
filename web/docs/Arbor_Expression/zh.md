# 表达式

对 x 的每一项计算公式（y 先按路径匹配，再按最长列表），对应 Grasshopper 的 Expression。

## 输入

- **表达式** `expression` · *STRING*  
  Python 风格的公式，例如 x * 2 + 1、x > 3、upper(x)、x if i % 2 else -x。
- **x** · *任意，可选*  
  主输入——结果与它的数据树结构相同。不接则只计算一个常量结果。
- **y** · *任意，可选*  
  可选的第二个值。按路径匹配：同一分支，或最近的父分支——y 在 {0} 上就对应 x 的所有 {0;…}——否则按分支顺序；逐项对应，不够时重复最后一项。

## 输出

- **数据** `data` · *任意 ×N*  
  所有计算结果（普通数据）。
- **数据树** `tree` · *数据树*  
  计算结果，结构与 x 相同。比较运算得到布尔值——可直接接「分流」。

## 可用名称
| 名称 | 含义 |
|---|---|
| `x`、`y` | 当前项 |
| `i` | 项在分支内的序号 |
| `b` | 分支序号 |
| `n` | 分支长度 |
| `name` | 分支名（`Mira`、`Mira · lab coat`），没有则为空 |
| `pi`、`e` | 常数 |

## 父分支
x = 服装，在 `{0;0}`、`{0;1}`、`{1;0}` 上；y = 每个角色一条描述，在 `{0}`、`{1}` 上。
`y + " wearing " + x` 让每套服装都配上自己角色的描述——父分支 `{0}` 对应所有 `{0;…}`。模板：*arbor_qwen_character_sheet*。

## 函数
`abs min max round int float str bool len sum sqrt sin cos tan atan2 floor ceil log exp clamp(v, lo, hi) lerp(a, b, t) upper lower strip replace(s, a, b) join(sep, …)`

## 示例
| 表达式 | x = 1, 2, 3 |
|---|---|
| `x * 2 + i` | 2, 5, 8 |
| `x > 1` | False, True, True |
| `lerp(0, 10, i / (n - 1))` | 0, 5, 10 |
| `"shots/" + name + "/" + str(i + 1)` | shots/Arrival/1……——用数据树给每一项生成文件名 |

## 安全
不允许属性访问、import、lambda 和推导式；会产生超大结果的写法（如 `9 ** 9 ** 9`）会直接报错。
