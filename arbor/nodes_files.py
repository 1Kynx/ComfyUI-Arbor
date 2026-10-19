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
from .common import IO, CAT_IMAGE, tree_in, tree_out, to_tree, unwrap
from .preview import is_image, label_of, to_pil

MAX_PREVIEWS = 64


def _natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def resolve_folder(folder: str) -> str:
    folder = os.path.expanduser(str(folder or "").strip().strip('"'))
    if not os.path.isabs(folder):
        folder = os.path.join(folder_paths.get_input_directory(), folder)
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


def load_image(path: str) -> torch.Tensor:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        arr = np.asarray(im, dtype=np.float32) / 255.0
    return torch.from_numpy(arr)[None]


class LoadFolder(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_LoadFolder", display_name="Load Folder", category=CAT_IMAGE,
            description="Load every image in a folder. With subfolders on, each folder becomes a "
                        "branch — the folder structure turns straight into a data tree.",
            search_aliases=["load folder as tree", "load images", "folder", "directory", "batch load", "load batch"],
            inputs=[
                IO.String.Input("folder", default="",
                                tooltip="Absolute path, or relative to ComfyUI's input folder"),
                IO.String.Input("pattern", default="*.png *.jpg *.jpeg *.webp",
                                tooltip="File patterns separated by spaces"),
                IO.Boolean.Input("subfolders", default=True, tooltip="Each subfolder becomes a branch"),
                IO.Combo.Input("sort", options=["name", "modified"], default="name"),
                IO.Int.Input("limit", default=0, min=0, max=100000, tooltip="Max images in total; 0 = all"),
            ],
            outputs=[tree_out("images"), tree_out("names"), tree_out("folders"),
                     IO.Int.Output(display_name="count")])

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
        for b, (rel, files) in enumerate(groups.items()):
            images[(b,)] = [load_image(p) for p in files]
            names[(b,)] = [os.path.splitext(os.path.basename(p))[0] for p in files]
        folders = [rel or os.path.basename(root) for rel in groups]
        count = sum(len(v) for v in images.values())
        return IO.NodeOutput(T.DataTree(images), T.DataTree(names), T.DataTree({(0,): folders}), count)


_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def _safe(name: str, limit: int = 80) -> str:
    return _BAD.sub("_", str(name)).strip(" .")[:limit] or "_"


def _unique(path: str) -> str:
    base, ext = os.path.splitext(path)
    k, out = 2, path
    while os.path.exists(out):
        out = f"{base}_{k}{ext}"
        k += 1
    return out


class SaveByPath(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="Arbor_SaveByPath", display_name="Save Images by Path", category=CAT_IMAGE,
            description="Save an image tree keeping its structure: one subfolder (or filename part) "
                        "per branch path. Optional names give each file a readable name.",
            search_aliases=["save by path", "save images", "save tree", "export", "save batch"],
            is_output_node=True, is_input_list=True,
            hidden=[IO.Hidden.prompt, IO.Hidden.extra_pnginfo],
            inputs=[
                tree_in("images"),
                IO.String.Input("filename_prefix", default="arbor/batch",
                                tooltip="Folder/prefix inside the output folder; supports %date% style vars"),
                IO.Combo.Input("layout", options=["subfolders", "flat"], default="subfolders",
                               tooltip="subfolders: prefix_0-1/000.png · flat: prefix_0-1_000.png"),
                tree_in("names", optional=True, tooltip="File names (matched to images item by item)"),
            ],
            outputs=[tree_out("paths")])

    @classmethod
    def execute(cls, images, filename_prefix, layout, names=None) -> IO.NodeOutput:
        from comfy.cli_args import args

        tree = to_tree(images)
        name_tree = to_tree(names) if names is not None else None
        prefix = str(unwrap(filename_prefix, "arbor/batch"))
        layout = unwrap(layout)
        out_dir = folder_paths.get_output_directory()
        first = next((v for v in tree.flat() if is_image(v)), None)
        if first is None:
            raise ValueError("Save Images by Path: no images in the tree")
        folder, filename, _, _, _ = folder_paths.get_save_image_path(
            prefix, out_dir, int(first.shape[2]), int(first.shape[1]))

        meta = None
        if not args.disable_metadata:
            meta = PngInfo()
            prompt = getattr(cls.hidden, "prompt", None)
            if prompt is not None:
                meta.add_text("prompt", json.dumps(prompt))
            for k, v in (getattr(cls.hidden, "extra_pnginfo", None) or {}).items():
                meta.add_text(k, json.dumps(v))

        saved, previews = {}, []
        name_paths = name_tree.paths() if name_tree else []
        for b, (path, items) in enumerate(tree.items()):
            tag = "-".join(map(str, path))
            row = []
            j = 0
            for v in items:
                if not is_image(v):
                    continue
                for f in range(v.shape[0]):
                    label = None
                    if name_tree and name_paths:
                        nb = name_tree.branches[name_paths[min(b, len(name_paths) - 1)]]
                        if nb:
                            label = _safe(label_of(nb[min(j, len(nb) - 1)]))
                    stem = label or f"{j:03d}"
                    if layout == "flat":
                        target = os.path.join(folder, f"{filename}_{tag}_{stem}.png")
                    else:
                        target = os.path.join(folder, f"{filename}_{tag}", f"{stem}.png")
                    target = _unique(target)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    to_pil(v[f]).save(target, pnginfo=meta, compress_level=4)
                    row.append(target)
                    if len(previews) < MAX_PREVIEWS:
                        sub = os.path.relpath(os.path.dirname(target), out_dir)
                        previews.append({"filename": os.path.basename(target),
                                         "subfolder": "" if sub == "." else sub, "type": "output"})
                    j += 1
            saved[path] = row
        return IO.NodeOutput(T.DataTree(saved), ui={"images": previews})


NODES = [LoadFolder, SaveByPath]
