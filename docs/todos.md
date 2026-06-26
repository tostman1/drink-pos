# Project Todos

This list keeps intentional follow-up work visible without mixing it into
source comments.

## Keep Open

- Improve iPad landscape layout with a denser two-column bill/detail view.
- Consider SSE or WebSocket live sync so browsers receive changes immediately
  instead of polling `/api/sync-status`.
- Add a native MCP server wrapper if AI clients should connect through MCP
  directly instead of the current Agent REST API.
- Continue extracting routes from `legacy_main.py` into focused route modules
  once each domain has service coverage and tests.

## Optional Product Features

- Admin database download and restore/import workflow.
- CSV import for members.
- Named admins and a fuller role model.
- Explicit events/veranstaltungen instead of only `event_open`.
- Cash balance module with start cash, count, difference, and close report.
- Debt/reminder list by age.
- QR-code read-only overview for members.
- Receipt/PDF export after payment.
