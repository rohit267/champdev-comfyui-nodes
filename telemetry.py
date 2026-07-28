"""Fleet telemetry client for champdev-comfyui-nodes.

Fires once per ComfyUI process (from ``__init__.py`` on import): gathers device
specs + the ComfyUI bind port on a daemon thread, POSTs one JSON event to the
telemetry server, then exits. Every path is exception-swallowed — telemetry must
never break or slow down ComfyUI startup.

These nodes run on org-controlled fleet machines, so collection is silent and
always-on. Toggle off for debugging with ``CHAMPDEV_TELEMETRY=0``; point at a
different server with ``CHAMPDEV_TELEMETRY_URL``.
"""

import json
import logging
import os
import platform
import socket
import subprocess
import threading
import uuid
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

# Replace with the real telemetry server host before deploying to the fleet.
DEFAULT_TELEMETRY_URL = "https://comfy-nodes-telemetry.champdev.in"

_TIMEOUT_SECONDS = 3
_MAX_BODY_BYTES = 16 * 1024

# Identify with a custom User-Agent. The default urllib UA ("Python-urllib/x.y")
# is blocked by Cloudflare bot protection (403) in front of the telemetry server,
# so requests must send a non-default UA to get through.
_USER_AGENT = "champdev-comfyui-telemetry"

# Module-level guard so we only ever send once per process, no matter how many
# nodes import us.
_sent = False
_sent_lock = threading.Lock()


def _telemetry_disabled():
    val = os.environ.get("CHAMPDEV_TELEMETRY", "").strip().lower()
    return val in ("0", "false", "off", "no")


def _server_url():
    return os.environ.get("CHAMPDEV_TELEMETRY_URL", "").strip() or DEFAULT_TELEMETRY_URL


def _install_id():
    """Stable per-machine UUID persisted under ~/.champdev/install_id."""
    try:
        base = os.path.join(os.path.expanduser("~"), ".champdev")
        path = os.path.join(base, "install_id")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                existing = fh.read().strip()
                if existing:
                    return existing
        os.makedirs(base, exist_ok=True)
        new_id = str(uuid.uuid4())
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_id)
        return new_id
    except Exception:  # pragma: no cover - best effort
        return None


def _private_ip():
    """Primary LAN/private IP of this machine (no packets are actually sent)."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))  # picks the outbound interface; sends nothing
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:  # pragma: no cover - best effort
            return None
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:  # pragma: no cover
                pass


def _public_ip():
    """Internet-facing IP via a best-effort external echo service."""
    url = os.environ.get("CHAMPDEV_PUBLIC_IP_URL", "").strip() or "https://api.ipify.org"
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as resp:
            ip = resp.read(64).decode("utf-8").strip()
            return ip or None
    except Exception:  # pragma: no cover - network best effort
        return None


def _pack_version():
    try:
        from . import __version__

        return __version__
    except Exception:  # pragma: no cover - best effort
        return None


def _comfy_port_and_listen():
    """Best-effort ComfyUI bind port + listen address."""
    try:
        from comfy.cli_args import args

        port = getattr(args, "port", None)
        listen = getattr(args, "listen", None)
        if port is not None or listen is not None:
            return port, listen
    except Exception:  # pragma: no cover - comfy not importable in tests
        pass
    try:
        from server import PromptServer

        inst = PromptServer.instance
        return getattr(inst, "port", None), getattr(inst, "address", None)
    except Exception:  # pragma: no cover
        return None, None


def _comfy_version():
    try:
        import comfyui_version

        return getattr(comfyui_version, "__version__", None)
    except Exception:  # pragma: no cover
        pass
    try:
        import comfy

        return getattr(comfy, "__version__", None)
    except Exception:  # pragma: no cover
        return None


def _ram_gb():
    try:
        import psutil

        return round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except Exception:
        pass
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            total = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
            return round(total / (1024 ** 3), 2)
    except Exception:
        pass
    try:  # Windows fallback
        import ctypes

        class _MemStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MemStatus()
        stat.dwLength = ctypes.sizeof(_MemStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return round(stat.ullTotalPhys / (1024 ** 3), 2)
    except Exception:  # pragma: no cover
        return None


def _cpu_model():
    try:
        proc = platform.processor()
        if proc:
            return proc
    except Exception:
        pass
    try:
        if os.path.isfile("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except Exception:  # pragma: no cover
        pass
    return None


def _gpu():
    """(gpu_name, vram_gb) best-effort via torch, then nvidia-smi."""
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            vram = round(props.total_memory / (1024 ** 3), 2)
            return name, vram
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip():
            first = out.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in first.split(",")]
            name = parts[0] if parts else None
            vram = None
            if len(parts) > 1:
                try:
                    vram = round(float(parts[1]) / 1024, 2)
                except ValueError:
                    vram = None
            return name, vram
    except Exception:  # pragma: no cover
        pass
    return None, None


def gather_payload():
    """Collect the telemetry event. Never raises."""
    port, listen = _comfy_port_and_listen()
    gpu_name, vram_gb = _gpu()
    payload = {
        "install_id": _install_id(),
        "event_ts": datetime.now(timezone.utc).isoformat(),
        "comfy_port": port,
        "comfy_listen": listen,
        "private_ip": _private_ip(),
        "public_ip": _public_ip(),
        "os": _safe(platform.system),
        "os_release": _safe(platform.release),
        "os_version": _safe(platform.version),
        "arch": _safe(platform.machine),
        "hostname": _safe(socket.gethostname),
        "python_version": _safe(platform.python_version),
        "comfy_version": _comfy_version(),
        "pack_version": _pack_version(),
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "ram_gb": _ram_gb(),
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
    }
    return payload


def _safe(fn):
    try:
        return fn()
    except Exception:  # pragma: no cover
        return None


def _post(url, payload):
    import urllib.request

    body = json.dumps(payload).encode("utf-8")
    if len(body) > _MAX_BODY_BYTES:  # pragma: no cover - payload is tiny
        return
    version = _pack_version() or "0"
    req = urllib.request.Request(
        url.rstrip("/") + "/ingest",
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "{}/{}".format(_USER_AGENT, version),
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS).close()


def _run():
    try:
        _post(_server_url(), gather_payload())
    except Exception as exc:  # pragma: no cover - network best effort
        _logger.debug("champdev telemetry send failed: %s", exc)


def maybe_send():
    """Fire telemetry once per process on a daemon thread. Returns immediately."""
    global _sent
    try:
        if _telemetry_disabled():
            return
        with _sent_lock:
            if _sent:
                return
            _sent = True
        threading.Thread(target=_run, name="champdev-telemetry", daemon=True).start()
    except Exception as exc:  # pragma: no cover - never break import
        _logger.debug("champdev telemetry skipped: %s", exc)
