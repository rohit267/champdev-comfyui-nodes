# Changelog

All notable changes to this project will be documented in this file.

## 0.4.1
- Fix File Manager lazy loading: the node no longer renders every file on first
  load. A ComfyUI DOM widget is sized to its content, so the file `<table>` grew
  the node unbounded (and an over-eager "fill the viewport" loop then loaded all
  rows). The widget now takes its height from the node size instead of its
  content, so the list is a bounded scroll box that loads ~20 rows at a time and
  the node stays a sensible height (resize the node to grow the list).

## 0.4.0
- File Manager UX improvements (`ChampdevFM`):
  - Lazy, windowed rendering: only ~20 rows (and thumbnails) load at a time, with
    more loading automatically as you scroll — so large folders no longer try to
    generate every thumbnail at once.
  - The file list now scrolls inside the node instead of the node growing very
    long with many files.
  - Larger side preview that loads the **original** image (not a thumbnail), with
    a draggable divider to resize it; click the preview to open fullscreen.
  - Keyboard navigation: `↑`/`↓` move the selection through the list (updating the
    preview), `Enter` opens fullscreen.
  - Fullscreen viewer: `←`/`→` cycle through the previewable media in the current
    view (wrapping), with a filename/position caption.

## 0.3.1
- Fix terminal "unknown terminal type" errors: the PTY now sets `TERM` to match
  the xterm.js frontend instead of inheriting ComfyUI's launch environment. Picks
  the best terminal type present in the host's terminfo database
  (`xterm-256color` → `xterm-color` → `xterm`) so slim Linux/containers degrade
  to fewer colors rather than failing.

## 0.3.0
- Add `ChampdevTerminal` (Champdev Terminal) node: a full interactive terminal
  (xterm.js) backed by a real PTY on the server. Cross-platform (stdlib `pty` on
  macOS/Linux, `pywinpty` on Windows). Fresh shell per connection.

## 0.2.0
- Add `ChampdevFM` (Champdev File Manager) node: browse, preview, play, upload,
  download, rename, move/copy, delete, create folders, and view properties for
  any path on disk. Vanilla-JS UI; no new dependencies.

## [Unreleased]

### Added
- `Champdev Save video` node aligned with core Save Video behavior.
- Video node options matching image node behavior:
  - save to ComfyUI temp directory
  - overwrite existing file
  - fixed filename without increment
  - auto-delete output after N seconds

## [0.1.0] - 2026-02-28

### Added
- Initial `chamdev-nodes` ComfyUI node pack scaffold.
- `Champdev Save Image` output node.
- Option to save into ComfyUI temp directory.
- Option for fixed filename mode without counter suffix.
- Option to overwrite existing file in fixed filename mode.
- Option to auto-delete output image after configured seconds.
