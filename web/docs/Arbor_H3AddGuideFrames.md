# Add Guide Frames for MiniMax H3

Anchor the listed frames of a video, each as its own single-frame guide, at the same frames of the MiniMax H3 target — the core 'Add Guide for MiniMax H3' once per frame, in one node.

## Inputs

- **positive** · *CONDITIONING*  
  The positive conditioning (from MiniMax H3 Image to Video or Reference to Video).
- **vae** · *VAE*  
  The H3 video VAE.
- **latent** · *LATENT*  
  The H3 AV latent you sample — for a refine, the encoded original.
- **images** · *IMAGE / VIDEO*  
  The original video's frames (an image batch at the output size), or the video itself.
- **frames** · *STRING*  
  Which frames to anchor, Batch Pick syntax: 0, 5, -1 (from the end), 3-5 (inclusive), 17::17 (every 17th from 17). Repeats are dropped.

## Outputs

- **positive** · *CONDITIONING*  
  The conditioning with one guide per frame.
- **count** · *INT*  
  How many frames were anchored.

## Why single frames
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
