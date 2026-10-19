# Smart Resize

Resize by longest / shortest side, megapixels, a box or a scale factor, snapping both sides to a multiple (8 / 16 / 64 for latent-friendly sizes).

## Inputs

- **image** · *IMAGE*  
  Image or batch to resize.
- **mode** · *COMBO*  
  How the target size is chosen. Only the fields for the chosen mode are shown.
  - **mode.size** `size` · *INT*  
    Target length of the longest / shortest side, in pixels.
  - **mode.megapixels** `megapixels` · *FLOAT*  
    Target area in megapixels (1.0 ≈ 1024 × 1024); aspect ratio is kept.
  - **mode.width** `width` · *INT*  
    Target box width.
  - **mode.height** `height` · *INT*  
    Target box height.
  - **mode.factor** `factor` · *FLOAT*  
    Scale factor (2.0 = twice as large).
- **multiple_of** · *COMBO (1 · 8 · 16 · 32 · 64)*  
  Round both sides to a multiple of this — use 8 / 16 / 64 for diffusion models.
- **method** · *COMBO (lanczos · bicubic · bilinear · area · nearest-exact)*  
  Resampling filter. lanczos is sharpest; area is best for strong downscaling.
- **allow_upscale** · *BOOLEAN*  
  Off: never make the image larger than it is.
- **mask** · *MASK, optional*  
  Optional mask, resized (and cropped) exactly like the image.

## Outputs

- **image** · *IMAGE*  
  Resized image.
- **mask** · *MASK*  
  Resized mask (all ones when no mask was given).
- **width** · *INT*  
  Final width.
- **height** · *INT*  
  Final height.

## Modes
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
