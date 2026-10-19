"""Single source for every node's documentation, in English and Chinese.

Feeds tools/build_locales.py, which writes
  - locales/<lang>/nodeDefs.json   names, descriptions, input / output tooltips
  - web/docs/<node id>/<lang>.md   the help page in ComfyUI's right-side panel

Per node and language:
  name     display name (en: kept from the schema when omitted)
  desc     one or two sentences (node description)
  inputs   {input id: tooltip}            en
           {input id: (label, tooltip)}   zh
  outputs  [tooltip, ...]                 en
           [(label, tooltip), ...]        zh
  doc      markdown body of the help page (after the generated I/O tables)
"""

INFO = {}


def node(node_id, en, zh):
    INFO[node_id] = {"en": en, "zh": zh}


# =============================================================== Image

node("Arbor_ImageSlider", en=dict(
    desc="Compare any number of images of any size: drag the slider to flip through them, or switch to Wipe for a before / after split.",
    inputs={"images": "Images to compare. Every input grows a new slot; batches are split into one slide per frame (max 64 slides)."},
    outputs=[],
    doc="""## How to use
- Connect one or more images. A batch counts as several slides.
- **Flip** shows one image at a time — drag the slider under the stage or press **← / →**.
- **Wipe** splits **A** (picked from the chip in the toolbar) against **B** (the slider); the divider follows the mouse.
- **Real** keeps relative sizes (a 512 px image looks half as big as a 1024 px one); **Fit** scales every image to fill the stage.
- Double-click the stage (or the ↗ button) to open the full-size image in a new tab.

## Tips
- Feed it a native list (e.g. the per-item results of an XY run): it receives the whole list at once instead of running per item.
- The chosen mode and scale are saved with the workflow.
"""), zh=dict(
    name="图像滑块对比",
    desc="对比任意数量、任意尺寸的图片：拖动滑条逐张切换，或切到「对比」模式左右分屏比较。",
    inputs={"images": ("图像", "要对比的图片。每连一个就会多出一个输入口；批次会拆成每帧一页（最多 64 页）。")},
    outputs=[],
    doc="""## 用法
- 接入一张或多张图片，一个批次会算作多页。
- **切换**：一次显示一张，拖动画面下方的滑条或按 **← / →** 切换。
- **对比**：用工具栏里的胶囊选择 **A**，滑条选择 **B**，分割线跟随鼠标移动。
- **原比例**：保持图片之间的相对大小（512 像素的图看起来是 1024 的一半）；**填充**：每张图都铺满画面。
- 双击画面（或点 ↗ 按钮）在新标签页打开原图。

## 提示
- 可以直接接原生列表（例如 XY 批量运行的逐项结果），节点会一次收下整个列表，而不是逐项运行。
- 选择的模式和缩放方式会随工作流保存。
"""))

node("Arbor_SmartResize", en=dict(
    desc="Resize by longest / shortest side, megapixels, a box or a scale factor, snapping both sides to a multiple (8 / 16 / 64 for latent-friendly sizes).",
    inputs={"image": "Image or batch to resize.",
            "mode": "How the target size is chosen. Only the fields for the chosen mode are shown.",
            "mode.size": "Target length of the longest / shortest side, in pixels.",
            "mode.megapixels": "Target area in megapixels (1.0 ≈ 1024 × 1024); aspect ratio is kept.",
            "mode.width": "Target box width.", "mode.height": "Target box height.",
            "mode.factor": "Scale factor (2.0 = twice as large).",
            "multiple_of": "Round both sides to a multiple of this — use 8 / 16 / 64 for diffusion models.",
            "method": "Resampling filter. lanczos is sharpest; area is best for strong downscaling.",
            "allow_upscale": "Off: never make the image larger than it is.",
            "mask": "Optional mask, resized (and cropped) exactly like the image."},
    outputs=["Resized image.", "Resized mask (all ones when no mask was given).", "Final width.", "Final height."],
    doc="""## Modes
| Mode | Result |
|---|---|
| longest side | longest side = size, aspect kept |
| shortest side | shortest side = size, aspect kept |
| megapixels | area ≈ megapixels, aspect kept |
| fit inside | largest size that fits in width × height (no crop) |
| fill & crop | exactly width × height, center-cropped |
| scale | multiply both sides by factor |

## Example
A 500 × 300 image, *longest side* = 1000, *multiple_of* = 64 → **1024 × 576**.

## Tips
- Use the width / height outputs to drive an Empty Latent Image of the same size.
"""), zh=dict(
    name="智能缩放",
    desc="按长边 / 短边 / 百万像素 / 框内适配 / 填满裁切 / 倍数缩放，并把两边对齐到 8、16、64 的倍数。",
    inputs={"image": ("图像", "要缩放的图像或批次。"),
            "mode": ("模式", "目标尺寸的计算方式，只显示所选模式需要的参数。"),
            "mode.size": ("尺寸", "长边 / 短边的目标像素。"),
            "mode.megapixels": ("百万像素", "目标面积（1.0 ≈ 1024 × 1024），保持宽高比。"),
            "mode.width": ("宽度", "目标框宽度。"), "mode.height": ("高度", "目标框高度。"),
            "mode.factor": ("倍数", "缩放倍数（2.0 = 放大一倍）。"),
            "multiple_of": ("对齐倍数", "两边都取整到这个数的倍数——扩散模型建议 8 / 16 / 64。"),
            "method": ("缩放算法", "lanczos 最锐利；大幅缩小时 area 效果最好。"),
            "allow_upscale": ("允许放大", "关闭后永远不会把图片放大。"),
            "mask": ("遮罩", "可选遮罩，按与图像完全相同的方式缩放（和裁切）。")},
    outputs=[("图像", "缩放后的图像。"), ("遮罩", "缩放后的遮罩（未接遮罩时为全 1）。"), ("宽度", "最终宽度。"), ("高度", "最终高度。")],
    doc="""## 模式
| 模式 | 结果 |
|---|---|
| longest side 长边 | 长边 = 尺寸，保持比例 |
| shortest side 短边 | 短边 = 尺寸，保持比例 |
| megapixels 百万像素 | 面积 ≈ 百万像素，保持比例 |
| fit inside 框内适配 | 能放进 宽 × 高 的最大尺寸（不裁切） |
| fill & crop 填满裁切 | 正好 宽 × 高，居中裁切 |
| scale 倍数 | 两边乘以倍数 |

## 示例
500 × 300 的图，*长边* = 1000，*对齐倍数* = 64 → **1024 × 576**。

## 提示
- 用宽度 / 高度输出驱动同尺寸的空 Latent。
"""))

