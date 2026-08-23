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
    from .password_auth import (  # noqa: F401  (registers /champdev/auth/* routes)
        routes as _AUTH_ROUTES,
    )
except ImportError as e:
    _logger.warning("champdev-comfyui-nodes: auth routes failed to load: %s", e)

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
__version__ = "0.6.1"

try:
    from . import telemetry
    telemetry.maybe_send()
except Exception as e:  # never let telemetry break node loading
    _logger.debug("champdev-comfyui-nodes: telemetry skipped: %s", e)

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "__version__",
]
