# RL-03 — financial-history decision package: ready gate

Owner request, 2026-11-23: prepare evidence for **OQ-06**, not a new financial
policy, v1→v2 migration, broader adoption implementation or production upgrade.
The supplied request ends at heading “5. Safe Adoption Proposal”; that section
is interpreted as a proposal only, with no assumed omitted requirements.

**Continuation authorization (2026-11-23):** owner completed the truncated request
and explicitly authorized review/final documentation, Standard Checks, reviewed
Conventional Commits, push of the existing branch, an open PR against main and
exact-final-head CI verification. This supersedes the initial no-commit/push/PR
authority note below **only for RL-03 delivery**. No merge/publication/deployment,
financial/report/runtime change, correction, new adoption path/default mode change,
real data access or v1→v2 migration. Existing synthetic RL-01/02 test migrations run
only inside mandatory checks on disposable state, never against an installation.
OQ-06 remains OPEN; recommendation stays NOT APPROVED.

- Clean incoming local main, fetched origin/main and remote main all verified at
  `33c16979d2ae17a5d53c118c7f173f324e02e75b`.
- Exact-head CI [45260937868](https://github.com/tostman1/drink-pos/actions/runs/45260937868)
  completed successfully: both quality matrices and actual non-publishing container,
  migration/recovery/DR/audit gates; publication skipped. This is **base** evidence,
  not evidence for the RL-03 working tree.
- Separate branch `feature/rl-03-financial-history-policy`; preserve all existing
  branches/owner merges. No delegation. No commit/push/PR/merge authorization inferred.
- Existing DP-002/003/004/005/011/013/014/023/024 traceability applies; do not turn
  a proposed accounting choice into a new approved requirement.

## Scope and acceptance before edits

1. Trace actual served handlers through both import modes; enumerate field-level
   snapshot writers, additive operations, read-time derivation and historical rewrites.
2. Compare A exact preservation, B separate provenance-labelled inference, and C
   narrowly approved corrections; include report examples and recommend **without approval**.
3. Inventory reachable source-defined schema changes using only allowlisted Python
   source and independently derived in-memory DDL/PRAGMA metadata. Never execute
   historical application code or open historical runtime files. Distinguish source
   provenance, synthetic reconstruction and authenticated DB/image/release provenance.
4. Add characterization tests of existing financial exceptions and metadata derivation,
   not failing policy assertions followed by financial implementation. No behavior change.
5. Propose fail-closed, installation-specific adoption/reconciliation/recovery gates;
   no executable transition, changed allowlist, production activation or dummy migration.
6. Run targeted tests and full Standard Checks on available Python 3.12/3.13; report
   local/container/manual evidence separately and update traceability/progress/handoff.

## Exclusions and risks

No application/schema/financial/report/UI/service-worker/recovery/deployment changes.
No real installations, historical tracked DB contents, member/financial records,
secrets, registry pulls, releases, real SumUp/SMTP, production scripts or deployments.
Schema equivalence does not establish source installation provenance or cost meaning.
Current zero predicates have no provenance; “immutable audit” is an intended contract
with existing cost/profit exceptions, not a database-enforced guarantee. Previously
overwritten values cannot be reconstructed from current settings. OQ-06 stays open.