node("Arbor_BatchPick", en=dict(
    desc="Pick frames from an image batch by index, inclusive range or slice. Order and repeats are kept.",
    inputs={"images": "Image batch to pick from.",
            "indices": "Comma / space separated: 0, 2, -1 (from the end), 3-5 (inclusive range), 1:8:2 or ::2 (Python slices)."},
    outputs=["The picked frames, as one batch.", "How many frames were picked."],
    doc="""## Examples (batch of 6)
| indices | frames |
|---|---|
| `0, -1` | first and last |
| `2-4` | 2, 3, 4 |
| `::2` | 0, 2, 4 |
| `1, 1, 1` | frame 1 three times |

## Tips
- An index outside the batch is an error rather than being skipped, so typos don't go unnoticed.
"""), zh=dict(
    name="批次挑选",
    desc="按序号、闭区间或切片从图像批次中挑帧，保留顺序和重复。",
    inputs={"images": ("图像", "要挑选的图像批次。"),
            "indices": ("序号", "用逗号或空格分隔：0, 2, -1（倒数）, 3-5（闭区间）, 1:8:2 或 ::2（Python 切片）。")},
    outputs=[("图像", "挑出的帧，合成一个批次。"), ("数量", "挑出的帧数。")],
    doc="""## 示例（6 帧的批次）
| 序号 | 结果 |
|---|---|
| `0, -1` | 第一帧和最后一帧 |
| `2-4` | 2, 3, 4 |
| `::2` | 0, 2, 4 |
| `1, 1, 1` | 第 1 帧重复三次 |

## 提示
- 序号超出批次范围会直接报错而不是跳过，避免输错了却没发现。
"""))

