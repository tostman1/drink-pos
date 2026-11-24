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

**D-17 RL-05 owner decision (2026-11-24):** normal consumption reports use actual net
consumption after approved erroneous-booking corrections, original-period attribution
and separate immutable originals/correction audit. Negative admin identity/purpose
mandatory, explicit correction-only pay success; no unkeyed retry guarantee. Addendum:
round cancellation is coordinated, stable unit/deduction provenance and exact once-only
compensation; paid/closed/unknown/legacy ambiguity fail closed, no provider refund,
inventory return or reopened settled debt. Actual additive v2 authorized only synthetic
implementation; no extra historic fingerprint/production migration/merge approval.
OQ-06 remains open for other policies/adoption/historical gaps; FH-05 remains open.

**RL-04 D-16 (2026-11-24):** owner approves routine historical snapshot preservation
only, including zero/nonzero/unusual round snapshots; missing defaults initialize,
existing default zero master is retained. Admin edits and startup do not infer past
costs. Paid reports read present stored profit including zero; operational formulas
stay unchanged. FH-04 characterization only: signed correction-detail semantics are
not unambiguous. No historical repair/reconstruction/inferred-cost storage/additional
adoption/v2/production operations. This supersedes RL-03 NOT-approved wording below
only for this bounded authorization. **OQ-06 remains OPEN** for separate questions;
FH-04/05 and EF-08a Windows WinError 5 remain unresolved. See rl-04-contract and
correction-audit-contract for exact boundaries.

RL-03 integration (2026-11-24): owner completed independent PR #8 evidence review
and explicitly approved guarded merge of reviewed `0b43f379...`; merged
`9d09015b2d83d652d88b283ef9f5ab45050128bf`, exact reviewed tree preserved.
**OQ-06 remains OPEN.** This approval accepts the evidence package only, **not**
snapshot rewrite prevention, accounting/reporting policy, inferred-cost storage,
append-only corrections, historical repair, new migrations/schema allowlists or
production rollout. FH-01..FH-06 and severities remain open; preserve-original
recommendation below stays **PROPOSED/NOT APPROVED**. No next work package authorized.

RL-03 proposal (2026-11-23), **not approved**: [financial-history decision record](docs/financial-history-policy.md)
compares A exact originals, B separate provenance-labelled inference, C controlled
corrections. Recommend A preservation invariant plus separately authorized B;
defer C, prefer additive corrections if required. Existing legacy startup **and served
item-update API** overwrite historical zeros/cost/profit; versioned startup does not
protect the API. No accounting/migration/adoption implementation here. Source-only
inventory finds eight fresh schemas and an ALTER-fee variant, **no authenticated
historical DB/release image**; no support widened. OQ-06 remains owner-pending.

RL-02 D-15 (2026-11-23): implement smaller opt-in baseline contract rather than
mandatory historical migrations. Fresh explicit initialization and exact-current
metadata-only adoption → v1, DELETE journal mode, no repeated existing financial/
default normalization, transactional ledger, no automatic WAL recovery. Default
legacy remains unchanged. Rollout must be separately reviewed. OQ-06's ledger seam
is implemented, but authentic historical support, adoption breadth, legitimate-zero/
round-cost/prototype-history policy and production adoption remain **unresolved**.
No new accounting interpretation is authorized by implementation/test success.

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
- **OQ-06 — financial preservation and adoption breadth:** RL-02 opt-in ledger/
  transaction gate is integrated. Remaining owner choice: original zero/nonzero/
  round snapshots, explicit unknown/inference provenance, corrections/report basis,
  authentic historical sources and exact supported adoption paths. RL-03 supplies
  evidence/options, not approval. Image downgrade on newer state is not safe rollback.
- **OQ-07 — product release identity:** Choose human version/channel/support policy,
  authenticated historical fixtures and exact tested-artifact promotion/provenance/
  digest receipt. Current mutable base/dependencies and separate publish rebuild
  do not prove reproducibility; no registry publication is authorized in RL-01.

Unresolved entries stay visible; they do not block adding the non-invasive
foundation or become inferred requirements just because they appear here.
