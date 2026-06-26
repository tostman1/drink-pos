# Drink POS Architecture

Drink POS is being migrated from a monolithic FastAPI module into a layered
application. The stable production entrypoint is `app/main.py`, which loads the
FastAPI app through `app/application.py`. The current production-compatible app
still lives in `app/legacy_main.py` while code moves into focused modules.

## Layers

- `app/config.py` owns environment values, defaults, and constants.
- `app/db/` owns SQLite connection setup and database initialization facades.
- `app/models/` owns Pydantic request models and typed response shapes.
- `app/utils/` owns parsing, formatting, validation, and general helpers.
- `app/services/` owns business logic with no FastAPI request or response types.
- `app/routes/` owns thin APIRouter modules that validate input and call services.

## Migration Strategy

`legacy_main.py` is the compatibility layer. New services accept
`sqlite3.Connection` explicitly, which makes them testable without an ASGI app.
Routes move one endpoint group at a time after matching service coverage exists
and tests protect behavior.

This avoids a risky big-bang rewrite of all production endpoints. The
bootstrap, module layout, and import boundaries are explicit; removing the
compatibility layer remains a tracked follow-up in `docs/todos.md`.

## Compatibility Rules

- REST paths and payloads stay compatible.
- The SQLite schema stays compatible.
- Payment and cashup behavior must be covered by tests before route migration.
- The legacy module remains as a fallback until each domain is fully covered.

## Remote Access

Remote access is currently handled operationally through Tailscale. The app
therefore remains designed as a local/private-network service; no public
internet exposure is required for normal operation.
