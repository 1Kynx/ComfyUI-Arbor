# Image Slider

Compare any number of images of any size: drag the slider to flip through them, or switch to Wipe for a before / after split.

## Inputs

- **images** · *IMAGE × N, optional, grows as you connect*  
  Images to compare. Every input grows a new slot; batches are split into one slide per frame (max 64 slides).

## How to use
- Connect one or more images. A batch counts as several slides.
- **Flip** shows one image at a time — drag the slider under the stage or press **← / →**.
- **Wipe** splits **A** (picked from the chip in the toolbar) against **B** (the slider); the divider follows the mouse.
- **Real** keeps relative sizes (a 512 px image looks half as big as a 1024 px one); **Fit** scales every image to fill the stage.
- Double-click the stage (or the ↗ button) to open the full-size image in a new tab.

## Tips
- Feed it a native list (e.g. the per-item results of an XY run): it receives the whole list at once instead of running per item.
- The chosen mode and scale are saved with the workflow.
