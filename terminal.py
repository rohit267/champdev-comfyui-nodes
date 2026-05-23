import asyncio
import json
import threading

import folder_paths
from aiohttp import web
from server import PromptServer

from . import pty_session

routes = PromptServer.instance.routes


@routes.get("/champdev/terminal/ws")
async def terminal_ws(request):
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

    def _safe_schedule(coro):
        try:
            asyncio.run_coroutine_threadsafe(coro, loop)
        except RuntimeError:
            pass

    def _reader():
        while not stop.is_set():
            data = session.read(65536, timeout=0.2)
            if data:
                _safe_schedule(ws.send_bytes(data))
            elif not session.is_alive():
                break
        _safe_schedule(ws.send_json({"type": "exit", "code": session.exit_code()}))

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
