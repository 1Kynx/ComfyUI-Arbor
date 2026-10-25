"""Docs for the Tree and List nodes (see node_info.py for the format)."""

from node_info import node

TREE_EN = "A data tree, or any value / list (becomes branch {0})."
TREE_ZH = ("数据树", "数据树，或任意值 / 列表（会成为分支 {0}）。")
OUT_EN = "The resulting tree."
OUT_ZH = ("数据树", "处理后的数据树。")


def simple(node_id, en_desc, zh_name, zh_desc, en_doc, zh_doc, extra_en=None, extra_zh=None):
    node(node_id,
         en=dict(desc=en_desc, inputs={"tree": TREE_EN, **(extra_en or {})}, outputs=[OUT_EN], doc=en_doc),
         zh=dict(name=zh_name, desc=zh_desc, inputs={"tree": TREE_ZH, **(extra_zh or {})}, outputs=[OUT_ZH], doc=zh_doc))


# =============================================================== Tree

node("Arbor_XYLists", en=dict(
    desc="From values to a batch run: every combination of x, y (and z) as aligned plain data — wire them into ordinary nodes and they run once per combination — plus the shape of the runs. With only x connected it flattens any tree into plain data.",
    inputs={"x": "Values for the rows — or any tree to flatten into plain data.",
            "y": "Values for the columns (optional).",
            "z": "Optional third parameter: becomes the columns, rows become x × y.",
            "mode": "cross: every combination · zip: item by item (longest list, the last item repeats); the shape keeps the branches of the longest input (x, then y, then z) — one row when that is a plain list."},
    outputs=["x of every run — connect to any widget input (cfg, steps, seed…). The node it feeds runs once per combination.",
             "y of every run.", "z of every run (empty values when z is not connected).",
             "Layout of the runs: connect to Image Grid (rows × columns) or Construct Tree (back into a tree). Each row is named after its x value and its items are the column values, so Image Grid labels itself. With only x, it is x's own tree.",
             "Number of runs."],
    doc="""## XY plot in four nodes
```
Panel (cfg) ─x─┐               ┌─ x ─► KSampler.cfg ─┐
               ├─ XY Lists ────┤─ y ─► CLIP Text ────┴─► VAE Decode ─► Image Grid
Panel (text)─y─┘               └─ shape ─────────────────────────────────┘
```
1. Type the x values and the y values in two **Panels** (or use **Number Sequence**) and connect them.
2. Connect *x* / *y* to the inputs you want to vary — ordinary nodes run once per combination.
3. Connect the decoded images and *shape* to **Image Grid**. It lays them out as rows × columns and labels both: the rows are named after x, the columns are the y values.

Example template: *Templates → ComfyUI-Arbor → arbor_qwen_lora_sweep*.

## Flatten any tree
Connect a tree to *x* only: *x* becomes its items as plain data (ordinary nodes run once per item) and *shape* is the tree itself. Run something per item, then put the results back with **Construct Tree** (*shape* = this shape). **Tree to Data** does the same in a smaller node.

## Flatten two trees side by side
Two trees of the same layout — pictures and their edit instructions from **Cross Reference**, say — go to *x* and *y* in **zip** mode: both come out as plain data, item k with item k, and *shape* keeps the branches of the longest input for putting the results back. Template: *arbor_qwen_edit_by_scene*.

## Tips
- 3 × 4 values = 12 runs; the limit is 10 000.
- Any widget accepts these outputs: drag from *x* onto a widget to turn it into an input.
"""), zh=dict(
    name="XY 组合列表",
    desc="从取值到批量运行：x、y（和 z）的所有组合输出为对齐的普通数据——接到普通节点上，每种组合运行一次——并输出运行结果的结构。只接 x 时，可把任意数据树展开成普通数据。",
    inputs={"x": ("x", "行的取值——或任意要展开成普通数据的数据树。"),
            "y": ("y", "列的取值（可选）。"),
            "z": ("z", "可选的第三个参数：作为列，行变为 x × y。"),
            "mode": ("模式", "cross 交叉：所有组合 · zip 配对：逐项对应（最长列表，不够时重复最后一项）；结构沿用最长那个输入的分支（依次看 x、y、z）——它是普通列表时就是单行。")},
    outputs=[("x", "每次运行的 x——接到任意参数输入（cfg、步数、种子……），被接的节点会对每种组合各运行一次。"),
             ("y", "每次运行的 y。"), ("z", "每次运行的 z（未接 z 时为空值）。"),
             ("结构", "运行结果的布局：接「图像网格」排成行 × 列，或接「构建数据树」收回成数据树。每行以 x 的取值命名，项就是列的取值，所以图像网格会自动标注行和列。只接 x 时，它就是 x 自己的数据树。"),
             ("数量", "运行次数。")],
    doc="""## 四个节点做 XY 对比图
```
面板(cfg) ─x─┐               ┌─ x ─► KSampler.cfg ─┐
             ├─ XY 组合列表 ──┤─ y ─► CLIP 文本 ────┴─► VAE 解码 ─► 图像网格
面板(提示词)─y┘               └─ 结构 ────────────────────────────────┘
```
1. 在两个 **面板** 里分别输入 x 和 y 的取值（或用 **数列**），接到 x、y 上。
2. 把 *x* / *y* 接到想要变化的参数上——普通节点会对每种组合各运行一次。
3. 解码后的图片和 *结构* 一起接 **图像网格**：自动排成行 × 列，行和列都自动标注——行以 x 命名，列是 y 的取值。

示例模板：*模板 → ComfyUI-Arbor → arbor_qwen_lora_sweep*。

## 展开任意数据树
只接 *x*：*x* 输出它的所有项（普通数据，普通节点逐项运行），*结构* 就是这棵树本身。逐项处理后，用 **构建数据树**（*结构* 接这里）把结果收回原来的分支。**数据树转数据** 用更小的节点做同样的事。

## 并排展开两棵树
两棵结构相同的数据树——例如 **交叉组合** 输出的图片和对应的编辑指令——分别接 *x* 和 *y*，用 **zip** 模式：两者都变成普通数据，第 k 项对第 k 项，*结构* 沿用最长那个输入的分支，用来把结果收回去。模板：*arbor_qwen_edit_by_scene*。

## 提示
- 3 × 4 个值 = 运行 12 次；上限 1 万次。
- 任何参数都能接这些输出：把 *x* 拖到参数上，它就会变成输入口。
"""))

