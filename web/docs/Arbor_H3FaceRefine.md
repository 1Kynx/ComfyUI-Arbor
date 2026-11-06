# Small Face Refine for MiniMax H3

Redraw the small faces in a mask. Each face is cropped, enlarged, redrawn at low noise and feathered back. Other frames and pixels stay as they are.

## Inputs

- **model** · *MODEL*  
  The H3 model, after its LoRAs. Connect it before Tiled Refine: a crop needs no tiling.
- **vae** · *VAE*  
  The H3 video VAE.
- **clip** · *CLIP*  
  The H3 text encoder.
- **images** · *IMAGE*  
  The finished video's frames.
- **masks** · *MASK, optional*  
  The faces to redraw, one mask per frame. Any mask will do. With core SAM3, use SAM3 Video Track, then SAM3 Track to Mask, and list the objects you want in its `object_indices`. Write the tracker's prompt as `face:16`: `:N` is how many to find, and plain `face` finds one. Leads can stay in this mask: their own masks take them out.
- **lead_masks** · *MASK × N, optional, grows as you connect*  
  One mask per lead. Each lead is redrawn alone, from the reference of the same number. Without a reference they are redrawn alone from the prompt, which also keeps two touching faces apart.
- **references** · *IMAGE × N, optional, grows as you connect*  
  The lead's picture, for the lead mask of the same number.
- **sampler** · *SAMPLER*  
  From KSamplerSelect, as on a custom sampler. Tested with `lcm`.
- **sigmas** · *SIGMAS*  
  Redraw strength, as on a custom sampler. A lower start keeps more of the original face. Tested with Manual Sigmas `0.7, 0.494118, 0`.
- **prompt** · *STRING*  
  One description used for every redrawn face.
- **seed** · *INT*  
  Noise seed. Each crop adds its own offset.
- **refine_size** · *INT*  
  Short edge a crop is enlarged to before it is redrawn. 768 is the short edge of H3's native 1344 × 768.
- **context** · *FLOAT*  
  Crop size as a multiple of the face. Lower lets the face fill the crop and enlarges it more; higher shows the model more of what surrounds it. It does not change which faces share a crop.
- **max_face** · *INT*  
  Faces that never get smaller than this many pixels stay as they are. A face that does, as in a push-in, is redrawn whole.
- **group_size** · *INT*  
  0 gives every face its own crop, which draws best. Above 0, nearby faces share one crop as long as its short edge is no more than this many pixels, which is quicker in a crowd. 288 is a good limit.
- **paste** · *COMBO (mask · bbox)*  
  What is pasted back: `mask` follows the mask's outline of the face, `bbox` is a steady box around it.
- **grow** · *FLOAT*  
  How far the pasted area reaches past the face, as a share of the face's size. It needs to cover the hair.
- **feather** · *FLOAT*  
  Softness of the pasted edge, as a share of the face's size.

## Outputs

- **images** · *IMAGE*  
  The video with the faces redrawn.
- **face_clips** · *IMAGE*  
  Each crop as it was redrawn, before it is shrunk back, one after another. Crops of other shapes sit centred on black. Connect it to a video node to see what the model drew. The report says which frames are which crop.
- **report** · *STRING*  
  One line per face: number, frames, position, size and what was done. Then one line per crop.

## What it is for
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