node("Arbor_ImageGrid", en=dict(
    desc="Lay images out as an XY comparison sheet: each branch is a row, each item a column.",
    inputs={"images": "An image tree — or the plain images of a batch run, together with shape.",
            "shape": "XY Lists' shape: pours plain images into rows × columns and labels the columns with the column values.",
            "row_labels": "One label per row: a list (e.g. the x Panel), or a tree with one branch per row (Cross Reference A works too).",
            "col_labels": "One label per column — overrides the labels taken from shape.",
            "fit": "How images of different sizes fill a cell: fit (scale to fit), original (no scaling), stretch.",
            "cell_size": "Longest side of a cell in pixels; 0 = the largest image's size.",
            "gap": "Space between cells and around the sheet, in pixels.",
            "font_size": "Label font size. Chinese labels render with a CJK font when one is installed.",
            "theme": "Light or dark sheet background.",
            "path_labels": "Label rows with their branch path when no row labels are connected."},
    outputs=["The comparison sheet as one image."],
    doc="""## How to use
- **After a batch run**: connect the decoded images to *images* and **XY Lists'** *shape* to *shape*. Rows and columns come out right, and the columns are labelled. Connect the x values to *row_labels*.
- **From a tree**: connect any image tree — each branch becomes a row. Use **Flip Matrix** first to swap rows and columns.

## Tips
- Long labels wrap to three lines and are cut with "…".
- Save the sheet with Save Image, or every image separately with **Save Images by Path**.
"""), zh=dict(
    name="图像网格",
    desc="把图片排成 XY 对比图：每个分支一行，每项一列。",
    inputs={"images": ("图像", "图像数据树——或批量运行得到的普通图片（配合形状使用）。"),
            "shape": ("形状", "XY 组合列表的形状：把普通图片排成行 × 列，并用列的取值标注列。"),
            "row_labels": ("行标签", "每行一个标签：列表（例如 x 的面板），或每行一个分支的数据树（交叉组合的 A 也可以）。"),
            "col_labels": ("列标签", "每列一个标签——会覆盖从形状得到的列标签。"),
            "fit": ("适配", "不同尺寸的图片如何填充格子：fit 缩放适配、original 原尺寸、stretch 拉伸。"),
            "cell_size": ("格子尺寸", "格子长边像素；0 = 最大图片的尺寸。"),
            "gap": ("间距", "格子之间以及四周的留白像素。"),
            "font_size": ("字号", "标签字号。系统装有中日韩字体时，中文标签会正常显示。"),
            "theme": ("主题", "浅色或深色背景。"),
            "path_labels": ("路径作行标签", "没有接行标签时，用分支路径作为行标签。")},
    outputs=[("图像", "合成后的对比图（一张）。")],
    doc="""## 用法
- **批量运行之后**：解码后的图片接 *图像*，**XY 组合列表** 的 *形状* 接 *形状*，行列自动排好并标注列；x 的取值接 *行标签*。
- **来自数据树**：直接接任意图像数据树，每个分支一行。想交换行列，先接 **翻转矩阵**。

## 提示
- 过长的标签最多折成三行，超出部分用「…」省略。
- 整张图用「保存图像」保存；想把每张单独存下来，用 **按路径保存图像**。
"""))

node("Arbor_LoadFolder", en=dict(
    desc="Load every image in a folder; with subfolders on, each folder becomes a branch — the folder structure turns straight into a data tree.",
    inputs={"folder": "Absolute path, or a path relative to ComfyUI's input folder.",
            "pattern": "File name patterns separated by spaces, e.g. *.png *.jpg.",
            "subfolders": "On: each subfolder (and the folder itself, if it has images) becomes a branch. Off: only this folder.",
            "sort": "name = natural order (img2 before img10); modified = oldest first.",
            "limit": "Maximum number of images in total; 0 = all. Every image is held in memory, so limit large folders."},
    outputs=["Image tree, one branch per folder.", "File names without extension, same layout — handy as labels or for Save Images by Path.",
             "Folder names, one per branch — use as row labels.", "Total number of images."],
    doc="""## Example
```
photos/            →  images {0}: 2 images   folders: photos
  a.png b.png
  day/             →  images {1}: 3 images   folders: day
  night/           →  images {2}: 1 image    folders: night
```

## Tips
- The node re-runs automatically when files are added, removed or changed.
- Images keep their own sizes; resize with **Smart Resize** if the next step needs one size.
"""), zh=dict(
    name="加载文件夹",
    desc="加载文件夹里的所有图片；开启子文件夹后，每个文件夹就是一个分支——目录结构直接变成数据树。",
    inputs={"folder": ("文件夹", "绝对路径，或相对 ComfyUI input 文件夹的路径。"),
            "pattern": ("文件匹配", "用空格分隔的文件名模式，例如 *.png *.jpg。"),
            "subfolders": ("子文件夹", "开启：每个子文件夹（以及本文件夹，如果里面有图）各成一个分支。关闭：只读本文件夹。"),
            "sort": ("排序", "name = 自然排序（img2 排在 img10 前）；modified = 按修改时间从旧到新。"),
            "limit": ("数量上限", "最多加载的图片总数；0 = 全部。所有图片都会载入内存，大文件夹请设上限。")},
    outputs=[("图像", "图像数据树，每个文件夹一个分支。"), ("文件名", "不带扩展名的文件名，结构相同——可作标签或给「按路径保存图像」用。"),
             ("文件夹", "文件夹名，每个分支一个——可作行标签。"), ("数量", "图片总数。")],
    doc="""## 示例
```
photos/            →  图像 {0}：2 张   文件夹：photos
  a.png b.png
  day/             →  图像 {1}：3 张   文件夹：day
  night/           →  图像 {2}：1 张   文件夹：night
```

## 提示
- 文件有增删改时，节点会自动重新读取。
- 图片保持各自的尺寸；后续需要统一尺寸时用 **智能缩放**。
"""))

