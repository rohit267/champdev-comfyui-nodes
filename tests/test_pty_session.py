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
