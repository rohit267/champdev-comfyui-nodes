import logging

_logger = logging.getLogger(__name__)

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

try:
    from .nodes import (
        NODE_CLASS_MAPPINGS as _SAVE_CLASSES,
        NODE_DISPLAY_NAME_MAPPINGS as _SAVE_NAMES,
    )
    NODE_CLASS_MAPPINGS.update(_SAVE_CLASSES)
    NODE_DISPLAY_NAME_MAPPINGS.update(_SAVE_NAMES)
except ImportError as e:
    _logger.warning("champdev-comfyui-nodes: save nodes failed to load: %s", e)

try:
    from .filemanager import (
        NODE_CLASS_MAPPINGS as _FM_CLASSES,
        NODE_DISPLAY_NAME_MAPPINGS as _FM_NAMES,
    )
    NODE_CLASS_MAPPINGS.update(_FM_CLASSES)
    NODE_DISPLAY_NAME_MAPPINGS.update(_FM_NAMES)
except ImportError as e:
    _logger.warning("champdev-comfyui-nodes: file manager node failed to load: %s", e)

try:
    from .terminal import (
        NODE_CLASS_MAPPINGS as _TERM_CLASSES,
        NODE_DISPLAY_NAME_MAPPINGS as _TERM_NAMES,
    )
    NODE_CLASS_MAPPINGS.update(_TERM_CLASSES)
    NODE_DISPLAY_NAME_MAPPINGS.update(_TERM_NAMES)
except ImportError as e:
    _logger.warning("champdev-comfyui-nodes: terminal node failed to load: %s", e)

WEB_DIRECTORY = "web"
__version__ = "0.4.3"
__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "__version__",
]
