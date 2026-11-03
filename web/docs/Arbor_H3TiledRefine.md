# Tiled Refine for MiniMax H3

Lower the memory of a MiniMax H3 step by sampling the video in overlapping spatial tiles, blended at every step. Every tile keeps all frames, so the video is never split in time; guide frames and denoise masks are cropped to each tile.

## Inputs

- **model** · *MODEL*  
  A MiniMax H3 model, after its LoRAs and attention patches (Chunk FeedForward, Block Sparse Attention).
- **tiles_x** · *INT*  
  Tiles across. 0 = auto: the fewest tiles that keep each one about H3's native 768 × 1344 size. 1 with tiles_y 1 = off.
- **tiles_y** · *INT*  
  Tiles down. 0 = auto.
- **overlap** · *INT*  
  Pixels that neighbouring tiles share. Their predictions are blended there, so the joins don't show. 128 is plenty; 0 leaves visible seams.

## Outputs

- **model** · *MODEL*  
  The model, patched to sample in tiles. Connect it to the guider (BasicGuider).

## What it is for
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
