"""Docs for the Tree, List and Util nodes (see node_info.py for the format)."""

from node_info import node

TREE_EN = "A data tree, or any value / list (becomes branch {0})."
TREE_ZH = ("数据树", "数据树，或任意值 / 列表（会成为分支 {0}）。")
OUT_EN = "The resulting tree."
OUT_ZH = ("数据树", "处理后的数据树。")

# =============================================================== Tree

node("Arbor_XYLists", en=dict(
    desc="One step from parameter values to a batch run: every combination of x, y (and z) as aligned native lists, plus the grid shape for List → Tree.",
    inputs={"x": "Values for the rows: a tree, a list or a single value (e.g. a Panel with 3 / 5 / 7).",
            "y": "Values for the columns (optional).",
            "z": "Optional third parameter: becomes the columns, rows become x × y.",
            "mode": "cross: every combination · zip: item by item (longest list, the last item repeats)."},
    outputs=["x of every run — connect to any widget input (cfg, steps, seed…). The node it feeds runs once per combination.",
             "y of every run.", "z of every run (empty values when z is not connected).",
             "Grid layout of the runs — connect to List → Tree's shape. Its items are the column values, so it also works as Tree → Grid's col_labels.",
             "Number of runs."],
    doc="""## XY plot in five nodes
```
Panel (cfg) ─x─┐               ┌─ x ─► KSampler.cfg ─┐
               ├─ XY Lists ────┤─ y ─► CLIP Text ────┴─► VAE Decode ─► List → Tree ─► Tree → Grid
Panel (text)─y─┘               └─ shape ──────────────────────────────┘
```
1. Type the x values and the y values in two **Panels** and connect their *tree* outputs.
2. Connect XY Lists' *x* / *y* to the inputs you want to vary — ordinary nodes run once per combination.
3. Collect the images with **List → Tree** (*shape* from this node), then **Tree → Grid** (row labels = the x Panel, column labels = *shape*).

Example template: *Templates → ComfyUI-Arbor → arbor_xy_sampler*.

## Tips
- 3 × 4 values = 12 runs; the limit is 10 000.
- Any widget accepts these outputs: drag from *x* onto a widget to turn it into an input.
"""), zh=dict(
    name="XY 组合列表",
    desc="一步从参数值到批量运行：x、y（和 z）的所有组合输出为对齐的原生列表，并输出给「列表 → 数据树」用的网格形状。",
    inputs={"x": ("x", "行的取值：数据树、列表或单个值（例如写着 3 / 5 / 7 的面板）。"),
            "y": ("y", "列的取值（可选）。"),
            "z": ("z", "可选的第三个参数：作为列，行变为 x × y。"),
            "mode": ("模式", "cross 交叉：所有组合 · zip 配对：逐项对应（最长列表，不够时重复最后一项）。")},
    outputs=[("x", "每次运行的 x——接到任意参数输入（cfg、步数、种子……），被接的节点会对每种组合各运行一次。"),
             ("y", "每次运行的 y。"), ("z", "每次运行的 z（未接 z 时为空值）。"),
             ("形状", "运行结果的网格布局——接「列表 → 数据树」的形状。它的项就是列的取值，也可以直接当「数据树 → 网格」的列标签。"),
             ("数量", "运行次数。")],
    doc="""## 五个节点做 XY 对比图
```
面板(cfg) ─x─┐               ┌─ x ─► KSampler.cfg ─┐
             ├─ XY 组合列表 ──┤─ y ─► CLIP 文本 ────┴─► VAE 解码 ─► 列表 → 数据树 ─► 数据树 → 网格
面板(提示词)─y┘               └─ 形状 ─────────────────────────────┘
```
1. 在两个 **面板** 里分别输入 x 和 y 的取值，接它们的 *数据树* 输出。
2. 把 *x* / *y* 接到想要变化的参数上——普通节点会对每种组合各运行一次。
3. 用 **列表 → 数据树**（*形状* 接本节点）收集图片，再接 **数据树 → 网格**（行标签 = x 的面板，列标签 = *形状*）。

示例模板：*模板 → ComfyUI-Arbor → arbor_xy_sampler*。

## 提示
- 3 × 4 个值 = 运行 12 次；上限 1 万次。
- 任何参数都能接这些输出：把 *x* 拖到参数上，它就会变成输入口。
"""))