node("Arbor_TreeToData", en=dict(
    desc="Every item of a tree as plain data, so ordinary nodes run once per item — plus its shape, to put the results back.",
    inputs={"tree": "The tree to run over — every item becomes one run of the nodes it feeds."},
    outputs=["Every item as plain data, in branch order: connect to any ordinary node (a text encoder, a sampler input…) and it runs once per item.",
             "The tree itself: connect to Construct Tree or Image Grid to put the results back into the same branches, with their names."],
    doc="""## Round trip
```
tree ─► Tree to Data ─ data ─► ordinary nodes (run once per item) ─┐
                    └─ shape ───────────────────────────────────► Construct Tree / Image Grid
```
`{0} Arrival: a, b · {1} Village: c` → *data* `a, b, c` → three runs → back as `{0} Arrival: A, B · {1} Village: C`.

## Tips
- A small node on purpose: for one tree it does what **XY Lists** does with only *x* connected.
- Two or three trees of the same layout (pictures and their edit instructions, say) flatten side by side with **XY Lists** in *zip* mode.
- The data nodes (Panel, Split Text, Prompt Template, Expression, Random, Collect) already have a *data* output; this is for every other tree.
"""), zh=dict(
    name="数据树转数据",
    desc="把数据树的所有项变成普通数据，让普通节点逐项运行——同时输出它的结构，用来把结果收回去。",
    inputs={"tree": ("数据树", "要逐项运行的数据树——每一项都会让下游节点运行一次。")},
    outputs=[("数据", "所有项（普通数据），按分支顺序排列：接到任意普通节点（文本编码器、采样器的参数……），它就逐项运行。"),
             ("结构", "这棵树本身：接「构建数据树」或「图像网格」，把结果连同分支名收回原来的分支。")],
    doc="""## 往返
```
数据树 ─► 数据树转数据 ─ 数据 ─► 普通节点（逐项运行）─┐
                     └─ 结构 ──────────────────────► 构建数据树 / 图像网格
```
`{0} Arrival: a, b · {1} Village: c` → *数据* `a, b, c` → 运行三次 → 收回为 `{0} Arrival: A, B · {1} Village: C`。

## 提示
- 这是个特意做小的节点：对一棵树来说，它和只接 *x* 的 **XY 组合列表** 作用相同。
- 两三棵结构相同的数据树（比如图片和对应的编辑指令）要并排展开时，用 **XY 组合列表** 的 *zip* 模式。
- 数据类节点（面板、拆分文本、提示词模板、表达式、随机、收集）本身就有 *数据* 输出；本节点用于其它所有数据树。
"""))

