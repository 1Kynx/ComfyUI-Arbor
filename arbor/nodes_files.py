"""Folder in, folder out: Load Folder, Save Images by Path."""

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
from .common import IO, CAT_IMAGE, schema, connected, tree_in, tree_out, to_tree, unwrap
from .preview import is_image, label_of, to_pil

MAX_PREVIEWS = 64


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
    Save Images by Path puts in front of a named branch (per level of a nested path)."""
    return "/".join(_PATH_TAG.sub("", part) for part in rel.replace("\\", "/").split("/"))


def load_image(path: str) -> torch.Tensor:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        arr = np.asarray(im, dtype=np.float32) / 255.0
    return torch.from_numpy(arr)[None]


class LoadFolder(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_LoadFolder", "Load Folder", CAT_IMAGE,
            "Load every image in a folder. With subfolders on, each folder becomes a branch — "
            "the folder structure turns straight into a data tree.",
            [IO.String.Input("folder", default="", tooltip="Absolute path; output/… for ComfyUI's output folder; "
                                     "any other relative path is in the input folder"),
             IO.String.Input("pattern", default="*.png *.jpg *.jpeg *.webp", tooltip="File patterns separated by spaces"),
             IO.Boolean.Input("subfolders", default=True, tooltip="Each subfolder becomes a branch"),
             IO.Combo.Input("sort", options=["name", "modified"], default="name"),
             IO.Int.Input("limit", default=0, min=0, max=100000, tooltip="Max images in total; 0 = all")],
            [tree_out("images"), tree_out("names"),
             IO.String.Output(display_name="folders", is_output_list=True,
                              tooltip="Folder names, one per branch (plain data)"),
             IO.Int.Output(display_name="count")],
            ["load folder as tree", "load images", "folder", "directory", "batch load", "load batch"],
            input_list=False)

    @classmethod
    def fingerprint_inputs(cls, folder, pattern, subfolders, sort, limit):
        try:
            groups = scan_folder(resolve_folder(folder), pattern, subfolders, sort, limit)
        except Exception as e:
            return str(e)
        h = hashlib.sha1()
        for files in groups.values():
            for p in files:
                h.update(f"{p}|{os.path.getmtime(p)}|{os.path.getsize(p)};".encode("utf-8", "replace"))
        return h.hexdigest()

    @classmethod
    def execute(cls, folder, pattern, subfolders, sort, limit) -> IO.NodeOutput:
        root = resolve_folder(folder)
        groups = scan_folder(root, pattern, subfolders, sort, limit)
        if not groups:
            raise FileNotFoundError(f"Load Folder: no files matching '{pattern}' in {root}")
        images, names = {}, {}
        for b, files in enumerate(groups.values()):
            images[(b,)] = [load_image(p) for p in files]
            names[(b,)] = [os.path.splitext(os.path.basename(p))[0] for p in files]
        folders = [folder_label(rel or os.path.basename(root)) for rel in groups]
        branch_names = {(b,): f for b, f in enumerate(folders)}  # rows of an Image Grid, Panel titles
        count = sum(len(v) for v in images.values())
        return IO.NodeOutput(T.DataTree(images, branch_names), T.DataTree(names, branch_names), folders, count)


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


def _png_metadata(hidden):
    """The workflow, embedded like Save Image does (unless metadata is disabled)."""
    from comfy.cli_args import args

    if args.disable_metadata:
        return None
    meta = PngInfo()
    prompt = getattr(hidden, "prompt", None)
    if prompt is not None:
        meta.add_text("prompt", json.dumps(prompt))
    for k, v in (getattr(hidden, "extra_pnginfo", None) or {}).items():
        meta.add_text(k, json.dumps(v))
    return meta


class SaveImagesByPath(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_SaveImagesByPath", "Save Images by Path", CAT_IMAGE,
            "Save an image tree keeping its structure: one subfolder (or filename part) per branch, "
            "named after the branch when it has a name. Optional names give each file a readable name.",
            [tree_in("images"),
             IO.String.Input("filename_prefix", default="arbor/batch",
                             tooltip="Folder / prefix inside the output folder; supports %date% style vars"),
             IO.Combo.Input("layout", options=["subfolders", "flat"], default="subfolders",
                            tooltip="subfolders: prefix/0-1/000.png (named: prefix/0-1 · name/000.png) · "
                                    "flat: prefix_0-1_000.png"),
             tree_in("names", optional=True, tooltip="File names (matched to images item by item)")],
            [tree_out("paths")],
            ["save by path", "save images", "save tree", "export", "save batch"],
            is_output_node=True, hidden=[IO.Hidden.prompt, IO.Hidden.extra_pnginfo])

    @classmethod
    def execute(cls, images, filename_prefix, layout, names=None) -> IO.NodeOutput:
        tree = to_tree(images)
        name_tree = to_tree(names) if connected(names) else None
        first = next((v for v in tree.flat() if is_image(v)), None)
        if first is None:
            raise ValueError("Save Images by Path: no images in the tree")
        out_dir = folder_paths.get_output_directory()
        folder, filename, *_ = folder_paths.get_save_image_path(
            str(unwrap(filename_prefix, "arbor/batch")), out_dir, int(first.shape[2]), int(first.shape[1]))
        flat = unwrap(layout) == "flat"
        meta = _png_metadata(cls.hidden)

        saved, previews = {}, []
        for b, (path, items) in enumerate(tree.items()):
            tag = "-".join(map(str, path))
            name = tree.label(path, label_of)
            if name:  # a named branch (a scene, a folder, "Mira · lab coat") keeps its name on disk
                tag = f"{tag} · {_safe(name, 60)}"
            frames = [v[f] for v in items if is_image(v) for f in range(v.shape[0])]
            row = []
            for j, frame in enumerate(frames):
                label = T.match_item(name_tree, b, j) if name_tree else None
                stem = _safe(label_of(label)) if label is not None else f"{j:03d}"
                target = _unique(os.path.join(folder, f"{filename}_{tag}_{stem}.png") if flat
                                 else os.path.join(folder, filename, tag, f"{stem}.png"))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                to_pil(frame).save(target, pnginfo=meta, compress_level=4)
                row.append(target)
                if len(previews) < MAX_PREVIEWS:
                    sub = os.path.relpath(os.path.dirname(target), out_dir)
                    previews.append({"filename": os.path.basename(target),
                                     "subfolder": "" if sub == "." else sub, "type": "output"})
            saved[path] = row
        return IO.NodeOutput(T.DataTree(saved), ui={"images": previews})


NODES = [LoadFolder, SaveImagesByPath]
