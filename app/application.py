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


def create_app(package: str | None = None) -> tuple[FastAPI, ModuleType]:
    """Return the FastAPI app and compatibility module for the current package."""

    legacy = load_legacy_module(package)
    return legacy.app, legacy
