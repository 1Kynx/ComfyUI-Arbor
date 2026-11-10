# Tiled Refine for MiniMax H3

Lower the memory of a MiniMax H3 step by sampling the video in overlapping spatial tiles, blended at every step. Every tile keeps all frames, so the video is never split in time; guide frames, denoise masks and a reference video of the same frame are cropped to each tile.

## Inputs

- **model** · *MODEL*  
  A MiniMax H3 model, after its LoRAs and attention patches (Chunk FeedForward, Block Sparse Attention).
- **tiles_x** · *INT*  
  Tiles across. 0 = auto: the fewest tiles that keep each one about H3's native 768 × 1344 size. 1 with tiles_y 1 = off.
- **tiles_y** · *INT*  
  Tiles down. 0 = auto.
- **overlap** · *INT*  
  Pixels that neighbouring tiles share. Their predictions are blended there, so the joins don't show. 128 is plenty; 0 leaves visible seams. 64 was a tenth quicker on a 2K refine and still seamless, half a dB further from an untiled run.
- **guide_mask** · *MASK, optional*  
  Where the guide counts, at any size, one mask per frame or one for all. The guide is a second copy of the video's tokens; only those inside the mask (grown by a token) go in. The masked area follows the guide; the rest keeps only what the start latent holds, so at high start noise it is redrawn (new faces, new detail) and at low noise it stays close. Fewer tokens run faster: with a third of the frame masked a step takes about half as long. For more margin than the one guide token (32 px) always kept around it, grow the mask first with Grow Mask. Not connected: the whole guide.

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

## Reference pictures and videos
From **MiniMax H3 Reference to Video**, reference pictures and videos have a canvas of their own and go to every tile whole. A reference video that shows the same frame as the video, as long and the same shape within 3%, is cut to each tile instead: that is how the IC refiner (Regenerate-2K-IC) and edits give their source, the draft as `<Video 1>`. Each tile then gets the matching part of the draft, not the whole of it. On a 2K IC refine of 124 frames in 2 × 2 tiles this took 565 s instead of 945 s, as sharp (10.74 against 10.83) and closer to the draft. A motion, camera or style reference of another shape or length still goes in whole, and costs a whole video's tokens in every tile: shrink or shorten it if it is slow.

Two more things follow that reference into a tile:

- **What the text says of it.** The text encoder is shown the reference video as well, two frames a second, and its picture tokens sit among the prompt's own: 6000 of a tile's 59000 tokens for a 5 s draft, more for a longer one, and the same 6000 in every tile. A tile keeps the ones over its own part, about half the text in a 2 × 2 grid. The prompt itself stays whole.
- **Where it lies.** The draft's grid is coarser than the video's and is cut out to whole patches, so the piece a tile gets reaches up to 5% past the tile. It is given the positions of where it really lies; H3 would otherwise read it as the tile exactly, a little off.

The same 2K refine, three steps: sampling 355 s instead of 423 s, as sharp, as close to the draft (27.7 against 27.5 dB) and to an untiled run, and no seams.

With core **Model Sparse Attention**, leave `sink_conditioning` on. It keeps the text and the references exact for every token, and that is most of the attention's work in a refine. Letting the reference be attended sparsely like the video was a tenth quicker in the same test, and came out 1 dB further from the draft.
