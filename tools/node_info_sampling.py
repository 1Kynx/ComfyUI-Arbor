"""Docs for the Sampling nodes (see node_info.py for the format)."""

from node_info import node

node("Arbor_H3TiledRefine", en=dict(
    desc="Lower the memory of a MiniMax H3 step by sampling the video in overlapping spatial tiles, blended at every step. Every tile keeps all frames, so the video is never split in time; guide frames and denoise masks are cropped to each tile.",
    inputs={"model": "A MiniMax H3 model, after its LoRAs and attention patches (Chunk FeedForward, Block Sparse Attention).",
            "tiles_x": "Tiles across. 0 = auto: the fewest tiles that keep each one about H3's native 768 × 1344 size. 1 with tiles_y 1 = off.",
            "tiles_y": "Tiles down. 0 = auto.",
            "overlap": "Pixels that neighbouring tiles share. Their predictions are blended there, so the joins don't show. 128 is plenty; 0 leaves visible seams.",
            "guide_mask": "Where the guide counts, at any size, one mask per frame or one for all. The guide is a second copy of the video's tokens; only those inside the mask (grown by a token) go in. The masked area follows the guide; the rest keeps only what the start latent holds, so at high start noise it is redrawn (new faces, new detail) and at low noise it stays close. Fewer tokens run faster: with a third of the frame masked a step takes about half as long. For more margin than the one guide token (32 px) always kept around it, grow the mask first with Grow Mask. Not connected: the whole guide."},
    outputs=["The model, patched to sample in tiles. Connect it to the guider (BasicGuider)."],
    doc="""## What it is for
Re-sampling an existing video at low denoise — detail repair, an upscale pass — so the result stays close to the original. The encoded original is the start latent, a few steps from sigma ≈ 0.5–0.7. That latent already fixes composition and motion, so every tile only has to add local detail.

## How it works
At every model call the video latent is cut into overlapping tiles on H3's 2 × 2 patch grid. Each tile keeps the whole timeline and goes through the model on its own, with the guide frames and the denoise mask cropped to it; H3 rebuilds its token layout for the tile's size. The denoised predictions are blended back with feathered weights before the next step. Audio is shared by every tile; its predictions are averaged (lock it with a 0 noise mask to keep the original).

## Measured (124 frames, 9 guide frames, two steps)
| Size | Untiled | Tiled | PSNR vs original |
|---|---|---|---|
| 1088 × 1920 | 99 s · 6.4 GB activations | 2 × 2: 77 s · 2.4 GB | 31.07 → 31.08 dB |
| 1440 × 2560 | 251 s | 2 × 2: 152 s | 32.06 → 32.28 dB |

No seams in the overlap zones. At 2K the 2 × 2 tiles are about H3's native size, which is why they stay closer to the original than one big canvas.

## Auto tiles
| Video | Auto grid |
|---|---|
| 768 × 1344 and smaller | 1 tile (off) |
| 1088 × 1920 | 2 |
| 1440 × 2560 | 2 × 2 |
| 2048 × 2048 | 2 × 3 |
| 2160 × 3840 | 5 × 2 |

## Tips
- Keep ComfyUI's default **dynamic VRAM**. With `--disable-dynamic-vram` or `--lowvram` the weights are streamed from RAM for every model call, so each tile streams them again: tiling still saves memory but runs slower.
- For text-to-video from noise, tiles can drift apart in content — use it for refinement, not generation.
- Pair it with **Add Guide Frames for MiniMax H3** to anchor the original's frames; the guides are cropped to every tile.
"""), zh=dict(
    name="MiniMax H3 分块精修",
    desc="把 MiniMax H3 每一步的画面切成重叠的空间块分别采样、每步羽化融合，降低显存。每块保留全部帧（不切时间）；引导帧和去噪蒙版按块同步裁剪。",
    inputs={"model": ("模型", "MiniMax H3 模型，接在 LoRA 和注意力补丁（Chunk FeedForward、Block Sparse Attention）之后。"),
            "tiles_x": ("横向块数", "横向分几块。0 = 自动：每块约为 H3 原生 768 × 1344 尺寸时块数最少。与纵向都为 1 = 关闭。"),
            "tiles_y": ("纵向块数", "纵向分几块。0 = 自动。"),
            "overlap": ("重叠", "相邻块共享的像素，在这里融合预测，接缝看不出来。128 足够；0 会有明显接缝。"),
            "guide_mask": ("引导蒙版", "引导在哪里起作用，尺寸不限，每帧一张或全部共用一张。引导是视频 token 的第二份拷贝，只有蒙版内（外扩一个 token）的那部分送进模型。蒙版内跟随引导；蒙版外只保留起始 latent 里的内容：起始噪声高时会重画（新的脸、新的细节），噪声低时变化不大。token 少了就更快：蒙版占画面三分之一时每步约省一半。蒙版周围固定多留一个引导 token（32 px）；要留更多就先接 Grow Mask 扩大蒙版。不接时用完整引导。")},
    outputs=[("模型", "按块采样的模型，接到引导器（BasicGuider）。")],
    doc="""## 用途
在原视频基础上低去噪二次采样——细节修复、放大精修——结果尽量贴近原片。原片编码成起始 latent，从 sigma ≈ 0.5–0.7 采几步。构图和动作已经由 latent 决定，每块只需补局部细节。

## 原理
每次模型调用，把视频 latent 按 H3 的 2 × 2 补丁网格切成重叠的块。每块保留完整时间轴，单独送进模型，引导帧和去噪蒙版裁到同一块；H3 按块的尺寸重建 token 布局。去噪预测按羽化权重融合，再进入下一步。音频是所有块共享的，预测取平均（用 0 噪声蒙版锁定即可保留原音频）。

## 实测（124 帧、9 个引导帧、两步）
| 尺寸 | 不分块 | 分块 | 对原片 PSNR |
|---|---|---|---|
| 1088 × 1920 | 99 s · 激活 6.4 GB | 2 × 2：77 s · 2.4 GB | 31.07 → 31.08 dB |
| 1440 × 2560 | 251 s | 2 × 2：152 s | 32.06 → 32.28 dB |

重叠区没有接缝。2K 时 2 × 2 的每块约等于 H3 原生尺寸，所以比整张大画布更贴原片。

## 自动分块
| 视频 | 自动网格 |
|---|---|
| 768 × 1344 及以下 | 1 块（关闭） |
| 1088 × 1920 | 2 |
| 1440 × 2560 | 2 × 2 |
| 2048 × 2048 | 2 × 3 |
| 2160 × 3840 | 5 × 2 |

## 提示
- 保持 ComfyUI 默认的 **动态显存**。用 `--disable-dynamic-vram` 或 `--lowvram` 时，权重每次模型调用都从内存读取，每个块都要再读一遍：仍然省显存，但更慢。
- 从噪声开始的文生视频，各块内容可能对不上——用于精修，不用于生成。
- 配合 **MiniMax H3 逐帧引导** 锚定原片的帧；引导会裁到每一块。
"""))

