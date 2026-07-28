# chamdev-nodes

Custom ComfyUI node pack by chamdev.

## Nodes

### Champdev Save Image
Save-image output node compatible with ComfyUI's standard image flow, with extra controls for temporary output and filename handling.

Inputs:
- `images` (`IMAGE`)
- `filename_prefix` (`STRING`)
- `save_to_comfy_temp_dir` (`BOOLEAN`): saves to ComfyUI temp directory instead of output directory.
- `overwrite_existing` (`BOOLEAN`): when fixed filename mode is on, overwrite existing file instead of auto-increment fallback.
- `fixed_filename_no_increment` (`BOOLEAN`): save using a fixed filename (no default counter suffix).
- `auto_delete_after_seconds` (`INT`): delete saved file after N seconds (`0` disables).

### Champdev Save video
Save-video output node that follows core Save Video behavior (takes a `VIDEO` input and saves via Comfy's video pipeline), with extra file-handling options.

Inputs:
- `video` (`VIDEO`)
- `filename_prefix` (`STRING`)
- `format` (`auto` + core-supported containers)
- `codec` (`auto` + core-supported codecs)
- `save_to_comfy_temp_dir` (`BOOLEAN`)
- `overwrite_existing` (`BOOLEAN`)
- `fixed_filename_no_increment` (`BOOLEAN`)
- `auto_delete_after_seconds` (`INT`)

### Champdev File Manager
A utility node (`ChampdevFM`) that embeds a file manager in its body. Browse any
folder on the machine running ComfyUI, preview images, play video/audio, and
manage files.

Widgets:
- `start_path` (`STRING`): folder the manager opens at (defaults to the output directory).
- `show_hidden` (`BOOLEAN`): show dotfiles.

Features: editable path bar (Enter to jump anywhere), up/refresh, filter, sortable
columns, multi-select, a resizable side preview that shows the **original** image
(click it for full screen), full-screen preview for images/video/audio with
`←`/`→` to step through them, and these operations — upload (button or
drag-and-drop), download, rename, move, copy, new folder, delete (with
confirmation), and properties.

Keyboard: with the list focused, `↑`/`↓` move the selection (the preview updates)
and `Enter` opens full screen; `Esc` closes it. Large folders load lazily —
rows and their thumbnails are fetched ~20 at a time as you scroll, and the list
scrolls inside the node.

> ⚠️ **Security:** this node can read, rename, move, and **delete files anywhere
> the ComfyUI server process can access**. It is meant for **local, single-user**
> use only. Do **not** enable it on a ComfyUI instance exposed to a network
> (`--listen`, reverse proxy, or shared host): anyone who can reach the UI could
> delete or exfiltrate arbitrary files. Use at your own risk.

### Champdev Terminal
A utility node (`ChampdevTerminal`) that embeds a full interactive terminal in its
body, backed by a real pseudo-terminal on the machine running ComfyUI. Supports
interactive programs (vim, top), ANSI colors, and resizing.

Widgets:
- `shell` (`STRING`): shell to launch (default empty = auto-detect — `$SHELL` or
  `/bin/bash`/`/bin/sh` on macOS/Linux; on Windows, PowerShell (`pwsh.exe`, then
  the built-in `powershell.exe`), falling back to `cmd.exe`).
- `start_dir` (`STRING`): working directory the shell starts in (defaults to the
  output directory).

The shell session is fresh per connection: it starts when the terminal connects
and is killed when you close/reload (the ⟳ Restart button starts a new shell).
macOS/Linux use the Python standard library (no extra dependency); Windows
requires the `pywinpty` package (see [Installation](#installation) — installed
from `requirements.txt`).

> ⚠️ **Security:** this node opens a **fully interactive shell on the machine
> running ComfyUI** — arbitrary command execution by design. It is for **local,
> single-user** use only. Do **not** enable it on a network-exposed ComfyUI
> (`--listen`, reverse proxy, or shared host): anyone who can reach the UI gets a
> shell on your machine. Use at your own risk.

## Installation

Easiest: install via **ComfyUI-Manager**, which installs dependencies for you.

To install manually, clone into your ComfyUI custom nodes directory and install
the dependencies with the **same Python that runs ComfyUI**:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/rohit267/chamdev-comfyui-nodes.git
cd chamdev-comfyui-nodes
# ComfyUI portable: use python_embeded\python.exe instead of `python`
python -m pip install -r requirements.txt
```

Restart ComfyUI.

> macOS/Linux have no dependencies (the terminal uses the Python standard
> library). On Windows the terminal needs `pywinpty`; the command above (and
> ComfyUI-Manager) installs it. If it's missing, the terminal shows the exact
> `pip install` command to run.

## Compatibility

- Python 3.10+
- ComfyUI (recent versions)

## License

MIT. See [LICENSE](./LICENSE).
