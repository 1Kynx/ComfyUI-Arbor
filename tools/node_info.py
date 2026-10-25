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
    name="Compare Viewer",
    desc="Compare images, videos and audio of any size: flip through them with the slider, or wipe A against B. Videos and audio play in sync and keep their place when you switch, so an A/B comparison stays on the same moment.",
    inputs={"images": "What to compare — images, videos or audio: a single value, a batch, a list or a tree. Every input grows a new slot; image batches give one slide per frame, audio batches one per clip (max 64 slides). Items of a named branch (a Load Folder folder, a storyboard scene) are labelled with its name."},
    outputs=[],
    doc="""## How to use
- Connect one or more inputs: pictures, videos (e.g. Load Folder with kind *videos*, Create Video) or audio. They can be mixed.
- **Flip** shows one slide at a time — drag the slider under the stage or press **← / →**.
- **Wipe** puts **A** (picked from the chip in the toolbar) against **B** (the slider). Two pictures or videos are split by a divider that follows the mouse; when either is audio they are stacked, A on top, and you hear the half under the mouse.
- Videos and audio share one **play / seek / loop** bar (Space plays and pauses). Switching slides keeps the current time — flip back and forth to hear or see the same moment in each version. Shorter clips hold their last frame.
- Audio shows its waveform; click it to jump.
- **Real** keeps relative sizes (a 512 px image looks half as big as a 1024 px one); **Fit** scales every picture to fill the stage.
- Double-click the stage (or the ↗ button) to open the current file in a new tab.

## Tips
- Feed it a native list (e.g. the per-item results of an XY run): it receives the whole list at once instead of running per item.
- Videos already in ComfyUI's output / input folder play straight from there; others are written to the temp folder first.
- In Wipe you hear one side at a time: the one that shows more of the stage (side by side) or the half under the mouse (stacked). The speaker button mutes everything.
- The chosen mode, scale and loop are saved with the workflow.
"""), zh=dict(
    name="对比查看器",
    desc="对比任意尺寸的图片、视频和音频：拖动滑条逐个切换，或用「对比」模式把 A 和 B 放在一起比较。视频和音频同步播放，切换时保持在同一时刻。",
    inputs={"images": ("输入", "要对比的内容——图片、视频或音频：单个、批次、列表或数据树都可以。每连一个就会多出一个输入口；图片批次每帧一页，音频批次每段一页（最多 64 页）。有名字的分支（加载的文件夹、分镜的场景）用名字标注。")},
    outputs=[],
    doc="""## 用法
- 接入一个或多个输入：图片、视频（例如「加载文件夹」类型选 *videos*、「创建视频」）或音频，可以混合。
- **切换**：一次显示一页，拖动画面下方的滑条或按 **← / →** 切换。
- **对比**：用工具栏里的胶囊选择 **A**，滑条选择 **B**。两个都是图片或视频时左右分屏，分割线跟随鼠标；只要有一个是音频就上下排列，A 在上，听到的是鼠标所在的那一半。
- 视频和音频共用一条 **播放 / 定位 / 循环** 控制条（空格键播放、暂停）。切换页面时保持当前时间——来回切换就能对比同一时刻的不同版本。较短的片段停在最后一帧。
- 音频显示波形，点击波形可以跳转。
- **原比例**：保持图片之间的相对大小（512 像素的图看起来是 1024 的一半）；**填充**：每张图都铺满画面。
- 双击画面（或点 ↗ 按钮）在新标签页打开当前文件。

## 提示
- 可以直接接原生列表（例如 XY 批量运行的逐项结果），节点会一次收下整个列表，而不是逐项运行。
- 已在 ComfyUI 的 output / input 文件夹里的视频直接播放原文件；其它视频先写到临时文件夹。
- 对比模式下一次只听一侧：左右分屏时听占画面更多的一侧，上下排列时听鼠标所在的那一半。喇叭按钮可以全部静音。
- 选择的模式、缩放方式和循环开关会随工作流保存。
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
    desc="Pick frames from an image batch or a video by index, inclusive range or slice. Order and repeats are kept.",
    inputs={"images": "Image batch — or a video, whose frames are picked from.",
            "indices": "Comma / space separated: 0, 2, -1 (from the end), 3-5 (inclusive range), 1:8:2 or ::2 (Python slices)."},
    outputs=["The picked frames, as one batch.", "How many frames were picked."],
    doc="""## Examples (batch of 6)
| indices | frames |
|---|---|
| `0, -1` | first and last |
| `2-4` | 2, 3, 4 |
| `::2` | 0, 2, 4 |
| `1, 1, 1` | frame 1 three times |

## Videos
Connect a video (Create Video, Load Video, a generated clip) and pick its frames as pictures: `0, -1` for a contact sheet of first and last frames, `-1` for the last frame to start the next shot from. A batch run of clips gives one picked batch per clip.

## Tips
- An index outside the batch is an error rather than being skipped, so typos don't go unnoticed.
"""), zh=dict(
    name="批次挑选",
    desc="按序号、闭区间或切片从图像批次或视频中挑帧，保留顺序和重复。",
    inputs={"images": ("图像", "要挑选的图像批次——或一段视频，从它的帧里挑。"),
            "indices": ("序号", "用逗号或空格分隔：0, 2, -1（倒数）, 3-5（闭区间）, 1:8:2 或 ::2（Python 切片）。")},
    outputs=[("图像", "挑出的帧，合成一个批次。"), ("数量", "挑出的帧数。")],
    doc="""## 示例（6 帧的批次）
| 序号 | 结果 |
|---|---|
| `0, -1` | 第一帧和最后一帧 |
| `2-4` | 2, 3, 4 |
| `::2` | 0, 2, 4 |
| `1, 1, 1` | 第 1 帧重复三次 |

## 视频
接入视频（创建视频、加载视频、生成的片段），把其中的帧挑出来作为图片：`0, -1` 做首尾帧对照表，`-1` 取最后一帧作为下一个镜头的起点。一批片段会得到每段一个挑选结果。

## 提示
- 序号超出批次范围会直接报错而不是跳过，避免输错了却没发现。
"""))

node("Arbor_SplitGrid", en=dict(
    desc="Cut a grid picture — a storyboard sheet, a contact sheet, a sprite sheet — into its panels, row by row. Gutters and margins are found and left out; without them the picture is cut evenly.",
    inputs={"image": "One sheet, or a batch / list of sheets — each sheet becomes one branch.",
            "rows": "How many rows of panels the sheet has.",
            "columns": "How many panels per row.",
            "find_gutters": "Look for gutters and margins — lines of one flat colour — near every cut and leave them out, so panels that are not quite even still come out clean. Off: cut into even parts.",
            "inset": "Pixels shaved off every panel edge, to drop the soft edge of a gutter."},
    outputs=["Every panel as plain data, in reading order (left to right, top to bottom) — panels may differ by a few pixels in size.",
             "One branch per sheet, its panels in reading order."],
    doc="""## Why a whole sheet
An image model that draws all the frames of a storyboard in one picture keeps the character, the light and the palette far more consistent than separate renders do. Ask for the grid in the prompt (*six panels, three columns and two rows, thin white gutters, no text*), give the sheet the panels' combined aspect (3 × 16:9 by 2 rows ≈ 8:3, e.g. 3264 × 1216), and cut it here.

Template: *arbor_h3_long_takes* draws one 3 × 2 sheet per scene with MOSS-Image, cuts each into six keyframes (one branch per scene) and pins them along one continuous take per scene.

## Checking the cuts
After a run the node shows the sheet with everything that was cut away shaded red and every panel outlined and numbered (0, 1, 2 … — the numbers **List Item** uses). A panel that swallowed a gutter, or two panels merged into one, shows at a glance.

## Tips
- The gutters only need to be roughly where an even split would cut; drawn grids are rarely exact and the found gutter wins.
- Panels come out a few pixels apart in size; video and image models resize them anyway, **Smart Resize** evens them out.
- The inverse of **Image Grid**.
"""), zh=dict(
    name="拆分网格",
    desc="把一张网格图——分镜表、联系表、精灵图——按行拆成一格一格的图片。自动找到并去掉格间留白和外边距；没有留白时均匀切分。",
    inputs={"image": ("图像", "一张网格图，或一批 / 一组网格图——每张成为一个分支。"),
            "rows": ("行数", "网格有几行。"),
            "columns": ("列数", "每行有几格。"),
            "find_gutters": ("查找留白", "在每条切线附近寻找格间留白和外边距（整条同一颜色的线）并去掉，格子大小不完全一致也能切干净。关闭：均匀切分。"),
            "inset": ("内缩", "每格四边再裁掉的像素，去掉留白边缘的过渡。")},
    outputs=[("数据", "所有格子（普通数据），按阅读顺序（从左到右、从上到下）——各格尺寸可能相差几个像素。"),
             ("数据树", "每张网格图一个分支，格子按阅读顺序排列。")],
    doc="""## 为什么要整张生成
让图像模型在一张图里画出分镜的所有画面，人物、光线和色调会比分开生成一致得多。在提示词里写明网格（*six panels, three columns and two rows, thin white gutters, no text*），图片比例取各格拼起来的比例（3 格 16:9 × 2 行 ≈ 8:3，例如 3264 × 1216），再用本节点拆开。

模板 *arbor_h3_long_takes* 用 MOSS-Image 为每个场景画一张 3 × 2 的分镜表，各拆成六张关键帧（每个场景一个分支），再把它们锚定在每个场景的一镜到底长镜头里。

## 检查切线
运行后节点上会显示网格图：被裁掉的部分标成红色，每一格画框并编号（0、1、2……——与 **列表取项** 的序号一致）。某格吞进了留白、或两格连在一起，一眼就能看出来。

## 提示
- 留白只要大致在均匀切分的位置附近即可；模型画的网格很少完全均匀，以找到的留白为准。
- 各格尺寸会差几个像素；视频和图像模型本来就会缩放，需要一致时接 **智能缩放**。
- 与 **图像网格** 互为逆操作。
"""))

node("Arbor_ImageGrid", en=dict(
    desc="Lay images out as an XY comparison sheet: each branch is a row, each item a column.",
    inputs={"images": "An image tree — or the plain images of a batch run, together with shape.",
            "shape": "XY Lists' shape: pours plain images into rows × columns and labels them (rows by x, columns by y).",
            "row_labels": "One label per row — a list, or a tree with one branch per row. Not needed when the tree or shape names its rows (XY Lists, Prompt Template, Cross Reference).",
            "col_labels": "One label per column — overrides the labels taken from shape (which labels the columns when every row holds the same values, as in XY Lists).",
            "fit": "How pictures of different sizes fill a cell: fit (whole picture, bars around) · fill (covers the cell, edges cut) · original (no scaling) · stretch (fills the cell, distorted).",
            "cell_size": "Longest side of a cell in pixels; 0 = the largest image's size.",
            "gap": "Space between cells and around the sheet, in pixels.",
            "font_size": "Label font size. Chinese labels render with a CJK font when one is installed.",
            "theme": "Light or dark sheet background.",
            "path_labels": "Label rows with their branch path when there are no row labels or row names.",
            "captions": "One caption per cell — e.g. the prompts or seeds of a batch run: a tree shaped like the grid (item by item, branch by branch) or a flat list read cell by cell. Long captions wrap to three lines.",
            "columns": "0: one row per branch. N: every branch wraps after N cells — a flat list of 20 becomes 4 rows of 5; a branch's label spans all its rows. Column labels are left out when wrapping.",
            "label_direction": "Row labels: auto (horizontal while they fit in two lines, otherwise standing up) · horizontal · vertical. Standing up, Chinese stacks upright; other text reads bottom to top.",
            "caption_style": "below: under each cell (the sheet grows to fit) · overlay: on a dark bar across the bottom of the picture."},
    outputs=["The comparison sheet as one image."],
    doc="""## How to use
- **After a batch run**: connect the decoded images to *images* and **XY Lists'** *shape* to *shape*. Rows and columns come out right and are labelled — rows with the x values, columns with the y values. Nothing else to connect.
- **From a tree**: connect any image tree — each branch becomes a row. Use **Reshape Tree** (*flip matrix*) first to swap rows and columns.

## Captions and layout
- **captions**: one text per cell — connect a Prompt Template, the seeds of an XY run or Load Media's *names*. *caption_style* puts them under the cells or on a bar over the picture.
- **columns**: wrap long branches (or a flat list) after N cells instead of one very long row.
- **fit = fill** crops every picture to the cell, so mixed sizes still make an even grid.
- Long row labels stand up by themselves (*label_direction* auto).

## Tips
- Long labels wrap to three lines and are cut with "…".
- Save the sheet with Save Image, or every image separately with **Save by Path**.
"""), zh=dict(
    name="图像网格",
    desc="把图片排成 XY 对比图：每个分支一行，每项一列。",
    inputs={"images": ("图像", "图像数据树——或批量运行得到的普通图片（配合结构使用）。"),
            "shape": ("结构", "XY 组合列表的结构：把普通图片排成行 × 列并标注（行是 x，列是 y）。"),
            "row_labels": ("行标签", "每行一个标签——列表，或每行一个分支的数据树。数据树或结构自带行名时（XY 组合列表、提示词模板、交叉组合）不用接。"),
            "col_labels": ("列标签", "每列一个标签——会覆盖从结构得到的列标签（结构每行取值都相同时才用来标注列，例如 XY 组合列表）。"),
            "fit": ("适配", "不同尺寸的图片如何填充格子：fit 完整显示（四周留白）· fill 铺满格子（裁掉多出的边缘）· original 原尺寸 · stretch 拉伸铺满（会变形）。"),
            "cell_size": ("格子尺寸", "格子长边像素；0 = 最大图片的尺寸。"),
            "gap": ("间距", "格子之间以及四周的留白像素。"),
            "font_size": ("字号", "标签字号。系统装有中日韩字体时，中文标签会正常显示。"),
            "theme": ("主题", "浅色或深色背景。"),
            "path_labels": ("路径作行标签", "既没有行标签也没有行名时，用分支路径作为行标签。"),
            "captions": ("单元格说明", "每格一句说明——例如批量运行的提示词或种子：与网格结构相同的数据树（每个分支逐项对应），或按格子顺序读取的列表。过长的说明最多折成三行。"),
            "columns": ("每行列数", "0：每个分支一行。N：每个分支满 N 格换行——20 项的平铺列表变成 4 行 × 5 列；分支的行标签跨越它的所有行。换行排版时不显示列标签。"),
            "label_direction": ("行标签方向", "auto 自动（两行内放得下就横排，否则竖排）· horizontal 横排 · vertical 竖排。竖排时中文逐字竖排、字保持正立，其它文字从下往上读。"),
            "caption_style": ("说明位置", "below：格子下方（对比图相应变高）· overlay：叠在画面底部的深色条上。")},
    outputs=[("图像", "合成后的对比图（一张）。")],
    doc="""## 用法
- **批量运行之后**：解码后的图片接 *图像*，**XY 组合列表** 的 *结构* 接 *结构*，行列自动排好并标注——行是 x 的取值，列是 y 的取值，不用再接别的。
- **来自数据树**：直接接任意图像数据树，每个分支一行。想交换行列，先接 **重组数据树**（*翻转矩阵*）。

## 单元格说明与排版
- **单元格说明**：每格一句文字——可以接提示词模板、XY 批量运行的种子，或「加载素材」的文件名。*说明位置* 决定放在格子下方还是叠在画面上。
- **每行列数**：过长的分支（或平铺列表）满 N 格自动换行，不再排成一长行。
- **适配选 fill**：每张图裁切铺满格子，尺寸不一的素材也能排得整整齐齐。
- 行标签过长时会自动竖排（*行标签方向* 为 auto）。

## 提示
- 过长的标签最多折成三行，超出部分用「…」省略。
- 整张图用「保存图像」保存；想把每张单独存下来，用 **按路径保存**。
"""))

node("Arbor_VideoGrid", en=dict(
    desc="Image Grid for video: each branch is a row, each clip a column, all playing in sync in one labelled video.",
    inputs={"videos": "A video tree — or the plain videos of a batch run, together with shape. An image batch counts as one clip (its frames played at the grid's frame rate).",
            "shape": "XY Lists' shape: pours plain videos into rows × columns and labels them (rows by x, columns by y).",
            "row_labels": "One label per row — a list, or a tree with one branch per row. Not needed when the tree or shape names its rows.",
            "col_labels": "One label per column — overrides the labels taken from shape.",
            "fit": "How clips of different sizes fill a cell: fit (whole clip, bars around) · fill (covers the cell, edges cut) · original (no scaling) · stretch (fills the cell, distorted).",
            "cell_size": "Longest side of a cell in pixels; 0 = the largest clip's size. Keep it modest — the grid video is width × height of all cells.",
            "gap": "Space between cells and around the grid, in pixels.",
            "font_size": "Label font size. Chinese labels render with a CJK font when one is installed.",
            "theme": "Light or dark background.",
            "path_labels": "Label rows with their branch path when there are no row labels or row names.",
            "captions": "One caption per cell — e.g. the prompts or seeds of a batch run: a tree shaped like the grid (item by item, branch by branch) or a flat list read cell by cell. Long captions wrap to three lines.",
            "columns": "0: one row per branch. N: every branch wraps after N cells — a flat list of 20 becomes 4 rows of 5; a branch's label spans all its rows. Column labels are left out when wrapping.",
            "label_direction": "Row labels: auto (horizontal while they fit in two lines, otherwise standing up) · horizontal · vertical. Standing up, Chinese stacks upright; other text reads bottom to top.",
            "caption_style": "below: under each cell (the sheet grows to fit) · overlay: on a dark bar across the bottom of the picture.",
            "fps": "Frame rate of the grid video; 0 = the highest frame rate among the clips. Every clip keeps its own speed.",
            "audio": "none: a silent grid · mix: every clip's sound mixed together (loudness kept below clipping)."},
    outputs=["The grid as one VIDEO (H.264 MP4 in the temp folder) — save it with Save by Path or Save Video, or compare it in the Compare Viewer."],
    doc="""## How to use
- **From a tree**: connect any video tree, e.g. *arbor_h3_two_characters*'s clips through **Construct Tree** (one row per scene), or **Load Folder** with kind *videos* (one row per folder).
- **After a batch run**: connect the plain videos to *videos* and **XY Lists'** *shape* to *shape* — rows and columns are laid out and labelled like **Image Grid**.
- The node shows the grid video when it runs; it also works on its own, nothing needs to follow it.

## Timing
- All clips start together. Each plays at its own frame rate; shorter clips hold their last frame until the longest one ends.
- Clips are decoded straight at cell size, frame by frame, so long or large videos do not need much memory.

## Captions and layout
- **captions**: one text per cell — connect a Prompt Template, the seeds of an XY run or Load Media's *names*. *caption_style* puts them under the cells or on a bar over the clip (drawn into every frame).
- **columns**: wrap long branches (or a flat list) after N cells instead of one very long row.
- **fit = fill** crops every picture to the cell, so mixed sizes still make an even grid.
- Long row labels stand up by themselves (*label_direction* auto).

## Tips
- Use **Reshape Tree** (*flip matrix*) first to swap rows and columns.
- For a single pair, the **Compare Viewer** is quicker: it plays both in sync with a wipe divider.
"""), zh=dict(
    name="视频网格",
    desc="视频版的图像网格：每个分支一行，每段视频一列，全部同步播放，合成为一段带标注的视频。",
    inputs={"videos": ("视频", "视频数据树——或批量运行得到的普通视频（配合结构使用）。图片批次算作一段视频（按网格帧率播放）。"),
            "shape": ("结构", "XY 组合列表的结构：把普通视频排成行 × 列并标注（行是 x，列是 y）。"),
            "row_labels": ("行标签", "每行一个标签——列表，或每行一个分支的数据树。数据树或结构自带行名时不用接。"),
            "col_labels": ("列标签", "每列一个标签——会覆盖从结构得到的列标签。"),
            "fit": ("适配", "不同尺寸的视频如何填充格子：fit 完整显示（四周留白）· fill 铺满格子（裁掉多出的边缘）· original 原尺寸 · stretch 拉伸铺满（会变形）。"),
            "cell_size": ("格子尺寸", "格子长边像素；0 = 最大视频的尺寸。别设太大——网格视频的尺寸是所有格子加起来。"),
            "gap": ("间距", "格子之间以及四周的留白像素。"),
            "font_size": ("字号", "标签字号。系统装有中日韩字体时，中文标签会正常显示。"),
            "theme": ("主题", "浅色或深色背景。"),
            "path_labels": ("路径作行标签", "既没有行标签也没有行名时，用分支路径作为行标签。"),
            "captions": ("单元格说明", "每格一句说明——例如批量运行的提示词或种子：与网格结构相同的数据树（每个分支逐项对应），或按格子顺序读取的列表。过长的说明最多折成三行。"),
            "columns": ("每行列数", "0：每个分支一行。N：每个分支满 N 格换行——20 项的平铺列表变成 4 行 × 5 列；分支的行标签跨越它的所有行。换行排版时不显示列标签。"),
            "label_direction": ("行标签方向", "auto 自动（两行内放得下就横排，否则竖排）· horizontal 横排 · vertical 竖排。竖排时中文逐字竖排、字保持正立，其它文字从下往上读。"),
            "caption_style": ("说明位置", "below：格子下方（对比图相应变高）· overlay：叠在画面底部的深色条上。"),
            "fps": ("帧率", "网格视频的帧率；0 = 各段视频中最高的帧率。每段视频保持自己的播放速度。"),
            "audio": ("音频", "none：无声 · mix：把所有视频的声音混在一起（自动压低音量避免爆音）。")},
    outputs=[("视频", "合成后的网格视频（VIDEO，临时文件夹里的 H.264 MP4）——用「按路径保存」或「保存视频」保存，也可以接「对比查看器」。")],
    doc="""## 用法
- **来自数据树**：接任意视频数据树，例如 *arbor_h3_two_characters* 里经 **构建数据树** 整理好的视频（每个场景一行），或「加载文件夹」类型选 *videos*（每个文件夹一行）。
- **批量运行之后**：普通视频接 *视频*，**XY 组合列表** 的 *结构* 接 *结构*——和 **图像网格** 一样自动排好行列并标注。
- 运行后节点上直接显示网格视频；节点可以单独运行，后面不必再接别的节点。

## 时间
- 所有视频同时开始，各自按自己的帧率播放；较短的视频停在最后一帧，直到最长的一段结束。
- 视频按格子尺寸逐帧解码，长视频或大尺寸视频也不会占用太多内存。

## 单元格说明与排版
- **单元格说明**：每格一句文字——可以接提示词模板、XY 批量运行的种子，或「加载素材」的文件名。*说明位置* 决定放在格子下方还是叠在画面上（每一帧都会画上）。
- **每行列数**：过长的分支（或平铺列表）满 N 格自动换行，不再排成一长行。
- **适配选 fill**：每张图裁切铺满格子，尺寸不一的素材也能排得整整齐齐。
- 行标签过长时会自动竖排（*行标签方向* 为 auto）。

## 提示
- 想交换行列，先接 **重组数据树**（*翻转矩阵*）。
- 只对比两段时，**对比查看器** 更方便：同步播放，还能左右拖动分割线。
"""))

node("Arbor_LoadMedia", en=dict(
    desc="Pick pictures, videos and audio from anywhere on disk and group them into named branches — several Load Image nodes in one, using the system's own file dialog, with thumbnails. Files are used where they are; nothing is copied.",
    inputs={"files": "The list (kept as text): '# name' starts a named group, an empty line a new group, every other line is a file — an absolute path, output/… (ComfyUI's output folder), arbor:… (Arbor's sample media) or relative to the input folder. Edit it in the node's Text view, or fill it with Add…."},
    outputs=["Everything, one branch per group, named after it — for the Compare Viewer, Save by Path or a Panel.",
             "Only the pictures (IMAGE), same groups — go on to Tree to Data → image nodes, or Image Grid.",
             "Only the videos (VIDEO), same groups.",
             "Only the audio clips (AUDIO), same groups.",
             "File names without extension, like files — handy as captions or for Save by Path."],
    doc="""## How to use
- **Add…** opens the system's file dialog. Select one or several pictures, videos or audio files and press **Add** — they go into the selected group.
- To take a **whole folder**, go into it and press **Add** without selecting anything (the name box says *(add this folder)*): every media file in it is added, each subfolder becoming a group named after it, like Load Folder.
- Files go into the group you clicked last; **+ Group** starts a new one. Rename a group in its header, drag thumbnails to reorder or move them between groups, × removes.
- **Text** shows the list itself — paste paths, write `# name` lines, delete lines.

```
# Arrival                              →  files {0} Arrival: 2 pictures
output/shots/arrival_01.png
output/shots/arrival_02.png

# Sound                                →  files {1} Sound: 1 audio
C:/music/theme.wav
```

## Load Media or Load Folder?
- **Load Media**: exactly the files you picked, in your order, from anywhere — the list is saved with the workflow.
- **Load Folder**: everything in a folder, re-read on every run — new files are picked up by themselves.

## Tips
- The dialog opens on the computer ComfyUI runs on and hands back real paths, so nothing is copied; it opens where you picked last. On macOS / Linux it picks files only — type folders in the Text view. Opened from another computer, type the paths in the Text view instead.
- Paths inside ComfyUI's output or input folder are written short (`output/…`, relative), so the workflow still works when ComfyUI moves.
- The templates use `arbor:storyboard/…`, the sample keyframes that come with Arbor.
- The node re-runs when a listed file changes.
"""), zh=dict(
    name="加载素材",
    desc="从硬盘任意位置挑选图片、视频和音频，分组成带名字的分支——相当于把多个「加载图像」合成一个节点，用系统自带的文件窗口选择，带缩略图。文件原地使用，不复制。",
    inputs={"files": ("文件", "文件列表（以文本保存）：「# 名字」开始一个有名字的分组，空一行开始新分组，其余每行一个文件——绝对路径、output/…（ComfyUI 的 output 文件夹）、arbor:…（Arbor 自带的示例素材），或相对于 input 文件夹的路径。可以在节点的「文本」视图里直接编辑，也可以用「添加…」添加。")},
    outputs=[("文件", "全部文件，每个分组一个分支，并以分组命名——可以接对比查看器、按路径保存或面板。"),
             ("图片", "只有图片（IMAGE），分组相同——接「数据树转数据」后给图片节点，或接图像网格。"),
             ("视频", "只有视频（VIDEO），分组相同。"),
             ("音频", "只有音频（AUDIO），分组相同。"),
             ("文件名", "不带扩展名的文件名，结构同「文件」——可作单元格说明，或给「按路径保存」命名。")],
    doc="""## 用法
- **添加…** 打开系统的文件窗口：选中一个或多个图片、视频、音频文件，点 **添加**——它们会放进选中的分组。
- 想添加**整个文件夹**：进入这个文件夹，不选任何文件直接点 **添加**（文件名框里是「（添加当前文件夹）」）——其中所有媒体文件都会加入，每个子文件夹成为一个以它命名的分组，和「加载文件夹」一样。
- 文件会加到最后点击的分组里；**+ 分组** 新建分组。在分组标题上改名，拖动缩略图调整顺序或移到别的分组，× 移除。
- **文本** 视图显示列表本身——可以粘贴路径、写「# 名字」、删除行。

```
# Arrival                              →  文件 {0} Arrival：2 张图片
output/shots/arrival_01.png
output/shots/arrival_02.png

# Sound                                →  文件 {1} Sound：1 段音频
C:/music/theme.wav
```

## 加载素材还是加载文件夹？
- **加载素材**：只读你挑选的文件，按你排的顺序，可以来自任何位置——列表随工作流保存。
- **加载文件夹**：读取文件夹里的全部文件，每次运行都重新读取——新增的文件会自动包含进来。

## 提示
- 系统窗口在运行 ComfyUI 的电脑上打开，返回真实路径，所以不需要复制文件；会从上次选择的位置打开。macOS / Linux 上只能选文件——文件夹请在「文本」视图里输入。从其它电脑访问时，请在「文本」视图里直接输入路径。
- 位于 ComfyUI output 或 input 文件夹里的文件会写成短路径（`output/…`、相对路径），ComfyUI 换位置后工作流仍然可用。
- 模板使用 `arbor:storyboard/…`，即 Arbor 自带的示例关键帧。
- 列表中的文件有改动时，节点会自动重新运行。
"""))

node("Arbor_LoadFolder", en=dict(
    desc="Load every picture, video or audio file in a folder; with subfolders on, each folder becomes a branch, named after it — the folder structure turns straight into a data tree.",
    inputs={"folder": "An absolute path; output/… for ComfyUI's output folder; arbor:… for Arbor's sample media; any other relative path is inside the input folder. The folder icon at the end of the box picks it with the system's folder dialog.",
            "kind": "What to load: images (IMAGE) · videos (VIDEO — read lazily, nothing is decoded until a node needs the frames) · audio (AUDIO). Each kind has its own file pattern.",
            "kind.pattern": "File name patterns separated by spaces, e.g. *.png *.jpg or *.mp4 *.mov or *.wav *.flac.",
            "subfolders": "On: each subfolder (and the folder itself, if it has matching files) becomes a branch. Off: only this folder.",
            "sort": "name = natural order (img2 before img10); modified = oldest first.",
            "limit": "Maximum number of files in total; 0 = all. Pictures and audio are held in memory, so limit large folders."},
    outputs=["The pictures / videos / audio as a tree, one branch per folder, named after it — Image Grid labels its rows with the names, the Panel and Compare Viewer show them.",
             "File names without extension, same layout — handy as labels or for Save by Path.",
             "Folder names as plain data, one per branch.", "Total number of files."],
    doc="""## Example
```
shots/             →  files {0}: 2 videos   folders: shots
  a.mp4 b.mp4
  day/             →  files {1}: 3 videos   folders: day
  night/           →  files {2}: 1 video    folders: night
```
Videos go on to **Tree to Data** → any node with a VIDEO input (Get Video Components, Save Video…), once per clip; audio the same with AUDIO inputs.

## Choosing the folder
The **folder icon** at the end of the folder box opens the system's folder dialog. A folder inside ComfyUI's output folder is written as `output/…`. The dialog opens on the computer ComfyUI runs on; from another computer, type the path.

## Round trip
Folders saved by **Save by Path** from named branches (`0 · Arrival`, `1 · The village`) load back with their names (*Arrival*, *The village*) and in their order. Template: *arbor_folder_review*.

## Tips
- The node re-runs automatically when files are added, removed or changed.
- Pictures keep their own sizes; resize with **Smart Resize** if the next step needs one size.
"""), zh=dict(
    name="加载文件夹",
    desc="加载文件夹里的所有图片、视频或音频；开启子文件夹后，每个文件夹就是一个以它命名的分支——目录结构直接变成数据树。",
    inputs={"folder": ("文件夹", "绝对路径；output/… 表示 ComfyUI 的 output 文件夹；arbor:… 表示 Arbor 自带的示例素材；其它相对路径都在 input 文件夹里。也可以点输入框末尾的文件夹图标，用系统的文件夹窗口选择。"),
            "kind": ("类型", "加载什么：images 图片（IMAGE）· videos 视频（VIDEO——按需读取，下游节点用到画面时才解码）· audio 音频（AUDIO）。每种类型有自己的文件匹配。"),
            "kind.pattern": ("文件匹配", "用空格分隔的文件名模式，例如 *.png *.jpg、*.mp4 *.mov 或 *.wav *.flac。"),
            "subfolders": ("子文件夹", "开启：每个子文件夹（以及本文件夹，如果里面有匹配的文件）各成一个分支。关闭：只读本文件夹。"),
            "sort": ("排序", "name = 自然排序（img2 排在 img10 前）；modified = 按修改时间从旧到新。"),
            "limit": ("数量上限", "最多加载的文件总数；0 = 全部。图片和音频会载入内存，大文件夹请设上限。")},
    outputs=[("文件", "图片 / 视频 / 音频组成的数据树，每个文件夹一个分支，并以文件夹命名——图像网格用名字标注行，面板和对比查看器也会显示。"),
             ("文件名", "不带扩展名的文件名，结构相同——可作标签或给「按路径保存」用。"),
             ("文件夹", "文件夹名（普通数据），每个分支一个。"), ("数量", "文件总数。")],
    doc="""## 示例
```
shots/             →  文件 {0}：2 个视频   文件夹：shots
  a.mp4 b.mp4
  day/             →  文件 {1}：3 个视频   文件夹：day
  night/           →  文件 {2}：1 个视频   文件夹：night
```
视频接 **数据树转数据** → 任意有 VIDEO 输入的节点（获取视频组件、保存视频……），每段运行一次；音频同理接 AUDIO 输入。

## 选择文件夹
点文件夹输入框末尾的 **文件夹图标** 打开系统的文件夹窗口。位于 ComfyUI output 文件夹里的文件夹会写成 `output/…`。窗口在运行 ComfyUI 的电脑上打开；从其它电脑访问时请直接输入路径。

## 往返
**按路径保存** 按有名字的分支保存的文件夹（`0 · Arrival`、`1 · The village`）读回来时会恢复名字（*Arrival*、*The village*）和顺序。模板：*arbor_folder_review*。

## 提示
- 文件有增删改时，节点会自动重新读取。
- 图片保持各自的尺寸；后续需要统一尺寸时用 **智能缩放**。
"""))

node("Arbor_SaveByPath", en=dict(
    desc="Save a tree keeping its structure — pictures as PNG, videos as MP4, audio as FLAC, text as TXT: one subfolder (or filename part) per branch, named after the branch when it has a name, with optional names per file.",
    inputs={"tree": "What to save — a tree, a list or a single value. Picture batches are saved frame by frame, audio batches clip by clip; other values are skipped.",
            "filename_prefix": "Where to save: a folder / prefix inside ComfyUI's output folder (arbor/run), output/…, or an absolute path such as D:/renders/run — the folder icon at the end of the box picks the folder. Outside the output folder only while ComfyUI listens on this computer alone. Supports %date%-style variables.",
            "layout": "subfolders: prefix/0-1/000.png (a named branch: prefix/0-1 · name/000.png) · flat: prefix_0-1_000.png. A plain list (one unnamed branch {0}) goes straight under the prefix: prefix/000.png · prefix_000.png",
            "names": "Optional file names, matched to the files item by item (e.g. Load Folder's names or a Prompt Template)."},
    outputs=["Saved file paths, in the same tree layout (and with the same names)."],
    doc="""## Example
Tree `{0} Arrival: 2 clips · {1} Village: 1 clip`, prefix `arbor/h3`, layout *subfolders*:
```
output/arbor/h3/0 · Arrival/000.mp4  001.mp4
output/arbor/h3/1 · Village/000.mp4
```
Pictures become `000.png …`, audio `000.flac …`, text `000.txt …` — a branch may mix them. **Load Folder** with `output/arbor/h3_two_characters` (kind *videos*) reads the tree back, names included. Template: *arbor_h3_storyboard_video*.

With *names* connected the files are called after the names instead (`cat.png`, `dog.png`, …).

## Saving anywhere
Click the **folder icon** at the end of the prefix box to pick the destination with the system's folder dialog — the last part of the prefix (`run`, `batch`) is kept as the file name part. An absolute prefix (`D:/renders/run`) saves outside ComfyUI's output folder:
- allowed while ComfyUI listens on this computer alone (the default, no `--listen`);
- refused when ComfyUI is opened to the network (`--listen`), because anyone who can queue a workflow could then write anywhere on your disk — set the environment variable `ARBOR_SAVE_ANYWHERE=1` to allow it anyway.

Previews of files saved outside the output folder are shown from a copy in the temp folder.

## Tips
- Existing files are never overwritten: a `_2`, `_3`, … suffix is added.
- The workflow is embedded in every PNG, MP4 and FLAC, like ComfyUI's own save nodes.
"""), zh=dict(
    name="按路径保存",
    desc="按数据树结构保存——图片存 PNG、视频存 MP4、音频存 FLAC、文字存 TXT：每个分支一个子文件夹（或文件名的一部分），有名字的分支用名字命名，可选为每个文件命名。",
    inputs={"tree": ("数据树", "要保存的内容——数据树、列表或单个值。图片批次逐帧保存，音频批次逐段保存；其它类型的值会跳过。"),
            "filename_prefix": ("文件名前缀", "保存位置：output 文件夹内的目录 / 前缀（arbor/run）、output/…，或绝对路径如 D:/renders/run——点输入框末尾的文件夹图标可以选择文件夹。只有 ComfyUI 只在本机监听时才能存到 output 以外。支持 %date% 等变量。"),
            "layout": ("布局", "subfolders：前缀/0-1/000.png（有名字的分支：前缀/0-1 · 名字/000.png）· flat：前缀_0-1_000.png。普通列表（只有一个未命名的分支 {0}）直接存在前缀下：前缀/000.png · 前缀_000.png"),
            "names": ("文件名", "可选，与文件逐项对应的文件名（例如「加载文件夹」的文件名或提示词模板的输出）。")},
    outputs=[("路径", "已保存文件的路径，结构（和分支名）与输入相同。")],
    doc="""## 示例
数据树 `{0} Arrival: 2 段 · {1} Village: 1 段`，前缀 `arbor/h3`，布局 *subfolders*：
```
output/arbor/h3/0 · Arrival/000.mp4  001.mp4
output/arbor/h3/1 · Village/000.mp4
```
图片存为 `000.png ……`，音频 `000.flac ……`，文字 `000.txt ……`——同一个分支里可以混合。**加载文件夹** 读取 `output/arbor/h3_two_characters`（类型选 *videos*）就能把数据树连同名字读回来。模板：*arbor_h3_storyboard_video*。

接入 *文件名* 后，文件按名字命名（`cat.png`、`dog.png`……）。

## 保存到任意位置
点前缀输入框末尾的 **文件夹图标**，用系统的文件夹窗口选择保存位置——前缀的最后一段（`run`、`batch`）保留为文件名部分。绝对路径前缀（`D:/renders/run`）会保存到 ComfyUI 的 output 文件夹以外：
- ComfyUI 只在本机监听时（默认，没有 `--listen`）允许；
- ComfyUI 对局域网开放时（`--listen`）拒绝，因为那样任何能提交工作流的人都能往你的硬盘任意位置写文件——如确实需要，设置环境变量 `ARBOR_SAVE_ANYWHERE=1` 即可允许。

保存在 output 以外的文件，预览会从临时文件夹里的副本显示。

## 提示
- 永远不会覆盖已有文件：会自动加 `_2`、`_3`…… 后缀。
- 和 ComfyUI 自带的保存节点一样，每个 PNG、MP4、FLAC 都内嵌工作流。
"""))

# =============================================================== Data

node("Arbor_Panel", en=dict(
    desc="Inspect anything, or type data in. Connected: shows the input and passes it through. Unconnected: each line you type is an item, an empty line starts a new branch and a `# title` line names it.",
    inputs={"data": "Anything — a data tree, a native list, an image, a number… Leave it unconnected to type data instead.",
            "text": "The typed data (used when nothing is connected). Edited in the panel itself.",
            "parse_numbers": "Typed values: lines like 7 / 3.5 / true become INT / FLOAT / BOOLEAN. The 123 / abc button in the panel.",
            "multiline": "Text mode: the whole text is one item. The Lines / Text switch in the panel."},
    outputs=["The data as a native list: downstream nodes run once per item (a single item runs once).",
             "The data as a tree — for Arbor nodes, keeps the branches."],
    doc="""## Viewing (input connected)
- Trees show as collapsible branches with their path, name and count (`{1} 7 N=3` — XY Lists names each row after its x value); images as thumbnails; audio and video with their length, rate and size (`Audio 2.3 s · 32 kHz · stereo`, `Video 736×416 · 56 frames · 24 fps · 2.3 s`).
- Long text folds to four lines — *more* unfolds it. Hover an item to copy it; the toolbar copies everything.
- **Live**: when everything upstream is a lightweight data node (Arbor data / tree / list nodes, primitives, string and math nodes) the view updates as you edit — no run needed (green dot). Anything heavier upstream (samplers, loaders) never runs on its own; the panel then shows the last run.
- ⤢ opens a large view.

## Typing (input unconnected)
- **Lines**: one item per line, an empty line starts a new branch. A line `# title` names its branch instead of being an item — the name shows up as the row label in **Image Grid**, as the folder name in **Save by Path**, and in every Panel downstream. The gutter shows each line's branch path and index, coloured by type (blue = number, purple = boolean).
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

```
# Arrival
night train
paper map

# The village
misty roofs
```
→ `{0} Arrival: [night train, paper map]`, `{1} The village: [misty roofs]` — a storyboard (template *arbor_qwen_storyboard*).
"""), zh=dict(
    name="面板",
    desc="查看任何数据，或直接输入数据。接入时：显示输入并原样传出。未接入时：每行是一项，空一行开始新分支，`# 标题` 行给分支命名。（对应 Grasshopper 的 Panel）",
    inputs={"data": ("数据", "任何数据——数据树、原生列表、图片、数字…… 不接则改为手动输入。"),
            "text": ("文本", "手动输入的数据（未接入输入时使用），直接在面板里编辑。"),
            "parse_numbers": ("识别数值", "像 7 / 3.5 / true 这样的行变成 INT / FLOAT / BOOLEAN，对应面板里的 123 / abc 按钮。"),
            "multiline": ("整段文本", "整段文字作为一项，对应面板里的「逐行 / 整段」开关。")},
    outputs=[("数据", "原生列表：下游节点会对每一项各运行一次（只有一项时运行一次）。"),
             ("数据树", "数据树形式——给 Arbor 节点用，保留分支结构。")],
    doc="""## 查看（接入输入时）
- 数据树显示为可折叠的分支，带路径、名称和数量（`{1} 7 N=3`——XY 组合列表会用 x 的取值给每行命名）；图片显示缩略图；音频和视频显示时长、采样率 / 帧率和尺寸（`Audio 2.3 s · 32 kHz · stereo`、`Video 736×416 · 56 frames · 24 fps · 2.3 s`）。
- 长文本默认折叠成四行，点「展开」查看全部。鼠标悬停某项可单独复制；工具栏按钮复制全部。
- **实时**：上游全是轻量数据节点（Arbor 的数据 / 数据树 / 列表节点、Primitive、字符串和数学节点）时，编辑就会实时刷新，无需运行（绿点）。上游有采样器、加载器等重节点时不会自动运行，显示上一次运行的结果。
- ⤢ 打开大窗口查看。

## 输入（未接入时）
- **逐行**：每行一项，空一行开始新分支。`# 标题` 这样的行不是数据项，而是给所在分支命名——名字会成为 **图像网格** 的行标签、**按路径保存** 的文件夹名，下游面板也会显示。左侧标出每行的分支路径和序号，按类型着色（蓝色 = 数字，紫色 = 布尔值）。
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

```
# 到站
夜行列车
纸质地图

# 村庄
晨雾中的屋顶
```
→ `{0} 到站: [夜行列车, 纸质地图]`、`{1} 村庄: [晨雾中的屋顶]`——一份分镜脚本（模板 *arbor_qwen_storyboard*）。
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
    desc="Fill {a} {b} … in a template from trees. Cross builds every combination as a grid-ready tree; zip pairs them branch by branch and item by item, like Grasshopper.",
    inputs={"template": "Text with placeholders {a} … {f} (and, in zip mode, {name} — the branch's name). Placeholders without a connected value stay as they are. Several lines are fine.",
            "mode": "cross: every combination — rows = {a}, columns = the last variable used. zip: branches paired in order, items one by one (longest list), the tree keeps its branches and names.",
            "vars": "Values for {a}, {b}, … — a tree, a list or a single value. Each connection adds the next letter."},
    outputs=["Every filled prompt as plain data — connect straight to a text encoder (it runs once per prompt).",
             "The prompts as a tree (cross: one branch per combination of the outer variables — ready for Image Grid)."],
    doc="""## Example
Template `a photo of {a}, {b} style`, a = `cat, dog`, b = `oil, ink`:

| mode | result |
|---|---|
| cross | `{0}: cat·oil, cat·ink` · `{1}: dog·oil, dog·ink` |
| zip | `{0}: cat·oil, dog·ink` |

## Zip with branches
Zip matches like **Expression**: branch by branch in order, item by item, the shorter list repeating its last item. Two shots per scene against one sound line per scene:
```
a = {0} Arrival: door, map · {1} Village: mist, steps
b = {0}: horn · {1}: bells          template "{name}: {a} + {b}"
→ {0} Arrival: "Arrival: door + horn", "Arrival: map + horn"
  {1} Village: "Village: mist + bells", "Village: steps + bells"
```
`{name}` is the branch's name (a scene, a page). Templates *arbor_h3_two_characters* and *arbor_h3_long_takes* write a structured video prompt per shot / per scene this way.

## Tips
- Type the values in **Panels** (one per line) and connect their *data* output (or *tree*, to keep branches).
- Connect *data* to a text encoder: the sampler runs once per prompt. Connect *tree* to **Image Grid**'s *shape* to lay the images out in the same rows. Up to 10 000 combinations.
"""), zh=dict(
    name="提示词模板",
    desc="用数据树填充模板中的 {a} {b} ……。交叉：生成所有组合，直接得到可做网格的数据树；配对：像 Grasshopper 一样按分支、逐项对应。",
    inputs={"template": ("模板", "带占位符 {a} … {f} 的文本（配对模式下还有 {name}——分支的名字）；没接值的占位符保持原样。可以写多行。"),
            "mode": ("模式", "cross 交叉：所有组合——行 = {a}，列 = 最后一个用到的变量。zip 配对：按顺序配对分支、逐项对应（最长列表），结果保留分支和名字。"),
            "vars": ("变量", "{a}、{b} …… 的取值——数据树、列表或单个值。每接一个就多出下一个字母。")},
    outputs=[("数据", "所有填好的提示词（普通数据）——可直接接文本编码器，每个提示词运行一次。"),
             ("数据树", "提示词数据树（交叉模式下，外层变量的每种组合一个分支——可直接做图像网格）。")],
    doc="""## 示例
模板 `a photo of {a}, {b} style`，a = `cat, dog`，b = `oil, ink`：

| 模式 | 结果 |
|---|---|
| cross 交叉 | `{0}: cat·oil, cat·ink` · `{1}: dog·oil, dog·ink` |
| zip 配对 | `{0}: cat·oil, dog·ink` |

## 按分支配对
配对模式与 **表达式** 的匹配方式相同：分支按顺序配对，分支内逐项对应，较短的列表重复最后一项。每个场景两个镜头，配上每个场景一句声音描述：
```
a = {0} Arrival: door, map · {1} Village: mist, steps
b = {0}: horn · {1}: bells          模板 "{name}: {a} + {b}"
→ {0} Arrival: "Arrival: door + horn", "Arrival: map + horn"
  {1} Village: "Village: mist + bells", "Village: steps + bells"
```
`{name}` 是分支的名字（场景、页面）。模板 *arbor_h3_two_characters* 和 *arbor_h3_long_takes* 就是这样为每个镜头 / 每个场景写结构化的视频提示词。

## 提示
- 在 **面板** 里逐行输入取值，接它的 *数据* 输出（想保留分支就接 *数据树*）。
- *数据* 接文本编码器，采样器每个提示词各跑一次；*数据树* 接 **图像网格** 的 *结构*，图片按同样的行排列。最多 1 万种组合。
"""))

