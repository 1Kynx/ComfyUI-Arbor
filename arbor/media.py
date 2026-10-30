"""Video and audio helpers shared by Compare Viewer, Video Grid and the file nodes.

VIDEO values are comfy_api VideoInput objects (VideoFromFile / VideoFromComponents);
AUDIO values are dicts {"waveform": [batch, channels, samples], "sample_rate"}.
"""

from __future__ import annotations

import io
import json
import os
import uuid
from fractions import Fraction

import numpy as np
import torch
import torch.nn.functional as F

import folder_paths

BROWSER_EXTS = {".mp4", ".m4v", ".webm", ".mov"}  # played as they are; anything else is re-encoded
VIEW_CRF = 8  # H.264 quality for videos re-encoded only to be shown (lower = closer to the source)


def is_video(v) -> bool:
    return hasattr(v, "save_to") and hasattr(v, "get_dimensions")


def is_audio(v) -> bool:
    return isinstance(v, dict) and isinstance(v.get("waveform"), torch.Tensor) and bool(v.get("sample_rate"))


def temp_file(prefix: str, ext: str) -> tuple[str, dict]:
    """A fresh file in temp/arbor and its /view reference."""
    sub = "arbor"
    d = os.path.join(folder_paths.get_temp_directory(), sub)
    os.makedirs(d, exist_ok=True)
    name = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
    return os.path.join(d, name), {"filename": name, "subfolder": sub, "type": "temp"}


def view_ref(path: str) -> dict | None:
    """/view reference for a file inside ComfyUI's output, input or temp folder, else None."""
    full = os.path.abspath(path)
    for kind, root in (("output", folder_paths.get_output_directory()), ("input", folder_paths.get_input_directory()),
                       ("temp", folder_paths.get_temp_directory())):
        try:
            rel = os.path.relpath(full, os.path.abspath(root))
        except ValueError:  # another drive
            continue
        if not rel.startswith(".."):
            sub, name = os.path.split(rel)
            return {"filename": name, "subfolder": sub, "type": kind}
    return None


def plain_file(v) -> str | None:
    """The file behind a video that is exactly that file (not trimmed, cropped or in memory)."""
    from comfy_api.latest import InputImpl
    if not isinstance(v, InputImpl.VideoFromFile):
        return None
    try:
        src = v.get_stream_source()
        start, duration = v.get_active_trim_window()
    except Exception:
        return None
    if not isinstance(src, str) or start or duration or getattr(v, "_VideoFromFile__crop", None) is not None:
        return None
    return src if os.path.isfile(src) else None


def video_info(v) -> dict:
    """Size, rate and length — whatever the video can tell without decoding."""
    out = {}
    for key, get in (("wh", lambda: v.get_dimensions()), ("fps", lambda: float(v.get_frame_rate())),
                     ("dur", lambda: float(v.get_duration())), ("frames", lambda: int(v.get_frame_count()))):
        try:
            out[key] = get()
        except Exception:
            pass
    w, h = out.pop("wh", (0, 0))
    return {"w": int(w), "h": int(h), **out}


def video_ref(v, prefix: str = "video") -> dict:
    """/view reference the browser can play: the file itself when it is one, else an MP4 in temp."""
    path = plain_file(v)
    if path and os.path.splitext(path)[1].lower() in BROWSER_EXTS:
        ref = view_ref(path)
        if ref:
            return ref
    from comfy_api.latest import Types
    path, ref = temp_file(prefix, "mp4")
    # near-lossless (ComfyUI's default is CRF 18): the viewer is for comparing, so a clip made in the
    # workflow should look like itself next to a picture or a saved file, not like a second encode
    try:
        v.save_to(path, format=Types.VideoContainer.MP4, codec=Types.VideoCodec.AUTO, crf=VIEW_CRF)
    except TypeError:  # a video type without the crf option
        v.save_to(path, format=Types.VideoContainer.MP4, codec=Types.VideoCodec.AUTO)
    return ref


