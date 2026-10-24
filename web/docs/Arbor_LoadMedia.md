# Load Media

Pick pictures, videos and audio from anywhere on disk and group them into named branches — several Load Image nodes in one, using the system's own file dialog, with thumbnails. Files are used where they are; nothing is copied.

## Inputs

- **files** · *STRING*  
  The list (kept as text): '# name' starts a named group, an empty line a new group, every other line is a file — an absolute path, output/… (ComfyUI's output folder), arbor:… (Arbor's sample media) or relative to the input folder. Edit it in the node's Text view, or fill it with Add….

## Outputs

- **files** · *TREE*  
  Everything, one branch per group, named after it — for the Compare Viewer, Save by Path or a Panel.
- **images** · *TREE*  
  Only the pictures (IMAGE), same groups — go on to Tree to Data → image nodes, or Image Grid.
- **videos** · *TREE*  
  Only the videos (VIDEO), same groups.
- **audio** · *TREE*  
  Only the audio clips (AUDIO), same groups.
- **names** · *TREE*  
  File names without extension, like files — handy as captions or for Save by Path.

## How to use
- **Add…** → **Files…** opens the system's file dialog — select one or several pictures, videos or audio files.
- **Add…** → **Folder…** opens the system's folder dialog and adds every media file in it — each subfolder becomes a group named after it, like Load Folder.
- Files go into the group you clicked last; **+ Group** starts a new one. Rename a group in its header, drag thumbnails to reorder or move them between groups, × removes.
- **Text** shows the list itself — paste paths, write `# name` lines, delete lines.

```
# Arrival                              →  files {0} Arrival: 2 pictures
output/shots/arrival_01.png
output/shots/arrival_02.png

# Sound                                →  files {1} Sound: 1 audio
C:/music/theme.wav
```

## Load Media or Load Folder?
- **Load Media**: exactly the files you picked, in your order, from anywhere — the list is saved with the workflow.
- **Load Folder**: everything in a folder, re-read on every run — new files are picked up by themselves.

## Tips
- The dialog opens on the computer ComfyUI runs on and hands back real paths, so nothing is copied; it opens where you picked last. Opened from another computer, type the paths in the Text view instead.
- Paths inside ComfyUI's output or input folder are written short (`output/…`, relative), so the workflow still works when ComfyUI moves.
- The templates use `arbor:storyboard/…`, the sample keyframes that come with Arbor.
- The node re-runs when a listed file changes.