node("Arbor_H3AddGuideFrames", en=dict(
    desc="Anchor the listed frames of a video, each as its own single-frame guide, at the same frames of the MiniMax H3 target — the core 'Add Guide for MiniMax H3' once per frame, in one node.",
    inputs={"positive": "The positive conditioning (from MiniMax H3 Image to Video or Reference to Video).",
            "vae": "The H3 video VAE.",
            "latent": "The H3 AV latent you sample — for a refine, the encoded original.",
            "images": "The original video's frames (an image batch at the output size), or the video itself.",
            "frames": "Which frames to anchor, Batch Pick syntax: 0, 5, -1 (from the end), 3-5 (inclusive), 17::17 (every 17th from 17). Repeats are dropped."},
    outputs=["The conditioning with one guide per frame.", "How many frames were anchored."],
    doc="""## Why single frames
A guide is extra tokens in H3's attention: a whole-clip guide is every latent frame again (+100%), a single frame is one latent frame (124-frame video: +2.7% each). Nine evenly spaced frames — the default `0, 17::17, -1` (0, 17 … 119 and the last) — add about 24% and hold identity, costume and detail close to the original.

## Examples (124 frames)
| frames | anchored |
|---|---|
| `0, 17::17, -1` | 0, 17, 34 … 119, 123 (9) |
| `0, 34::34, -1` | 0, 34, 68, 102, 123 (5) |
| `0::8` | every 8th frame (16) |

## Tips
- Every frame is anchored at its own index, so connect frames at the output size and with the same frame count as the latent.
- Same result as chaining one core **Add Guide for MiniMax H3** per frame; guides already on the conditioning are kept.
- With **Tiled Refine for MiniMax H3**, each tile gets its part of every guide.
"""), zh=dict(
    name="MiniMax H3 逐帧引导",
    desc="把视频中列出的帧逐帧作为单帧引导，锚定到 MiniMax H3 目标视频的同一帧——相当于每帧一个核心「Add Guide for MiniMax H3」，合成一个节点。",
    inputs={"positive": ("正向条件", "正向条件（来自 MiniMax H3 Image to Video 或 Reference to Video）。"),
            "vae": ("VAE", "H3 视频 VAE。"),
            "latent": ("Latent", "要采样的 H3 AV latent——精修时就是原片编码。"),
            "images": ("图像", "原视频的帧（输出尺寸的图像批次），或直接接视频。"),
            "frames": ("帧", "要锚定哪些帧，语法同批次挑选：0, 5, -1（倒数）, 3-5（闭区间）, 17::17（从 17 起每 17 帧）。重复的会去掉。")},
    outputs=[("正向条件", "每帧一个引导的条件。"), ("数量", "锚定的帧数。")],
    doc="""## 为什么用单帧
引导是 H3 注意力里额外的 token：整段引导等于再加一遍所有潜帧（+100%），单帧只加一个潜帧（124 帧视频每个 +2.7%）。默认 `0, 17::17, -1`（0、17……119 和最后一帧）共 9 帧，约 +24%，就能把人物、服装和细节稳在原片上。

## 示例（124 帧）
| 帧 | 锚定 |
|---|---|
| `0, 17::17, -1` | 0, 17, 34 … 119, 123（9 帧） |
| `0, 34::34, -1` | 0, 34, 68, 102, 123（5 帧） |
| `0::8` | 每 8 帧一个（16 帧） |

## 提示
- 每帧锚定在自己的序号上，所以接入的帧要与 latent 尺寸相同、帧数一致。
- 与逐帧串联核心 **Add Guide for MiniMax H3** 结果相同；条件里已有的引导会保留。
- 配合 **MiniMax H3 分块精修** 时，每一块都得到每个引导对应的部分。
"""))

