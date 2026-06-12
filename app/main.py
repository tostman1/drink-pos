"""Drink POS FastAPI bootstrap module.

The legacy application surface is re-exported during the modularization so
existing tests, scripts, and ASGI entrypoints can keep importing ``main``.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType


def _load_legacy_module() -> ModuleType:
    """Load the legacy app module in the current import style.

    The existing unit tests repeatedly remove only ``main`` from ``sys.modules``
    while changing environment variables. Reloading the legacy module here keeps
    that behavior working until the legacy surface is fully retired.
    """

    module_name = f"{__package__}.legacy_main" if __package__ else "legacy_main"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


_legacy = _load_legacy_module()
__all__ = [name for name in dir(_legacy) if not name.startswith("_")]
globals().update({name: getattr(_legacy, name) for name in __all__})
sys.modules[__name__] = _legacy
