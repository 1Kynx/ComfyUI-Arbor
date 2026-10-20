# Compare Viewer

Compare images, videos and audio of any size: flip through them with the slider, or wipe A against B. Videos and audio play in sync and keep their place when you switch, so an A/B comparison stays on the same moment.

## Inputs

- **images** · *IMAGE / VIDEO / AUDIO / TREE × N, optional, grows as you connect*  
  What to compare — images, videos or audio: a single value, a batch, a list or a tree. Every input grows a new slot; image batches give one slide per frame, audio batches one per clip (max 64 slides). Items of a named branch (a Load Folder folder, a storyboard scene) are labelled with its name.

## How to use
- Connect one or more inputs: pictures, videos (e.g. Load Folder with kind *videos*, Create Video) or audio. They can be mixed.
- **Flip** shows one slide at a time — drag the slider under the stage or press **← / →**.
- **Wipe** puts **A** (picked from the chip in the toolbar) against **B** (the slider). Two pictures or videos are split by a divider that follows the mouse; when either is audio they are stacked, A on top, and you hear the half under the mouse.
- Videos and audio share one **play / seek / loop** bar (Space plays and pauses). Switching slides keeps the current time — flip back and forth to hear or see the same moment in each version. Shorter clips hold their last frame.
- Audio shows its waveform; click it to jump.
- **Real** keeps relative sizes (a 512 px image looks half as big as a 1024 px one); **Fit** scales every picture to fill the stage.
- Double-click the stage (or the ↗ button) to open the current file in a new tab.

## Tips
- Feed it a native list (e.g. the per-item results of an XY run): it receives the whole list at once instead of running per item.
- Videos already in ComfyUI's output / input folder play straight from there; others are written to the temp folder first.
- In Wipe you hear one side at a time: the one that shows more of the stage (side by side) or the half under the mouse (stacked). The speaker button mutes everything.
- The chosen mode, scale and loop are saved with the workflow.