node("Arbor_SaveImagesByPath", en=dict(
    desc="Save an image tree keeping its structure: one subfolder (or filename part) per branch path, with optional names per file.",
    inputs={"images": "Image tree to save. Batches are saved frame by frame.",
            "filename_prefix": "Folder / prefix inside ComfyUI's output folder. Supports %date%-style variables like Save Image.",
            "layout": "subfolders: prefix_0-1/000.png · flat: prefix_0-1_000.png",
            "names": "Optional file names, matched to the images item by item (e.g. Load Folder's names or a Prompt Template)."},
    outputs=["Saved file paths, in the same tree layout."],
    doc="""## Example
Tree `{0}: 2 images, {1}: 3 images`, prefix `arbor/run`, layout *subfolders*:
```
output/arbor/run_0/000.png  001.png
output/arbor/run_1/000.png  001.png  002.png
```
With *names* connected the files are called after the names instead (`cat.png`, `dog.png`, …).

## Tips
- Existing files are never overwritten: a `_2`, `_3`, … suffix is added.
- The workflow is embedded in every PNG, like Save Image.
"""), zh=dict(
    name="按路径保存图像",
    desc="按数据树结构保存图片：每个分支路径一个子文件夹（或文件名的一部分），可选为每个文件命名。",
    inputs={"images": ("图像", "要保存的图像数据树，批次会逐帧保存。"),
            "filename_prefix": ("文件名前缀", "output 文件夹内的目录 / 前缀，和「保存图像」一样支持 %date% 等变量。"),
            "layout": ("布局", "subfolders：前缀_0-1/000.png · flat：前缀_0-1_000.png"),
            "names": ("文件名", "可选，与图像逐项对应的文件名（例如「加载文件夹」的文件名或提示词模板的输出）。")},
    outputs=[("路径", "已保存文件的路径，结构与输入相同。")],
    doc="""## 示例
数据树 `{0}: 2 张, {1}: 3 张`，前缀 `arbor/run`，布局 *subfolders*：
```
output/arbor/run_0/000.png  001.png
output/arbor/run_1/000.png  001.png  002.png
```
接入 *文件名* 后，文件按名字命名（`cat.png`、`dog.png`……）。

## 提示
- 永远不会覆盖已有文件：会自动加 `_2`、`_3`…… 后缀。
- 和「保存图像」一样，每张 PNG 都内嵌工作流。
"""))

# =============================================================== Data

node("Arbor_Panel", en=dict(
    desc="Inspect anything, or type data in. Connected: shows the input and passes it through. Unconnected: each line you type is an item, an empty line starts a new branch.",
    inputs={"data": "Anything — a data tree, a native list, an image, a number… Leave it unconnected to type data instead.",
            "text": "The typed data (used when nothing is connected). Edited in the panel itself.",
            "parse_numbers": "Typed values: lines like 7 / 3.5 / true become INT / FLOAT / BOOLEAN. The 123 / abc button in the panel.",
            "multiline": "Text mode: the whole text is one item. The Lines / Text switch in the panel."},
    outputs=["The data as a native list: downstream nodes run once per item (a single item runs once).",
             "The data as a tree — for Arbor nodes, keeps the branches."],
    doc="""## Viewing (input connected)
- Trees show as collapsible branches with their path and count (`{0;1} N=3`); images as thumbnails.
- Long text folds to four lines — *more* unfolds it. Hover an item to copy it; the toolbar copies everything.
- **Live**: when everything upstream is a lightweight data node (Arbor data / tree / list nodes, primitives, string and math nodes) the view updates as you edit — no run needed (green dot). Anything heavier upstream (samplers, loaders) never runs on its own; the panel then shows the last run.
- ⤢ opens a large view.

## Typing (input unconnected)
- **Lines**: one item per line, an empty line starts a new branch. The gutter shows each line's branch path and index, coloured by type (blue = number, purple = boolean).
- **Text**: the whole text is one item — for long prompts.
- **123 / abc**: read numbers and true / false, or keep everything as text.
- ⤢ opens a large editor. Ctrl+Enter still queues the workflow.

## Example
```
3
5
7

a cat
a dog
```
→ tree `{0}: [3, 5, 7]`, `{1}: ["a cat", "a dog"]`.
"""), zh=dict(
    name="面板",
    desc="查看任何数据，或直接输入数据。接入时：显示输入并原样传出。未接入时：每行是一项，空一行开始新分支。（对应 Grasshopper 的 Panel）",
    inputs={"data": ("数据", "任何数据——数据树、原生列表、图片、数字…… 不接则改为手动输入。"),
            "text": ("文本", "手动输入的数据（未接入输入时使用），直接在面板里编辑。"),
            "parse_numbers": ("识别数值", "像 7 / 3.5 / true 这样的行变成 INT / FLOAT / BOOLEAN，对应面板里的 123 / abc 按钮。"),
            "multiline": ("整段文本", "整段文字作为一项，对应面板里的「逐行 / 整段」开关。")},
    outputs=[("数据", "原生列表：下游节点会对每一项各运行一次（只有一项时运行一次）。"),
             ("数据树", "数据树形式——给 Arbor 节点用，保留分支结构。")],
    doc="""## 查看（接入输入时）
- 数据树显示为可折叠的分支，带路径和数量（`{0;1} N=3`）；图片显示缩略图。
- 长文本默认折叠成四行，点「展开」查看全部。鼠标悬停某项可单独复制；工具栏按钮复制全部。
- **实时**：上游全是轻量数据节点（Arbor 的数据 / 数据树 / 列表节点、Primitive、字符串和数学节点）时，编辑就会实时刷新，无需运行（绿点）。上游有采样器、加载器等重节点时不会自动运行，显示上一次运行的结果。
- ⤢ 打开大窗口查看。

## 输入（未接入时）
- **逐行**：每行一项，空一行开始新分支。左侧标出每行的分支路径和序号，按类型着色（蓝色 = 数字，紫色 = 布尔值）。
- **整段**：整段文字作为一项——适合长提示词。
- **123 / abc**：识别数字和 true / false，或全部保留为文本。
- ⤢ 打开大编辑窗口。Ctrl+Enter 仍可运行工作流。

## 示例
```
3
5
7

a cat
a dog
```
→ 数据树 `{0}: [3, 5, 7]`，`{1}: ["a cat", "a dog"]`。
"""))