node("Arbor_ReshapeTree", en=dict(
    desc="Change how items are grouped into branches — Grasshopper's Graft, Flatten, Simplify, Flip Matrix, Shift Paths and Renumber in one node.",
    inputs={"tree": TREE_EN,
            "mode": "graft: every item its own branch · flatten: everything in one branch · simplify: drop path indices all branches share · flip matrix: swap rows and columns · shift paths: drop path indices, joining branches that meet · renumber: {0}, {1}, {2}, … in order.",
            "mode.path": "flatten: path of the single output branch, e.g. {0}.",
            "mode.offset": "shift paths: −1 drops the last index (undoes graft), +1 the first."},
    outputs=[OUT_EN],
    doc="""## Modes
| mode | example |
|---|---|
| graft | `{0}: a, b, c` → `{0;0}: a · {0;1}: b · {0;2}: c` |
| flatten | `{0}: a, b · {1}: c` → `{0}: a, b, c` |
| simplify | `{0;0;1}: a · {0;0;2}: b` → `{1}: a · {2}: b` |
| flip matrix | `{0}: a, b · {1}: c, d` → `{0}: a, c · {1}: b, d` · `{0;0}`, `{0;1}` → `{0;0}`, `{0;1}`, … (the prefix stays, like Grasshopper) |
| shift paths (−1) | `{0;0}: a · {0;1}: b · {1;0}: c` → `{0}: a, b · {1}: c` |
| renumber | `{0;3}: a · {2;1}: b` → `{0}: a · {1}: b` |

## Tips
- *flip matrix* before **Image Grid** swaps the axes of a sheet.
- *graft* then a per-item operation, then *shift paths −1*, groups the results back.
- Names travel with the structure: after *graft* the old branch's name names the group, and *shift paths −1* lands back on it — `Mira · lab coat` rows fold into a `Mira` row.
- Search for graft, flatten, flip matrix… — they all find this node.
"""), zh=dict(
    name="重组数据树",
    desc="改变项在分支里的分组方式——一个节点包含 Grasshopper 的 Graft、Flatten、Simplify、Flip Matrix、Shift Paths 和 Renumber。",
    inputs={"tree": TREE_ZH,
            "mode": ("模式", "graft 升树：每项单独一个分支 · flatten 拍平：全部放进一个分支 · simplify 简化：去掉所有分支共有的路径层级 · flip matrix 翻转矩阵：行列互换 · shift paths 移动路径：去掉路径层级，落到同一路径的分支合并 · renumber 重新编号：按顺序编为 {0}、{1}、{2}……"),
            "mode.path": ("路径", "flatten：输出的唯一分支的路径，例如 {0}。"),
            "mode.offset": ("偏移", "shift paths：−1 去掉最后一级（撤销升树），+1 去掉第一级。")},
    outputs=[OUT_ZH],
    doc="""## 模式
| 模式 | 示例 |
|---|---|
| graft 升树 | `{0}: a, b, c` → `{0;0}: a · {0;1}: b · {0;2}: c` |
| flatten 拍平 | `{0}: a, b · {1}: c` → `{0}: a, b, c` |
| simplify 简化 | `{0;0;1}: a · {0;0;2}: b` → `{1}: a · {2}: b` |
| flip matrix 翻转矩阵 | `{0}: a, b · {1}: c, d` → `{0}: a, c · {1}: b, d` · `{0;0}`、`{0;1}` → `{0;0}`、`{0;1}`……（前缀保留，与 Grasshopper 相同） |
| shift paths 移动路径（−1） | `{0;0}: a · {0;1}: b · {1;0}: c` → `{0}: a, b · {1}: c` |
| renumber 重新编号 | `{0;3}: a · {2;1}: b` → `{0}: a · {1}: b` |

## 提示
- 在 **图像网格** 前用 *翻转矩阵* 可以交换对比图的行列。
- 先 *升树*，逐项处理后再 *移动路径 −1*，结果就重新分好组。
- 分支名跟着结构走：*升树* 后原分支的名字成为这一组的名字，*移动路径 −1* 又回到它——`Mira · lab coat` 这样的行会合并成 `Mira` 一行。
- 搜索 graft、flatten、flip matrix 等都能找到本节点。
"""))

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
    outputs=[("数据树", "只含该分支的数据树。")],
    doc="""## 提示
- 路径不存在时会报错，并列出实际存在的路径。
"""))

