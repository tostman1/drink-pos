"""Application bootstrap for Drink POS.

The production-compatible FastAPI app still lives in ``legacy_main`` while the
domain modules are extracted. Keeping the bootstrap in one place makes that
boundary explicit and gives future route migrations a stable entrypoint.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

from fastapi import FastAPI

try:
    from app.routes.registry import include_legacy_routes
except ImportError:
    from routes.registry import include_legacy_routes


LEGACY_MODULE_NAME = "legacy_main"


def legacy_module_name(package: str | None = None) -> str:
    """Return the import path for the legacy compatibility module."""

    return f"{package}.legacy_main" if package else LEGACY_MODULE_NAME


def load_legacy_module(package: str | None = None) -> ModuleType:
    """Load or reload the legacy compatibility module.

    The existing tests repeatedly remove only ``main`` from ``sys.modules``
    while changing environment variables. Reloading ``legacy_main`` preserves
    that behavior until each domain is fully owned by modular services/routes.
    """

    module_name = legacy_module_name(package)
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def build_app_from_legacy(legacy_app: FastAPI) -> FastAPI:
    """Build the runtime app from categorized legacy routes."""

    app = FastAPI(title=legacy_app.title)
    include_legacy_routes(app, legacy_app)
    for handler in legacy_app.router.on_startup:
        app.router.on_startup.append(handler)
    for handler in legacy_app.router.on_shutdown:
        app.router.on_shutdown.append(handler)
    return app


def create_app(package: str | None = None) -> tuple[FastAPI, ModuleType]:
    """Return the FastAPI app and compatibility module for the current package."""

    legacy = load_legacy_module(package)
    legacy_app = legacy.app
    app = build_app_from_legacy(legacy_app)
    legacy.legacy_app = legacy_app
    legacy.app = app
    return app, legacy