node("Arbor_NumberSlider", en=dict(
    desc="Grasshopper-style number slider: drag the bar to set a value between min and max, click it to type. A step of 1 gives whole numbers.",
    inputs={"value": "Current value — set it on the bar.",
            "min": "Lower end of the range (click the left number under the bar).",
            "max": "Upper end of the range (click the right number under the bar).",
            "step": "Values snap to min + k × step: 1 = whole numbers, 0.05 = steps of 0.05, 0 = continuous. "
                    "Also sets how many decimals are shown."},
    outputs=["One output for every number input: connects to INT inputs (steps, seed) and FLOAT inputs "
             "(cfg, denoise) alike. Whole numbers come out as INT, others as FLOAT."],
    doc="""## How to use
- **Drag** across the bar — the value follows the pointer. Hold **Shift** while dragging for 10× finer control.
- **Click** the bar (without dragging) to type a value; Enter confirms, Esc cancels. A value outside the range widens the range.
- **Scroll** over the bar or press **← / →** to move by one step (Shift: 10 steps).
- Under the bar: click **min**, **step** or **max** to edit them.

## Examples
| min · step · max | values |
|---|---|
| 0 · 0.05 · 1 | 0, 0.05, 0.10, … 1 |
| 1 · 1 · 50 | whole numbers — steps, batch sizes |
| 0 · 0 · 1 | any value (shown with up to 4 decimals) |

## Tips
- The single *value* output connects to any number input — FLOAT (cfg, denoise, LoRA strength) or INT (steps, seed, batch size). Drag it onto a widget to turn the widget into an input.
- Connected to an INT-only input (steps, seed, width…) the value is sent rounded to a whole number, and the bar shows an **INT** tag — so a slider at 4.5 can't break a sampler.
- Live Panels downstream follow the slider while you drag.
"""), zh=dict(
    name="数值滑块",
    desc="Grasshopper 风格的数值滑块：在滑条上拖动，在最小值和最大值之间取值；单击可直接输入。步长为 1 时为整数。",
    inputs={"value": ("数值", "当前数值——在滑条上设置。"),
            "min": ("最小值", "范围下限（点击滑条下方左侧的数字修改）。"),
            "max": ("最大值", "范围上限（点击滑条下方右侧的数字修改）。"),
            "step": ("步长", "数值对齐到 最小值 + k × 步长：1 = 整数，0.05 = 以 0.05 为间隔，0 = 连续取值。同时决定显示几位小数。")},
    outputs=[("数据", "一个输出兼顾所有数值输入：INT（步数、种子）和 FLOAT（cfg、denoise）都能直接连接。整数以 INT 输出，其余以 FLOAT 输出。")],
    doc="""## 用法
- 在滑条上**拖动**——数值跟随鼠标位置。拖动时按住 **Shift** 可精细调节（10 倍精度）。
- **单击**滑条（不拖动）直接输入数值；Enter 确认，Esc 取消。输入超出范围的值时，范围会自动扩展。
- 在滑条上**滚动鼠标**或按 **← / →** 按一个步长加减（按住 Shift 为 10 个步长）。
- 滑条下方：点击 **最小值**、**步长** 或 **最大值** 即可修改。

## 示例
| 最小值 · 步长 · 最大值 | 取值 |
|---|---|
| 0 · 0.05 · 1 | 0, 0.05, 0.10, … 1 |
| 1 · 1 · 50 | 整数——步数、批次大小 |
| 0 · 0 · 1 | 任意值（最多显示 4 位小数） |

## 提示
- 唯一的 *数值* 输出可接任何数值输入——FLOAT（cfg、denoise、LoRA 强度）或 INT（步数、种子、批次大小）。把它拖到参数上，参数会变成输入口。
- 接到只收整数的参数（步数、种子、宽度……）时，数值会自动取整后传出，滑条上显示 **INT** 标记——滑块停在 4.5 也不会让采样器报错。
- 拖动时，下游的实时面板会跟着变化。
"""))

