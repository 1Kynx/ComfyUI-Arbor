# 按路径保存

按数据树结构保存——图片存 PNG、视频存 MP4、音频存 FLAC、文字存 TXT：每个分支一个子文件夹（或文件名的一部分），有名字的分支用名字命名，可选为每个文件命名。

## 输入

- **数据树** `tree` · *任意*  
  要保存的内容——数据树、列表或单个值。图片批次逐帧保存，音频批次逐段保存；其它类型的值会跳过。
- **文件名前缀** `filename_prefix` · *STRING*  
  保存位置：output 文件夹内的目录 / 前缀（arbor/run）、output/…，或绝对路径如 D:/renders/run——点输入框末尾的文件夹图标可以选择文件夹。只有 ComfyUI 只在本机监听时才能存到 output 以外。支持 %date% 等变量。
- **布局** `layout` · *COMBO (subfolders · flat)*  
  subfolders：前缀/0-1/000.png（有名字的分支：前缀/0-1 · 名字/000.png）· flat：前缀_0-1_000.png。普通列表（只有一个未命名的分支 {0}）直接存在前缀下：前缀/000.png · 前缀_000.png
- **文件名** `names` · *任意，可选*  
  可选，与文件逐项对应的文件名（例如「加载文件夹」的文件名或提示词模板的输出）。

## 输出

- **路径** `paths` · *数据树*  
  已保存文件的路径，结构（和分支名）与输入相同。

## 示例
数据树 `{0} Arrival: 2 段 · {1} Village: 1 段`，前缀 `arbor/h3`，布局 *subfolders*：
```
output/arbor/h3/0 · Arrival/000.mp4  001.mp4
output/arbor/h3/1 · Village/000.mp4
```
图片存为 `000.png ……`，音频 `000.flac ……`，文字 `000.txt ……`——同一个分支里可以混合。**加载文件夹** 读取 `output/arbor/h3_two_characters`（类型选 *videos*）就能把数据树连同名字读回来。模板：*arbor_h3_storyboard_video*。

接入 *文件名* 后，文件按名字命名（`cat.png`、`dog.png`……）。

## 保存到任意位置
点前缀输入框末尾的 **文件夹图标**，用系统的文件夹窗口选择保存位置——前缀的最后一段（`run`、`batch`）保留为文件名部分。绝对路径前缀（`D:/renders/run`）会保存到 ComfyUI 的 output 文件夹以外：
- ComfyUI 只在本机监听时（默认，没有 `--listen`）允许；
- ComfyUI 对局域网开放时（`--listen`）拒绝，因为那样任何能提交工作流的人都能往你的硬盘任意位置写文件——如确实需要，设置环境变量 `ARBOR_SAVE_ANYWHERE=1` 即可允许。

保存在 output 以外的文件，预览会从临时文件夹里的副本显示。

## 提示
- 永远不会覆盖已有文件：会自动加 `_2`、`_3`…… 后缀。
- 和 ComfyUI 自带的保存节点一样，每个 PNG、MP4、FLAC 都内嵌工作流。