node("Arbor_TreeToList", en=dict(
    desc="Flatten a tree into a native ComfyUI list: downstream nodes then run once per item. Collect the results with List → Tree.",
    inputs={"tree": TREE_EN},
    outputs=["Every item as a native list (branch order, then item order).", "Number of items."],
    doc="""## How it works
ComfyUI runs a node once per item when it receives a list. **Tree → List** turns a tree into such a list, so an ordinary node (a sampler, a text encoder…) processes every item. Afterwards **List → Tree** with the same tree as *shape* restores the branches.

## Tips
- For an XY plot, **XY Lists** does the combining and flattening in one node.
- Feeding several lists into one node pairs them by index; the shorter list repeats its last item.
"""), zh=dict(
    name="数据树 → 列表",
    desc="把数据树展开成 ComfyUI 原生列表，下游节点会对每一项各运行一次；再用「列表 → 数据树」收回结果。",
    inputs={"tree": TREE_ZH},
    outputs=[("列表", "所有项组成的原生列表（先按分支、再按项的顺序）。"), ("数量", "项数。")],
    doc="""## 原理
ComfyUI 的节点收到列表时会对每一项各运行一次。**数据树 → 列表** 把数据树变成这样的列表，于是普通节点（采样器、文本编码器……）会处理每一项；之后用 **列表 → 数据树** 并接上同一棵树作为 *形状*，即可还原分支。

## 提示
- 做 XY 对比图时，**XY 组合列表** 一个节点就能完成组合和展开。
- 同一个节点接入多个列表时按序号配对，较短的列表重复最后一项。
"""))

node("Arbor_ListToTree", en=dict(
    desc="Collect a native list back into a tree. Connect the tree you fed into Tree → List (or XY Lists' shape) as shape to restore its branches.",
    inputs={"list": "Native list, e.g. the per-item results of a batch run.",
            "shape": "Tree whose branch layout to copy. Its item count must match the list. Without it everything goes into {0}.",
            "split_batch": "Split batches into single frames before rebuilding."},
    outputs=["The values arranged like shape."],
    doc="""## Example
shape `{0}: a, b · {1}: c, d`, list `1, 2, 3, 4` → `{0}: 1, 2 · {1}: 3, 4`.

## Tips
- A count mismatch is an error with both counts in the message — usually the shape is from a different tree than the one that was flattened.
- With a batch size above 1 every result is a batch; that is fine, the batch stays one item.
"""), zh=dict(
    name="列表 → 数据树",
    desc="把原生列表收回成数据树。把当初送进「数据树 → 列表」的那棵树（或 XY 组合列表的形状）接到形状上，即可还原分支。",
    inputs={"list": ("列表", "原生列表，例如批量运行的逐项结果。"),
            "shape": ("形状", "要复制其分支结构的数据树，项数必须与列表一致；不接则全部放进 {0}。"),
            "split_batch": ("拆分批次", "重建前先把批次拆成单帧。")},
    outputs=[("数据树", "按形状排列好的值。")],
    doc="""## 示例
形状 `{0}: a, b · {1}: c, d`，列表 `1, 2, 3, 4` → `{0}: 1, 2 · {1}: 3, 4`。

## 提示
- 数量不一致会报错，并给出两边的数量——通常是形状接错了树，和当初展开的那棵不是同一棵。
- 批次大小大于 1 时，每个结果都是一个批次；没关系，一个批次仍算一项。
"""))

def simple(node_id, en_desc, zh_name, zh_desc, en_doc, zh_doc, extra_en=None, extra_zh=None):
    node(node_id,
         en=dict(desc=en_desc, inputs={"tree": TREE_EN, **(extra_en or {})}, outputs=[OUT_EN], doc=en_doc),
         zh=dict(name=zh_name, desc=zh_desc, inputs={"tree": TREE_ZH, **(extra_zh or {})}, outputs=[OUT_ZH], doc=zh_doc))


