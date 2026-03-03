# Changelog

All notable changes to this project will be documented in this file.

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
