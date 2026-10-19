# 重复

重复项：each 得到 aabbcc，whole 得到 abcabc。

## 输入

- **数据树** `tree` · *任意*  
  数据树，或任意值 / 列表（会成为分支 {0}）。
- **次数** `count` · *INT*  
  重复的次数。
- **模式** `mode` · *COMBO (each · whole)*  
  each：每项原地重复 · whole：整个列表重复。

## 输出

- **数据树** `tree` · *数据树*  
  处理后的数据树。

## 示例
次数 2：`a, b` → each `a, a, b, b` · whole `a, b, a, b`