node("Arbor_H3RegionRedraw", en=dict(
    desc="Repair the small faces of a finished video, which is what its defaults are for. With other settings it repairs or replaces anything else in a mask, from a reference picture if you like. Other frames and pixels stay as they are.",
    inputs={"model": "The H3 model, after its LoRAs. Connect it before Tiled Refine: a crop needs no tiling.",
            "vae": "The H3 video VAE.",
            "clip": "The H3 text encoder.",
            "images": "The finished video's frames.",
            "masks": "What to redraw from the prompt, one mask per frame. Any mask will do. With core SAM3, use SAM3 Video Track, then SAM3 Track to Mask, and list the objects you want in its `object_indices`. Write the tracker's prompt with a count, like `face:16`: `:N` is how many to find, and plain `face` finds one. Subjects can stay in this mask: their own masks take them out.",
            "subject_masks": "One mask per subject. Each is redrawn alone, from the reference of the same number. Without a reference it is redrawn alone from the prompt, which also keeps two touching regions apart.",
            "subject_references": "The picture for the subject mask of the same number. The prompt calls it `<Picture 1>`, whichever subject it is.",
            "sampler": "From KSamplerSelect, as on a custom sampler. Tested with `lcm`.",
            "sigmas": "Redraw strength, as on a custom sampler. Repair with Manual Sigmas `0.7, 0.494118, 0`. To replace something, start near 1.",
            "denoise": "How much of `sigmas` to take, from its end, exactly as Split Sigmas Denoise does: the steps are counted, not the noise levels. 1 takes them all, as they come. 0.5 of `0.7, 0.494118, 0` takes `0.494118, 0`; 0.5 of a schedule from 1.0 takes its lower half. 0 leaves everything as it was.",
            "prompt": "What the regions should look like, subjects included, in H3's prompt format. The default repairs faces in any style; change it for anything else. With a subject reference, `<Picture 1>` is that subject's picture. See Writing the prompt.",
            "seed": "Noise seed. Each crop adds its own offset.",
            "refine_size": "Short edge a crop is enlarged to before it is redrawn. 512 repairs faces a third quicker than 768, the short edge of H3's native 1344 × 768, and as well. For replacing something, 768.",
            "context": "Crop size as a multiple of the region. Lower lets it fill the crop and enlarges it more; higher shows the model more of what surrounds it. 2 keeps faces closest to the original at the same speed as 4; below 2 the redrawn area can reach the crop's edge.",
            "max_size": "Regions in `masks` that never get smaller than this many pixels stay as they are. One that does, as in a push-in, is redrawn whole. Subjects are always redrawn.",
            "group_size": "How far across, in pixels of the video, a crop shared by nearby regions may be. They share one only when that is less work than a crop each, and each keeps the room around it and the enlargement it would have alone, so they are drawn as well; the shared canvas also stays within 1536 pixels, which can stop a group sooner. 0 gives every region a crop of its own.",
            "paste": "What is redrawn and pasted back: `mask` follows the mask's outline, `bbox` is a steady box around it, which leaves room for something of another shape.",
            "grow": "How far the redrawn area reaches past the mask, as a share of the region's size. For a face it needs to cover the hair.",
            "feather": "Softness of the pasted edge, as a share of the region's size."},
    outputs=["The video with the regions redrawn.", "Each crop before and after it was redrawn, at the canvas size, as a list with one clip per crop: one above the other when the crop is wider than tall, side by side when it is taller.", "One line per region: number, frames, position, size and what was done. Then one line per crop, in the order of the clips."],
    doc="""## What it is for
A face a few dozen pixels wide is more than the model can draw at 2K. More tiles, more steps or a sharper guide don't change that: it still has the same pixels. This node gives each masked region a canvas of its own.

## Repairing faces
It works on a 768p draft as well as on a 2K video. Connect SAM3 Track to Mask with `face:16` as the SAM3 prompt to `masks`, and Manual Sigmas `0.7, 0.494118, 0` with the lcm sampler. The other settings can stay as they are. If a face still looks unlike the original, lower `denoise` or use Manual Sigmas `0.5, 0.3, 0`: both repair less. Faces in the mask that are under `max_size` are redrawn, a lead's among them, so leave out of the mask with `object_indices` any face that must not change.

## Writing the prompt
The default is written the way MiniMax H3's prompt guide asks: `integrated_multimodal_description`, then `overall_soundscape` and `non_diegetic_music`, which are `N/A` because the sound is kept silent here. It names no style, only that the style stays as it is, so it serves live action, anime and 3D alike. Besides clear eyes, nose and mouth, it asks for small natural movement: breathing, blinking, glances, slight head turns. Without it, faces that are redrawn tend to go still.

To redraw something else from text, keep the three fields and change the description. Say what is there and what it does, not where the shot is:

```
integrated_multimodal_description: [Shot 1] The style, colors and lighting stay the same throughout the shot. Her hand holds a small worn paperback book with a deep red cover and gold lettering.

overall_soundscape: N/A

non_diegetic_music: N/A
```

With a subject picture, H3 works in its reference mode, which has fields of its own:

```
subject_definitions:
<Subject 1> is the person in <Picture 1>, with the same face, hair and clothing.

summary:
[reference generation] <Subject 1> takes the place of the person in this shot.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - face, hair and clothing are kept.

detailed_description:
The style, colors and lighting stay the same throughout the shot.
[Shot 1] <Subject 1> stands still in place of the person in this shot, with the same pose, framing and light.

overall_soundscape: N/A

non_diegetic_music: N/A
```

Write in English, as the guide does. Text that shows on screen goes in double quotes, as it reads.

## How it works
1. Every separate piece of a mask is a region. Each is followed from frame to frame by where it is and how large, within a shot, so something that is there for two seconds costs nothing afterwards. A region hidden for up to a second is picked up again.
2. Each region gets a crop that holds still, and moves only when the region would near its edge: the model takes a moving crop for a moving camera, and shakes what surrounds the region. It grows with the region in a push-in. The crop is enlarged to `refine_size` and redrawn without a guide. Only the area around the mask is redrawn, as with Set Latent Noise Mask: the rest of the crop stays and gives the model something to match. Regions that are on screen together and near each other share a crop when that is less work, each as large on its canvas as it would be alone. H3 samples one video at a time and every call costs about as much as a small crop does, so crops of one canvas are put one after another into one video, cut to cut, and sampled together: each starts on a clip of the VAE, which encodes clips apart, so none leaks into the next. In a crowd this is up to about twice as quick.
3. The result is shrunk and feathered back in.

Connect KSamplerSelect and Manual Sigmas as you would on a custom sampler.

## Repair or replace
The sigmas decide. Starting at 0.7 keeps what is there and draws it better; starting near 1 keeps only the surroundings and draws what the prompt or picture says. To replace something, use a model without a refiner LoRA: with one, the object is erased and the surroundings fill the hole. For an object, `paste` set to `bbox` with a larger `grow` leaves room for a different shape. 

## Replacing a whole person
Stay with `paste` on `mask`, with `grow` about 0.06 and `feather` about 0.03. A larger `grow` redraws more of the background, a smaller one cuts into the person: `bbox` repaints the background inside its box, and the box shows. Set `context` to about 2, so the model sees what surrounds the person. The first sigma decides how much of the shot survives: `0.99, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0` swaps the person fully and keeps a little of the pose; 1.0 takes the pose from the picture; 0.97 keeps the size and pose better, but the old hair and clothes can stay; below 0.92 the person stays.

Say what stays the same, not where: a prompt naming a place draws that place in every shot, close-ups included. "In place of the person in this shot, with the same pose, framing and light" works. Add "stands still" if the person should: otherwise the new one may walk out of the mask, and is cut off at its edge. Pick the one object: SAM3 Track to Mask's `object_indices` picks it, since a limit such as `:1` in the SAM3 prompt still tracks others. Reflections are objects of their own and stay as they were. Close-ups come out softer, as a crop larger than `refine_size` is drawn smaller than it was.

## Subjects with a picture
Give each subject a SAM3 Track to Mask of its own and connect it to Subject Mask 1, 2 and so on, with its picture on Subject Reference 1, 2 and so on. Describe the subjects in `prompt`: each picture is `<Picture 1>` to its own subject. The number is the only link: nothing has to work out what goes where. If a subject changes track between shots, list every track in `object_indices`, e.g. `2,7,13`.

## What is redrawn
Everything in the subject masks, and everything in `masks` apart from regions that are always larger than `max_size`. Leave out of the masks whatever should stay: what isn't redrawn can't change.

A mask is one layer, so it can't say where one thing ends and the next begins. Regions that touch in it are redrawn together in one crop.

What is redrawn is drawn anew, not recovered. It can change between seeds.
"""), zh=dict(
    name="MiniMax H3 局部重绘",
    desc="修复成片里的小脸，默认设置就是为此准备的。换一组设置也能修复或替换蒙版里的其他内容，可以使用参考图。其余帧和像素保持不变。",
    inputs={"model": ("模型", "H3 模型，接在 LoRA 之后。请接在分块精修之前：裁切后的画面不需要分块。"),
            "vae": ("VAE", "H3 视频 VAE。"),
            "clip": ("CLIP", "H3 文本编码器。"),
            "images": ("图像", "成片的帧。"),
            "masks": ("蒙版", "按提示词重画的部分，每帧一张蒙版，任何工具生成的都可以。用原生 SAM3 时，接 SAM3 Video Track，再接 SAM3 Track to Mask，在它的 `object_indices` 里写要修的对象。跟踪的提示词要写数量，比如 `face:16`：`:N` 是最多找几个，只写 `face` 只会找一个。主体可以留在这里，主体蒙版会把它们去掉。"),
            "subject_masks": ("主体蒙版", "每个主体一张蒙版。各自单独重画，并使用编号相同的参考图。不接参考图时按提示词单独重画，也可以用来分开连在一起的两块区域。"),
            "subject_references": ("主体参考图", "对应编号相同的主体蒙版。提示词里用 `<Picture 1>` 指代它，哪个主体都一样。"),
            "sampler": ("采样器", "接 KSamplerSelect，和自定义采样器一样。测试用的是 `lcm`。"),
            "sigmas": ("Sigmas", "重画强度，和自定义采样器一样。修复用 Manual Sigmas `0.7, 0.494118, 0`。要替换东西，起点接近 1。"),
            "denoise": ("降噪", "从 `sigmas` 末尾取多少步，和 Split Sigmas Denoise 完全一致：按步数算，不按噪声大小算。1 = 全部照用。对 `0.7, 0.494118, 0` 取 0.5 得到 `0.494118, 0`；对从 1.0 开始的调度取 0.5 得到后一半。0 = 什么都不改。"),
            "prompt": ("提示词", "重画的区域（包括主体）要画成什么样，按 H3 的提示词格式写。默认内容用来修复人脸，任何画风都适用，修其他东西请改掉。接了主体参考图时，`<Picture 1>` 指那个主体的图片。见“提示词怎么写”。"),
            "seed": ("种子", "噪声种子。每个裁切区域会加上自己的偏移。"),
            "refine_size": ("精修尺寸", "裁切区域重画前，短边放大到的像素数。修人脸时 512 比 768（H3 原生 1344 × 768 的短边）快三分之一，效果相当。替换东西时用 768。"),
            "context": ("参考范围", "裁切框是区域的多少倍。调小后区域占满框、放大更多；调大后模型能看到更多周围的画面。2 的速度和 4 一样，人脸最贴近原片；低于 2 时重画范围可能碰到裁切框边缘。"),
            "max_size": ("最大尺寸", "`蒙版` 里始终大于这个像素数的区域保持不变。有过小于它的时候（比如推镜），整段都重画。主体总会重画。"),
            "group_size": ("合并尺寸", "相邻区域共用的裁切框在原视频里最多多宽（像素）。只有合并后工作量更少时才合并，每块区域保留单独处理时的周围范围和放大倍数，所以画得一样好；共用画布也不会超过 1536 像素，这可能让一组更早停止合并。0 = 每块区域单独一个框。"),
            "paste": ("贴回方式", "重画和贴回的范围：`mask` 沿蒙版轮廓，`bbox` 用外面的稳定方框，能给形状不同的新东西留空间。"),
            "grow": ("外扩", "重画范围超出蒙版多少，按区域尺寸的比例计算。修人脸时需要盖住头发。"),
            "feather": ("羽化", "贴回边缘的柔和程度，按区域尺寸的比例计算。")},
    outputs=[("图像", "局部重绘后的视频。"), ("对比片段", "每个裁切框重画前后的对比，画布尺寸，列表形式，一个裁切框一段：横的框上下排列，竖的框左右排列。"), ("报告", "每块区域一行：编号、帧范围、位置、尺寸和处理结果；之后每个裁切框一行，顺序和片段一致。")],
    doc="""## 用途
几十像素宽的脸，模型在 2K 画面里画不出来。多分块、加步数、锐化引导都改变不了这一点：它占的像素还是那么多。这个节点让蒙版里的每块区域都有自己的画布。

## 修复人脸
768p 草稿和 2K 成片都能用。把 SAM3 提示词写成 `face:16`，SAM3 Track to Mask 接到 `蒙版`，Manual Sigmas 用 `0.7, 0.494118, 0`，采样器用 lcm。其余设置保持默认即可。如果脸和原片还是差得多，调小 `降噪`，或者把 Manual Sigmas 改用 `0.5, 0.3, 0`：两者都会修复得更少。蒙版里小于 `最大尺寸` 的脸都会重画，主角也不例外，不能变的脸请用 `object_indices` 排除在蒙版外。

## 提示词怎么写
默认提示词按 MiniMax H3 官方提示词指南的格式写：先是 `integrated_multimodal_description`，然后是 `overall_soundscape` 和 `non_diegetic_music`。这里声音保持静音，所以后两项写 `N/A`。它不指定画风，只要求画风保持不变，所以写实、动画、3D 都能直接用。除了清楚的眼睛、鼻子和嘴，它还描述了细小的自然动作：呼吸、眨眼、看向别处、轻微转头。不写这些，重画的脸容易僵住。

按文字重画别的东西时，保留这三项，只改描述。写那里有什么、在做什么，不要写镜头在什么地方：

```
integrated_multimodal_description: [Shot 1] The style, colors and lighting stay the same throughout the shot. Her hand holds a small worn paperback book with a deep red cover and gold lettering.

overall_soundscape: N/A

non_diegetic_music: N/A
```

接了主体参考图时，H3 用的是参考模式，有它自己的几项：

```
subject_definitions:
<Subject 1> is the person in <Picture 1>, with the same face, hair and clothing.

summary:
[reference generation] <Subject 1> takes the place of the person in this shot.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - face, hair and clothing are kept.

detailed_description:
The style, colors and lighting stay the same throughout the shot.
[Shot 1] <Subject 1> stands still in place of the person in this shot, with the same pose, framing and light.

overall_soundscape: N/A

non_diegetic_music: N/A
```

和指南一样用英文写。画面里出现的文字放在双引号里，照原样写。

## 原理
1. 蒙版里每一块独立的区域单独处理。在同一镜头内按位置和大小逐帧跟随，所以只出现两秒的东西，后面的画面不受影响。被遮挡不超过一秒，会重新接上。
2. 每块区域一个裁切框，框保持不动，区域快到框边时才移动：模型会把移动的框当成镜头在动，周围画面就会抖。推镜时框跟着变大。裁切后放大到 `精修尺寸`，不带引导重画。和 Set Latent Noise Mask 一样，只重画蒙版附近的区域，框里其余部分保持不变，给模型作参照。同一时间挨在一起的区域，在工作量更少时共用一个框，每块区域在画布上和单独处理时一样大。H3 一次只能采样一段视频，每次调用的固定开销和一个小框的采样差不多，所以同尺寸的框会按时间首尾相连，拼成一段视频一起采样：每段都从 VAE 的一个编码块开头，各块单独编码，所以不会互相串。人多时最多能快到约两倍。
3. 结果缩回原尺寸，羽化贴回。

KSamplerSelect 和 Manual Sigmas 的接法与自定义采样器相同。

## 修复还是替换
由 sigmas 决定。从 0.7 开始会保留原来的内容，画得更好；从接近 1 开始只保留周围环境，按提示词或图片重画。替换时请用不带精修 LoRA 的模型：带了之后物体只会被抹掉，由周围画面填上。替换物体时，`贴回方式` 用 `bbox` 并调大 `外扩`，能给形状不同的新东西留空间。

## 替换整个人
`贴回方式` 用 `mask`，`外扩` 约 0.06，`羽化` 约 0.03。`外扩` 调大会重画更多背景，调小会切到人物：`bbox` 会连框里的背景一起重画，方框边缘看得出来。`参考范围` 设为 2 左右，让模型看到人物周围的画面。第一个 sigma 决定原镜头留下多少：`0.99, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0` 能完全换掉人物，并保留一点姿势；1.0 的姿势来自参考图；0.97 更能保住大小和姿势，但原来的头发和衣服可能留下；低于 0.92 人物基本不变。

提示词写什么保持不变，不要写地点：写了地点之后，每个镜头（包括特写）都会画成那个地点。"in place of the person in this shot, with the same pose, framing and light" 这样的写法有效。人物不该走动时加上 "stands still"：否则新人物可能走出蒙版，在边缘被切掉。只接要替换的那一个对象：用 SAM3 Track to Mask 的 `object_indices` 选定，因为 SAM3 提示词里的 `:1` 这类限制仍会跟踪到别的对象。倒影是单独的对象，不会跟着改变。特写会比较软，因为比 `精修尺寸` 大的裁切框是缩小后重画的。

## 带参考图的主体
每个主体接一个单独的 SAM3 Track to Mask，连到主体蒙版1、2……，图片连到主体参考图1、2……。在 `提示词` 里描述主体：每张图片对它自己的主体来说都是 `<Picture 1>`。编号就是唯一的对应关系，不用判断什么对应什么。主体跨镜头换了跟踪编号时，在 `object_indices` 里全部写上，例如 `2,7,13`。

## 哪些部分会被重画
主体蒙版里的全部，以及 `蒙版` 里除了始终大于 `最大尺寸` 的区域。不想动的部分请不要放进蒙版：没被重画就不会变。

蒙版只有一层，分不清两个东西的边界。在蒙版里连在一起的区域会放在同一个框里重画。

重画的内容是新画的，不是还原的。不同种子下可能不一样。
"""))