simple("Arbor_Graft",
       "Every item gets its own branch: {p} → {p;i} (Grasshopper's Graft).",
       "升树", "每一项单独成为一个分支：{p} → {p;i}（对应 Grasshopper 的 Graft）。",
       """## Example
`{0}: a, b, c` → `{0;0}: a · {0;1}: b · {0;2}: c`

Undo it with **Shift Paths** (offset −1).
""", """## 示例
`{0}: a, b, c` → `{0;0}: a · {0;1}: b · {0;2}: c`

用 **移动路径**（偏移 −1）可以撤销。
""")

simple("Arbor_Flatten",
       "Put every item into one branch (Grasshopper's Flatten).",
       "拍平", "所有项放进同一个分支（对应 Grasshopper 的 Flatten）。",
       """## Example
`{0}: a, b · {1}: c` → `{0}: a, b, c`
""", """## 示例
`{0}: a, b · {1}: c` → `{0}: a, b, c`
""",
       {"path": "Path of the single output branch, e.g. {0}."}, {"path": ("路径", "输出的唯一分支的路径，例如 {0}。")})

simple("Arbor_Simplify",
       "Remove path indices that every branch shares (Grasshopper's Simplify).",
       "简化树", "去掉所有分支共有的路径层级（对应 Grasshopper 的 Simplify）。",
       """## Example
`{0;0;1}: a · {0;0;2}: b` → `{1}: a · {2}: b`
""", """## 示例
`{0;0;1}: a · {0;0;2}: b` → `{1}: a · {2}: b`
""")

simple("Arbor_FlipMatrix",
       "Swap rows and columns: item j of every branch goes to {j} (Grasshopper's Flip Matrix).",
       "翻转矩阵", "行列互换：每个分支的第 j 项放到 {j}（对应 Grasshopper 的 Flip Matrix）。",
       """## Example
`{0}: a, b · {1}: c, d` → `{0}: a, c · {1}: b, d`

Put it before **Tree → Grid** to swap the axes of a sheet.
""", """## 示例
`{0}: a, b · {1}: c, d` → `{0}: a, c · {1}: b, d`

放在 **数据树 → 网格** 前面即可交换对比图的行列。
""")

simple("Arbor_ShiftPaths",
       "Drop path indices: +1 removes the first, −1 the last; branches that end up on the same path are joined (Grasshopper's Shift Paths).",
       "移动路径", "去掉路径层级：+1 去掉第一级，−1 去掉最后一级；落到同一路径的分支会合并（对应 Grasshopper 的 Shift Paths）。",
       """## Example
offset −1: `{0;0}: a · {0;1}: b · {1;0}: c` → `{0}: a, b · {1}: c` (undoes Graft).
""", """## 示例
偏移 −1：`{0;0}: a · {0;1}: b · {1;0}: c` → `{0}: a, b · {1}: c`（撤销升树）。
""",
       {"offset": "Positive drops leading indices, negative drops trailing ones."},
       {"offset": ("偏移", "正数去掉开头的层级，负数去掉末尾的层级。")})

simple("Arbor_Renumber",
       "Re-index branches as {0}, {1}, {2}, … keeping their order.",
       "重新编号", "按原顺序把分支重新编号为 {0}、{1}、{2}……",
       """## Example
`{0;3}: a · {2;1}: b` → `{0}: a · {1}: b`
""", """## 示例
`{0;3}: a · {2;1}: b` → `{0}: a · {1}: b`
""")

node("Arbor_TreeBranch", en=dict(
    desc="Pick one branch by path (e.g. {0;1}) or, when path is empty, by index (Grasshopper's Tree Branch).",
    inputs={"tree": TREE_EN, "path": "Exact path such as {0;1}; leave empty to pick by index.",
            "index": "Branch index when path is empty; wraps around, −1 = last branch."},
    outputs=["A tree with only that branch."],
    doc="""## Tips
- A path that doesn't exist is an error listing the paths that do.
"""), zh=dict(
    name="取分支",
    desc="按路径（如 {0;1}）取出一个分支；路径留空时按序号取（对应 Grasshopper 的 Tree Branch）。",
    inputs={"tree": TREE_ZH, "path": ("路径", "完整路径，如 {0;1}；留空则按序号取。"),
            "index": ("序号", "路径为空时使用的分支序号；会循环，−1 = 最后一个分支。")},
    outputs=[("分支", "只含该分支的数据树。")],
    doc="""## 提示
- 路径不存在时会报错，并列出实际存在的路径。
"""))

