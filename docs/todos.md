# Project Todos

This list keeps intentional follow-up work visible without mixing it into
source comments.

## Keep Open

- Clarify/fix cashup round display mismatch: in the latest stable build,
  "Bestätigte Runden" can appear to show only one payer even though two round
  units are counted/deducted. Local code inspection suggests the backend keeps
  all round units in `auto_rounds.rounds`, while `auto_rounds.charges`
  intentionally lists only unpaid round charges. Check a real
  `/api/admin/cashup-preview` payload before changing whether this is wording,
  table ordering/visibility, or missing `paid_round_units` in production data.
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
