import os

import folder_paths
from aiohttp import web
from server import PromptServer

from . import fm_core

routes = PromptServer.instance.routes


def _thumb_cache_dir():
    return os.path.join(folder_paths.get_temp_directory(), "champdev_fm_thumbs")


@routes.get("/champdev/fm/list")
async def fm_list(request):
    try:
        path = request.query.get("path") or folder_paths.get_output_directory()
        show_hidden = request.query.get("show_hidden") == "true"
        sort = request.query.get("sort", "name")
        return web.json_response(fm_core.list_dir(path, show_hidden, sort))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.get("/champdev/fm/file")
async def fm_file(request):
    try:
        real = fm_core.safe_realpath(request.query.get("path"))
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
        size = int(request.query.get("size", 256))
        out = fm_core.make_thumbnail(request.query.get("path"), _thumb_cache_dir(), size)
        return web.FileResponse(out)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.get("/champdev/fm/properties")
async def fm_properties(request):
    try:
        return web.json_response(fm_core.get_properties(request.query.get("path")))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/delete")
async def fm_delete(request):
    try:
        data = await request.json()
        return web.json_response({"results": fm_core.delete_paths(data.get("paths", []))})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/rename")
async def fm_rename(request):
    try:
        data = await request.json()
        return web.json_response(fm_core.rename_path(data["path"], data["new_name"]))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/mkdir")
async def fm_mkdir(request):
    try:
        data = await request.json()
        return web.json_response(fm_core.make_dir(data["path"], data["name"]))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.post("/champdev/fm/move")
async def fm_move(request):
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
