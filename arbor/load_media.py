"""Load Media: a hand-picked list of pictures, videos and audio files, grouped into named branches.

The list lives in the node as text, the Panel's way: `# name` starts a named branch, an empty
line starts a new branch, every other line is a file: an absolute path, output/… (ComfyUI's output
folder), arbor:… (Arbor's sample media) or relative to ComfyUI's input folder.
The node's Add… button fills it from the system's own file / folder dialog (opened by the server, see
dialogs.py and the /arbor/media routes below), so the files are used where they are, nothing is copied.
"""

from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import folder_paths

from . import tree as T
from .common import IO, CAT_MEDIA, schema, tree_out, unwrap
from .nodes_files import EXAMPLE_MEDIA, KINDS, LOADERS, _natural_key, folder_label, resolve_path, scan_folder, \
    short_path

EXTS = {kind: {p.strip("*").lower() for p in pattern.split()} for kind, pattern in KINDS.items()}
KIND_OF = {ext: kind for kind, exts in EXTS.items() for ext in exts}
SINGULAR = {"images": "image", "videos": "video", "audio": "audio"}


def kind_of(path: str) -> str | None:
    return KIND_OF.get(os.path.splitext(path)[1].lower())


def parse_list(text: str) -> list[tuple[str, list[str]]]:
    """[(branch name, [file lines])]: '# name' starts a named branch, an empty line a new one."""
    groups: list[tuple[str, list[str]]] = []
    name, files = "", []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            if files or name:
                groups.append((name, files))
            name, files = line.lstrip("#").strip(), []
        elif not line:
            if files:
                groups.append((name, files))
                name, files = "", []
        else:
            files.append(line.strip('"'))
    if files or name:
        groups.append((name, files))
    return [(n, f) for n, f in groups if f]


class LoadMedia(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return schema(
            "Arbor_LoadMedia", "Load Media", CAT_MEDIA,
            "Pick pictures, videos and audio anywhere on disk (Add… opens the system's file or folder dialog) and "
            "group them into named branches. Files are used where they are; each group becomes a branch named after it.",
            [IO.String.Input("files", multiline=True, default="",
                             tooltip="One file per line (absolute, output/…, arbor:… or inside input); '# name' starts "
                                     "a named group, an empty line a new group")],
            [tree_out("files", tooltip="Everything, one branch per group, named after it"),
             tree_out("images", tooltip="The pictures (IMAGE), same groups"),
             tree_out("videos", tooltip="The videos (VIDEO), same groups"),
             tree_out("audio", tooltip="The audio clips (AUDIO), same groups"),
             tree_out("names", tooltip="File names without extension, like files")],
            ["load media", "load images", "load videos", "load audio", "multiple images", "image list",
             "加载素材", "素材"],
            input_list=False)

    @classmethod
    def fingerprint_inputs(cls, files):
        h = hashlib.sha256(str(files).encode())
        for _, entries in parse_list(files):
            for e in entries:
                p = resolve_path(e)
                if os.path.isfile(p):
                    st = os.stat(p)
                    h.update(f"{p}|{st.st_mtime_ns}|{st.st_size}".encode())
        return h.hexdigest()

    @classmethod
    def execute(cls, files) -> IO.NodeOutput:
        groups = parse_list(files)
        if not groups:
            raise ValueError("Load Media: the list is empty — use Add… to pick files or a folder")
        everything, names = {}, {}
        by_kind = {k: {} for k in KINDS}
        labels = {}
        for b, (label, entries) in enumerate(groups):
            path = (b,)
            if label:
                labels[path] = label
            for e in entries:
                p = resolve_path(e)
                kind = kind_of(p)
                if kind is None:
                    raise ValueError(f"Load Media: '{e}' is not a picture, video or audio file")
                if not os.path.isfile(p):
                    raise FileNotFoundError(f"Load Media: '{p}' not found")
                value = LOADERS[kind](p)
                everything.setdefault(path, []).append(value)
                names.setdefault(path, []).append(os.path.splitext(os.path.basename(p))[0])
                by_kind[kind].setdefault(path, []).append(value)
        pick = lambda branches: {p: n for p, n in labels.items() if p in branches}
        return IO.NodeOutput(T.DataTree(everything, labels), *(T.DataTree(by_kind[k], pick(by_kind[k])) for k in KINDS),
                             T.DataTree(names, labels))


NODES = [LoadMedia]


# ------------------------------------------------------------------ dialogs and thumbnails

_THUMBS: OrderedDict = OrderedDict()
FILTERS = [("Pictures, videos and audio", ";".join(f"*{e}" for exts in EXTS.values() for e in sorted(exts))),
           ("Pictures", ";".join(f"*{e}" for e in sorted(EXTS["images"]))),
           ("Videos", ";".join(f"*{e}" for e in sorted(EXTS["videos"]))),
           ("Audio", ";".join(f"*{e}" for e in sorted(EXTS["audio"]))),
           ("All files", "*.*")]


def _roots() -> list[str]:
    return [os.path.abspath(p) for p in (folder_paths.get_input_directory(), folder_paths.get_output_directory(),
                                         folder_paths.get_temp_directory(), EXAMPLE_MEDIA)]


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), root]) == root
    except ValueError:  # another drive
        return False


