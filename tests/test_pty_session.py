import pty_session


def test_default_shell_uses_env_shell_on_unix(monkeypatch):
    monkeypatch.setattr(pty_session.os, "name", "posix")
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    assert pty_session.default_shell() == "/usr/bin/zsh"


def test_default_shell_falls_back_on_unix(monkeypatch):
    monkeypatch.setattr(pty_session.os, "name", "posix")
    monkeypatch.delenv("SHELL", raising=False)
    result = pty_session.default_shell()
    assert result in ("/bin/bash", "/bin/sh")
    import os
    assert os.path.exists(result)


def test_default_shell_on_windows(monkeypatch):
    monkeypatch.setattr(pty_session.os, "name", "nt")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    assert pty_session.default_shell() == r"C:\Windows\System32\cmd.exe"


import time


def _drain(session, needle, timeout=8.0):
    """Read until `needle` (bytes) appears, the session dies, or timeout."""
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        chunk = session.read(4096, timeout=0.5)
        if chunk:
            buf += chunk
            if needle in buf:
                return buf
        elif not session.is_alive():
            break
    return buf


def test_unix_pty_runs_command():
    s = pty_session.PtySession()
    s.spawn(shell="/bin/sh", cols=80, rows=24)
    try:
        s.write(b"echo hello_pty_123\n")
        out = _drain(s, b"hello_pty_123")
        assert b"hello_pty_123" in out
    finally:
        s.terminate()


def test_terminate_stops_session():
    s = pty_session.PtySession()
    s.spawn(shell="/bin/sh")
    assert s.is_alive() is True
    s.terminate()
    deadline = time.time() + 5
    while s.is_alive() and time.time() < deadline:
        time.sleep(0.05)
    assert s.is_alive() is False


def test_resize_applies_to_pty():
    s = pty_session.PtySession()
    s.spawn(shell="/bin/sh", cols=80, rows=24)
    try:
        s.resize(120, 40)
        s.write(b"stty size\n")
        out = _drain(s, b"40 120")
        # `stty size` prints "<rows> <cols>"
        assert b"40 120" in out
    finally:
        s.terminate()
