import os

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
TEXT_EXTS = {".txt", ".json", ".yaml", ".yml", ".md", ".csv", ".log", ".py", ".js"}


def safe_realpath(path):
    if not path:
        raise ValueError("path is required")
    return os.path.realpath(os.path.expanduser(path))


def classify_kind(name):
    ext = os.path.splitext(name)[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in TEXT_EXTS:
        return "text"
    return "other"


def _entry(path):
    st = os.stat(path)
    is_dir = os.path.isdir(path)
    name = os.path.basename(path)
    return {
        "name": name,
        "path": path,
        "is_dir": is_dir,
        "size": 0 if is_dir else st.st_size,
        "mtime": st.st_mtime,
        "ctime": st.st_ctime,
        "ext": "" if is_dir else os.path.splitext(name)[1].lower(),
        "kind": "folder" if is_dir else classify_kind(name),
    }


_SORT_KEYS = {
    "name": lambda e: e["name"].lower(),
    "size": lambda e: e["size"],
    "mtime": lambda e: e["mtime"],
    "kind": lambda e: e["kind"],
}


def list_dir(path, show_hidden=False, sort="name"):
    real = safe_realpath(path)
    if not os.path.exists(real):
        raise FileNotFoundError(real)
    if not os.path.isdir(real):
        raise NotADirectoryError(real)

    entries = []
    for name in os.listdir(real):
        if not show_hidden and name.startswith("."):
            continue
        try:
            entries.append(_entry(os.path.join(real, name)))
        except OSError:
            continue  # skip unreadable entries

    key = _SORT_KEYS.get(sort, _SORT_KEYS["name"])
    entries.sort(key=lambda e: (not e["is_dir"], key(e)))

    parent = os.path.dirname(real)
    return {
        "cwd": real,
        "parent": None if parent == real else parent,
        "entries": entries,
    }


def get_properties(path):
    real = safe_realpath(path)
    if not os.path.exists(real):
        raise FileNotFoundError(real)
    info = _entry(real)
    if info["kind"] == "image" and Image is not None:
        try:
            with Image.open(real) as im:
                info["width"], info["height"] = im.size
        except Exception:
            pass
    return info
