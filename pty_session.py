import os

IS_WINDOWS = os.name == "nt"


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
