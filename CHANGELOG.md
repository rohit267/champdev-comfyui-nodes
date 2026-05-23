# Changelog

All notable changes to this project will be documented in this file.

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
