# Load Media

Pick pictures, videos and audio from anywhere on disk and group them into named branches — several Load Image nodes in one, using the system's own file dialog, with thumbnails. Files are used where they are; nothing is copied.

## Inputs

- **folder** · *STRING*  
  Base folder: relative entries in the list are read from here and the file dialog starts here. An absolute path; output/… for ComfyUI's output folder; arbor:… for Arbor's sample media; any other relative path is inside input.
- **files** · *STRING*  
  The list (kept as text): '# name' starts a named group, an empty line a new group, every other line is a file — relative to the folder, or absolute. Edit it in the node's Text view, or fill it with Add files… / Add folder….

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
- **Add files…** opens the system's file dialog — select one or several pictures, videos or audio files.
- **Add folder…** opens the system's folder dialog and adds every media file in it — each subfolder becomes a group named after it, like Load Folder.
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
- The dialog opens on the computer ComfyUI runs on (it hands back real paths, so nothing is copied). Opened from another computer, type the paths in the Text view instead.
- The templates use `arbor:storyboard`, the sample keyframes that come with Arbor.
- The node re-runs when a listed file changes.
