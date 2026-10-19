# Load Folder

Load every image in a folder; with subfolders on, each folder becomes a branch — the folder structure turns straight into a data tree.

## Inputs

- **folder** · *STRING*  
  An absolute path; output/… for ComfyUI's output folder; any other relative path is inside the input folder.
- **pattern** · *STRING*  
  File name patterns separated by spaces, e.g. *.png *.jpg.
- **subfolders** · *BOOLEAN*  
  On: each subfolder (and the folder itself, if it has images) becomes a branch. Off: only this folder.
- **sort** · *COMBO (name · modified)*  
  name = natural order (img2 before img10); modified = oldest first.
- **limit** · *INT*  
  Maximum number of images in total; 0 = all. Every image is held in memory, so limit large folders.

## Outputs

- **images** · *TREE*  
  Image tree, one branch per folder, named after it — Image Grid labels its rows with the names, the Panel and Image Slider show them.
- **names** · *TREE*  
  File names without extension, same layout — handy as labels or for Save Images by Path.
- **folders** · *STRING ×N*  
  Folder names as plain data, one per branch.
- **count** · *INT*  
  Total number of images.

## Example
```
photos/            →  images {0}: 2 images   folders: photos
  a.png b.png
  day/             →  images {1}: 3 images   folders: day
  night/           →  images {2}: 1 image    folders: night
```

## Round trip
Folders saved by **Save Images by Path** from named branches (`0 · Arrival`, `1 · The village`) load back with their names (*Arrival*, *The village*) and in their order. Template: *arbor_folder_review*.

## Tips
- The node re-runs automatically when files are added, removed or changed.
- Images keep their own sizes; resize with **Smart Resize** if the next step needs one size.