node("Arbor_PromptTemplate", en=dict(
    desc="Fill {a} {b} … in a template from trees. Cross builds every combination as a grid-ready tree; zip pairs items one by one.",
    inputs={"template": "Text with placeholders {a} … {f}. Placeholders without a connected value stay as they are.",
            "mode": "cross: every combination — rows = {a}, columns = the last variable used. zip: item by item (longest list).",
            "vars": "Values for {a}, {b}, … — a tree, a list or a single value. Each connection adds the next letter."},
    outputs=["Every filled prompt as plain data — connect straight to a text encoder (it runs once per prompt).",
             "The prompts as a tree (cross: one branch per combination of the outer variables — ready for Image Grid)."],
    doc="""## Example
Template `a photo of {a}, {b} style`, a = `cat, dog`, b = `oil, ink`:

| mode | result |
|---|---|
| cross | `{0}: cat·oil, cat·ink` · `{1}: dog·oil, dog·ink` |
| zip | `{0}: cat·oil, dog·ink` |

## Tips
- Type the values in **Panels** (one per line) and connect their *data* output (or *tree*, to keep branches).
- Connect *data* to a text encoder: the sampler runs once per prompt. Connect *tree* to **Image Grid**'s *shape* to lay the images out in the same rows. Up to 10 000 combinations.
"""), zh=dict(
    name="提示词模板",
    desc="用数据树填充模板中的 {a} {b} ……。交叉：生成所有组合，直接得到可做网格的数据树；配对：逐项对应。",
    inputs={"template": ("模板", "带占位符 {a} … {f} 的文本；没接值的占位符保持原样。"),
            "mode": ("模式", "cross 交叉：所有组合——行 = {a}，列 = 最后一个用到的变量。zip 配对：逐项对应（最长列表）。"),
            "vars": ("变量", "{a}、{b} …… 的取值——数据树、列表或单个值。每接一个就多出下一个字母。")},
    outputs=[("数据", "所有填好的提示词（普通数据）——可直接接文本编码器，每个提示词运行一次。"),
             ("数据树", "提示词数据树（交叉模式下，外层变量的每种组合一个分支——可直接做图像网格）。")],
    doc="""## 示例
模板 `a photo of {a}, {b} style`，a = `cat, dog`，b = `oil, ink`：

| 模式 | 结果 |
|---|---|
| cross 交叉 | `{0}: cat·oil, cat·ink` · `{1}: dog·oil, dog·ink` |
| zip 配对 | `{0}: cat·oil, dog·ink` |

## 提示
- 在 **面板** 里逐行输入取值，接它的 *数据* 输出（想保留分支就接 *数据树*）。
- *数据* 接文本编码器，采样器每个提示词各跑一次；*数据树* 接 **图像网格** 的 *形状*，图片按同样的行排列。最多 1 万种组合。
"""))

node("Arbor_Expression", en=dict(
    desc="Evaluate a formula for every item of x (y matched longest-list), like Grasshopper's Expression.",
    inputs={"expression": "Python-style formula, e.g. x * 2 + 1, x > 3, upper(x), x if i % 2 else -x.",
            "x": "Main input — the result has the same tree layout. Leave empty for a single constant result.",
            "y": "Optional second value, matched to x branch by branch, item by item (the last item repeats)."},
    outputs=["Every result as plain data.",
             "Results in x's tree layout. Comparisons give booleans — ready for Dispatch."],
    doc="""## Names
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
"""), zh=dict(
    name="表达式",
    desc="对 x 的每一项计算公式（y 按最长列表匹配），对应 Grasshopper 的 Expression。",
    inputs={"expression": ("表达式", "Python 风格的公式，例如 x * 2 + 1、x > 3、upper(x)、x if i % 2 else -x。"),
            "x": ("x", "主输入——结果与它的数据树结构相同。不接则只计算一个常量结果。"),
            "y": ("y", "可选的第二个值，按分支、按项与 x 对应（不够时重复最后一项）。")},
    outputs=[("数据", "所有计算结果（普通数据）。"),
             ("数据树", "计算结果，结构与 x 相同。比较运算得到布尔值——可直接接「分流」。")],
    doc="""## 可用名称
| 名称 | 含义 |
|---|---|
| `x`、`y` | 当前项 |
| `i` | 项在分支内的序号 |
| `b` | 分支序号 |
| `n` | 分支长度 |
| `pi`、`e` | 常数 |

## 函数
`abs min max round int float str bool len sum sqrt sin cos tan atan2 floor ceil log exp clamp(v, lo, hi) lerp(a, b, t) upper lower strip replace(s, a, b) join(sep, …)`

## 示例
| 表达式 | x = 1, 2, 3 |
|---|---|
| `x * 2 + i` | 2, 5, 8 |
| `x > 1` | False, True, True |
| `lerp(0, 10, i / (n - 1))` | 0, 5, 10 |

## 安全
不允许属性访问、import、lambda 和推导式；会产生超大结果的写法（如 `9 ** 9 ** 9`）会直接报错。
"""))