def is_local(request) -> bool:
    return request.remote in ("127.0.0.1", "::1", "localhost")


def allowed(request, path: str) -> bool:
    """Anything on disk for the machine ComfyUI runs on; only ComfyUI's own folders for other ones."""
    return is_local(request) or any(_inside(path, r) for r in _roots())


def tree_of(path: str) -> list[dict]:
    """Every media file under path, one group per folder (Load Folder's order and names)."""
    pattern = " ".join(KINDS.values())
    out = []
    for rel, files in scan_folder(path, pattern, True, "name", 0).items():
        name = folder_label(rel) if rel else os.path.basename(os.path.normpath(path))
        out.append({"name": name, "files": [short_path(f) for f in files]})
    return out


def thumbnail(path: str, size: int) -> bytes:
    """A small WEBP of a picture or of a video's first frame (cached by file, time and size)."""
    from PIL import Image
    st = os.stat(path)
    key = (path, st.st_mtime_ns, size)
    if key in _THUMBS:
        _THUMBS.move_to_end(key)
        return _THUMBS[key]
    if kind_of(path) == "videos":
        import av
        with av.open(path) as c:
            img = next(c.decode(video=0)).to_image()
    else:
        img = Image.open(path)
        img.draft("RGB", (size, size))
        img = img.convert("RGB")
    img.thumbnail((size, size))
    import io
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=80)
    data = buf.getvalue()
    _THUMBS[key] = data
    if len(_THUMBS) > 512:
        _THUMBS.popitem(last=False)
    return data


def register_routes():
    from aiohttp import web
    from server import PromptServer

    routes = PromptServer.instance.routes

    @routes.post("/arbor/media/pick")
    async def _pick(request):
        """Open the system dialog on this computer. mode: files | folder | tree (a folder, read as groups)."""
        import asyncio
        from . import dialogs

        if not is_local(request):
            return web.json_response({"error": "remote"}, status=403)
        q = await request.json()
        mode = q.get("mode", "files")
        start = resolve_path(q.get("start", "")) if q.get("start") else folder_paths.get_input_directory()
        if not os.path.isdir(start):  # a file: start in its folder
            start = os.path.dirname(start) if os.path.isdir(os.path.dirname(start)) else folder_paths.get_input_directory()
        try:
            paths = await asyncio.to_thread(dialogs.pick, "files" if mode == "files" else "folder", start,
                                            q.get("title", ""), FILTERS)
        except dialogs.Unavailable as e:
            return web.json_response({"error": str(e)}, status=409)
        except Exception as e:  # pragma: no cover - a broken system dialog
            return web.json_response({"error": f"The system dialog failed: {e}"}, status=500)
        # entries / folder written the short way (output/…, arbor:…, relative to input) where possible;
        # dir = where the next dialog should start
        out = {"paths": paths, "entries": [short_path(p) for p in paths],
               "dir": paths[0] if mode != "files" else (os.path.dirname(paths[0]) if paths else "")}
        if mode == "tree" and paths:
            out["groups"] = tree_of(paths[0])
        return web.json_response(out)

    @routes.get("/arbor/media/thumb")
    async def _thumb(request):
        q = request.rel_url.query
        path = resolve_path(q.get("path", ""))
        if not allowed(request, path) or not os.path.isfile(path) or kind_of(path) not in ("images", "videos"):
            return web.Response(status=404)
        try:
            data = thumbnail(path, max(32, min(512, int(q.get("size", 160)))))
        except Exception:
            return web.Response(status=415)
        return web.Response(body=data, content_type="image/webp", headers={"Cache-Control": "max-age=600"})