# ------------------------------------------------------------------ audio

def write_flac(waveform: torch.Tensor, rate: int, path: str | io.BytesIO, meta: dict | None = None):
    """One clip ([channels, samples]) as FLAC, the way ComfyUI's audio saving writes it."""
    import av
    waveform = waveform.detach().float().cpu()
    if waveform.dim() == 1:
        waveform = waveform[None]
    if waveform.shape[0] > 2:  # FLAC layouts here: mono or stereo
        waveform = waveform[:2]
    layout = "mono" if waveform.shape[0] == 1 else "stereo"
    buf = io.BytesIO()
    container = av.open(buf, mode="w", format="flac")
    for k, v in (meta or {}).items():
        container.metadata[k] = json.dumps(v)
    stream = container.add_stream("flac", rate=rate, layout=layout)
    frame = av.AudioFrame.from_ndarray(waveform.movedim(0, 1).reshape(1, -1).numpy(), format="flt", layout=layout)
    frame.sample_rate = rate
    frame.pts = 0
    container.mux(stream.encode(frame))
    container.mux(stream.encode(None))
    container.close()
    if isinstance(path, io.BytesIO):
        path.write(buf.getbuffer())
    else:
        with open(path, "wb") as f:
            f.write(buf.getbuffer())


def peaks(waveform: torch.Tensor, n: int = 480) -> list[float]:
    """n loudness peaks (0..1) of a clip ([channels, samples]) for drawing its waveform."""
    mono = waveform.detach().float().cpu().abs()
    mono = mono.amax(0) if mono.dim() > 1 else mono
    if mono.numel() == 0:
        return []
    n = max(1, min(n, mono.numel()))
    edges = torch.linspace(0, mono.numel(), n + 1).long()
    out = [float(mono[a:max(b, a + 1)].max()) for a, b in zip(edges[:-1].tolist(), edges[1:].tolist())]
    top = max(out) or 1.0
    return [round(min(1.0, p / top), 3) for p in out]


def audio_clips(a: dict) -> list[tuple[torch.Tensor, int]]:
    """Every clip of an AUDIO batch as ([channels, samples], rate)."""
    rate = int(a["sample_rate"])
    w = a["waveform"]
    w = w[None, None] if w.dim() == 1 else (w[None] if w.dim() == 2 else w)
    return [(clip, rate) for clip in w]


def audio_ref(waveform: torch.Tensor, rate: int, prefix: str = "audio") -> dict:
    path, ref = temp_file(prefix, "flac")
    write_flac(waveform, rate, path)
    return ref


def video_audio(v) -> tuple[torch.Tensor, int] | None:
    """The sound track of a video as ([channels, samples], rate), or None."""
    path = plain_file(v)
    if path:
        from .nodes_files import load_audio
        try:
            a = load_audio(path)
        except Exception:
            return None
        return a["waveform"][0], int(a["sample_rate"])
    try:
        a = v.get_components().audio
    except Exception:
        return None
    if not is_audio(a):
        return None
    return audio_clips(a)[0]


def mix(tracks: list[tuple[torch.Tensor, int]], rate: int = 48000) -> torch.Tensor | None:
    """Mix clips into one stereo track at `rate` ([2, samples]); louder than 1 is scaled down."""
    tracks = [t for t in tracks if t is not None and t[0].numel()]
    if not tracks:
        return None
    parts = []
    for w, r in tracks:
        w = w.float()
        w = w.repeat(2, 1) if w.shape[0] == 1 else w[:2]
        if r != rate:
            w = F.interpolate(w[None], size=max(1, round(w.shape[1] * rate / r)), mode="linear",
                              align_corners=False)[0]
        parts.append(w)
    out = torch.zeros(2, max(p.shape[1] for p in parts))
    for p in parts:
        out[:, :p.shape[1]] += p
    peak = float(out.abs().max())
    return out / peak if peak > 1 else out


