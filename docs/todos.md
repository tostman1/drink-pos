# Project Todos

This list keeps intentional follow-up work visible without mixing it into
source comments.

## Keep Open

- Improve iPad landscape layout with a denser two-column bill/detail view.
- Consider SSE or WebSocket live sync so browsers receive changes immediately
  instead of polling `/api/sync-status`.
- Add a native MCP server wrapper if AI clients should connect through MCP
  directly instead of the current Agent REST API.
- Retire compatibility handler bodies from `legacy_main.py` gradually after each
  domain has service coverage and behavior tests. The runtime app is already
  assembled through modular routers.

## Optional Product Features

- Admin database download and restore/import workflow.
- Explicit events/veranstaltungen instead of only `event_open`.
- Cash balance module with start cash, count, difference, and close report.
