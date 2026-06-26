# Drink POS Architecture

Drink POS has a modular runtime shell around the original production handlers.
The stable production entrypoint is `app/main.py`, which loads the FastAPI app
through `app/application.py`. Runtime routes are grouped by `app/routes/registry.py`
into public, static, payment, admin, and agent routers before being mounted.

## Layers

- `app/config.py` owns environment values, defaults, and constants.
- `app/db/` owns SQLite connection setup and database initialization facades.
- `app/models/` owns Pydantic request models and typed response shapes.
- `app/utils/` owns parsing, formatting, validation, and general helpers.
- `app/services/` owns business logic with no FastAPI request or response types.
- `app/routes/` owns APIRouter modules and the legacy route registry.

## Migration Strategy

`legacy_main.py` is now a compatibility handler catalog rather than the app that
is served directly. New services accept `sqlite3.Connection` explicitly, which
makes them testable without an ASGI app.

This avoids changing all production handler bodies at once while still ensuring
the served ASGI app is assembled through modular routers. Retiring individual
legacy handler bodies remains a lower-risk follow-up in `docs/todos.md`.

## Compatibility Rules

- REST paths and payloads stay compatible.
- The SQLite schema stays compatible.
- Payment and cashup behavior must be covered by tests before route migration.
- The legacy module remains as a fallback until each domain is fully covered.

## Remote Access

Remote access is currently handled operationally through Tailscale. The app
therefore remains designed as a local/private-network service; no public
internet exposure is required for normal operation.