node("Arbor_Random", en=dict(
    desc="Seeded shuffle, or pick a number of items (with or without repeats). Same seed, same result.",
    inputs={"tree": ("data", "Items to shuffle or pick from — plain data or a tree (handled branch by branch)."),
            "mode": "shuffle: reorder everything · pick: choose count different items · pick (repeats): choose count items, repeats allowed.",
            "count": "Items to pick per branch (ignored by shuffle).",
            "seed": "Random seed — the same seed always gives the same result.",
            "per_branch": "On: every branch separately. Off: all items as one list."},
    outputs=["The shuffled / picked items as plain data.", "The shuffled / picked items, branch by branch."],
    doc="""## Tips
- Pick random prompts or styles for a batch: Panel (one per line) → **Random** (pick 4) → *data* to a text encoder.
- Set the seed's *control after generate* to *randomize* for a new pick on every run.
"""), zh=dict(
    name="随机",
    desc="带种子的打乱，或抽取若干项（可选允许重复）。种子相同，结果相同。",
    inputs={"tree": ("数据", "要打乱或从中抽取的项——普通数据或数据树（按分支处理）。"),
            "mode": ("模式", "shuffle 打乱：重新排序 · pick 抽取：抽 count 个不同的项 · pick (repeats)：抽 count 个，允许重复。"),
            "count": ("数量", "每个分支抽取的项数（打乱模式忽略）。"),
            "seed": ("种子", "随机种子——相同的种子总是得到相同的结果。"),
            "per_branch": ("逐分支", "开启：每个分支分别处理。关闭：所有项当作一个列表。")},
    outputs=[("数据", "打乱 / 抽取后的项（普通数据）。"), ("数据树", "打乱 / 抽取后的项，按分支排列。")],
    doc="""## 提示
- 为批量出图随机挑选提示词或风格：面板（每行一个）→ **随机**（抽 4 个）→ *数据* 接文本编码器。
- 把种子的「运行后操作」设为随机，每次运行都会重新抽取。
"""))

node("Arbor_ConstructTree", en=dict(
    desc="Build a tree from plain data: put every item on one path, or — with shape connected — pour the items back into another tree's branches.",
    inputs={"data": "Any value or plain data (a native list), e.g. the results of a batch run.",
            "path": "Branch path for the items when no shape is connected, e.g. {0} or {0;2}.",
            "shape": "A tree whose branch layout to copy — XY Lists' shape, or the tree you flattened. The item counts must match.",
            "split_batch": "Split IMAGE / MASK / LATENT batches into one item per frame first."},
    outputs=["The tree."],
    doc="""## Two ways
| connected | result |
|---|---|
| data only | every item on *path*: `{0}: a, b, c` |
| data + shape | the items poured into shape's branches: shape `{0}: ·, · · {1}: ·, ·` + `a b c d` → `{0}: a, b · {1}: c, d` |

## Round trip
Tree → **XY Lists** (x only) → ordinary nodes run per item → **Construct Tree** with *shape* = XY Lists' shape → the results are back in the original branches.

## Tips
- A count mismatch is an error with both counts in the message — usually the shape is from a different tree than the one that was flattened.
- Every Arbor tree input already accepts plain data (as `{0}`); use this node for a specific path, a shape or split batches.
"""), zh=dict(
    name="构建数据树",
    desc="用普通数据构建数据树：所有项放在一个路径上，或——接入形状时——按另一棵树的分支把项收回去。",
    inputs={"data": ("数据", "任意值或普通数据（原生列表），例如批量运行的结果。"),
            "path": ("路径", "未接形状时放置这些项的分支路径，例如 {0} 或 {0;2}。"),
            "shape": ("形状", "要复制其分支结构的数据树——XY 组合列表的形状，或当初展开的那棵树。项数必须一致。"),
            "split_batch": ("拆分批次", "先把 IMAGE / MASK / LATENT 批次拆成每帧一项。")},
    outputs=[("数据树", "构建好的数据树。")],
    doc="""## 两种用法
| 接入 | 结果 |
|---|---|
| 只接数据 | 所有项放在 *路径* 上：`{0}: a, b, c` |
| 数据 + 形状 | 按形状的分支收回：形状 `{0}: ·, · · {1}: ·, ·` + `a b c d` → `{0}: a, b · {1}: c, d` |

## 往返
数据树 → **XY 组合列表**（只接 x）→ 普通节点逐项运行 → **构建数据树**（*形状* 接 XY 组合列表的形状）→ 结果回到原来的分支。

## 提示
- 数量不一致会报错，并给出两边的数量——通常是形状接错了树，和当初展开的那棵不是同一棵。
- Arbor 的每个数据树输入本来就接受普通数据（作为 `{0}`）；需要指定路径、按形状收回或拆分批次时才用本节点。
"""))

