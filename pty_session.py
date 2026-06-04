import os
import signal

IS_WINDOWS = os.name == "nt"

if not IS_WINDOWS:
    import fcntl
    import pty
    import select
    import struct
    import termios


def default_shell():
    if os.name == "nt":
        return os.environ.get("COMSPEC") or "cmd.exe"
    shell = os.environ.get("SHELL")
    if shell:
        return shell
    for candidate in ("/bin/bash", "/bin/sh"):
        if os.path.exists(candidate):
            return candidate
    return "/bin/sh"


# Terminal types we prefer, best first. The frontend is xterm.js, which speaks
# xterm-256color; we fall back to plainer entries only if the richer ones are
# missing from the host's terminfo database (e.g. slim Linux/containers that
# ship only base terminfo), so the worst case is fewer colors rather than an
# "unknown terminal type" error.
_TERM_PREFERENCES = ("xterm-256color", "xterm-color", "xterm")


def _terminfo_has(name):
    """True if a compiled terminfo entry for `name` exists on disk.

    ncurses stores entries as ``<dir>/<first-char>/<name>`` (glibc/Linux) or
    ``<dir>/<2-hex>/<name>`` (macOS/BSD). We check both layouts across the
    standard search directories. A false negative only causes a fallback to a
    plainer-but-valid TERM, never an error.
    """
    if not name:
        return False
    first = name[0]
    subdirs = (first, "%02x" % ord(first))
    dirs = []
    env_dir = os.environ.get("TERMINFO")
    if env_dir:
        dirs.append(env_dir)
    home = os.environ.get("HOME")
    if home:
        dirs.append(os.path.join(home, ".terminfo"))
    for d in (os.environ.get("TERMINFO_DIRS") or "").split(os.pathsep):
        dirs.append(d or "/usr/share/terminfo")
    dirs += [
        "/usr/share/terminfo",
        "/lib/terminfo",
        "/etc/terminfo",
        "/usr/lib/terminfo",
        "/usr/share/lib/terminfo",
    ]
    for d in dirs:
        if not d:
            continue
        for sub in subdirs:
            if os.path.isfile(os.path.join(d, sub, name)):
                return True
    return False


def resolve_term():
    """Pick a TERM that matches the xterm.js frontend and exists on the host.

    On Windows the default cmd.exe/PowerShell ignore TERM (ConPTY + xterm.js
    handle VT directly), and bash/MSYS shells that do read terminfo ship
    xterm-256color, so we use it unconditionally there.
    """
    if IS_WINDOWS:
        return "xterm-256color"
    for name in _TERM_PREFERENCES:
        if _terminfo_has(name):
            return name
    # Nothing matched (unusual layout or near-empty DB) — best effort.
    return _TERM_PREFERENCES[0]


def _set_winsize_unix(fd, cols, rows):
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


class _UnixPty:
    def __init__(self):
        self.pid = None
        self.fd = None
        self._exit_code = None

    def spawn(self, shell, cwd, env, cols, rows):
        argv = [shell]
        pid, fd = pty.fork()
        if pid == 0:
            # Child process: become the shell.
            try:
                if cwd:
                    os.chdir(cwd)
                os.execvpe(argv[0], argv, env or os.environ.copy())
            except Exception:
                os._exit(127)
        # Parent.
        self.pid = pid
        self.fd = fd
        _set_winsize_unix(fd, cols, rows)

    def read(self, max_bytes, timeout):
        if self.fd is None:
            return b""
        try:
            ready, _, _ = select.select([self.fd], [], [], timeout)
        except (OSError, ValueError):
            return b""
        if not ready:
            return b""
        try:
            return os.read(self.fd, max_bytes)
        except OSError:
            return b""  # slave closed (EOF/EIO)

    def write(self, data):
        if self.fd is not None:
            try:
                os.write(self.fd, data)
            except OSError:
                pass

    def resize(self, cols, rows):
        if self.fd is not None:
            try:
                _set_winsize_unix(self.fd, cols, rows)
            except OSError:
                pass

    def is_alive(self):
        if self.pid is None:
            return False
        try:
            wpid, status = os.waitpid(self.pid, os.WNOHANG)
        except OSError:
            return False
        if wpid == 0:
            return True
        if os.WIFEXITED(status):
            self._exit_code = os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            self._exit_code = -os.WTERMSIG(status)
        return False

    def terminate(self):
        if self.pid is not None:
            try:
                os.killpg(self.pid, signal.SIGKILL)
            except OSError:
                try:
                    os.kill(self.pid, signal.SIGKILL)
                except OSError:
                    pass
            try:  # reap immediately and capture the exit status
                wpid, status = os.waitpid(self.pid, 0)
                if wpid == self.pid:
                    if os.WIFEXITED(status):
                        self._exit_code = os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        self._exit_code = -os.WTERMSIG(status)
            except OSError:
                pass
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        self.pid = None  # reaped; prevents a later kill on a recycled pid

    def exit_code(self):
        return self._exit_code


class _WinPty:
    """Windows ConPTY implementation backed by pywinpty."""

    def __init__(self):
        self._proc = None

    def spawn(self, shell, cwd, env, cols, rows):
        from winpty import PtyProcess  # lazy: only imported on Windows

        spawn_env = env or os.environ.copy()
        self._proc = PtyProcess.spawn(
            shell,
            cwd=cwd or None,
            env=spawn_env,
            dimensions=(rows, cols),
        )

    def read(self, max_bytes, timeout):
        if self._proc is None:
            return b""
        try:
            data = self._proc.read(max_bytes)  # returns str
        except EOFError:
            return b""
        except Exception:
            return b""
        if not data:
            return b""
        return data.encode("utf-8", "replace")

    def write(self, data):
        if self._proc is not None:
            try:
                self._proc.write(data.decode("utf-8", "replace"))
            except Exception:
                pass

    def resize(self, cols, rows):
        if self._proc is not None:
            try:
                self._proc.setwinsize(rows, cols)
            except Exception:
                pass

    def is_alive(self):
        return self._proc is not None and self._proc.isalive()

    def terminate(self):
        if self._proc is not None:
            try:
                self._proc.terminate(force=True)
            except Exception:
                pass

    def exit_code(self):
        if self._proc is None:
            return None
        return getattr(self._proc, "exitstatus", None)


class PtySession:
    """Cross-platform pseudo-terminal session facade."""

    def __init__(self):
        self._impl = _WinPty() if IS_WINDOWS else _UnixPty()

    def spawn(self, shell=None, cwd=None, env=None, cols=80, rows=24):
        spawn_env = dict(env) if env is not None else os.environ.copy()
        # The frontend is xterm.js, so declare a matching terminal type.
        # Otherwise the shell inherits whatever TERM ComfyUI was launched
        # with (unset, or e.g. "xterm-ghostty" whose terminfo may be absent),
        # and terminfo-aware programs fail with "unknown terminal type".
        spawn_env["TERM"] = resolve_term()
        self._impl.spawn(shell or default_shell(), cwd, spawn_env, int(cols), int(rows))

    def read(self, max_bytes=65536, timeout=None):
        return self._impl.read(max_bytes, timeout)

    def write(self, data):
        self._impl.write(data)

    def resize(self, cols, rows):
        self._impl.resize(int(cols), int(rows))

    def is_alive(self):
        return self._impl.is_alive()

    def terminate(self):
        self._impl.terminate()

    def exit_code(self):
        return self._impl.exit_code()
