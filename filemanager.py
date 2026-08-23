import os

import folder_paths
from aiohttp import web
from server import PromptServer

from . import fm_core
from . import password_auth

routes = PromptServer.instance.routes

# Browse root while locked: the ComfyUI install directory. Everything above it
# (home dirs, /etc, ...) requires the password.
BROWSE_ROOT = getattr(folder_paths, "base_path", None) or folder_paths.get_output_directory()


def _thumb_cache_dir():
    return os.path.join(folder_paths.get_temp_directory(), "champdev_fm_thumbs")


def _clamp_to_root(path):
    """While locked, pin a requested path inside BROWSE_ROOT instead of 403ing,
    so the FM always shows files down to the ComfyUI root."""
    real = fm_core.safe_realpath(path)
    root = os.path.realpath(BROWSE_ROOT)
    if real == root or real.startswith(root + os.sep):
        return real, False
    # Common path with root — move down into the deepest allowed ancestor.
    common = os.path.commonpath([real, root])
    if common == root:
        return root, True
    if common.startswith(root + os.sep):
        return common, True
    # Completely unrelated path → fall back to root itself.
    return root, True


def _browse_denied():
    return web.json_response({"error": "unlock to browse outside ComfyUI"}, status=403)


@routes.get("/champdev/fm/list")
async def fm_list(request):
    try:
        path = request.query.get("path") or folder_paths.get_output_directory()
        clamped = False
        if not password_auth.is_authed(request):
            path, clamped = _clamp_to_root(path)
        show_hidden = request.query.get("show_hidden") == "true"
        sort = request.query.get("sort", "name")
        res = fm_core.list_dir(path, show_hidden, sort)
        if clamped:
            res["clamped"] = True
        return web.json_response(res)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.get("/champdev/fm/file")
async def fm_file(request):
    try:
        path = request.query.get("path")
        if not password_auth.is_authed(request) and not _inside_root(path):
            return _browse_denied()
        real = fm_core.safe_realpath(path)
        if not os.path.isfile(real):
            return web.json_response({"error": "not a file"}, status=404)
        headers = {}
        if request.query.get("download") == "1":
            safe_name = (
                os.path.basename(real)
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\r", "")
                .replace("\n", "")
            )
            headers["Content-Disposition"] = f'attachment; filename="{safe_name}"'
        return web.FileResponse(real, headers=headers)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.get("/champdev/fm/thumbnail")
async def fm_thumbnail(request):
    try:
        if not password_auth.is_authed(request) and not _inside_root(request.query.get("path")):
            return _browse_denied()
        size = int(request.query.get("size", 256))
        out = fm_core.make_thumbnail(request.query.get("path"), _thumb_cache_dir(), size)
        return web.FileResponse(out)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.get("/champdev/fm/properties")
async def fm_properties(request):
    try:
        if not password_auth.is_authed(request) and not _inside_root(request.query.get("path")):
            return _browse_denied()
        return web.json_response(fm_core.get_properties(request.query.get("path")))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/delete")
async def fm_delete(request):
    if not password_auth.is_authed(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        data = await request.json()
        return web.json_response({"results": fm_core.delete_paths(data.get("paths", []))})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/rename")
async def fm_rename(request):
    if not password_auth.is_authed(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        data = await request.json()
        return web.json_response(fm_core.rename_path(data["path"], data["new_name"]))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/mkdir")
async def fm_mkdir(request):
    if not password_auth.is_authed(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        data = await request.json()
        return web.json_response(fm_core.make_dir(data["path"], data["name"]))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/move")
async def fm_move(request):
    if not password_auth.is_authed(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        data = await request.json()
        results = fm_core.move_paths(
            data.get("paths", []), data["dest"], data.get("copy", False)
        )
        return web.json_response({"results": results})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/upload")
async def fm_upload(request):
    if not password_auth.is_authed(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        reader = await request.multipart()
        dest = folder_paths.get_output_directory()
        results = []
        async for part in reader:
            if part.name == "dest":
                dest = (await part.text()).strip() or dest
            elif part.name == "files":
                data = await part.read()
                results.append(fm_core.save_upload_bytes(dest, part.filename, data))
        return web.json_response({"results": results})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


class ChampdevFM:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "start_path": ("STRING", {"default": folder_paths.get_output_directory()}),
                "show_hidden": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "noop"
    CATEGORY = "chamdev-nodes/utils"

    def noop(self, start_path="", show_hidden=False):
        return ()


NODE_CLASS_MAPPINGS = {"ChampdevFM": ChampdevFM}
NODE_DISPLAY_NAME_MAPPINGS = {"ChampdevFM": "Champdev File Manager"}
