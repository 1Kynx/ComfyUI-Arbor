"""The system's own file and folder dialogs, opened by the ComfyUI server on its own screen.

A web page never learns where a picked file lives, so Load Media / Load Folder ask the server:
it shows the native dialog (Windows: the Explorer dialog through IFileOpenDialog; macOS: osascript;
Linux: zenity or kdialog) and answers with real paths. Only useful when ComfyUI runs on the
computer you are sitting at — the routes refuse requests from other machines.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading

_lock = threading.Lock()


class Unavailable(RuntimeError):
    """No system dialog can be shown here."""


def pick(mode: str, start: str = "", title: str = "", filters: list[tuple[str, str]] | None = None) -> list[str]:
    """mode 'files' (several files) or 'folder'. Returns the chosen paths, [] when cancelled."""
    if not _lock.acquire(blocking=False):
        raise Unavailable("A file dialog is already open")
    try:
        if os.name == "nt":
            return _windows(mode, start, title, filters or [])
        if sys.platform == "darwin":
            return _mac(mode, start, title)
        return _linux(mode, start, title, filters or [])
    finally:
        _lock.release()


# ------------------------------------------------------------------ Windows (IFileOpenDialog)

def _windows(mode, start, title, filters):
    import ctypes
    from ctypes import wintypes as wt

    ole32, shell32, user32 = ctypes.windll.ole32, ctypes.windll.shell32, ctypes.windll.user32

    class GUID(ctypes.Structure):
        _fields_ = [("a", ctypes.c_ulong), ("b", ctypes.c_ushort), ("c", ctypes.c_ushort), ("d", ctypes.c_ubyte * 8)]

    def guid(s):
        g = GUID()
        ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g))
        return g

    class FILTERSPEC(ctypes.Structure):
        _fields_ = [("name", wt.LPCWSTR), ("spec", wt.LPCWSTR)]

    def method(obj, index, *argtypes):
        vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(vtable[index])

    def ok(hr, what):
        if hr < 0:
            raise OSError(f"{what} failed (0x{hr & 0xFFFFFFFF:08X})")

    def release(obj):
        if obj:
            method(obj, 2)(obj)

    def path_of(item):
        s = ctypes.c_wchar_p()
        ok(method(item, 5, ctypes.c_ulong, ctypes.POINTER(ctypes.c_wchar_p))(item, 0x80058000, ctypes.byref(s)),
           "GetDisplayName")
        try:
            return s.value
        finally:
            ole32.CoTaskMemFree(s)

    ole32.CoInitializeEx(None, 0x2)  # apartment threaded, on this worker thread
    dialog = ctypes.c_void_p()
    try:
        ok(ole32.CoCreateInstance(ctypes.byref(guid("{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}")), None, 1,
                                  ctypes.byref(guid("{d57c7288-d4ad-4768-be02-9d969532d960}")), ctypes.byref(dialog)),
           "CoCreateInstance")
        opts = ctypes.c_ulong()
        method(dialog, 10, ctypes.POINTER(ctypes.c_ulong))(dialog, ctypes.byref(opts))
        flags = opts.value | 0x40 | 0x800  # file system only, path must exist
        flags |= 0x20 if mode == "folder" else (0x200 | 0x1000)  # pick folders | multi-select, file must exist
        method(dialog, 9, ctypes.c_ulong)(dialog, flags)
        if title:
            method(dialog, 17, wt.LPCWSTR)(dialog, title)
        if mode != "folder" and filters:
            specs = (FILTERSPEC * len(filters))(*[FILTERSPEC(n, s) for n, s in filters])
            method(dialog, 4, ctypes.c_uint, ctypes.POINTER(FILTERSPEC))(dialog, len(filters), specs)
        if start and os.path.isdir(start):
            folder = ctypes.c_void_p()
            if shell32.SHCreateItemFromParsingName(ctypes.c_wchar_p(start), None,
                                                   ctypes.byref(guid("{43826d1e-e718-42ee-bc55-a1e261c37bfe}")),
                                                   ctypes.byref(folder)) >= 0:
                method(dialog, 12, ctypes.c_void_p)(dialog, folder)  # SetFolder
                release(folder)
        # owned by the window in front (the browser you clicked in), so the dialog opens on top of it
        hr = method(dialog, 3, wt.HWND)(dialog, user32.GetForegroundWindow())
        if hr & 0xFFFFFFFF == 0x800704C7:  # cancelled
            return []
        ok(hr, "Show")
        results = ctypes.c_void_p()
        ok(method(dialog, 27, ctypes.POINTER(ctypes.c_void_p))(dialog, ctypes.byref(results)), "GetResults")
        try:
            count = ctypes.c_ulong()
            method(results, 7, ctypes.POINTER(ctypes.c_ulong))(results, ctypes.byref(count))
            paths = []
            for i in range(count.value):
                item = ctypes.c_void_p()
                ok(method(results, 8, ctypes.c_ulong, ctypes.POINTER(ctypes.c_void_p))(results, i, ctypes.byref(item)),
                   "GetItemAt")
                try:
                    paths.append(path_of(item))
                finally:
                    release(item)
            return paths
        finally:
            release(results)
    finally:
        release(dialog)
        ole32.CoUninitialize()


# ------------------------------------------------------------------ macOS / Linux

def _mac(mode, start, title):
    loc = f' default location (POSIX file "{start}")' if start and os.path.isdir(start) else ""
    prompt = f' with prompt "{title}"' if title else ""
    if mode == "folder":
        script = f"POSIX path of (choose folder{prompt}{loc})"
    else:
        script = (f"set picked to choose file{prompt}{loc} with multiple selections allowed\n"
                  "set out to \"\"\nrepeat with f in picked\nset out to out & POSIX path of f & linefeed\nend repeat\n"
                  "return out")
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:  # cancelled
        return []
    return [p.rstrip("/") if mode == "folder" else p for p in r.stdout.splitlines() if p.strip()]


def _linux(mode, start, title, filters):
    start = (start.rstrip("/") + "/") if start and os.path.isdir(start) else ""
    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", "--separator=\n", f"--title={title or 'Select'}"]
        cmd += ["--directory"] if mode == "folder" else ["--multiple"] + [f"--file-filter={n} | {s}" for n, s in filters]
        if start:
            cmd.append(f"--filename={start}")
    elif shutil.which("kdialog"):
        if mode == "folder":
            cmd = ["kdialog", "--getexistingdirectory", start or os.path.expanduser("~")]
        else:
            cmd = ["kdialog", "--getopenfilename", start or os.path.expanduser("~"),
                   " ".join(s.replace(";", " ") for _, s in filters[:1]), "--multiple", "--separate-output"]
    else:
        raise Unavailable("No system file dialog found (install zenity or kdialog) — type the path instead")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [p for p in r.stdout.splitlines() if p.strip()]
