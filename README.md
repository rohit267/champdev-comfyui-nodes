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

## Installation

Clone into your ComfyUI custom nodes directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/<your-username>/chamdev-nodes.git
```

Restart ComfyUI.

## Compatibility

- Python 3.10+
- ComfyUI (recent versions)

## License

MIT. See [LICENSE](./LICENSE).