node("Arbor_Expression", en=dict(
    desc="Evaluate a formula for every item, like Grasshopper's Expression: x and y are matched branch by branch in order and item by item (longest list).",
    inputs={"expression": "Python-style formula, e.g. x * 2 + 1, x > 3, upper(x), x if i % 2 else -x.",
            "x": "First value — a tree, a list or a single value. Leave both empty for a single constant result.",
            "y": "Optional second value, matched to x branch by branch in order and item by item; whichever is shorter repeats its last branch / item."},
    outputs=["Every result as plain data.",
             "Results as a tree, with the paths of the input whose paths are longest (x on a tie). Comparisons give booleans — ready for Dispatch."],
    doc="""## Names
| name | meaning |
|---|---|
| `x`, `y` | the current items |
| `i` | item index in the branch |
| `b` | branch index |
| `n` | branch length |
| `name` | the branch's name (`Mira`, `Mira · lab coat`), or empty |
| `pi`, `e` | constants |

## Data matching (as in Grasshopper)
- Branches pair **in order**, not by path: x's 1st branch with y's 1st, 2nd with 2nd…; the input with fewer branches repeats its last one.
- Items pair **longest-list**: the shorter list repeats its last item, so a single y works with every x.
- The result takes the paths of the input with the **longest paths** (x on a tie); if that input runs out of branches, its last path counts on (`{0;1;0}`, `{0;1;1}`, …).

So combine data where the branches line up: one description per character with the outfits per character (same branches, same order) — then go deeper. Template: *arbor_qwen_character_sheet*.

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
"""), zh=dict(
    name="表达式",
    desc="对每一项计算公式，对应 Grasshopper 的 Expression：x 和 y 按分支顺序、按项（最长列表）配对。",
    inputs={"expression": ("表达式", "Python 风格的公式，例如 x * 2 + 1、x > 3、upper(x)、x if i % 2 else -x。"),
            "x": ("x", "第一个值——数据树、列表或单个值。x、y 都不接时只计算一个常量结果。"),
            "y": ("y", "可选的第二个值，与 x 按分支顺序、逐项配对；短的一方重复最后一个分支 / 最后一项。")},
    outputs=[("数据", "所有计算结果（普通数据）。"),
             ("数据树", "计算结果（数据树），沿用路径最长的输入的路径（一样长时用 x）。比较运算得到布尔值——可直接接「分流」。")],
    doc="""## 可用名称
| 名称 | 含义 |
|---|---|
| `x`、`y` | 当前项 |
| `i` | 项在分支内的序号 |
| `b` | 分支序号 |
| `n` | 分支长度 |
| `name` | 分支名（`Mira`、`Mira · lab coat`），没有则为空 |
| `pi`、`e` | 常数 |

## 数据匹配（与 Grasshopper 相同）
- 分支 **按顺序** 配对，不看路径：x 的第 1 个分支配 y 的第 1 个，第 2 个配第 2 个……；分支少的一方重复最后一个分支。
- 项按 **最长列表** 配对：短的一方重复最后一项，所以单个 y 可以配所有 x。
- 结果沿用 **路径最长** 的那个输入的路径（一样长时用 x）；它的分支不够时，最后一条路径的末位继续往上数（`{0;1;0}`、`{0;1;1}`……）。

所以要在分支对得上的那一层组合数据：每个角色一条描述，配每个角色的服装（分支相同、顺序相同），然后再往下一层。模板：*arbor_qwen_character_sheet*。

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

node("Arbor_Collect", en=dict(
    desc="Gather any values — pictures, masks, latents, audio, video, text — into data: one branch per input, named, or all in one list.",
    inputs={"inputs": "Anything. Every connection adds a slot. A list fills its branch with all its items; a tree keeps its own branches under {i;…}.",
            "mode": "branch per input: input 1 → {0}, input 2 → {1}, … (only connected slots count) · one list: everything in {0}, like ComfyUI's Create List.",
            "names": "One name per line, for the branches in input order. The names label Image Grid rows, Panel branches and Compare Viewer slides, and name the folders of Save by Path. In one-list mode the first line names the list.",
            "split_batch": "Split IMAGE / MASK / LATENT batches into one item per frame."},
    outputs=["Every collected item as plain data — ordinary nodes run once per item.",
             "The collected items as a tree, one named branch per input."],
    doc="""## Compare pipelines
```
Qwen   ─► input0 ┐
Flux   ─► input1 ├─ Collect (names: Qwen / Flux / original) ─ tree ─► Image Grid
LoadImage ► input2 ┘
```
Every pipeline becomes a row of the sheet, labelled with its name.

## Reference sets per scene
Connect one batch of reference pictures per scene, turn on *split_batch*, write the scene names: `{0} Arrival: 3 pictures · {1} Village: 2 pictures` — ready for **List Item**, **Cross Reference** or a reference-to-video run.

## Tips
- Text typed by hand is easier in a **Panel**; this node is for values that come from other nodes.
- Only connected slots count, so `{0}`, `{1}`, … have no gaps.
"""), zh=dict(
    name="收集",
    desc="把任意数据——图片、蒙版、latent、音频、视频、文字——收集成数据：每个输入一个有名字的分支，或全部放进一个列表。",
    inputs={"inputs": ("输入", "任意数据。每连一个就多出一个输入口。列表的所有项都放进它的分支；数据树保留自己的分支，放在 {i;…} 下。"),
            "mode": ("模式", "branch per input 每个输入一个分支：第 1 个输入 → {0}，第 2 个 → {1}……（只算已连接的输入口）· one list 一个列表：全部放进 {0}，同 ComfyUI 的 Create List。"),
            "names": ("名字", "一行一个名字，按输入顺序给分支命名。名字会成为图像网格的行标签、面板的分支名、对比查看器的页名，以及「按路径保存」的文件夹名。一个列表模式下，第一行给这个列表命名。"),
            "split_batch": ("拆分批次", "把 IMAGE / MASK / LATENT 批次拆成每帧一项。")},
    outputs=[("数据", "收集到的所有项（普通数据）——普通节点逐项运行。"),
             ("数据树", "收集到的项（数据树），每个输入一个有名字的分支。")],
    doc="""## 对比不同流程
```
Qwen    ─► 输入0 ┐
Flux    ─► 输入1 ├─ 收集（名字：Qwen / Flux / 原图）─ 数据树 ─► 图像网格
加载图像 ─► 输入2 ┘
```
每条流程成为对比图的一行，并用名字标注。

## 按场景准备参考图
每个场景接一批参考图，打开 *拆分批次*，写上场景名：`{0} Arrival: 3 张 · {1} Village: 2 张`——可以直接接 **列表取项**、**交叉组合** 或参考生视频。

## 提示
- 手动输入文字用 **面板** 更方便；本节点用于来自其它节点的数据。
- 只算已连接的输入口，所以 `{0}`、`{1}`……不会有空缺。
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
Tree → **Tree to Data** → ordinary nodes run per item → **Construct Tree** with *shape* = its shape → the results are back in the original branches.

## Tips
- A count mismatch is an error with both counts in the message — usually the shape is from a different tree than the one that was flattened.
- Every Arbor tree input already accepts plain data (as `{0}`); use this node for a specific path, a shape or split batches.
"""), zh=dict(
    name="构建数据树",
    desc="用普通数据构建数据树：所有项放在一个路径上，或——接入结构时——按另一棵树的分支把项收回去。",
    inputs={"data": ("数据", "任意值或普通数据（原生列表），例如批量运行的结果。"),
            "path": ("路径", "未接结构时放置这些项的分支路径，例如 {0} 或 {0;2}。"),
            "shape": ("结构", "要复制其分支结构的数据树——XY 组合列表的结构，或当初展开的那棵树。项数必须一致。"),
            "split_batch": ("拆分批次", "先把 IMAGE / MASK / LATENT 批次拆成每帧一项。")},
    outputs=[("数据树", "构建好的数据树。")],
    doc="""## 两种用法
| 接入 | 结果 |
|---|---|
| 只接数据 | 所有项放在 *路径* 上：`{0}: a, b, c` |
| 数据 + 结构 | 按结构的分支收回：结构 `{0}: ·, · · {1}: ·, ·` + `a b c d` → `{0}: a, b · {1}: c, d` |

## 往返
数据树 → **数据树转数据** → 普通节点逐项运行 → **构建数据树**（*结构* 接它的结构）→ 结果回到原来的分支。

## 提示
- 数量不一致会报错，并给出两边的数量——通常是结构接错了树，和当初展开的那棵不是同一棵。
- Arbor 的每个数据树输入本来就接受普通数据（作为 `{0}`）；需要指定路径、按结构收回或拆分批次时才用本节点。
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
    desc="Split text into items — one per line or separator; an empty line starts a new branch. table reads a pasted spreadsheet: one branch per column.",
    inputs={"text": "The text. Can be typed or connected from any STRING output.",
            "separator": "What separates items inside a paragraph: newline, comma, semicolon or |. table: rows copied from a spreadsheet or a CSV — cells split by tabs (or commas when there are none, quotes allowed), the first row names the columns, every column becomes a branch.",
            "blank_line_branches": "Paragraphs separated by an empty line become branches {0}, {1}, …",
            "strip": "Trim spaces around every item."},
    outputs=["Every item as plain text data (paragraphs one after another).", "The items as a tree: one branch per paragraph."],
    doc="""## Example
`red, green` ⏎ ⏎ `cat, dog` with separator `,` → `{0}: red, green` · `{1}: cat, dog`.

## Tables
Copy a shot list out of Excel or Google Sheets and paste it, separator `table`:
```
scene     motion                  sound
Arrival   the train pulls away    a distant horn
Village   mist drifts             birdsong
```
→ `{0} scene: Arrival, Village` · `{1} motion: …` · `{2} sound: …`. **Tree Branch** (index 1) takes the motion column for **Prompt Template**; **Reshape Tree** *flip matrix* turns it into one branch per row.

## Tips
- For typing, a **Panel** does the same with a live preview; use this node when the text comes from another node (a file loader, an LLM…).
"""), zh=dict(
    name="拆分文本",
    desc="把文本拆成多项——每行或每个分隔符一项；空行开始新分支。table 读取粘贴的表格：每列一个分支。",
    inputs={"text": ("文本", "要拆分的文本，可以手动输入，也可以接任意 STRING 输出。"),
            "separator": ("分隔符", "段落内用什么分隔各项：换行、逗号、分号或 |。table 表格：从电子表格或 CSV 复制来的行——用制表符分隔单元格（没有制表符时用逗号，支持引号），第一行是列名，每一列成为一个分支。"),
            "blank_line_branches": ("空行分支", "用空行分隔的段落分别成为分支 {0}、{1}……"),
            "strip": ("去除首尾空白", "去掉每一项两端的空格。")},
    outputs=[("数据", "拆分后的所有项（普通文本数据，各段依次排列）。"), ("数据树", "拆分后的数据树：每个段落一个分支。")],
    doc="""## 示例
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
"""))
