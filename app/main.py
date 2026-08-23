"""Drink POS FastAPI bootstrap module.

``main`` is the stable ASGI and test import entrypoint. The application is
loaded through ``application.create_app`` so the legacy compatibility layer is
centralized while routes and services continue moving into focused modules.
"""

from __future__ import annotations

import sys


try:
    from app.application import create_app
except ImportError:
    from application import create_app


app, _legacy = create_app(__package__)
__all__ = [name for name in dir(_legacy) if not name.startswith("_")]
globals().update({name: getattr(_legacy, name) for name in __all__})
globals()["app"] = app
sys.modules[__name__] = _legacy