node("Arbor_Merge", en=dict(
    desc="Combine trees — Grasshopper's Merge and Entwine in one node.",
    inputs={"trees": "Trees to combine. Every connection adds a slot.",
            "mode": "merge: items on the same path are appended in input order · entwine: input i is placed under {i;…}, so the inputs stay apart."},
    outputs=[OUT_EN],
    doc="""## Example
`{0}: a` and `{0}: b · {1}: c`:
- merge → `{0}: a, b · {1}: c`
- entwine → `{0;0}: a · {1;0}: b · {1;1}: c`
"""), zh=dict(
    name="合并",
    desc="合并多棵数据树——一个节点包含 Grasshopper 的 Merge 和 Entwine。",
    inputs={"trees": ("数据树", "要合并的数据树，每连一个就多出一个输入口。"),
            "mode": ("模式", "merge 合并：相同路径的项按输入顺序追加 · entwine 编织：第 i 个输入放在 {i;…} 下，各输入保持分开。")},
    outputs=[OUT_ZH],
    doc="""## 示例
`{0}: a` 和 `{0}: b · {1}: c`：
- merge 合并 → `{0}: a, b · {1}: c`
- entwine 编织 → `{0;0}: a · {1;0}: b · {1;1}: c`
"""))

node("Arbor_TreeStatistics", en=dict(
    desc="Branch count, item count, depth and the list of paths.",
    inputs={"tree": TREE_EN},
    outputs=["Number of branches.", "Total number of items.", "Longest path length.", "One line per branch: path and item count."],
    doc="""## Tips
- For a quick look a **Panel** shows the same, live; use this node when you need the numbers downstream (e.g. as the count of a Number Sequence).
"""), zh=dict(
    name="数据树统计",
    desc="分支数、项数、深度和路径列表。",
    inputs={"tree": TREE_ZH},
    outputs=[("分支数", "分支的数量。"), ("项数", "所有项的总数。"), ("深度", "最长路径的层数。"), ("路径", "每个分支一行：路径和项数。")],
    doc="""## 提示
- 只是想看一眼的话，**面板** 能实时显示同样的信息；需要把这些数字接到下游（例如作为数列的数量）时用本节点。
"""))

# =============================================================== List

