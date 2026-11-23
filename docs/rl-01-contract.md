# RL-01 release safety — ready gate and observed baseline

Approved bounded engineering package, 2026-11-23. DP-023 (new), DP-014,
DP-015, DP-019 and financial/state preservation DP-003..013. Base fetched main
`dbc314e0790534ee44f362be4a194143385eb071`, clean checkout, exact CI
https://github.com/tostman1/drink-pos/actions/runs/45199604894 succeeded.
Branch `feature/rl-01-release-safety`. No deployment/publication/merge authority.

## Current verified behavior (not proposed guarantees)

| Concern | Actual implementation / risk |
| --- | --- |
| Version | `app/core/build.py` uses APP_BUILD_* or `local-dev` fallback (not Git discovery); no authoritative product SemVer or migration ledger. HTTP metadata must remain unchanged. |
| Image build | Dockerfile uses mutable `python:3.12-slim`, unpinned runtime requirements, injected commit/ref/channel/tags. A commit alone does not make rebuilds byte-identical. |
| Publication | Only explicit main `workflow_dispatch publish=true`, after both check jobs, `production-images` environment. Environment reviewers/settings remain operator responsibility. stable/latest/main and short sha tags are mutable; registry content digest is immutable but not yet captured as a product release receipt. No image published in RL-01. |
| Selection | compose.yaml allows DRINK_POS_IMAGE override, defaults stable, pull_policy always on app and backup. Synology hardcodes stable. Separate resolution can select different app/backup images during a moving tag. Operator-managed files may differ; none inspected. |
| Podman | Scripts pull --policy newer, force-recreate (one variant remove-orphans), then image prune -f. No backup, compatibility, readiness, health, reconciliation or rollback check. POSIX sources .env as shell code; PowerShell parses it differently and native nonzero exits are not reliably caught by ErrorActionPreference on all supported shells. |
| Unattended | Optional systemd timer daily 04:10, Persistent=true; service calls script in /opt/drink_pos. Installation/enabling not proven. No running schedules accessed or changed. |
| Replacement | Image owns code, ./data remains mounted. Restart starts new code on old state; persistent files are not overwritten wholesale, but startup can change their contents. Health alone is not financial compatibility proof. |
| Startup | main → application → registry/legacy startup → schema.init_db; creates directories/messages BEFORE SQL checks, enables WAL, CREATE/ALTER then seed/normalization/backfill/defaults/indexes/commit. No preflight gate or version ledger. PRAGMA user_version/application_id are not maintained migration versions. |
| Migration | All helpers run on every startup; guarded DDL does not imply whole-startup idempotency or atomicity. Early DDL can persist before first DML transaction; later DML/DDL roll back on close after failure. WAL/message-file changes are outside that transaction. Duplicate payment IDs can fail late unique-index creation. |
| Financial changes | Zero purchase snapshots filled from current item costs, purchase totals/profits recalculated; round-item costs reset. Legitimate zero snapshots cannot be distinguished from pre-feature rows. Repeated startup can backfill again when costs later become positive. Debt/sales amounts are not deliberately rewritten, but historical cost/profit IS mutable at startup. |
| Prototype | drinks imported by name if missing; positive orders imported only when order_lines empty, old tables retained, current prices/date used. This is not authenticated historical accounting reconstruction. |
| Recovery | EF-08a exact SQLite + partial CSV; EF-08b all-writer-quiesced DB/events/messages/nonsecret configuration, verified no-clobber relocation-only restore; EF-08c public-age encrypted transfer, separate private-key full verification/independent receipt. None implies automatic rollback or business reconciliation. |

## Chosen smallest useful foundation

Standalone stdlib identity/preflight tools, no application imports/startup. Preflight
accepts ONLY an explicitly attested isolated, completed EF-08b application bundle
(including a decrypted, fully verified EF-08c payload). No loose/live DB defaults.
Reject SQLite sidecars before opening and require rollback-journal snapshot header;
immutable reads are restricted to that offline snapshot, never active WAL. Verify
full inventory/integrity/FKs/logical state, current release/installation binding,
configuration and an explicitly operator-approved exact compatibility tuple.
Missing evidence is UNKNOWN, not success. Successful preflight authorizes only a
separately approved disposable rehearsal, never production replacement.

Release identity distinguishes exact source commit, migration-code hash, human
version (nullable when unassigned), explicit channel, runtime baseline and EF-08b
format. Database schema is a separate exact sqlite_master fingerprint captured in
compatibility evidence, not invented by importing startup. Image digest is nullable
until publication/inspection; production assessment requires an independently
recorded exact pinned reference. Local rehearsal needs no registry. Compatibility
approval binds full identities and exact source/target schema; no wildcard paths.
Evidence is trusted operator input, not signed provenance or inferred compatibility.

## Acceptance / tests written before implementation

- DP-023 fail-closed JSON/exit codes; missing metadata/backup/key evidence, mutable
  or conflicting references, schema/path/configuration/installation mismatch,
  corruption, sidecars, isolation refusal; no writes/startup/network/subprocess.
- DP-014 characterize synthetic prototype import, partial DDL/DML failure,
  repeated zero-cost backfill, rollback journal/WAL and interrupted process recovery.
- Disposable synthetic full-state fixture → verified bundle → startup copy → exact
  permitted cost changes only → API debt/payment/event parity → second startup →
  independent restore. No authentic historical-release compatibility claimed.
- Actual non-publishing image identity and rehearsal in CI, Python 3.12/3.13 full
  Standard Checks. UI/REST/payment/invoice/migration implementation unchanged.
- Optional digest-pinned Compose example only; existing defaults/scripts/timer stay
  byte-identical. No generic deployment controller or destructive rollback commands.

## Exclusions / decisions still needed

Versioned, transactional migrations require separate RL-02 approval. Earlier-image
schema compatibility, release naming/support policy, immutable base/dependency
provenance, signed release receipts, environment reviewers and operator-managed
schedule adoption are NOT established here. MV-01..06 and EF-08a intermittent
Windows WinError 5 remain open; synthetic success is not real-installation evidence.
