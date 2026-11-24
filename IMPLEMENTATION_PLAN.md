# Engineering foundation work packages

## Current roadmap authority — 2026-11-24

Main baseline `7a6aa5dff411c8fb5601b87758a0fc64810aa0c3`; RL-01–RL-06 are
integrated (PRs #6–11). RL-06 NAS/manual acceptance is still pending. The original
package scopes/approval-time exclusions below remain historical; their OPEN/no-merge/
no-v2 wording is superseded **only** by recorded integration/RL-05 evidence, not
deleted or renumbered. No RL-07–11 entries previously existed; IDs are now reserved.
EF modernization suggestions remain separate, not silently replaced product policy.

The owner approved target requirements DP-026–040 and documentation delivery only.
**Every implementation, real integration test, deployment and merge needs separate
authorization.** Read [focused specification](docs/product-operability.md) and open
PO-ADR-01–14 in DECISIONS; recommended options are not approved designs.

| Planned package | Depends on / decision gates | Target acceptance and exclusions |
| --- | --- | --- |
| RL-07 — Simple Deployment, Configuration Foundation & First-Run Wizard | RL-01–06/EF-08 retained; PO-ADR-01–06, 09–11, 13 and preparedness part of 14 | DP-026–031 foundations; PO-V01–06. Strong no-default admin/bootstrap, one-Compose/no-CLI GUI setup, typed settings/secret/key/ENV transition, DB-independent recovery design and trusted image/TLS prerequisite. Extend traceability schema/checker/tests for planned+implemented lifecycle **before promotion**. No implicit production rollout/SumUp activation. |
| RL-08 — SumUp GUI, Diagnostics, Guided Payment Acceptance & Feature Gating | RL-07 settings/secrets/auth/bootstrap accepted; PO-ADR-06–08, provider capability/limits and acceptance policy verified | DP-028/030/031 integration + DP-032–037; PO-V03/05–12. All nine settings, pairing, no-charge diagnostics, isolated success/cancel/timeout tests, exact config/identity/UNKNOWN holds, explicit activation, complete UI/API gating and no production fake provider. Mocks/synthetic tests first; real tests need separate owner approval/credentials. |
| RL-09 — Integrated Backup, Restore & Recovery GUI | RL-07 independent control/key/format architecture, RL-08 unresolved provider identity/access model; EF-08a/b/c and release/migration contracts; PO-ADR-03/04/07/09/10/14 | DP-030/038; PO-V05/13. Consistent complete encrypted backups/history/upload/prevalidation, all-writer maintenance/new-root recovery and DB-unavailable GUI, original/post-backup retention and reconciliation. No second incompatible format/active DB overwrite/auto-payment-mail replay. Resolve EF-08a Windows reliability in separately bounded scope before claiming that platform's readiness. |
| RL-10 — Updates & Maintenance Center | RL-07 image provenance, RL-09 proven restore/key/maintenance, RL-08 payment holds; PO-ADR-11/12 and exact compatibility policy | DP-039; PO-V14. Version/image/schema/backup/storage/pending/recovery status, candidate approval/quiescence/verified backup/isolated rehearsal, restricted install/restart, health/full-state verification/recovery. No unrestricted Docker socket/privileged host control, blind pruning/unattended updates or incompatible image-only rollback. |
| RL-11 — Synology, Mobile, PWA & Operational Acceptance | RL-07, RL-08, RL-09 and RL-10 implementation individually accepted; PO-ADR-13/14 and unresolved device/operator gaps; explicit authorization for devices/integrations | DP-040 plus all journey requirements; PO-V01–15 and retained MV-01–06. Actual DSM GUI-only install/security/HTTPS, tablet/mobile/installed-PWA/cache/offline, finance/net correction/round block matrix, live provider only approved, independent key/image/DB-unavailable loss/update recovery and post-backup reconciliation. Record assistance/errors/time/real RPO/RTO; never infer hardware/offsite/immutable/provider passes from CI. |

### Package ready/done gates

Before each implementation: verify current main, secure approval/scope, select DP IDs,
resolve blocking technical choices with owner/security/accounting review, write failing
served-boundary regressions and define migration/recovery/rollback evidence. Preserve
existing interfaces unless explicitly reviewed, never substitute prototypes wholesale.
RL-07 does not bypass strict unknown/future/WAL gates or adopt arbitrary historical DBs.

Each package must deliver small commits, updated traceability/docs, full unchanged
Standard Checks and exact-head non-publishing branch/PR container gates. GUI work
also reviews worker cache version and device/PWA checks. Implemented, review-ready,
owner-merged and operationally accepted are distinct states. For live tests record
separate owner authority; a C timeout safety pass with UNKNOWN still blocks activation.
At each handoff retain partial/failed evidence and outstanding choices, then stop.

The current docs-only package uses no behavioral regression/code edits: old 25-entry
catalog remains intact and new planned partition is supplementally audited (details
in product-operability). RL-07 owns machine-gate evolution; current CI is not weakened.

## RL-06 — isolated Synology test deployment (2026-11-24)

DP-025 plus preserved DP-001/008/009/015/016/021–024. Ready gate
`docs/rl-06-contract.md`; exact-tested AMD64 archive, local/internal-network single
test service, explicit synthetic-only empty v2 initialization, read-only preflight,
quiesced EF-08b backup/new-root recovery, actual Compose rehearsal and German
`docs/synology-test-deployment.md`. Existing production defaults/updaters unchanged.
One OPEN/UNMERGED PR; real NAS/device/HTTPS/PWA/offsite/key acceptance pending.

## RL-05 — approved transaction integrity + round addendum (2026-11-24)

Ready gate `docs/rl-05-contract.md`, exact round lifecycle/blocks in
`docs/round-cancellation-contract.md`. Append source-linked corrections, net-original-
period reports, keyed negative admin/payment receipts, serialized request decisions,
explicit correction-only success and existing vanilla UI adaptation. Real additive
v2 migration plus durable round unit/deduction/reversal provenance and fail-closed
paid/closed/unknown/legacy states. Synthetic full financial/container/source-loss
recovery and both Python exact-head CI; no merge/publication/production/history repair.

## RL-04 — approved scoped financial integrity (2026-11-24)

DP-002/004/005/013/014/024; ready gate `docs/rl-04-contract.md`. Remove routine
master-edit/startup historical cost/profit inference and round resets; preserve
existing default zero master; paid reports honor stored zero/nonzero profit.
Characterize FH-04 exact lifecycle/audit/replay/failure, no new correction accounting.
Synthetic served full-state/both-mode/recovery/mocked-payment scenario and actual
image CI. Reviewable feature PR only; no merge/production/publication/schema/v2/
additional adoption/history repair. FH-04/05 and broader OQ-06 remain open.

## RL-01 — approved release-readiness and upgrade-safety foundation (2026-11-23)

DP-023/014/015/019; ready gate in `docs/rl-01-contract.md`. Baseline/update risk
inventory, deterministic offline identities, explicit read-only isolated-bundle
preflight with non-success unknown, exact operator compatibility/state/config/key
evidence, synthetic existing-startup/full-state/API/recovery tests and optional
digest-pinned deployment guidance. No migration/runtime/UI/payment/deployment-default
rewrite, image publication, deployment or merge. Final evidence in progress/handoff.

## RL-02 — approved bounded versioned migration contract and opt-in gate

DP-024/014/015/023, authorized 2026-11-23. Ready gate `docs/rl-02-contract.md`,
implemented contract `docs/migration-safety.md`. Default legacy unchanged; strict
fresh transactional initialization or exact-current metadata-only adoption → v1,
read-only repeat verification, no existing financial/history normalization. Exact
fingerprints only, future/unknown/partial/WAL state reject before writes; ledger and
SQLite changes commit together. No authentic historical/v1→v2 support, mandatory
rollout, accounting policy, automatic production upgrade or merge/publication.
OQ-06 unresolved; next package requires owner-approved preservation/adoption policy.

## RL-03 — authorized decision/evidence package, not policy implementation

Owner request 2026-11-23; ready gate `docs/rl-03-contract.md`. DP-002/003/004/005/
011/013/014/023/024. Exact financial write matrix, A/B/C proposed decision, source-only
schema/provenance inventory, synthetic characterization tests and fail-closed safe
adoption proposal. No app changes, new fingerprint support, accounting policy,
v1→v2 migration or production upgrade. Owner continuation explicitly authorizes
reviewed commits/push/open PR/final-head CI, **not merge**. Deliver owner decision
inputs; next implementation/operations need separate approval. Proposed next scope
`RL-04 — Historical Snapshot Write Preservation` in `docs/financial-history-policy.md`
addresses FH-01/02/06 only after A approval; FH-03/04/adoption breadth remain separate.

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

## EF-08b — approved portable application recovery (2026-11-23)

DP-014/010/011/013/018/019; ready gate in `docs/ef-08b-contract.md`.
Separate versioned whole-state bundle, all-writer maintenance precondition,
observed change detection, atomic no-replace publication and isolated verified
restore with bounded event-path relocation. One-shot JSON/status CLI, filesystem
transport boundary and optional generic Compose example. No invoice/mail/provider
redesign or runtime-handler changes, no retention/deployment/image publication.
Rehearsal covers complete synthetic state/failure injection and actual image tools.
MV-06 offsite/ACL/RPO/RTO/operator acceptance remains separately bounded follow-up.

## EF-08c — approved independent disaster recovery (2026-11-23)

DP-022/021/014 and financial preservation requirements; ready gate in
`docs/ef-08c-contract.md`. Optional external-age replica adapter, independent
decryption verification, safe tar/atomic publication, explicit lifecycle journal/
monitoring and complete synthetic source-loss/reconstruction/timing CI rehearsal.
EF-08a/b formats/interfaces and business handlers remain unchanged. No real storage,
credentials, deployment/publication/merge; MV-06 real geography/immutability/ACL/
escrow/image acquisition/operator timed reconciliation remains separate acceptance.