node("Arbor_ListItem", en=dict(
    desc="Pick items from every branch by index, list, range or slice — Grasshopper's List Item and Sub List in one node.",
    inputs={"tree": TREE_EN,
            "index": "Which items: `0` · `-1` (last) · `0, 2` · `1:4` (slice, end excluded) · `2-5` (range, end included) · `::2` (every other). A connected number works too, or a tree of indices: its branches pair with the list's in order, so every branch picks its own items.",
            "wrap": "Out-of-range indices wrap around the branch length. Off: they give an empty value, so branches stay aligned."},
    outputs=["The picked items, branch by branch.",
             "The picked items as plain data, branch after branch: index k on a tree of sheets gives frame k of every sheet as one list — straight into a node that runs once per item."],
    doc="""## Examples
`{0}: a, b, c, d · {1}: e, f`:

| index | result |
|---|---|
| `1` | `{0}: b · {1}: f` |
| `-1` | `{0}: d · {1}: f` |
| `0, 2` | `{0}: a, c · {1}: e, e` (wrap) |
| `1:` | `{0}: b, c, d · {1}: f` |
| `::2` | `{0}: a, c · {1}: e` |

`:-1` and `1:` pair every item with the next one (a → b, b → c, c → d): *arbor_h3_continuous_shots* takes its first and last frames this way. The same syntax picks frames in **Batch Pick**.

## One pick per branch
Connect a tree of indices to *index*: `{0}: 2 · {1}: 0 · {2}: 1, 3` takes item 2 of the first branch, item 0 of the second and items 1 and 3 of the third. Type the picks in a **Panel** one line per branch and **Reshape Tree** *graft* them — to keep the best take of every shot, for instance.
"""), zh=dict(
    name="列表取项",
    desc="按序号、列表、范围或切片从每个分支取项——一个节点包含 Grasshopper 的 List Item 和 Sub List。",
    inputs={"tree": TREE_ZH,
            "index": ("序号", "取哪些项：`0` · `-1`（最后一项）· `0, 2` · `1:4`（切片，不含结尾）· `2-5`（范围，含结尾）· `::2`（隔一个取一个）。也可以接入数字，或接入序号数据树：它的分支按顺序与列表的分支配对，每个分支取自己的项。"),
            "wrap": ("循环", "序号超出分支长度时循环。关闭时得到空值，各分支仍保持对齐。")},
    outputs=[("数据树", "按分支取出的项。"),
             ("数据", "取出的项（普通数据），各分支依次排列：对一棵「每张网格图一个分支」的数据树取序号 k，就得到每张图的第 k 格组成的列表——可直接接按项运行的节点。")],
    doc="""## 示例
`{0}: a, b, c, d · {1}: e, f`：

| 序号 | 结果 |
|---|---|
| `1` | `{0}: b · {1}: f` |
| `-1` | `{0}: d · {1}: f` |
| `0, 2` | `{0}: a, c · {1}: e, e`（循环） |
| `1:` | `{0}: b, c, d · {1}: f` |
| `::2` | `{0}: a, c · {1}: e` |

`:-1` 和 `1:` 能把每一项和下一项配成对（a → b、b → c、c → d）：模板 *arbor_h3_continuous_shots* 就这样取首帧和尾帧。**批次挑选** 用的是同样的写法。

## 每个分支各取各的
给 *序号* 接一棵序号数据树：`{0}: 2 · {1}: 0 · {2}: 1, 3` 取第一个分支的第 2 项、第二个分支的第 0 项、第三个分支的第 1 和第 3 项。在 **面板** 里每个分支写一行，再用 **重塑数据树** 的 *升树* 拆开——例如为每个镜头留下最好的一版。
"""))

PATTERN_EN = ("Typed repeating pattern ('T F', 'true,false', '1 0 1', 'TFT'), or connect BOOLEAN values / a boolean tree "
              "(e.g. Expression 'x > 2'), whose branches pair with the list's in order, like Grasshopper.")
PATTERN_ZH = ("模式", "输入重复模式（'T F'、'true,false'、'1 0 1'、'TFT'），或接入 BOOLEAN 值 / 布尔数据树"
              "（例如表达式 'x > 2'），其分支与列表的分支按顺序配对，与 Grasshopper 相同。")