node("Arbor_Merge", en=dict(
    desc="Combine trees; items on the same path are appended in input order (Grasshopper's Merge).",
    inputs={"trees": "Trees to combine. Every connection adds a slot."},
    outputs=[OUT_EN],
    doc="""## Example
`{0}: a` + `{0}: b · {1}: c` → `{0}: a, b · {1}: c`

To keep inputs apart instead, use **Entwine**.
"""), zh=dict(
    name="合并",
    desc="合并多棵数据树；相同路径的项按输入顺序追加（对应 Grasshopper 的 Merge）。",
    inputs={"trees": ("数据树", "要合并的数据树，每连一个就多出一个输入口。")},
    outputs=[OUT_ZH],
    doc="""## 示例
`{0}: a` + `{0}: b · {1}: c` → `{0}: a, b · {1}: c`

想让各输入保持分开，用 **编织**。
"""))

node("Arbor_Entwine", en=dict(
    desc="Stack trees side by side: input i is placed under {i;…} (Grasshopper's Entwine).",
    inputs={"trees": "Trees to stack. Every connection adds a slot."},
    outputs=[OUT_EN],
    doc="""## Example
`{0}: a, b` + `{0}: c` → `{0;0}: a, b · {1;0}: c`
"""), zh=dict(
    name="编织",
    desc="把多棵数据树并排放置：第 i 个输入放在 {i;…} 下（对应 Grasshopper 的 Entwine）。",
    inputs={"trees": ("数据树", "要并排的数据树，每连一个就多出一个输入口。")},
    outputs=[OUT_ZH],
    doc="""## 示例
`{0}: a, b` + `{0}: c` → `{0;0}: a, b · {1;0}: c`
"""))

node("Arbor_TreeInfo", en=dict(
    desc="Branch count, item count, depth and the list of paths.",
    inputs={"tree": TREE_EN},
    outputs=["Number of branches.", "Total number of items.", "Longest path length.", "One line per branch: path and item count."],
    doc="""## Tips
- For a quick look a **Panel** shows the same, live; use this node when you need the numbers downstream (e.g. as a count for Series).
"""), zh=dict(
    name="数据树统计",
    desc="分支数、项数、深度和路径列表。",
    inputs={"tree": TREE_ZH},
    outputs=[("分支数", "分支的数量。"), ("项数", "所有项的总数。"), ("深度", "最长路径的层数。"), ("路径", "每个分支一行：路径和项数。")],
    doc="""## 提示
- 只是想看一眼的话，**面板** 能实时显示同样的信息；需要把这些数字接到下游（例如作为等差数列的数量）时用本节点。
"""))

# =============================================================== List

node("Arbor_ListItem", en=dict(
    desc="Pick item i from every branch (Grasshopper's List Item).",
    inputs={"tree": TREE_EN, "index": "Item index; negative counts from the end (−1 = last).",
            "wrap": "Wrap the index around the branch length. Off: out-of-range gives an empty value."},
    outputs=["One item per branch."],
    doc="""## Example
index 1: `{0}: a, b, c · {1}: d, e` → `{0}: b · {1}: e`
"""), zh=dict(
    name="列表取项",
    desc="从每个分支取第 i 项（对应 Grasshopper 的 List Item）。",
    inputs={"tree": TREE_ZH, "index": ("序号", "项序号；负数从末尾数（−1 = 最后一项）。"),
            "wrap": ("循环", "序号超出长度时循环。关闭时超出范围得到空值。")},
    outputs=[("项", "每个分支取出的一项。")],
    doc="""## 示例
序号 1：`{0}: a, b, c · {1}: d, e` → `{0}: b · {1}: e`
"""))

node("Arbor_SubList", en=dict(
    desc="Slice items [start, end) from every branch.",
    inputs={"tree": TREE_EN, "start": "First item to keep (negative counts from the end).",
            "end": "Stop before this item; −1 keeps through the last item."},
    outputs=[OUT_EN],
    doc="""## Example
start 1, end −1: `a, b, c, d` → `b, c, d`
"""), zh=dict(
    name="子列表",
    desc="从每个分支截取 [start, end) 的项。",
    inputs={"tree": TREE_ZH, "start": ("起始", "保留的第一项（负数从末尾数）。"),
            "end": ("结束", "在这一项之前停止；−1 表示一直保留到最后一项。")},
    outputs=[OUT_ZH],
    doc="""## 示例
起始 1，结束 −1：`a, b, c, d` → `b, c, d`
"""))

