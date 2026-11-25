# Drink-POS engineering contract

## Read first

Read the current checkpoint at the top of `docs/HANDOFF.md` and `docs/PROCESS.md`
first. On first inspection of a work package, read the relevant sections of
`REQUIREMENTS.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `docs/AUDIT.md`,
`IMPLEMENTATION_PLAN.md`, and `docs/standard-checks.md`. Expand to full files only
when scope/conflicts require it; do not reload historical receipts or reconstruct
unchanged context. On resume refresh only state that could have changed. This is
rehabilitation of an existing application, not permission to rewrite it. Use
Drink-POS code, tests and requirements as the application baseline; do not import
another application's architecture or business rules. Historical agent prompts are
background, not approval to execute every proposed refactoring.

## Preserve behavior

- Follow the served runtime through `app/main.py`, `app/application.py`,
  `app/routes/registry.py` and `app/legacy_main.py`. Extracted modules are not
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
  owner merged PR #1 as `052c2bbc54f05f7c7d850feb8ad597a4e4868670`. Do not
  rewrite that branch or undo the owner merge.
- Work on separate feature branches from verified `main`; before delivery
  reconcile current verified main into the active branch, preserving valid work.
- No deployment, production image publication, production DB access, real
  payment, or email delivery without separate explicit authorization.
- Use disposable databases/message/artifact directories. Never run production
  Compose/update/restore scripts as a verification shortcut.
- Do not commit `.env`, secrets, runtime messages, databases, invoices, or backups.
- Do not delegate agents unless the user explicitly requests delegation.

## CI waiting is deterministic

Waiting is not reasoning: waiting for GitHub CI is mechanical work for the
deterministic helper, and LLM polling is forbidden. Use one
`python scripts/wait_for_ci.py` invocation per CI phase (branch/PR run, then
exact post-merge main), bound to the exact expected commit SHA and the required
jobs; the result is one final JSON stored outside Git. Defaults, flags, and the
exit/status contract are in [Standard Checks](docs/standard-checks.md#deterministic-ci-waiting--ef-03).
Missing, skipped, stale or failed checks are never success, and success is never
merge permission: review, exact-head guard, protection, and approval gates stay
unchanged.

## Reviewable increments

Workflow: implement → test → commit → PR → CI → review → conditional merge →
exact main CI. Details, the failure path, and the durable checkpoint format are
in `docs/PROCESS.md`.

- Before a behavior change, identify a requirement ID and write a failing
  regression test.
- Keep one work package/small concern per commit; avoid repo-wide formatting or
  speculative layers.
- Missing tools, skipped checks, and warnings are evidence gaps, not passes.
- Update traceability, `docs/PROGRESS.md`, and `docs/HANDOFF.md`; use
  `git commit -F`, commit/push only when authorized and never merge a PR
  without approval.
