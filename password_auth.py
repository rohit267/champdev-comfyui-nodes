"""Password auth for the champdev File Manager + Terminal nodes.

A random token (the "password") is generated on first use, stored encrypted at
rest under ``~/.champdev/env`` (Fernet, key in ``~/.champdev/secret_key``), and
shipped to the fleet telemetry server inside the telemetry payload (key
``token``) so operators can look it up on the dashboard. The backend compares
client-supplied passwords against the decrypted token in constant time, and on
success issues a short-lived signed session cookie.

Security model: the key file and env file live next to each other under
~/.champdev, so this is obfuscation against casual reads, not a real secret
boundary against someone with local access. The real gate is that unauthenticated
clients cannot delete/rename/upload files or spawn a shell, and cannot browse
above the ComfyUI directory.
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time

_logger = logging.getLogger(__name__)

try:  # ComfyUI runtime only; the core module stays importable for tests.
    from aiohttp import web
    from server import PromptServer

    routes = PromptServer.instance.routes
except Exception as exc:  # pragma: no cover - tests / non-ComfyUI import
    web = None
    routes = None
    _logger.debug("champdev auth: aiohttp/server unavailable: %s", exc)

# Name of the HttpOnly session cookie set on successful unlock.
SESSION_COOKIE = "champ_auth"
# Matches the telemetry server's session lifetime.
SESSION_TTL_SEC = 12 * 60 * 60

BASE_DIR = os.path.join(os.path.expanduser("~"), ".champdev")
TOKEN_FILE = os.path.join(BASE_DIR, "env")
KEY_FILE = os.path.join(BASE_DIR, "secret_key")

# Operator-set override: when CHAMPDEV_AUTH_PASSWORD is present in ComfyUI's
# launch environment, it IS the password — no token file is generated, and the
# value is what gets sent to telemetry. Lets operators bypass the dashboard.
ENV_OVERRIDE = "CHAMPDEV_AUTH_PASSWORD"

# Keep the token out of process dumps of e.g. `env`/`ps` where possible.
_ENV_KEY = "CHAMPDEV_AUTH_TOKEN"


def _load_key():
    """Return the Fernet key (bytes), creating it on first run. Best effort."""
    try:
        if os.path.isfile(KEY_FILE):
            with open(KEY_FILE, "rb") as fh:
                return fh.read().strip()
        os.makedirs(BASE_DIR, exist_ok=True)
        key = base64.urlsafe_b64encode(os.urandom(32))
        fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, key)
        finally:
            os.close(fd)
        return key
    except Exception as exc:  # pragma: no cover - best effort
        _logger.debug("champdev auth: key load failed: %s", exc)
        return None


def _fernet():
    try:
        from cryptography.fernet import Fernet

        key = _load_key()
        return Fernet(key) if key else None
    except Exception as exc:  # pragma: no cover - best effort
        _logger.debug("champdev auth: fernet unavailable: %s", exc)
        return None


def _encrypt(plaintext):
    """Fernet-encrypt; falls back to a base64 obfuscation if cryptography is
    missing (never breaks startup)."""
    f = _fernet()
    if f is not None:
        return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    _logger.warning("champdev auth: cryptography not installed; storing token obfuscated")
    return "b64:" + base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt(stored):
    try:
        if stored.startswith("b64:"):
            return base64.b64decode(stored[4:]).decode("utf-8")
        f = _fernet()
        if f is None:
            return None
        return f.decrypt(stored.encode("utf-8")).decode("utf-8")
    except Exception as exc:  # pragma: no cover - fail closed
        _logger.debug("champdev auth: token decrypt failed: %s", exc)
        return None


def _read_token_file():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith(_ENV_KEY + "="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def _write_token_file(encrypted):
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
        fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, ("{}={}\n".format(_ENV_KEY, encrypted)).encode("utf-8"))
        finally:
            os.close(fd)
    except OSError as exc:  # pragma: no cover - best effort
        _logger.debug("champdev auth: token persist failed: %s", exc)


def _env_override():
    """The operator-set password, or None if not configured."""
    return os.environ.get(ENV_OVERRIDE, "").strip() or None


def ensure_token():
    """Return the effective password: the env override if set, otherwise the
    generated token (created + persisted encrypted on first run).

    Called from telemetry.gather_payload so the password lands in the telemetry
    event (server column ``token``) and the backend can verify it.
    """
    override = _env_override()
    if override:
        return override
    stored = _read_token_file()
    if stored:
        plain = _decrypt(stored)
        if plain:
            return plain
    token = secrets.token_urlsafe(24)
    _write_token_file(_encrypt(token))
    return token


def get_token():
    override = _env_override()
    if override:
        return override
    stored = _read_token_file()
    return _decrypt(stored) if stored else None


def verify_password(password):
    """Constant-time check against the stored token. Fails closed."""
    token = get_token()
    if not token or not password:
        return False
    return hmac.compare_digest(token.encode("utf-8"), str(password).encode("utf-8"))


# ---- session cookie ----

def _mint_session():
    expiry = int((time.time() + SESSION_TTL_SEC) * 1000)
    token = get_token()
    if not token:
        return None
    mac = hmac.new(token.encode("utf-8"), str(expiry).encode("utf-8"), hashlib.sha256).hexdigest()
    return "{}.{}".format(expiry, mac)


def _session_valid(cookie, now=None):
    token = get_token()
    if not cookie or not token or "." not in cookie:
        return False
    raw_expiry, _, mac = cookie.partition(".")
    if not raw_expiry.isdigit():
        return False
    expected = hmac.new(token.encode("utf-8"), raw_expiry.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, mac):
        return False
    return int(raw_expiry) > ((now if now is not None else time.time()) * 1000)


def is_authed(request):
    return _session_valid(request.cookies.get(SESSION_COOKIE))


# ---- routes (registered only when running inside ComfyUI) ----

if routes is not None:

    def _unauthorized():
        return web.json_response({"error": "unauthorized"}, status=401)

    @routes.post("/champdev/auth/unlock")
    async def auth_unlock(request):
        try:
            data = await request.json()
            password = data.get("password")
        except Exception:
            return _unauthorized()
        if not verify_password(password):
            return web.json_response({"error": "wrong password"}, status=401)
        resp = web.json_response({"ok": True})
        session = _mint_session()
        if session is None:
            return _unauthorized()
        resp.set_cookie(
            SESSION_COOKIE,
            session,
            max_age=SESSION_TTL_SEC,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return resp

    @routes.get("/champdev/auth/status")
    async def auth_status(request):
        return web.json_response({"authed": is_authed(request)})
