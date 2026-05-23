NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

try:
    from .nodes import (
        NODE_CLASS_MAPPINGS as _SAVE_CLASSES,
        NODE_DISPLAY_NAME_MAPPINGS as _SAVE_NAMES,
    )
    NODE_CLASS_MAPPINGS.update(_SAVE_CLASSES)
    NODE_DISPLAY_NAME_MAPPINGS.update(_SAVE_NAMES)
except ImportError:
    pass

try:
    from .filemanager import (
        NODE_CLASS_MAPPINGS as _FM_CLASSES,
        NODE_DISPLAY_NAME_MAPPINGS as _FM_NAMES,
    )
    NODE_CLASS_MAPPINGS.update(_FM_CLASSES)
    NODE_DISPLAY_NAME_MAPPINGS.update(_FM_NAMES)
except ImportError:
    pass

WEB_DIRECTORY = "web"
__version__ = "0.2.0"
__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "__version__",
]
