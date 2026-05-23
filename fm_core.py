import hashlib
import os
import shutil

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


def _leaf_path(path):
    """Resolve the parent directory but keep the final component unresolved,
    so destructive operations act on a symlink itself, not its target."""
    if not path:
        raise ValueError("path is required")
    expanded = os.path.expanduser(path)
    parent = os.path.dirname(expanded) or "."
    return os.path.join(os.path.realpath(parent), os.path.basename(expanded))


def _next_available_path(path):
    index = 1
    candidate = path
    while os.path.exists(candidate):
        candidate = "{}_{}".format(path, "{:05d}".format(index))
        index += 1
    return candidate


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


def _reject_separators(name, label):
    if not name or os.path.sep in name or (os.path.altsep and os.path.altsep in name):
        raise ValueError("{} must be a bare name".format(label))
    if name in (".", ".."):
        raise ValueError("{} must not be '.' or '..'".format(label))


def rename_path(path, new_name):
    real = _leaf_path(path)
    _reject_separators(new_name, "new_name")
    target = os.path.join(os.path.dirname(real), new_name)
    if os.path.exists(target):
        raise FileExistsError(target)
    os.rename(real, target)
    return {"ok": True, "path": target}


def make_dir(parent, name):
    real_parent = safe_realpath(parent)
    _reject_separators(name, "name")
    target = os.path.join(real_parent, name)
    os.makedirs(target, exist_ok=False)
    return {"ok": True, "path": target}


def delete_paths(paths):
    results = []
    for p in paths:
        try:
            real = _leaf_path(p)
            if os.path.isdir(real) and not os.path.islink(real):
                shutil.rmtree(real)
            else:
                os.remove(real)
            results.append({"path": real, "ok": True})
        except OSError as e:
            results.append({"path": p, "ok": False, "error": str(e)})
    return results


def move_paths(paths, dest, copy=False):
    real_dest = safe_realpath(dest)
    if not os.path.isdir(real_dest):
        raise NotADirectoryError(real_dest)

    results = []
    for p in paths:
        try:
            real = _leaf_path(p)
            target = os.path.join(real_dest, os.path.basename(real))
            if os.path.exists(target):
                raise FileExistsError(target)
            if copy:
                if os.path.isdir(real):
                    shutil.copytree(real, target)
                else:
                    shutil.copy2(real, target)
            else:
                shutil.move(real, target)
            results.append({"path": real, "ok": True, "target": target})
        except OSError as e:
            results.append({"path": p, "ok": False, "error": str(e)})
    return results


def save_upload_bytes(dest, filename, data):
    real_dest = safe_realpath(dest)
    if not os.path.isdir(real_dest):
        raise NotADirectoryError(real_dest)
    safe_name = os.path.basename(filename or "")
    if not safe_name:
        raise ValueError("invalid filename")
    target = os.path.join(real_dest, safe_name)
    target = _next_available_path(target)
    with open(target, "wb") as f:
        f.write(data)
    return {"ok": True, "path": target}


def make_thumbnail(path, cache_dir, size=256):
    if Image is None:
        raise RuntimeError("PIL not available")
    cache_dir = os.path.realpath(os.path.expanduser(cache_dir))
    real = safe_realpath(path)
    if classify_kind(os.path.basename(real)) != "image":
        raise ValueError("not an image")
    st = os.stat(real)
    key = hashlib.sha1(f"{real}:{st.st_mtime}:{size}".encode()).hexdigest()
    os.makedirs(cache_dir, exist_ok=True)
    out = os.path.join(cache_dir, key + ".jpg")
    if os.path.exists(out):
        return out
    with Image.open(real) as im:
        im = im.convert("RGB")
        im.thumbnail((size, size))
        im.save(out, "JPEG", quality=85)
    return out


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
