import asyncio
import json
import logging
import os
import threading
import urllib.error
import urllib.request

import folder_paths
from aiohttp import web
from server import PromptServer

from . import password_auth
from . import pty_session

routes = PromptServer.instance.routes
_logger = logging.getLogger(__name__)

# Cloudflare in front of static.champdev.in blocks urllib's default UA (see
# telemetry.py's fix for the same host class) — send a non-default one.
_USER_AGENT = "champdev-comfyui-terminal"

# Same two models the endpoint-service provision workflow installs
# (../endpoint-service/src/modules/provision/service.ts MODELS), kept in sync
# by hand since this pack has no dependency on that repo.
_BOOTSTRAP_MODELS = [
    {"folder": "loras", "filename": "zit_x.safetensors", "url": "https://static.champdev.in/zit_x.safetensors"},
    {
        "folder": "checkpoints",
        "filename": "z-image-turbo-fp8-aio.safetensors",
        "url": "https://huggingface.co/SeeSee21/Z-Image-Turbo-AIO/resolve/main/z-image-turbo-fp8-aio.safetensors",
    },
]


def _model_dir(folder_key):
    dirs = folder_paths.get_folder_paths(folder_key)
    target = dirs[0] if dirs else os.path.join(folder_paths.models_dir, folder_key)
    os.makedirs(target, exist_ok=True)
    return target


def _download_file(url, dest, attempts=3):
    partial = dest + ".partial"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp, open(partial, "wb") as fh:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
            if os.path.getsize(partial) < 1024:
                raise urllib.error.URLError("download too small — not a model file?")
            os.replace(partial, dest)
            return
        except Exception:
            if os.path.exists(partial):
                os.remove(partial)
            if attempt == attempts:
                raise


def _ensure_bootstrap_models():
    # No OS branch needed here: folder_paths already resolves the right models
    # dir per-OS, and urllib downloads work the same on every platform — unlike
    # the endpoint-service's remote-shell path, which has to pick bash vs
    # PowerShell because it runs the download *inside* a shell over the wire.
    for spec in _BOOTSTRAP_MODELS:
        dest = os.path.join(_model_dir(spec["folder"]), spec["filename"])
        if os.path.isfile(dest) and os.path.getsize(dest) > 1024:
            continue
        _logger.info("champdev terminal: downloading model %s...", spec["filename"])
        try:
            _download_file(spec["url"], dest)
            _logger.info("champdev terminal: %s downloaded", spec["filename"])
        except Exception as e:
            _logger.warning("champdev terminal: failed to download %s: %s", spec["filename"], e)


# Runs once per ComfyUI process, off the startup path — models can be GBs and
# must never delay node registration. Never let this break node loading.
try:
    threading.Thread(target=_ensure_bootstrap_models, daemon=True).start()
except Exception as e:
    _logger.debug("champdev terminal: model bootstrap skipped: %s", e)


@routes.get("/champdev/terminal/ws")
async def terminal_ws(request):
    # No shell is spawned unless the session is unlocked with the password.
    if not password_auth.is_authed(request):
        return web.json_response({"error": "unauthorized"}, status=401)

    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    q = request.query
    try:
        cols = int(q.get("cols", 80))
        rows = int(q.get("rows", 24))
    except ValueError:
        cols, rows = 80, 24
    shell = q.get("shell") or None
    cwd = q.get("cwd") or folder_paths.get_output_directory()

    session = pty_session.PtySession()
    try:
        session.spawn(shell=shell, cwd=cwd, cols=cols, rows=rows)
    except Exception as e:
        await ws.send_json({"type": "exit", "code": -1, "error": str(e)})
        await ws.close()
        return ws

    loop = asyncio.get_running_loop()
    stop = threading.Event()

    def _drain_future(fut):
        # Retrieve any exception so a closed-ws send doesn't log
        # "Future exception was never retrieved".
        if not fut.cancelled():
            fut.exception()

    def _safe_schedule(coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, loop)
        except RuntimeError:
            return
        fut.add_done_callback(_drain_future)

    def _reader():
        shell_exited = False
        while not stop.is_set():
            data = session.read(65536, timeout=0.2)
            if data:
                _safe_schedule(ws.send_bytes(data))
            elif not session.is_alive():
                shell_exited = True
                break
        # Only notify/close when the shell ended on its own; on a client
        # disconnect the socket is already gone.
        if shell_exited:
            _safe_schedule(ws.send_json({"type": "exit", "code": session.exit_code()}))
            _safe_schedule(ws.close())

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                except ValueError:
                    continue
                kind = payload.get("type")
                if kind == "input":
                    session.write(payload.get("data", "").encode("utf-8", "replace"))
                elif kind == "resize":
                    try:
                        session.resize(int(payload["cols"]), int(payload["rows"]))
                    except (KeyError, ValueError, TypeError):
                        pass
            elif msg.type == web.WSMsgType.ERROR:
                break
    finally:
        stop.set()
        session.terminate()

    return ws


class ChampdevTerminal:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "shell": ("STRING", {"default": ""}),
                "start_dir": ("STRING", {"default": folder_paths.get_output_directory()}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "noop"
    CATEGORY = "chamdev-nodes/utils"

    def noop(self, shell="", start_dir=""):
        return ()


NODE_CLASS_MAPPINGS = {"ChampdevTerminal": ChampdevTerminal}
NODE_DISPLAY_NAME_MAPPINGS = {"ChampdevTerminal": "Champdev Terminal"}
