"""Docs for the Sampling nodes (see node_info.py for the format)."""

from node_info import node

node("Arbor_H3TiledRefine", en=dict(
    desc="Lower the memory of a MiniMax H3 step by sampling the video in overlapping spatial tiles, blended at every step. Every tile keeps all frames, so the video is never split in time; guide frames and denoise masks are cropped to each tile.",
    inputs={"model": "A MiniMax H3 model, after its LoRAs and attention patches (Chunk FeedForward, Block Sparse Attention).",
            "tiles_x": "Tiles across. 0 = auto: the fewest tiles that keep each one about H3's native 768 × 1344 size. 1 with tiles_y 1 = off.",
            "tiles_y": "Tiles down. 0 = auto.",
            "overlap": "Pixels that neighbouring tiles share. Their predictions are blended there, so the joins don't show. 128 is plenty; 0 leaves visible seams."},
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
            "overlap": ("重叠", "相邻块共享的像素，在这里融合预测，接缝看不出来。128 足够；0 会有明显接缝。")},
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

node("Arbor_H3FaceRefine", en=dict(
    desc="Redraw the small faces in a mask. Each face is cropped, enlarged, redrawn at low noise and feathered back. Other frames and pixels stay as they are.",
    inputs={"model": "The H3 model, after its LoRAs. Connect it before Tiled Refine: a crop needs no tiling.",
            "vae": "The H3 video VAE.",
            "clip": "The H3 text encoder.",
            "images": "The finished video's frames.",
            "masks": "The faces to redraw, one mask per frame. Any mask will do. With core SAM3, use SAM3 Video Track, then SAM3 Track to Mask, and list the objects you want in its `object_indices`. Write the tracker's prompt as `face:16`: `:N` is how many to find, and plain `face` finds one. Leads can stay in this mask: their own masks take them out.",
            "lead_masks": "One mask per lead. Each lead is redrawn alone, from the reference of the same number. Without a reference they are redrawn alone from the prompt, which also keeps two touching faces apart.",
            "references": "The lead's picture, for the lead mask of the same number.",
            "sampler": "From KSamplerSelect, as on a custom sampler. Tested with `lcm`.",
            "sigmas": "Redraw strength, as on a custom sampler. A lower start keeps more of the original face. Tested with Manual Sigmas `0.7, 0.494118, 0`.",
            "prompt": "One description used for every redrawn face.",
            "seed": "Noise seed. Each crop adds its own offset.",
            "refine_size": "Short edge a crop is enlarged to before it is redrawn. 768 is the short edge of H3's native 1344 × 768.",
            "context": "Crop size as a multiple of the face. Lower lets the face fill the crop and enlarges it more; higher shows the model more of what surrounds it. It does not change which faces share a crop.",
            "max_face": "Faces that never get smaller than this many pixels stay as they are. A face that does, as in a push-in, is redrawn whole.",
            "group_size": "0 gives every face its own crop, which draws best. Above 0, nearby faces share one crop as long as its short edge is no more than this many pixels, which is quicker in a crowd. 288 is a good limit.",
            "paste": "What is pasted back: `mask` follows the mask's outline of the face, `bbox` is a steady box around it.",
            "grow": "How far the pasted area reaches past the face, as a share of the face's size. It needs to cover the hair.",
            "feather": "Softness of the pasted edge, as a share of the face's size."},
    outputs=["The video with the faces redrawn.", "Each crop as it was redrawn, before it is shrunk back, one after another. Crops of other shapes sit centred on black. Connect it to a video node to see what the model drew. The report says which frames are which crop.", "One line per face: number, frames, position, size and what was done. Then one line per crop."],
    doc="""## What it is for
A face a few dozen pixels wide is more than the model can draw at 2K. More tiles, more steps or a sharper guide don't change that: the face still has the same pixels. This node gives each small face a canvas of its own.

## How it works
1. Every separate piece of the mask is a face. Each is followed from frame to frame by where it is and how large, within a shot, so a passer-by in the first two seconds costs nothing afterwards. A face hidden for up to a second is picked up again.
2. Each face gets a crop that follows it, growing with it in a push-in, is enlarged to `refine_size` and redrawn without a guide. Only the area around the face is redrawn, as with Set Latent Noise Mask: the rest of the crop stays and gives the model something to match. With `group_size` above 0, faces that sit together at the same time share a crop.
3. The result is shrunk, matched to the shot's colour and feathered in over the head.

Connect KSamplerSelect and Manual Sigmas as you would on a custom sampler.

## Leads with a picture
Give each lead a SAM3 Track to Mask of their own and connect it to Lead Mask 1, 2 and so on, with their picture on Reference 1, 2 and so on. The number is the only link: nothing has to work out who is who. If a lead changes track between shots, list every track in `object_indices`, e.g. `2,7,13`.

A lead is redrawn however large they are, and the result moves toward the picture, not toward the rest of the video.

## Which faces are redrawn
Everything in `masks`, apart from faces that are always larger than `max_face`. So leave out of the mask any face that should stay: a face that isn't redrawn can't change.

A mask is one layer, so it can't say where one face ends and the next begins. Faces that touch in it are redrawn together in one crop, and draw a little worse than a face alone.

Faces are redrawn, not recovered. They can change between seeds.
"""), zh=dict(
    name="MiniMax H3 小脸修复",
    desc="重画蒙版里的小脸。把每张脸裁出来，放大后低噪声重画，再羽化贴回。其余帧和像素保持不变。",
    inputs={"model": ("模型", "H3 模型，接在 LoRA 之后。请接在分块精修之前：裁切后的画面不需要分块。"),
            "vae": ("VAE", "H3 视频 VAE。"),
            "clip": ("CLIP", "H3 文本编码器。"),
            "images": ("图像", "成片的帧。"),
            "masks": ("蒙版", "要重画的脸，每帧一张蒙版，任何工具生成的都可以。用原生 SAM3 时，接 SAM3 Video Track，再接 SAM3 Track to Mask，在它的 `object_indices` 里写要修的对象。跟踪的提示词写 `face:16`：`:N` 是最多找几个，只写 `face` 只会找一个。主角可以留在这里，主角蒙版会把他们去掉。"),
            "lead_masks": ("主角蒙版", "每个主角一张蒙版。各自单独重画，并使用编号相同的参考图。不接参考图时按提示词单独重画，也可以用来分开连在一起的两张脸。"),
            "references": ("参考图", "主角的图片，对应编号相同的主角蒙版。"),
            "sampler": ("采样器", "接 KSamplerSelect，和自定义采样器一样。测试用的是 `lcm`。"),
            "sigmas": ("Sigmas", "重画强度，和自定义采样器一样。起点越低越保留原来的脸。测试用的是 Manual Sigmas `0.7, 0.494118, 0`。"),
            "prompt": ("提示词", "所有被重画的脸共用的一句描述。"),
            "seed": ("种子", "噪声种子。每个裁切区域会加上自己的偏移。"),
            "refine_size": ("精修尺寸", "裁切区域重画前，短边放大到的像素数。768 就是 H3 原生 1344 × 768 的短边。"),
            "context": ("参考范围", "裁切框是人脸的多少倍。调小后脸占满框、放大更多；调大后模型能看到更多周围的画面。不影响哪些脸共用一个框。"),
            "max_face": ("最大人脸", "始终大于这个像素数的脸保持不变。有过小于它的时候（比如推镜），整段都重画。"),
            "group_size": ("合并尺寸", "0 = 每张脸单独一个框，画得最好。大于 0 时，相邻的脸共用一个框，框的短边不超过这个像素数，人多时更快。可以用 288。"),
            "paste": ("贴回方式", "贴回的范围：`mask` 沿蒙版的人脸轮廓，`bbox` 用人脸外的稳定方框。"),
            "grow": ("外扩", "贴回范围超出人脸多少，按人脸尺寸的比例计算。需要盖住头发。"),
            "feather": ("羽化", "贴回边缘的柔和程度，按人脸尺寸的比例计算。")},
    outputs=[("图像", "小脸重画后的视频。"), ("小脸片段", "每个裁切区域重画后、缩回之前的画面，首尾相接。形状不同的片段居中放在黑底上。接到视频节点可以看模型实际画了什么，哪段属于哪个裁切框见报告。"), ("报告", "每张脸一行：编号、帧范围、位置、尺寸和处理结果；之后每个裁切框一行。")],
    doc="""## 用途
几十像素宽的脸，模型在 2K 画面里画不出来。多分块、加步数、锐化引导都改变不了这一点：脸占的像素还是那么多。这个节点让每张小脸都有自己的画布。

## 原理
1. 蒙版里每一块独立的区域算一张脸。在同一镜头内按位置和大小逐帧跟随，所以路人只在前两秒出现时，后面的画面不受影响。脸被遮挡不超过一秒，会重新接上。
2. 每张脸一个裁切框，框跟随人脸移动，推镜时也跟着变大，放大到 `精修尺寸`，不带引导重画。和 Set Latent Noise Mask 一样，只重画人脸附近的区域，框里其余部分保持不变，给模型作参照。`合并尺寸` 大于 0 时，同一时间挨在一起的脸共用一个框。
3. 结果缩回原尺寸，匹配镜头颜色，羽化贴回头部。

KSamplerSelect 和 Manual Sigmas 的接法与自定义采样器相同。

## 用参考图修复主角
每个主角接一个单独的 SAM3 Track to Mask，连到主角蒙版1、2……，图片连到参考图1、2……。编号就是唯一的对应关系，不用判断谁是谁。主角跨镜头换了跟踪编号时，在 `object_indices` 里全部写上，例如 `2,7,13`。

主角不管多大都会重画，结果会向参考图靠近，而不是向视频其余部分靠近。

## 哪些脸会被重画
`蒙版` 里的都会，除了始终大于 `最大人脸` 的。不想动的脸请不要放进蒙版：没被重画的脸就不会变。

蒙版只有一层，分不清两张脸的边界。在蒙版里连在一起的脸会放在同一个框里重画，效果比单独一张脸略差。

脸是重画的，不是还原的。不同种子下长相可能不一样。
"""))
