# 按模式剔除

保留模式为真的项（对应 Grasshopper 的 Cull Pattern）。

## 输入

- **数据树** `tree` · *任意*  
  数据树，或任意值 / 列表（会成为分支 {0}）。
- **模式** `pattern` · *STRING / BOOLEAN / 数据树*  
  输入重复模式（'T F'、'true,false'、'1 0 1'、'TFT'），或接入 BOOLEAN 值 / 布尔数据树（例如表达式 'x > 2'），按分支匹配。

## 输出

- **数据树** `tree` · *数据树*  
  保留下来的项。

## 示例
| 模式 | `a, b, c, d` |
|---|---|
| `T F` | a, c |
| `F F T` | c |
| 表达式 `i % 2 == 1` | b, d |
| 原生 Boolean = False | （全部剔除） |
