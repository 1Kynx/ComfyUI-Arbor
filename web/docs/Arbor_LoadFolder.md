# Load Folder

Load every picture, video or audio file in a folder; with subfolders on, each folder becomes a branch, named after it — the folder structure turns straight into a data tree.

## Inputs

- **folder** · *STRING*  
  An absolute path; output/… for ComfyUI's output folder; any other relative path is inside the input folder.
- **kind** · *COMBO*  
  What to load: images (IMAGE) · videos (VIDEO — read lazily, nothing is decoded until a node needs the frames) · audio (AUDIO). Each kind has its own file pattern.
  - **kind.pattern** `pattern` · *STRING*  
    File name patterns separated by spaces, e.g. *.png *.jpg or *.mp4 *.mov or *.wav *.flac.
- **subfolders** · *BOOLEAN*  
  On: each subfolder (and the folder itself, if it has matching files) becomes a branch. Off: only this folder.
- **sort** · *COMBO (name · modified)*  
  name = natural order (img2 before img10); modified = oldest first.
- **limit** · *INT*  
  Maximum number of files in total; 0 = all. Pictures and audio are held in memory, so limit large folders.

## Outputs

- **files** · *TREE*  
  The pictures / videos / audio as a tree, one branch per folder, named after it — Image Grid labels its rows with the names, the Panel and Image Slider show them.
- **names** · *TREE*  
  File names without extension, same layout — handy as labels or for Save by Path.
- **folders** · *STRING ×N*  
  Folder names as plain data, one per branch.
- **count** · *INT*  
  Total number of files.

## Example
```
shots/             →  files {0}: 2 videos   folders: shots
  a.mp4 b.mp4
  day/             →  files {1}: 3 videos   folders: day
  night/           →  files {2}: 1 video    folders: night
```
Videos go on to **Tree to Data** → any node with a VIDEO input (Get Video Components, Save Video…), once per clip; audio the same with AUDIO inputs.

## Round trip
Folders saved by **Save by Path** from named branches (`0 · Arrival`, `1 · The village`) load back with their names (*Arrival*, *The village*) and in their order. Template: *arbor_folder_review*.

## Tips
- The node re-runs automatically when files are added, removed or changed.
- Pictures keep their own sizes; resize with **Smart Resize** if the next step needs one size.
