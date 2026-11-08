# Region Redraw for MiniMax H3

Repair the small faces of a finished video, which is what its defaults are for. With other settings it repairs or replaces anything else in a mask, from a reference picture if you like. Other frames and pixels stay as they are.

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
  What to redraw from the prompt, one mask per frame. Any mask will do. With core SAM3, use SAM3 Video Track, then SAM3 Track to Mask, and list the objects you want in its `object_indices`. Write the tracker's prompt with a count, like `face:16`: `:N` is how many to find, and plain `face` finds one. Subjects can stay in this mask: their own masks take them out.
- **subject_masks** · *MASK × N, optional, grows as you connect*  
  One mask per subject. Each is redrawn alone, from the reference of the same number. Without a reference it is redrawn alone from the prompt, which also keeps two touching regions apart.
- **subject_references** · *IMAGE × N, optional, grows as you connect*  
  The picture for the subject mask of the same number. The prompt calls it `<Picture 1>`, whichever subject it is.
- **sampler** · *SAMPLER*  
  From KSamplerSelect, as on a custom sampler. Tested with `lcm`.
- **sigmas** · *SIGMAS*  
  Redraw strength, as on a custom sampler. Repair with Manual Sigmas `0.7, 0.494118, 0`. To replace something, start near 1.
- **denoise** · *FLOAT*  
  How much of `sigmas` to take, from its end, exactly as Split Sigmas Denoise does: the steps are counted, not the noise levels. 1 takes them all, as they come. 0.5 of `0.7, 0.494118, 0` takes `0.494118, 0`; 0.5 of a schedule from 1.0 takes its lower half. 0 leaves everything as it was.
- **prompt** · *STRING*  
  What the regions should look like, subjects included, in H3's prompt format. The default repairs faces in any style; change it for anything else. With a subject reference, `<Picture 1>` is that subject's picture. See Writing the prompt.
- **seed** · *INT*  
  Noise seed. Each crop adds its own offset.
- **refine_size** · *INT*  
  Short edge a crop is enlarged to before it is redrawn. 512 repairs faces a third quicker than 768, the short edge of H3's native 1344 × 768, and as well. For replacing something, 768.
- **context** · *FLOAT*  
  Crop size as a multiple of the region. Lower lets it fill the crop and enlarges it more; higher shows the model more of what surrounds it. 2 keeps faces closest to the original at the same speed as 4; below 2 the redrawn area can reach the crop's edge.
- **max_size** · *INT*  
  Regions in `masks` that never get smaller than this many pixels stay as they are. One that does, as in a push-in, is redrawn whole. Subjects are always redrawn.
- **group_size** · *INT*  
  How far across, in pixels of the video, a crop shared by nearby regions may be. They share one only when that is less work than a crop each, and each keeps the room around it and the enlargement it would have alone, so they are drawn as well; the shared canvas also stays within 1536 pixels, which can stop a group sooner. 0 gives every region a crop of its own.
- **paste** · *COMBO (mask · bbox)*  
  What is redrawn and pasted back: `mask` follows the mask's outline, `bbox` is a steady box around it, which leaves room for something of another shape.
- **grow** · *FLOAT*  
  How far the redrawn area reaches past the mask, as a share of the region's size. For a face at 0.7 it needs to cover the hair. Starting near 1, set it to 0: what lies past the mask is what holds the pose.
- **feather** · *FLOAT*  
  Softness of the pasted edge, as a share of the region's size.

## Outputs

- **images** · *IMAGE*  
  The video with the regions redrawn.
- **compare** · *IMAGE ×N*  
  Each crop before and after it was redrawn, at the canvas size, as a list with one clip per crop: one above the other when the crop is wider than tall, side by side when it is taller.
- **report** · *STRING*  
  One line per region: number, frames, position, size and what was done. Then one line per crop, in the order of the clips.

## What it is for
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

Starting near 1, the model keeps a pose only where it can see one. What lies past the mask is all it has to go on, so set `grow` to 0, `feather` to about 0.03 and `context` to 1.5 or 2. With the face-repair settings, `grow` 0.35, a head looking down in profile came back facing the camera. With `grow` 0 it kept its angle and followed the original movement, and was a third quicker. Even 0.06 lost much of that, and more `feather` or a `context` of 1.2 did too.

Name the style in the prompt as well, *live-action* for instance: from 1 the model can't see the style inside the mask, and the default, which only asks for the style to stay as it is, let a live-action face turn into anime. From 0.7 the style is still there to see.

## Replacing a whole person
Stay with `paste` on `mask`, with `grow` about 0.06 and `feather` about 0.03. A larger `grow` redraws more of the background, a smaller one cuts into the person: `bbox` repaints the background inside its box, and the box shows. Set `context` to about 2, so the model sees what surrounds the person. The first sigma decides how much of the shot survives: `0.99, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0` swaps the person fully and keeps a little of the pose; 1.0 takes the pose from the picture; 0.97 keeps the size and pose better, but the old hair and clothes can stay; below 0.92 the person stays.

Say what stays the same, not where: a prompt naming a place draws that place in every shot, close-ups included. "In place of the person in this shot, with the same pose, framing and light" works. Add "stands still" if the person should: otherwise the new one may walk out of the mask, and is cut off at its edge. Pick the one object: SAM3 Track to Mask's `object_indices` picks it, since a limit such as `:1` in the SAM3 prompt still tracks others. Reflections are objects of their own and stay as they were. Close-ups come out softer, as a crop larger than `refine_size` is drawn smaller than it was.

## Subjects with a picture
Give each subject a SAM3 Track to Mask of its own and connect it to Subject Mask 1, 2 and so on, with its picture on Subject Reference 1, 2 and so on. Describe the subjects in `prompt`: each picture is `<Picture 1>` to its own subject. The number is the only link: nothing has to work out what goes where. If a subject changes track between shots, list every track in `object_indices`, e.g. `2,7,13`.

## What is redrawn
Everything in the subject masks, and everything in `masks` apart from regions that are always larger than `max_size`. Leave out of the masks whatever should stay: what isn't redrawn can't change.

A mask is one layer, so it can't say where one thing ends and the next begins. Regions that touch in it are redrawn together in one crop.

What is redrawn is drawn anew, not recovered. It can change between seeds.
