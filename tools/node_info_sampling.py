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