node("Arbor_Dispatch", en=dict(
    desc="Split items by a true / false pattern: A keeps the true ones, B the false ones — use A alone to cull a list (Grasshopper's Dispatch and Cull Pattern).",
    inputs={"tree": TREE_EN, "pattern": PATTERN_EN},
    outputs=["Items where the pattern is true — the kept items when culling.", "Items where the pattern is false."],
    doc="""## Examples
| pattern | `a, b, c, d` → A | B |
|---|---|---|
| `T F` | a, c | b, d |
| `F F T` | c | a, b, d |
| Expression `i % 2 == 1` | b, d | a, c |
| a native Boolean = False | (nothing) | everything |

To cull a list, use A and leave B unconnected.
"""), zh=dict(
    name="分流",
    desc="按真 / 假模式拆分：A 是为真的项，B 是为假的项——只用 A 就是剔除（对应 Grasshopper 的 Dispatch 和 Cull Pattern）。",
    inputs={"tree": TREE_ZH, "pattern": PATTERN_ZH},
    outputs=[("A", "模式为真的项——剔除时保留下来的就是它。"), ("B", "模式为假的项。")],
    doc="""## 示例
| 模式 | `a, b, c, d` → A | B |
|---|---|---|
| `T F` | a, c | b, d |
| `F F T` | c | a, b, d |
| 表达式 `i % 2 == 1` | b, d | a, c |
| 原生 Boolean = False | （空） | 全部 |

要剔除列表中的项，接 A、不接 B 即可。
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
    desc="Repeat items: each gives aabbcc, whole gives abcabc. With a shape connected, every branch is stretched to the item count of its matching branch instead — Grasshopper's Longest List.",
    inputs={"tree": TREE_EN, "count": "How many times (ignored while a shape is connected).",
            "mode": "each: repeat every item in place · whole: repeat the whole list. With a shape: each spreads the items evenly (a a b b), whole cycles them (a b a b).",
            "shape": "Optional tree to match. Branches pair in order (the last one repeats); each branch gets as many items as its partner and takes its path, so the result lines up with the shape item by item."},
    outputs=[OUT_EN],
    doc="""## Example
count 2: `a, b` → each `a, a, b, b` · whole `a, b, a, b`

## Match a shape
One location per scene, two shots per scene:
```
tree  = {0}: tea house · {1}: bamboo · {2}: rooftop
shape = {0}: shot 1, shot 2 · {1}: shot 1, shot 2 · {2}: shot 1, shot 2
→ {0}: tea house, tea house · {1}: bamboo, bamboo · {2}: rooftop, rooftop
```
**Tree to Data** on both now gives two lists of six that line up — every shot gets its own scene's location as a reference picture. Template: *arbor_h3_two_characters*.
"""), zh=dict(
    name="重复",
    desc="重复项：each 得到 aabbcc，whole 得到 abcabc。接上形状时，改为把每个分支拉长到对应分支的项数——即 Grasshopper 的 Longest List。",
    inputs={"tree": TREE_ZH, "count": ("次数", "重复的次数（接了形状时不起作用）。"),
            "mode": ("模式", "each：每项原地重复 · whole：整个列表重复。接形状时：each 均匀铺开（a a b b），whole 循环（a b a b）。"),
            "shape": ("形状", "可选，要对齐的数据树。分支按顺序配对（不够时重复最后一个）；每个分支拉长到对应分支的项数并沿用它的路径，结果与形状逐项对齐。")},
    outputs=[OUT_ZH],
    doc="""## 示例
次数 2：`a, b` → each `a, a, b, b` · whole `a, b, a, b`

## 对齐形状
每个场景一个地点、两个镜头：
```
数据 = {0}: 茶室 · {1}: 竹林 · {2}: 天台
形状 = {0}: 镜头1, 镜头2 · {1}: 镜头1, 镜头2 · {2}: 镜头1, 镜头2
→ {0}: 茶室, 茶室 · {1}: 竹林, 竹林 · {2}: 天台, 天台
```
两边再各接 **数据树转数据**，就得到两个逐项对齐的六项列表——每个镜头都拿到自己场景的地点作参考图。模板：*arbor_h3_two_characters*。
"""))

simple("Arbor_SortList",
       "Sort every branch — numbers first (by value), then text (alphabetically) — or reverse it.",
       "列表排序", "对每个分支排序——数字在前（按数值），文本在后（按字母）——或反转顺序。",
       "## Example\n`3, b, 1, a` → ascending `1, 3, a, b` · descending `b, a, 3, 1` · reverse `a, 1, b, 3`\n",
       "## 示例\n`3, b, 1, a` → 升序 `1, 3, a, b` · 降序 `b, a, 3, 1` · 反转 `a, 1, b, 3`\n",
       {"order": "ascending · descending · reverse (keep the items, flip their order)."},
       {"order": ("顺序", "ascending 升序 · descending 降序 · reverse 反转（不排序，只把顺序倒过来）。")})

node("Arbor_CrossReference", en=dict(
    desc="Every combination of A × B, branch by branch, like Grasshopper's Cross Reference: branches pair in order (the shorter tree repeats its last branch) and the result takes the paths of the input with the longest paths. With group on: rows = A, columns = B.",
    inputs={"A": "First set of values.", "B": "Second set of values.",
            "group": "Off (default): Grasshopper's Cross Reference — all combinations stay in the branch. On: one sub-branch per A item, the same as grafting A first — grid-ready (rows = A, columns = B)."},
    outputs=["A repeated for every B.", "B cycled for every A."],
    doc="""## Example
A `3, 5`, B `x, y, z`:
- group off → A `{0}: 3, 3, 3, 5, 5, 5` · B `{0}: x, y, z, x, y, z`
- group on → A `{0;0}: 3, 3, 3 · {0;1}: 5, 5, 5` · B `{0;0}: x, y, z · {0;1}: x, y, z`

## Tips
- For an XY plot, **XY Lists** does this and the flattening in one node.
- With group on, each sub-branch is named after its A value (pictures and other non-text values get their number), and the branch it came from becomes the parent and keeps its name: `Mira · lab coat`, `Arrival · 2`. **Image Grid** labels its rows with these; B works as column labels.
"""), zh=dict(
    name="交叉组合",
    desc="按分支生成 A × B 的所有组合，对应 Grasshopper 的 Cross Reference：分支按顺序配对（短的一方重复最后一个分支），结果沿用路径最长的输入的路径。开启分组时：行 = A，列 = B。",
    inputs={"A": ("A", "第一组取值。"), "B": ("B", "第二组取值。"),
            "group": ("分组", "关闭（默认）：与 Grasshopper 的 Cross Reference 相同，所有组合留在原分支里。开启：每个 A 项一个子分支，等于先对 A 升树——结果可直接做网格（行 = A，列 = B）。")},
    outputs=[("A", "A 按 B 的个数重复。"), ("B", "B 按 A 的个数循环。")],
    doc="""## 示例
A `3, 5`，B `x, y, z`：
- 关闭分组 → A `{0}: 3, 3, 3, 5, 5, 5` · B `{0}: x, y, z, x, y, z`
- 开启分组 → A `{0;0}: 3, 3, 3 · {0;1}: 5, 5, 5` · B `{0;0}: x, y, z · {0;1}: x, y, z`

## 提示
- 做 XY 对比图时，**XY 组合列表** 一个节点就能完成组合和展开。
- 开启分组时，每个子分支以对应的 A 值命名（图片等非文字的值用序号），原来的分支成为父分支并保留名字：`Mira · lab coat`、`Arrival · 2`。**图像网格** 会用它标注行；B 可作为列标签。
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
    name="数据序号切换",
    desc="按序号传出第 N 个输入（按已连接的输入计数，循环）。未选中的输入不会被计算。",
    inputs={"index": ("序号", "0 = 第一个已连接的输入；负数从末尾数；会循环。也可接 BOOLEAN：False = 0，True = 1。"),
            "inputs": ("输入", "任意类型的候选输入，每连一个就多出一个输入口；只有被选中的才会计算。")},
    outputs=[("数据", "被选中的输入，原样传出。"), ("数量", "已连接的输入数量。")],
    doc="""## 提示
- 在工作流的整条分支之间切换（模型、提示词、图片来源），其余分支完全不计算。
- 用 **数值滑块**（*整数* 输出）或布尔值驱动 *序号*，就是一个 if / else。
- ComfyUI 自带的 If/Else Switch 只能接两路；本节点最多 32 路。
"""))