node("Arbor_NumberSequence", en=dict(
    desc="A list of numbers, defined by a step (series) or by both ends (range).",
    inputs={"mode": "series: start, start + step, … · range: start → end split evenly. Only that mode's fields are shown.",
            "mode.start": "First number.",
            "mode.step": "series: difference between neighbours (negative counts down).",
            "mode.count": "series: how many numbers.",
            "mode.end": "range: last number (included).",
            "mode.steps": "range: number of equal parts — you get steps + 1 numbers.",
            "as_int": "Round to whole numbers — for seeds, steps, sizes."},
    outputs=["The numbers as plain data — connect straight to cfg, steps, seed… (the node runs once per number) or to any Arbor input."],
    doc="""## Examples
| mode | values | result |
|---|---|---|
| series | start 3 · step 2 · count 4 | 3, 5, 7, 9 |
| series | start 1000 · step 1 · count 4 · as_int | four consecutive seeds |
| range | start 0 · end 1 · steps 4 | 0, 0.25, 0.5, 0.75, 1 |
| range | start 3 · end 9 · steps 3 | 3, 5, 7, 9 |

Use **series** when you know the step, **range** when you know both ends (e.g. cfg 3 → 9).

## Tips
- Connect the output straight to a widget (cfg, steps, width…): the node it feeds runs once per number.
- For a parameter sweep against a second value, connect it to **XY Lists**.
"""), zh=dict(
    name="数列",
    desc="生成一串数字，按步长（series）或按两端（range）定义。",
    inputs={"mode": ("模式", "series：起始值、起始值 + 步长…… · range：从起点到终点平均分。只显示当前模式需要的参数。"),
            "mode.start": ("起始值", "第一个数。"),
            "mode.step": ("步长", "series：相邻两数之差（负数为递减）。"),
            "mode.count": ("数量", "series：数的个数。"),
            "mode.end": ("终点", "range：最后一个数（包含）。"),
            "mode.steps": ("段数", "range：等分的段数，得到 段数 + 1 个数。"),
            "as_int": ("输出整数", "取整——用于种子、步数、尺寸。")},
    outputs=[("数据", "这些数（普通数据）——可直接接 cfg、步数、种子等参数（每个数运行一次），也可接任何 Arbor 输入。")],
    doc="""## 示例
| 模式 | 参数 | 结果 |
|---|---|---|
| series | 起始 3 · 步长 2 · 数量 4 | 3, 5, 7, 9 |
| series | 起始 1000 · 步长 1 · 数量 4 · 输出整数 | 四个连续的种子 |
| range | 起点 0 · 终点 1 · 段数 4 | 0, 0.25, 0.5, 0.75, 1 |
| range | 起点 3 · 终点 9 · 段数 3 | 3, 5, 7, 9 |

知道步长用 **series**，知道两端（例如 cfg 3 → 9）用 **range**。

## 提示
- 输出可直接接参数（cfg、步数、宽度……），被接的节点会对每个数各运行一次。
- 要和另一个参数交叉对比，接 **XY 组合列表**。
"""))

node("Arbor_SplitText", en=dict(
    desc="Split text into items — one per line or separator; an empty line starts a new branch.",
    inputs={"text": "The text. Can be typed or connected from any STRING output.",
            "separator": "What separates items inside a paragraph: newline, comma, semicolon or |.",
            "blank_line_branches": "Paragraphs separated by an empty line become branches {0}, {1}, …",
            "strip": "Trim spaces around every item."},
    outputs=["Every item as plain text data (paragraphs one after another).", "The items as a tree: one branch per paragraph."],
    doc="""## Example
`red, green` ⏎ ⏎ `cat, dog` with separator `,` → `{0}: red, green` · `{1}: cat, dog`.

## Tips
- For typing, a **Panel** does the same with a live preview; use this node when the text comes from another node (a file loader, an LLM…).
"""), zh=dict(
    name="拆分文本",
    desc="把文本拆成多项——每行或每个分隔符一项；空行开始新分支。",
    inputs={"text": ("文本", "要拆分的文本，可以手动输入，也可以接任意 STRING 输出。"),
            "separator": ("分隔符", "段落内用什么分隔各项：换行、逗号、分号或 |。"),
            "blank_line_branches": ("空行分支", "用空行分隔的段落分别成为分支 {0}、{1}……"),
            "strip": ("去除首尾空白", "去掉每一项两端的空格。")},
    outputs=[("数据", "拆分后的所有项（普通文本数据，各段依次排列）。"), ("数据树", "拆分后的数据树：每个段落一个分支。")],
    doc="""## 示例
`red, green` ⏎ ⏎ `cat, dog`，分隔符 `,` → `{0}: red, green` · `{1}: cat, dog`。

## 提示
- 手动输入时用 **面板** 效果相同，还能实时预览；文本来自其他节点（读文件、LLM……）时用本节点。
"""))
