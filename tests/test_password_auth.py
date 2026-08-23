import time

import password_auth


def test_ensure_token_creates_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))

    token = password_auth.ensure_token()
    assert token and len(token) >= 20

    # A second call returns the same token (persisted, not regenerated).
    assert password_auth.ensure_token() == token
    assert password_auth.get_token() == token


def test_token_file_does_not_contain_plaintext(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))

    token = password_auth.ensure_token()
    raw = (tmp_path / "env").read_text(encoding="utf-8")
    assert token not in raw


def test_verify_password(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))

    token = password_auth.ensure_token()
    assert password_auth.verify_password(token) is True
    assert password_auth.verify_password("wrong") is False
    assert password_auth.verify_password("") is False
    assert password_auth.verify_password(None) is False


def test_fails_closed_without_token(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))

    assert password_auth.get_token() is None
    assert password_auth.verify_password("anything") is False
    assert password_auth._session_valid("123.abc") is False


def test_session_cookie_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))

    token = password_auth.ensure_token()
    cookie = password_auth._mint_session()
    assert cookie and "." in cookie
    assert password_auth._session_valid(cookie) is True
    assert password_auth._session_valid("tampered." + cookie.split(".", 1)[1]) is False
    assert password_auth._session_valid(cookie.split(".", 1)[0] + ".badmac") is False


def test_session_cookie_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))

    password_auth.ensure_token()
    cookie = password_auth._mint_session()
    now = time.time() + password_auth.SESSION_TTL_SEC * 2
    assert password_auth._session_valid(cookie, now=now) is False


def test_env_override_is_effective_password(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))
    monkeypatch.setenv("CHAMPDEV_AUTH_PASSWORD", "op-secret")

    # The override is what ensure_token returns (sent to telemetry)...
    assert password_auth.ensure_token() == "op-secret"
    # ...no token file is generated...
    assert not (tmp_path / "env").exists()
    # ...and verification + session signing use it.
    assert password_auth.verify_password("op-secret") is True
    assert password_auth.verify_password("generated") is False
    cookie = password_auth._mint_session()
    assert password_auth._session_valid(cookie) is True


def test_env_override_fallback_to_generated(tmp_path, monkeypatch):
    monkeypatch.setattr(password_auth, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(password_auth, "TOKEN_FILE", str(tmp_path / "env"))
    monkeypatch.setattr(password_auth, "KEY_FILE", str(tmp_path / "secret_key"))
    monkeypatch.delenv("CHAMPDEV_AUTH_PASSWORD", raising=False)

    token = password_auth.ensure_token()
    assert token and len(token) >= 20
    assert (tmp_path / "env").exists()
    assert password_auth.verify_password(token) is True
