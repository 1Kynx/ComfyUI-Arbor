"""Folder in, folder out: Load Folder, Save by Path — pictures, videos, audio (and text when saving)."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re

import numpy as np
import torch
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo

import folder_paths

from . import tree as T
from .common import IO, CAT_MEDIA, schema, connected, tree_in, tree_out, to_tree, unwrap
from . import media
from .media import is_audio, is_video
from .preview import is_image, label_of, to_pil

MAX_PREVIEWS = 64

# what Load Folder reads, and the file patterns each kind starts with
KINDS = {
    "images": "*.png *.jpg *.jpeg *.webp",
    "videos": "*.mp4 *.mov *.webm *.mkv *.avi",
    "audio": "*.wav *.flac *.mp3 *.ogg *.m4a *.opus",
}


def _natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def resolve_folder(folder: str) -> str:
    """Absolute path; 'output/…' is in ComfyUI's output folder, any other relative path in input."""
    folder = os.path.expanduser(str(folder or "").strip().strip('"'))
    if not os.path.isabs(folder):
        head, _, rest = folder.replace("\\", "/").partition("/")
        if head.lower() == "output":
            folder = os.path.join(folder_paths.get_output_directory(), rest)
        else:
            folder = os.path.join(folder_paths.get_input_directory(), rest if head.lower() == "input" else folder)
    folder = os.path.normpath(folder)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Load Folder: '{folder}' is not a folder")
    return folder


def scan_folder(folder: str, pattern: str, subfolders: bool, sort: str, limit: int) -> dict[str, list[str]]:
    """{relative folder: [file paths]} in display order; empty folders are skipped."""
    pats = [p for p in re.split(r"[\s,;]+", pattern or "") if p] or ["*"]
    groups: dict[str, list[str]] = {}
    walker = os.walk(folder) if subfolders else [(folder, [], os.listdir(folder))]
    for root, dirs, files in walker:
        dirs.sort(key=_natural_key)
        hits = [os.path.join(root, f) for f in files
                if any(fnmatch.fnmatch(f.lower(), p.lower()) for p in pats)
                and os.path.isfile(os.path.join(root, f))]
        if not hits:
            continue
        if sort == "modified":
            hits.sort(key=os.path.getmtime)
        else:
            hits.sort(key=lambda p: _natural_key(os.path.basename(p)))
        rel = os.path.relpath(root, folder)
        groups[rel if rel != "." else ""] = hits
    ordered = dict(sorted(groups.items(), key=lambda kv: _natural_key(kv[0])))
    if limit > 0:
        left, out = limit, {}
        for k, v in ordered.items():
            if left <= 0:
                break
            out[k] = v[:left]
            left -= len(out[k])
        ordered = out
    return ordered


_PATH_TAG = re.compile(r"^\d+(-\d+)* · (?=\S)")


def folder_label(rel: str) -> str:
    """'2 · Night market' -> 'Night market': a folder name without the path tag that
    Save by Path puts in front of a named branch (per level of a nested path)."""
    return "/".join(_PATH_TAG.sub("", part) for part in rel.replace("\\", "/").split("/"))


# ======================================================================= media in

def load_image(path: str) -> torch.Tensor:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        arr = np.asarray(im, dtype=np.float32) / 255.0
    return torch.from_numpy(arr)[None]


def load_video(path: str):
    """A ComfyUI VIDEO that reads the file lazily (nothing is decoded until a node asks)."""
    from comfy_api.latest import InputImpl
    return InputImpl.VideoFromFile(path)


def load_audio(path: str) -> dict:
    """A ComfyUI AUDIO dict: waveform [1, channels, samples] float32, sample_rate."""
    import av
    with av.open(path) as f:
        if not f.streams.audio:
            raise ValueError(f"Load Folder: no audio stream in {os.path.basename(path)}")
        stream = f.streams.audio[0]
        channels = stream.channels
        chunks = []
        for frame in f.decode(streams=stream.index):
            buf = torch.from_numpy(frame.to_ndarray())
            if buf.shape[0] != channels:  # interleaved
                buf = buf.view(-1, channels).t()
            chunks.append(buf)
        if not chunks:
            raise ValueError(f"Load Folder: no audio in {os.path.basename(path)}")
        wav = torch.cat(chunks, dim=1)
        if not wav.dtype.is_floating_point:
            wav = wav.float() / (2 ** (8 * wav.element_size() - 1))
        return {"waveform": wav.float()[None], "sample_rate": stream.codec_context.sample_rate}


LOADERS = {"images": load_image, "videos": load_video, "audio": load_audio}


