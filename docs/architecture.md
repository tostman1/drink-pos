# Drink POS Architecture

Drink POS is being migrated from a monolithic FastAPI module into a layered
application. The current production-compatible entrypoint is `app/main.py`,
which re-exports `app/legacy_main.py` while the code moves into focused modules.

## Layers

- `app/config.py` owns environment values, defaults, and constants.
- `app/db/` owns SQLite connection setup and database initialization facades.
- `app/models/` owns Pydantic request models and typed response shapes.
- `app/utils/` owns parsing, formatting, validation, and general helpers.
- `app/services/` owns business logic with no FastAPI request or response types.
- `app/routes/` owns thin APIRouter modules that validate input and call services.

## Migration Strategy

The first migration step keeps `legacy_main.py` active for backward
compatibility. New services accept `sqlite3.Connection` explicitly, which makes
them testable without an ASGI app. Routes will move one endpoint group at a time
after matching service coverage exists and tests protect behavior.

## Compatibility Rules

- REST paths and payloads stay compatible.
- The SQLite schema stays compatible.
- Payment and cashup behavior must be covered by tests before route migration.
- The legacy module remains as a fallback until each domain is fully covered.