PATTERN_EN = ("Typed repeating pattern ('T F', 'true,false', '1 0 1', 'TFT'), or connect BOOLEAN values / a boolean tree "
              "(e.g. Expression 'x > 2'), matched branch by branch.")
PATTERN_ZH = ("模式", "输入重复模式（'T F'、'true,false'、'1 0 1'、'TFT'），或接入 BOOLEAN 值 / 布尔数据树"
              "（例如表达式 'x > 2'），按分支匹配。")

node("Arbor_CullPattern", en=dict(
    desc="Keep the items where the pattern is true (Grasshopper's Cull Pattern).",
    inputs={"tree": TREE_EN, "pattern": PATTERN_EN},
    outputs=["The kept items."],
    doc="""## Examples
| pattern | `a, b, c, d` |
|---|---|
| `T F` | a, c |
| `F F T` | c |
| Expression `i % 2 == 1` | b, d |
| a native Boolean = False | (nothing) |
"""), zh=dict(
    name="按模式剔除",
    desc="保留模式为真的项（对应 Grasshopper 的 Cull Pattern）。",
    inputs={"tree": TREE_ZH, "pattern": PATTERN_ZH},
    outputs=[("数据树", "保留下来的项。")],
    doc="""## 示例
| 模式 | `a, b, c, d` |
|---|---|
| `T F` | a, c |
| `F F T` | c |
| 表达式 `i % 2 == 1` | b, d |
| 原生 Boolean = False | （全部剔除） |
"""))

node("Arbor_Dispatch", en=dict(
    desc="Split items into A (pattern true) and B (pattern false) (Grasshopper's Dispatch).",
    inputs={"tree": TREE_EN, "pattern": PATTERN_EN},
    outputs=["Items where the pattern is true.", "Items where the pattern is false."],
    doc="""## Example
pattern `T F`: `a, b, c, d` → A `a, c` · B `b, d`
"""), zh=dict(
    name="分流",
    desc="按模式把项分成 A（为真）和 B（为假）（对应 Grasshopper 的 Dispatch）。",
    inputs={"tree": TREE_ZH, "pattern": PATTERN_ZH},
    outputs=[("A", "模式为真的项。"), ("B", "模式为假的项。")],
    doc="""## 示例
模式 `T F`：`a, b, c, d` → A `a, c` · B `b, d`
"""))

node("Arbor_Partition", en=dict(
    desc="Chop every branch into chunks of size items: {p} → {p;k} (Grasshopper's Partition).",
    inputs={"tree": TREE_EN, "size": "Items per chunk; the last chunk may be shorter."},
    outputs=[OUT_EN],
    doc="""## Example
size 2: `{0}: a, b, c, d, e` → `{0;0}: a, b · {0;1}: c, d · {0;2}: e`

Handy for turning a flat list of images into grid rows.
"""), zh=dict(
    name="分组",
    desc="把每个分支切成每组 size 项：{p} → {p;k}（对应 Grasshopper 的 Partition）。",
    inputs={"tree": TREE_ZH, "size": ("每组项数", "每组的项数；最后一组可能不足。")},
    outputs=[OUT_ZH],
    doc="""## 示例
每组 2 项：`{0}: a, b, c, d, e` → `{0;0}: a, b · {0;1}: c, d · {0;2}: e`

适合把一串平铺的图片排成网格的行。
"""))

node("Arbor_Repeat", en=dict(
    desc="Repeat items: each gives aabbcc, whole gives abcabc.",
    inputs={"tree": TREE_EN, "count": "How many times.", "mode": "each: repeat every item in place · whole: repeat the whole list."},
    outputs=[OUT_EN],
    doc="""## Example
count 2: `a, b` → each `a, a, b, b` · whole `a, b, a, b`
"""), zh=dict(
    name="重复",
    desc="重复项：each 得到 aabbcc，whole 得到 abcabc。",
    inputs={"tree": TREE_ZH, "count": ("次数", "重复的次数。"), "mode": ("模式", "each：每项原地重复 · whole：整个列表重复。")},
    outputs=[OUT_ZH],
    doc="""## 示例
次数 2：`a, b` → each `a, a, b, b` · whole `a, b, a, b`
"""))