class LoadFolder(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        kinds = [IO.DynamicCombo.Option(k, [IO.String.Input("pattern", default=p,
                                                             tooltip="File patterns separated by spaces")])
                 for k, p in KINDS.items()]
        return schema(
            "Arbor_LoadFolder", "Load Folder", CAT_MEDIA,
            "Load every picture, video or audio file in a folder. With subfolders on, each folder becomes a "
            "branch, named after it — the folder structure turns straight into a data tree.",
            [IO.String.Input("folder", default="", tooltip="Absolute path; output/… for ComfyUI's output folder; "
                                                           "any other relative path is in the input folder"),
             IO.DynamicCombo.Input("kind", options=kinds,
                                   tooltip="What to load: images (IMAGE) · videos (VIDEO, read lazily) · audio (AUDIO)"),
             IO.Boolean.Input("subfolders", default=True, tooltip="Each subfolder becomes a branch"),
             IO.Combo.Input("sort", options=["name", "modified"], default="name"),
             IO.Int.Input("limit", default=0, min=0, max=100000, tooltip="Max files in total; 0 = all")],
            [tree_out("files", tooltip="The pictures / videos / audio, one branch per folder, named after it"),
             tree_out("names"),
             IO.String.Output(display_name="folders", is_output_list=True,
                              tooltip="Folder names, one per branch (plain data)"),
             IO.Int.Output(display_name="count")],
            ["load folder as tree", "load images", "load videos", "load audio", "folder", "directory",
             "batch load", "load batch"],
            input_list=False)

    @classmethod
    def fingerprint_inputs(cls, folder, kind, subfolders, sort, limit):
        try:
            groups = scan_folder(resolve_folder(folder), kind.get("pattern", ""), subfolders, sort, limit)
        except Exception as e:
            return str(e)
        h = hashlib.sha1(kind.get("kind", "").encode())
        for files in groups.values():
            for p in files:
                h.update(f"{p}|{os.path.getmtime(p)}|{os.path.getsize(p)};".encode("utf-8", "replace"))
        return h.hexdigest()

    @classmethod
    def execute(cls, folder, kind, subfolders, sort, limit) -> IO.NodeOutput:
        root = resolve_folder(folder)
        pattern = kind.get("pattern", "")
        groups = scan_folder(root, pattern, subfolders, sort, limit)
        if not groups:
            raise FileNotFoundError(f"Load Folder: no files matching '{pattern}' in {root}")
        load = LOADERS[kind["kind"]]
        files, names = {}, {}
        for b, paths in enumerate(groups.values()):
            files[(b,)] = [load(p) for p in paths]
            names[(b,)] = [os.path.splitext(os.path.basename(p))[0] for p in paths]
        folders = [folder_label(rel or os.path.basename(root)) for rel in groups]
        branch_names = {(b,): f for b, f in enumerate(folders)}  # rows of an Image Grid, Panel titles
        count = sum(len(v) for v in files.values())
        return IO.NodeOutput(T.DataTree(files, branch_names), T.DataTree(names, branch_names), folders, count)


# ======================================================================= media out

_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def _safe(name: str, limit: int = 80) -> str:
    """A file / folder name: no path characters, at most ``limit`` long, and — cut first, then
    trimmed — never ending in a space or dot, which Windows silently drops."""
    return _BAD.sub("_", str(name))[:limit].strip(" .") or "_"


def _unique(path: str) -> str:
    base, ext = os.path.splitext(path)
    k, out = 2, path
    while os.path.exists(out):
        out = f"{base}_{k}{ext}"
        k += 1
    return out


def _metadata(hidden) -> dict:
    """The workflow, as Save Image / Save Video embed it (unless metadata is disabled)."""
    from comfy.cli_args import args

    if args.disable_metadata:
        return {}
    meta = {}
    if getattr(hidden, "prompt", None) is not None:
        meta["prompt"] = hidden.prompt
    meta.update(getattr(hidden, "extra_pnginfo", None) or {})
    return meta


def media_files(items: list) -> list[tuple[str, object]]:
    """Everything a branch saves, one entry per file: ('png', frame), ('mp4', video),
    ('flac', (waveform, rate)), ('txt', text). Other values are skipped."""
    out = []
    for v in items:
        if is_image(v):
            out += [("png", v[f]) for f in range(v.shape[0])]
        elif is_video(v):
            out.append(("mp4", v))
        elif is_audio(v):
            out += [("flac", (w, int(v["sample_rate"]))) for w in v["waveform"].cpu()]
        elif isinstance(v, str):
            out.append(("txt", v))
    return out


def write_png(frame: torch.Tensor, path: str, meta: dict):
    info = None
    if meta:
        info = PngInfo()
        for k, v in meta.items():
            info.add_text(k, json.dumps(v))
    to_pil(frame).save(path, pnginfo=info, compress_level=4)


def write_mp4(video, path: str, meta: dict):
    from comfy_api.latest import Types
    video.save_to(path, format=Types.VideoContainer.MP4, codec=Types.VideoCodec.AUTO, metadata=meta or None)


def write_flac(audio: tuple[torch.Tensor, int], path: str, meta: dict):
    waveform, rate = audio
    media.write_flac(waveform, rate, path, meta)


def write_txt(text: str, path: str, _meta: dict):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


WRITERS = {"png": write_png, "mp4": write_mp4, "flac": write_flac, "txt": write_txt}


class SaveByPath(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_SaveByPath", "Save by Path", CAT_MEDIA,
            "Save a tree keeping its structure: one subfolder (or filename part) per branch, named after the "
            "branch when it has a name. Pictures are saved as PNG (a batch frame by frame), videos as MP4, "
            "audio as FLAC, text as TXT. Optional names give each file a readable name.",
            [tree_in("tree", tooltip="Pictures, videos, audio or text — a tree, a list or a single value"),
             IO.String.Input("filename_prefix", default="arbor/batch",
                             tooltip="Folder / prefix inside the output folder; supports %date% style vars"),
             IO.Combo.Input("layout", options=["subfolders", "flat"], default="subfolders",
                            tooltip="subfolders: prefix/0-1/000.png (named: prefix/0-1 · name/000.png) · "
                                    "flat: prefix_0-1_000.png"),
             tree_in("names", optional=True, tooltip="File names (matched to the files item by item)")],
            [tree_out("paths")],
            ["save by path", "save images", "save videos", "save audio", "save tree", "export", "save batch"],
            is_output_node=True, hidden=[IO.Hidden.prompt, IO.Hidden.extra_pnginfo])

    @classmethod
    def execute(cls, tree, filename_prefix, layout, names=None) -> IO.NodeOutput:
        data = to_tree(tree)
        name_tree = to_tree(names) if connected(names) else None
        plan = {path: media_files(items) for path, items in data.items()}
        first = next((f for files in plan.values() for f in files), None)
        if first is None:
            raise ValueError("Save by Path: nothing to save — connect pictures, videos, audio or text")
        w, h = 0, 0
        if first[0] == "png":
            h, w = int(first[1].shape[0]), int(first[1].shape[1])
        elif first[0] == "mp4":
            w, h = first[1].get_dimensions()
        out_dir = folder_paths.get_output_directory()
        folder, filename, *_ = folder_paths.get_save_image_path(
            str(unwrap(filename_prefix, "arbor/batch")), out_dir, w, h)
        flat = unwrap(layout) == "flat"
        meta = _metadata(cls.hidden)

        saved, previews = {}, {"images": [], "audio": [], "video": []}
        for b, (path, files) in enumerate(plan.items()):
            tag = "-".join(map(str, path))
            name = data.label(path, label_of)
            if name:  # a named branch (a scene, a folder, "Mira · lab coat") keeps its name on disk
                tag = f"{tag} · {_safe(name, 60)}"
            row = []
            for j, (ext, payload) in enumerate(files):
                label = T.match_item(name_tree, b, j) if name_tree else None
                stem = _safe(label_of(label)) if label is not None else f"{j:03d}"
                target = _unique(os.path.join(folder, f"{filename}_{tag}_{stem}.{ext}") if flat
                                 else os.path.join(folder, filename, tag, f"{stem}.{ext}"))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                WRITERS[ext](payload, target, meta)
                row.append(target)
                kind = {"png": "images", "mp4": "video", "flac": "audio"}.get(ext)
                if kind and len(previews[kind]) < MAX_PREVIEWS:
                    sub = os.path.relpath(os.path.dirname(target), out_dir)
                    previews[kind].append({"filename": os.path.basename(target),
                                           "subfolder": "" if sub == "." else sub, "type": "output"})
            saved[path] = row
        ui = {}
        if previews["images"]:
            ui["images"] = previews["images"]
        elif previews["video"]:  # how Save Video shows its result
            ui["images"], ui["animated"] = previews["video"], [True]
        if previews["audio"]:
            ui["audio"] = previews["audio"]
        return IO.NodeOutput(T.DataTree(saved, data.names), ui=ui)


NODES = [LoadFolder, SaveByPath]
