# Decisions and open questions

## Confirmed decisions

| ID | Decision / evidence | Consequence |
| --- | --- | --- |
| D-01 | Retain FastAPI/direct sqlite3/WAL/vanilla PWA and authoritative served legacy handlers (owner foundation scope; ARCHITECTURE.md EF-ADR-001) | No architectural transplant; parity tests precede one-seam migrations |
| D-02 | Preserve immediate round approval/charge as observed API contract (`legacy_main.create_round_request`; existing and HTTP tests) | Correct operating-agent docs; do not silently add approvals/change debt rules |
| D-03 | Independent branch was created from verified `fb08128`; owner subsequently merged PR #1 as `052c2bb` and authorized integration | Merge verified main into foundation before delivery, preserve history/work |
| D-04 | PR/main checks never publish; explicit approved main dispatch separates verified image publication | Keep stable/latest naming and deployment compatibility; no dispatch/deploy in this assignment |
| D-05 | Mandatory Ruff/syntax/unittest/browser/security/container gates, mechanical format debt isolated | No ignores to hide meaningful errors; local/CI/manual evidence labeled separately |
| D-06 | Owner approves PR #2 merge only after final pushed-HEAD checks, then main-CI/tree verification | Mark ready, use normal reviewed integration without bypass; no release/publication/deployment |
| D-07 | Next intended session is database backup, restore and data integrity | Prepare bounded EF-08 recovery handoff only; implement nothing from it during finalization |
| D-08 | Owner approved bounded EF-08a implementation on 2026-11-23 | Full SQLite plus unchanged CSV in atomic bundles; new-target-only restore; count retention opt-in (minimum two); no production/deployment/mail redesign |
| D-09 | EF-08b uses explicit all-writer maintenance quiescence, observed change checks and a distinct application bundle contract | No online/DB-lock-only consistency claim; preserve event CSV→PDF→SMTP→commit behavior; exact artifact relocation only, no side-effect redesign |
| D-10 | Application recovery core is filesystem/one-shot CLI only, atomic no-replace publication on Linux/Windows; no new retention | Scheduling/transport/encryption/independent copies remain operator-controlled; unsupported publication semantics fail closed; no production adoption |
| D-11 | EF-08c optional encrypted filesystem replicas use established external age and standard tar, unchanged EF-08b bundle inside; PR #5 correction makes producer public-key-only | v2 marker means encrypted transfer only; separate private-key full verification, explicit trusted independent/offsite receipts; combined verification opt-in, no immutable/geography proof |
| D-12 | Complete installation-loss rehearsal removes only owned synthetic source storage, preserves compatible image/key escrow independently and gates network-disabled startup on explicit synthetic reconciliation | Synthetic RPO/RTO reported separately from operational guarantees; Windows EF-08a rename issue remains a separate reliability follow-up |
| D-13 | RL-01 preflight is standalone, explicit isolated EF-08b bundle only, exact identities/schema/installation/config and trusted key/compatibility evidence; unknown non-success | No live-state/default discovery, migrations, deployment or automatic rollback; readiness approves rehearsal only. Existing startup/deployment defaults preserved. |
| D-14 | RL-01 characterizes existing partial DDL and repeatable purchase-cost backfills without rewriting migrations; digest/version evidence remains nullable until actually available | Synthetic fixtures are not authentic release evidence. Versioned migrations/pre-write gate and tested-image promotion require separate RL-02/release decisions. |

## Unresolved decisions (not implementation authorization)

- **OQ-01 — agent financial authority:** Should token-operating agents immediately
  charge rounds or require a separate consent/role? Current behavior is confirmed
  but can incur debt. Owner must decide; EF-05, not this foundation.
- **OQ-02 — uncertain SMTP side effects:** What retry/reconciliation policy is
  acceptable when files/mail precede DB closure? No exactly-once claim; avoid blind
  retries or duplicate invoices. EF-08 needs explicit acceptance.
- **OQ-03 — recovery scope:** What retention/export verification is required for
  all operational tables and separate event files? Synthetic rehearsal first;
  production recovery remains independently authorized.
- **OQ-04 — legacy module ownership:** Which one seam should migrate first after
  parity coverage? Extracted helpers are not automatically runtime equivalents.
- **OQ-05 — release protection:** Owner must configure required reviewers for
  `production-images` and select merge-required checks. No settings change or
  production release is authorized by this PR.
- **OQ-06 — migration contract:** Choose version ledger, whole-migration atomicity,
  supported source/target paths and treatment of legitimate zero-cost historical
  snapshots before RL-02; image downgrade on newer state is not automatically safe.
- **OQ-07 — product release identity:** Choose human version/channel/support policy,
  authenticated historical fixtures and exact tested-artifact promotion/provenance/
  digest receipt. Current mutable base/dependencies and separate publish rebuild
  do not prove reproducibility; no registry publication is authorized in RL-01.

Unresolved entries stay visible; they do not block adding the non-invasive
foundation or become inferred requirements just because they appear here.
