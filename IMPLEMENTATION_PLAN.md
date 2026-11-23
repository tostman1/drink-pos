# Engineering foundation work packages

## EF-01 — Reconstruct before restructuring

- Scope: verify main/handoff, inspect all diff/docs/tests/workflows, record actual
  domain and runtime seams, add agent/process/traceability/handoff documentation.
- Requirements: DP-001 through DP-020.
- Acceptance: exact commit/branch evidence; PR #1 intact; requirements distinguish
  old main from now-integrated handoff features and cite real code/tests; manual gaps remain visible.
- Risk/exclusion: stale historical claims; no architectural transplant or rewrite.
- Status: implemented; evidence in `docs/HANDOFF.md` and `docs/PROGRESS.md`.

## EF-02 — Repeatable checks and characterization

- Scope: pinned dev tools, repository-wide conservative Ruff, Python and all
  JavaScript syntax (including inline scripts/handlers and unused ES modules),
  Ruff format/compileall, JSON/manifests, traceability validation, security audit,
  browser smoke, existing unittest suite plus runtime HTTP regressions.
  Single cross-platform Standard Checks command.
- Requirements: DP-002, DP-003, DP-004, DP-006, DP-008, DP-009, DP-015, DP-018.
- Acceptance: check failures are nonzero, missing tools are not silent skips;
  disposable state/no external services; real ASGI app startup/routes checked;
  tests guard snapshots, archived debt, cashup/debt separation, rollback.
- Risk/exclusion: import/global state and misleading extracted service functions;
  no behavioral substitution or unmeasured coverage claim. Formatter debt is
  corrected mechanically in isolated commits with AST parity before final gate.
- Status: implemented and verified locally/CI; evidence in docs/PROGRESS.md.

## EF-03 — Non-publishing CI and review delivery

- Scope: read-only PR/branch quality checks on Python 3.12/3.13 and Node 24;
  Compose validation, local-only container build/start/restart smoke test with
  synthetic data. Preserve owner-triggered publication behind an explicit gate.
- Requirements: DP-014, DP-015, DP-018, DP-019, DP-020.
- Acceptance: no login/push/secrets/write permission in verification jobs; image
  metadata/health/static routes/db persistence checked; publish gated on successful
  checks and explicit main dispatch; separate committed/pushed open PR.
- Risk/exclusion: original workflow published every branch push; replacement
  verification is non-publishing. No production Compose start or deployment.
- Status: implemented, main integrated, branch and PR container CI passed;
  final evidence recorded. Owner authorized conditional PR #2 merge; publication
  and deployment remain separately controlled and forbidden in this session.

## EF-04 — First bounded rehabilitation (follow-up)

- Select one seam only after review, with failing characterization tests and an
  approved acceptance statement. Candidates: config duplication, compatibility
  import state, lifecycle deprecation, or one pure calculation.
- Require before/after runtime parity, no API/schema/business-rule drift, and
  integration validation with PR #1 in a disposable worktree.
- Do not mount prototype routers or replace order/payment/round services wholesale.
- UI extraction requires real-device/PWA regression evidence; payment/provider
  retry changes require an explicit idempotency/reconciliation design.
- Status: not started. Structural follow-up needs owner approval; these candidates
  are not commitments or approved product requirements.

## Dependency-aware modernization roadmap

| Priority / independently deliverable package | Depends on | Acceptance and boundary |
| --- | --- | --- |
| EF-04a Compatibility/config characterization | EF-01..03 reviewed | Test both import modes, environment reload and schema state; propose one seam, no financial change |
| EF-04b One pure calculation extraction | EF-04a + selected DP contract | Differential tests match served results; remove one duplication only; no new provider architecture |
| EF-05 Authorization/round decision | EF-01 audit + owner decision OQ-01 | Decide whether immediate agent charge is intended; explicit approved rule before implementation |
| EF-06 Lifecycle/dependency maintenance | EF-03 + HTTP/container baseline | Move startup only after lifecycle parity; update deprecation/tool pins separately |
| EF-07 Frontend seam characterization | EF-03 browser + target-device checks | One shared helper at a time with DOM/PWA parity; no SPA transplant |
| EF-08 Recovery/invoice side-effect hardening | MV-06 + OQ-02/OQ-03 | Synthetic all-table/artifact recovery and explicit uncertain-mail design; no production restore |

All roadmap items are **proposals**, not approved implementation in this PR.
The owner selected database backup/restore/data integrity as the next session's
intended focus (bounded recovery portion of EF-08). Do not implement it during
foundation finalization; define synthetic-data acceptance and preserve operational
compatibility first. Invoice-mail redesign is outside that next-session scope.

## EF-08a — approved bounded database recovery (2026-11-23)

Owner approved implementation/branch/commit/push/PR, not merge or deployment.
Requirements DP-014/DP-013; acceptance and baseline evidence in `docs/recovery.md`.
Persistent Backup API snapshots, verification/checksums/atomic bundles, opt-in
retention and no-clobber new-target restore; synthetic all-table/artifact rehearsal.
Invoice/SMTP side-effect redesign remains deferred (OQ-02). Production pinned
image, schedules and data are untouched. Final evidence in progress/handoff.
