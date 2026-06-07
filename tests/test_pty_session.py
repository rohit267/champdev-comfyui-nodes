import builtins

import pytest

import pty_session


def test_winpty_missing_gives_actionable_error(monkeypatch):
    # On Windows without pywinpty installed, spawning must fail with a clear,
    # actionable message (telling the user how to install pywinpty), not the
    # cryptic "No module named 'winpty'" that bubbled straight to the UI.
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "winpty":
            raise ImportError("No module named 'winpty'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    impl = pty_session._WinPty()
    with pytest.raises(RuntimeError) as excinfo:
        impl.spawn(r"C:\Windows\System32\cmd.exe", None, None, 80, 24)
    msg = str(excinfo.value)
    assert "pywinpty" in msg
    assert "pip install" in msg


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
    assert s.exit_code() == -9  # killed by SIGKILL


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


def test_pty_overrides_inherited_term_for_xtermjs(monkeypatch):
    # The frontend is xterm.js, so the shell must NOT inherit whatever TERM
    # ComfyUI was launched with (here a bogus value that has no terminfo entry,
    # which is what triggers "unknown terminal type"). It should instead get a
    # valid, host-resolved xterm TERM.
    monkeypatch.setenv("TERM", "totally-bogus-term-xyz")
    expected = pty_session.resolve_term()
    needle = ("TERMIS:%s:END" % expected).encode()
    s = pty_session.PtySession()
    s.spawn(shell="/bin/sh", cols=80, rows=24)
    try:
        s.write(b'printf "TERMIS:%s:END\\n" "$TERM"\n')
        out = _drain(s, needle)
        assert needle in out
        assert b"totally-bogus-term-xyz" not in out
    finally:
        s.terminate()


def test_resolve_term_prefers_256color(monkeypatch):
    monkeypatch.setattr(pty_session, "IS_WINDOWS", False)
    monkeypatch.setattr(pty_session, "_terminfo_has", lambda name: True)
    assert pty_session.resolve_term() == "xterm-256color"


def test_resolve_term_falls_back_when_256color_missing(monkeypatch):
    # Simulate a slim Linux/container with only the base "xterm" entry.
    monkeypatch.setattr(pty_session, "IS_WINDOWS", False)
    monkeypatch.setattr(pty_session, "_terminfo_has", lambda name: name == "xterm")
    assert pty_session.resolve_term() == "xterm"


def test_resolve_term_best_effort_when_db_empty(monkeypatch):
    monkeypatch.setattr(pty_session, "IS_WINDOWS", False)
    monkeypatch.setattr(pty_session, "_terminfo_has", lambda name: False)
    assert pty_session.resolve_term() == "xterm-256color"


def test_resolve_term_windows_uses_256color(monkeypatch):
    monkeypatch.setattr(pty_session, "IS_WINDOWS", True)
    assert pty_session.resolve_term() == "xterm-256color"


def test_terminfo_has_detects_present_and_absent(monkeypatch):
    # xterm should exist anywhere a usable terminfo DB is installed (the CI/dev
    # host running this suite). A made-up name must not.
    assert pty_session._terminfo_has("xterm") is True
    assert pty_session._terminfo_has("no-such-terminal-xyz") is False
