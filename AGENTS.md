# Drink-POS engineering contract

## Read first

Read `docs/HANDOFF.md`, `docs/PROGRESS.md`, `docs/PROCESS.md`, `REQUIREMENTS.md`,
`ARCHITECTURE.md`, `DECISIONS.md`, `docs/AUDIT.md`, and `IMPLEMENTATION_PLAN.md`.
Also read `docs/product-operability.md`: owner-approved target requirements,
explicitly planned, with open architecture choices and acceptance gates.
This is rehabilitation of an existing application, not permission to rewrite it.
Use Drink-POS code, tests and requirements as the application baseline; do not
import another application's architecture or business rules. Historical agent
prompts are background, not approval to execute every proposed refactoring.

## Preserve behavior

- Follow the served runtime through `app/main.py`, `app/application.py`,
  `app/routes/registry.py`, and `app/legacy_main.py`. Extracted modules are not
  automatically equivalent to the current handlers.
- Keep REST paths, request compatibility, import modes (`main` and `app.main`),
  SQLite migrations, snapshots, immutable audit history, and idempotency intact.
- Open debt and the current `event_open` tally are different. Named events use
  separate `event_sessions`/`event_lines`; do not conflate either with payment.
- Payment totals are server-calculated. Uncertain SumUp results never justify
  marking debt paid. Do not blindly retry payment-creating network calls.
- Offline writes remain limited to ordinary member drink bookings. Payments,
  rounds, corrections, event controls, and admin operations stay online-only.
- Preserve German UI wording, EUR, decimal-comma display, and CSV encoding.
- UI changes require a service-worker cache-version review and device checks.

## Safe execution

- Inspect Git status before editing; never discard somebody else's changes.
- Original handoff branch preserves `250a4e6d3e4180b469d4f2a91623b60f2fd1ed72`;
  owner merged PR #1 as `052c2bbc54f05f7c7d850feb8ad597a4e4868670`.
  Do not rewrite that branch or undo the owner merge.
- Work on separate feature branches from verified `main`. Do not silently
  cherry-pick/rewrite the handoff. Before delivery reconcile current verified main
  into the active branch while preserving valid work; historical foundation
  instructions do not authorize modifying an unrelated branch.
- No deployment, production image publication, production DB access, real
  payment, or email delivery without separate explicit authorization.
- Use disposable databases/message/artifact directories. Never run production
  Compose/update/restore scripts as a verification shortcut.
- Do not commit `.env`, secrets, runtime messages, databases, invoices, or backups.
- Do not delegate agents unless the user explicitly requests delegation.

## Binding product operability (owner approved 2026-11-24)

- Ordinary association administrators must install, configure, maintain and recover
  without SSH/CLI, manual SQLite/YAML/.env operations or developer assistance.
  Target: Paste Compose → Start → Browser → Guided Setup → Operate. DSM Container
  Manager is principal; support other Docker-compatible systems. Runbooks supplement,
  not replace, routine GUI journeys. These are future requirements, not a claim
  existing deployment/recovery interfaces already meet them.
- One simple Compose, minimal unavoidable image/port/persistent-volume inputs,
  one app service by default; justify extra isolation only for safety. No shared
  default admin PIN, activation on container start, default privileged container
  or Docker socket. A web app cannot change all host/container settings.
- GUI settings require typed/versioned persistence and explicit precedence/migration.
  Secrets need approved server-only protection, masking, rotation and independent
  key/new-hardware recovery; never plaintext API-key settings or stored-secret
  responses/browser state/JS/logs/CSV/receipts. Existing SMTP/PIN TEXT storage is a
  migration risk, not an approved secure-secret implementation.
- Every sensitive payment setting change requires fresh action-bound server-side
  admin PIN verification, warnings, confirmation and secret-free audit. Session or
  reused browser PIN alone is insufficient. Serialize against active/unresolved
  payments; retain original provider identities/reconciliation access on disable.
- SumUp incomplete/unverified/inactive/unavailable means no normal card/Self-Pay/
  fee/rounding controls or card-creation calls; backend fails closed/no provider
  request/fake payment. Cash remains subject to financial holds. Production must
  reject fake/test providers. Completeness/connectivity is not readiness/payment.
- Live acceptance tests use separate durable records, not member debt/beverage
  revenue; explicit live-test approval and fresh PIN required. Verify exact provider
  success; cancel acknowledgement/local timeout never proves failure. UNKNOWN stays
  held/intervention; no unsafe replay or automatic refund. Docs approval is not
  permission to run SumUp/SMTP tests or use credentials.
- Backup/restore/update GUIs reuse EF-08 and exact release/migration contracts.
  Drain all writers; restore to isolated new state, preserve old/failed/post-backup
  financial activity and reconcile before activation. Independent browser recovery
  must work without the main DB. Readiness is not container replacement permission;
  updates need a restricted execution boundary, not unrestricted host access.
- RL-07–RL-11 are planned and separately authorized; resolve PO-ADR gates before
  implementing recommendations. Preserve RL-01–06/EF-08 evidence and unchanged
  RL-06 artifacts. CI does not close DSM/mobile/PWA/provider/operator acceptance.

## Reviewable increments

Before a behavior change, identify a requirement ID and write a failing regression
test. Keep one work package/small concern per commit; avoid repo-wide formatting
or speculative layers. Run `python scripts/standard_checks.py` and the relevant
manual/container checks from `docs/standard-checks.md`. Missing tools, skipped
checks, and warnings are evidence gaps, not passes. Update traceability,
`docs/PROGRESS.md`, and `docs/HANDOFF.md`; use `git commit -F`, commit/push only
when authorized and never merge a PR without approval. See `docs/PROCESS.md`.
