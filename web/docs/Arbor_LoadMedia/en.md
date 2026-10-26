# Load Media

Pick pictures, videos and audio from anywhere on disk and group them into named branches — several Load Image nodes in one, using the system's own file dialog, with thumbnails. Files are used where they are; nothing is copied.

## Inputs

- **files** · *STRING*  
  The list (kept as text): '# name' starts a named group, an empty line a new group, every other line is a file — an absolute path, output/… (ComfyUI's output folder), arbor:… (Arbor's sample media) or relative to the input folder. Edit it in the node's Text view, or fill it with Add….

## Outputs

- **files** · *TREE*  
  Everything, one branch per group, named after it — the data tree: Cross Reference, Tree Branch, the Compare Viewer, Save by Path, a Panel.
- **names** · *TREE*  
  File names without extension, like files — handy as captions or for Save by Path.
- **images** · *IMAGE ×N*  
  Every picture (IMAGE) as plain data, in list order — connect straight to image nodes, which run once per picture.
- **videos** · *VIDEO ×N*  
  Every video (VIDEO) as plain data.
- **audio** · *AUDIO ×N*  
  Every audio clip (AUDIO) as plain data.

## How to use
- **Add…** opens the system's file dialog. Select one or several pictures, videos or audio files and press **Add** — they go into the selected group.
- To take a **whole folder**, go into it and press **Add** without selecting anything (the name box says *(add this folder)*): every media file in it is added, each subfolder becoming a group named after it, like Load Folder.
- Files go into the group you clicked last; **+ Group** starts a new one. Rename a group in its header, drag thumbnails to reorder or move them between groups, × removes.
- **Text** shows the list itself — paste paths, write `# name` lines, delete lines.

```
# Arrival                              →  files {0} Arrival: 2 pictures
output/shots/arrival_01.png
output/shots/arrival_02.png

# Sound                                →  files {1} Sound: 1 audio
C:/music/theme.wav
```

## Data tree or data?
- **files** / **names** keep the groups: one branch per group, named after it. Use them wherever the groups matter — **Cross Reference** pairs every group with something else, **Tree Branch** takes one group out (*{0}* or its name).
- **images** / **videos** / **audio** are plain data: every file of that kind, in list order, without the groups. Connect them straight to ordinary nodes, which then run once per file.

## Load Media or Load Folder?
- **Load Media**: exactly the files you picked, in your order, from anywhere — the list is saved with the workflow.
- **Load Folder**: everything in a folder, re-read on every run — new files are picked up by themselves.

## Tips
- The dialog opens on the computer ComfyUI runs on and hands back real paths, so nothing is copied; it opens where you picked last. On macOS / Linux it picks files only — type folders in the Text view. Opened from another computer, type the paths in the Text view instead.
- Paths inside ComfyUI's output or input folder are written short (`output/…`, relative), so the workflow still works when ComfyUI moves.
- The templates use `arbor:storyboard/…`, the sample keyframes that come with Arbor.
- The node re-runs when a listed file changes.
