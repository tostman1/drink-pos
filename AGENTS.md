# Drink-POS engineering contract

## Read first

Read the current checkpoint at the top of `docs/HANDOFF.md`, current evidence in
`docs/PROGRESS.md`, and `docs/PROCESS.md` first. On the first inspection of a work
package, read relevant sections of `REQUIREMENTS.md`, `ARCHITECTURE.md`,
`DECISIONS.md`, `docs/AUDIT.md`, and `IMPLEMENTATION_PLAN.md`. Expand to full files
when scope/conflicts require it; do not repeatedly load historical receipts or
reconstruct unchanged context during the same package. Reuse verified information;
on resume refresh only the local/external state that could have changed.
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

## Waiting is not reasoning — binding for every session and work package

- An LLM must not repeatedly reason, comment, invoke tools or reconstruct context
  solely to wait for external operations. This covers Actions, PR checks,
  mergeability/protection, final-head/post-merge CI, artifacts and rate-limit recovery.
- Follow the mandatory workflow in `docs/PROCESS.md` and exact usage/exit codes in
  `docs/standard-checks.md`. Use `python scripts/wait_for_ci.py` once per identified
  run or PR + expected full HEAD SHA. Defaults: 90s initial, 30s discovery, 60s poll,
  120s long-running, at most three backoff retries, 30-minute budget; final JSON only.
- No tight LLM polling, repeated `gh run view`/`gh pr checks`, short sleeps followed
  by model turns, unchanged PR/status inspections, repeated full log downloads,
  redundant commentary, in-flight implementation rewrites/reviews, or duplicate
  agents monitoring the same operation. Elapsed time is not a reason for model use.
- Use one supported blocking/background shell invocation and its completion event.
  Never poll background completion/result files. If execution cannot outlive the
  wait, preserve the existing HANDOFF checkpoint and stop; timeout is not success.
- Distinguish GitHub REST/GraphQL/secondary limits, provider request/token limits
  and tool timeouts. Respect Retry-After/reset/backoff deterministically. Provider
  limits require checkpoint/stop, not blind model retries, quota bypass, or a claim
  that a fixed sleep guarantees recovery.
- Use targeted files/searches, concise outputs and batched independent reads. Avoid
  redundant Git queries and unchanged summaries/code dumps. Preserve important
  knowledge in authoritative docs, using existing IDs rather than duplicate lists.
- None of this weakens regression/security/migration/container checks, required
  reviews/protection, exact-HEAD/final-head/post-merge evidence, approval gates,
  traceability, or separate publication/deployment authorization.

## Reviewable increments

Before a behavior change, identify a requirement ID and write a failing regression
test. Keep one work package/small concern per commit; avoid repo-wide formatting
or speculative layers. Run `python scripts/standard_checks.py` and the relevant
manual/container checks from `docs/standard-checks.md`. Missing tools, skipped
checks, and warnings are evidence gaps, not passes. Update traceability,
`docs/PROGRESS.md`, and `docs/HANDOFF.md`; use `git commit -F`, commit/push only
when authorized and never merge a PR without approval. See `docs/PROCESS.md`.