simple("Arbor_Reverse",
       "Reverse the item order in every branch.",
       "反转列表", "反转每个分支内的项顺序。",
       "## Example\n`a, b, c` → `c, b, a`\n", "## 示例\n`a, b, c` → `c, b, a`\n")

simple("Arbor_Sort",
       "Sort every branch — numbers first (by value), then text (alphabetically).",
       "排序", "对每个分支排序——数字在前（按数值），文本在后（按字母）。",
       "## Example\n`3, b, 1, a` → `1, 3, a, b`\n", "## 示例\n`3, b, 1, a` → `1, 3, a, b`\n",
       {"descending": "Largest first."}, {"descending": ("降序", "从大到小。")})

node("Arbor_CrossReference", en=dict(
    desc="Every combination of A × B, branch by branch (Grasshopper's Cross Reference). With group on: rows = A, columns = B.",
    inputs={"A": "First set of values.", "B": "Second set of values.",
            "group": "One branch per A item — the result is grid-ready (rows = A, columns = B)."},
    outputs=["A repeated for every B.", "B cycled for every A."],
    doc="""## Example
A `3, 5`, B `x, y, z`, group on:
- A → `{0;0}: 3, 3, 3 · {0;1}: 5, 5, 5`
- B → `{0;0}: x, y, z · {0;1}: x, y, z`

## Tips
- For an XY plot, **XY Lists** does this and the flattening in one node.
- Both outputs work directly as **Tree → Grid** labels.
"""), zh=dict(
    name="交叉组合",
    desc="按分支生成 A × B 的所有组合（对应 Grasshopper 的 Cross Reference）。开启分组时：行 = A，列 = B。",
    inputs={"A": ("A", "第一组取值。"), "B": ("B", "第二组取值。"),
            "group": ("分组", "每个 A 项一个分支——结果可直接做网格（行 = A，列 = B）。")},
    outputs=[("A", "A 按 B 的个数重复。"), ("B", "B 按 A 的个数循环。")],
    doc="""## 示例
A `3, 5`，B `x, y, z`，开启分组：
- A → `{0;0}: 3, 3, 3 · {0;1}: 5, 5, 5`
- B → `{0;0}: x, y, z · {0;1}: x, y, z`

## 提示
- 做 XY 对比图时，**XY 组合列表** 一个节点就能完成组合和展开。
- 两个输出都可以直接当 **数据树 → 网格** 的标签。
"""))

# =============================================================== Util

node("Arbor_IndexSwitch", en=dict(
    desc="Pass through input N (counting connected inputs, wrapping around). Unselected inputs are lazy and never execute.",
    inputs={"index": "0 = first connected input; negative counts from the end; wraps around. A BOOLEAN works too: False = 0, True = 1.",
            "inputs": "Candidates of any type. Every connection adds a slot; only the selected one is computed."},
    outputs=["The selected input.", "Number of connected inputs."],
    doc="""## Tips
- Switch between whole branches of a workflow (models, prompts, image sources) without computing the others.
- Drive *index* with a **Number Slider** (*int* output) or a Boolean for an if / else.
- ComfyUI's own *If/Else Switch* takes exactly two inputs; this one takes up to 32.
"""), zh=dict(
    name="序号切换",
    desc="按序号传出第 N 个输入（按已连接的输入计数，循环）。未选中的输入不会被计算。",
    inputs={"index": ("序号", "0 = 第一个已连接的输入；负数从末尾数；会循环。也可接 BOOLEAN：False = 0，True = 1。"),
            "inputs": ("输入", "任意类型的候选输入，每连一个就多出一个输入口；只有被选中的才会计算。")},
    outputs=[("输出", "被选中的输入。"), ("数量", "已连接的输入数量。")],
    doc="""## 提示
- 在工作流的整条分支之间切换（模型、提示词、图片来源），其余分支完全不计算。
- 用 **数值滑块**（*整数* 输出）或布尔值驱动 *序号*，就是一个 if / else。
- ComfyUI 自带的 If/Else Switch 只能接两路；本节点最多 32 路。
"""))
