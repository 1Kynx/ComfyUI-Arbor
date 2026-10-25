# 拆分文本

把文本拆成多项——每行或每个分隔符一项；空行开始新分支。table 读取粘贴的表格：每列一个分支。

## 输入

- **文本** `text` · *STRING*  
  要拆分的文本，可以手动输入，也可以接任意 STRING 输出。
- **分隔符** `separator` · *COMBO (newline · , · ; · | · table)*  
  段落内用什么分隔各项：换行、逗号、分号或 |。table 表格：从电子表格或 CSV 复制来的行——用制表符分隔单元格（没有制表符时用逗号，支持引号），第一行是列名，每一列成为一个分支。
- **空行分支** `blank_line_branches` · *BOOLEAN*  
  用空行分隔的段落分别成为分支 {0}、{1}……
- **去除首尾空白** `strip` · *BOOLEAN*  
  去掉每一项两端的空格。

## 输出

- **数据** `data` · *STRING ×N*  
  拆分后的所有项（普通文本数据，各段依次排列）。
- **数据树** `tree` · *数据树*  
  拆分后的数据树：每个段落一个分支。

## 示例
`red, green` ⏎ ⏎ `cat, dog`，分隔符 `,` → `{0}: red, green` · `{1}: cat, dog`。

## 表格
从 Excel 或在线表格复制一份镜头表粘贴进来，分隔符选 `table`：
```
scene     motion                  sound
Arrival   the train pulls away    a distant horn
Village   mist drifts             birdsong
```
→ `{0} scene: Arrival, Village` · `{1} motion: …` · `{2} sound: …`。用 **数据树分支**（序号 1）取出 motion 列接 **提示词模板**；**重塑数据树** 的 *翻转矩阵* 可以变成每行一个分支。

## 提示
- 手动输入时用 **面板** 效果相同，还能实时预览；文本来自其他节点（读文件、LLM……）时用本节点。