# ------------------------------------------------------------------ frames

def _resize(frames: torch.Tensor, w: int, h: int) -> np.ndarray:
    """[N,H,W,C] float 0..1 -> [N,h,w,3] uint8."""
    out = []
    for k in range(0, frames.shape[0], 16):
        x = frames[k:k + 16, ..., :3].float().movedim(-1, 1)
        if x.shape[-2:] != (h, w):
            x = F.interpolate(x, size=(h, w), mode="bilinear", antialias=True, align_corners=False)
        out.append((x.clamp(0, 1) * 255).round().byte().movedim(1, -1).cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, h, w, 3), np.uint8)


def clip_frames(v, size, crop: tuple[int, int] | None = None) -> tuple[np.ndarray, float]:
    """Every frame of a video (or an image batch) resized by size(w, h) -> (tw, th) and, with
    crop=(cw, ch), cut to that size around the centre — as uint8 [N, h, w, 3] — and its frame rate
    (0 for an image batch). Videos on disk are decoded and scaled frame by frame, so a long clip
    never sits in memory at full size."""
    def cut(frames: np.ndarray) -> np.ndarray:
        if crop is None:
            return frames
        h, w = frames.shape[1:3]
        cw, ch = min(crop[0], w), min(crop[1], h)
        x, y = (w - cw) // 2, (h - ch) // 2
        return frames[:, y:y + ch, x:x + cw]

    if isinstance(v, torch.Tensor):
        tw, th = size(int(v.shape[2]), int(v.shape[1]))
        return cut(_resize(v, tw, th)), 0.0
    path = plain_file(v)
    if path:
        import av
        with av.open(path) as c:
            stream = c.streams.video[0]
            stream.thread_type = "AUTO"
            fps = float(stream.average_rate or stream.guessed_rate or v.get_frame_rate())
            frames = []
            for frame in c.decode(stream):
                tw, th = size(frame.width, frame.height)
                frames.append(cut(frame.reformat(width=tw, height=th, format="rgb24").to_ndarray()[None])[0])
        if frames:
            return np.stack(frames), fps
    comps = v.get_components()
    images = comps.images
    tw, th = size(int(images.shape[2]), int(images.shape[1]))
    return cut(_resize(images, tw, th)), float(comps.frame_rate)


def encode_mp4(frames, count: int, fps: float, width: int, height: int, audio: torch.Tensor | None,
               rate: int = 48000, path: str | None = None) -> str:
    """Encode `count` frames from the iterator `frames` (uint8 [height, width, 3]) as H.264 MP4,
    with an optional stereo track ([2, samples] at `rate`). Returns the file path (temp by default)."""
    import av
    if path is None:
        path, _ = temp_file("video_grid", "mp4")
    rate_q = Fraction(fps).limit_denominator(1001)
    with av.open(path, mode="w") as c:
        vs = c.add_stream("libx264", rate=rate_q)
        vs.width, vs.height, vs.pix_fmt = width, height, "yuv420p"
        vs.options = {"crf": "19", "preset": "medium"}
        aus = None
        if audio is not None:
            aus = c.add_stream("aac", rate=rate, layout="stereo")
        for k, arr in zip(range(count), frames):
            frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
            frame.pts = k
            frame.time_base = 1 / rate_q
            c.mux(vs.encode(frame))
        c.mux(vs.encode(None))
        if aus is not None:
            samples = audio[:, :int(round(count / fps * rate))].contiguous().numpy().astype(np.float32)
            step = 1024
            for k in range(0, samples.shape[1], step):
                af = av.AudioFrame.from_ndarray(np.ascontiguousarray(samples[:, k:k + step]), format="fltp",
                                                layout="stereo")
                af.sample_rate = rate
                af.pts = k
                c.mux(aus.encode(af))
            c.mux(aus.encode(None))
    return path
