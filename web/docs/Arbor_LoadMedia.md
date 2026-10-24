# Load Media

Pick pictures, videos and audio from anywhere on disk and group them into named branches — several Load Image nodes in one, with a browse window and thumbnails. Files are used where they are; nothing is copied.

## Inputs

- **folder** · *STRING*  
  Base folder: relative entries in the list are read from here and Browse… starts here. An absolute path; output/… for ComfyUI's output folder; arbor:… for Arbor's sample media; any other relative path is inside input.
- **files** · *STRING*  
  The list (kept as text): '# name' starts a named group, an empty line a new group, every other line is a file — relative to the folder, or absolute. Edit it in the node's Text view, or fill it with Browse….

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
- **Browse…** opens a file window: pick files (click to select, double-click to add one) and **Add selected**, or **Add whole folder** — every subfolder becomes a group named after it, like Load Folder.
- Files go into the group you clicked last; **+ Group** starts a new one. Rename a group in its header, drag thumbnails to reorder or move them between groups, × removes.
- **Text** shows the list itself — paste paths, write `# name` lines, delete lines.

```
# Arrival            →  files {0} Arrival: 2 pictures
0 · Arrival/000.jpg
0 · Arrival/001.jpg

# Sound              →  files {1} Sound: 1 audio
C:/music/theme.wav
```

## Load Media or Load Folder?
- **Load Media**: exactly the files you picked, in your order, from anywhere — the list is saved with the workflow.
- **Load Folder**: everything in a folder, re-read on every run — new files are picked up by themselves.

## Tips
- Browsing anywhere on disk works on the computer ComfyUI runs on. Opened from another computer, only ComfyUI's input / output folders can be browsed (typing paths still works).
- The templates use `arbor:storyboard`, the sample keyframes that come with Arbor.
- The node re-runs when a listed file changes.
