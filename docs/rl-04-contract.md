# RL-04 — financial integrity ready gate

Owner authorization 2026-11-24; clean local/fetched main baseline
`8dd961bfb23d7fe090a8cf2895a269bb544db09e`, branch
`feature/rl-04-financial-integrity`. DP-002/004/005/013/014/024.

## Work plan before implementation

1. **FH-01:** served `legacy_main.admin_update_drink` updates current items, then
   two zero-predicate O/TI UPDATEs, then ITEM_UPDATED audit/commit. Remove only the
   history writes; retain master edits and audit rollback. Test unchanged/repeated
   saves, signed/paid/closed/archived/nonzero/zero snapshots and subsequent bookings.
2. **FH-02/06:** `_init_legacy` calls `ensure_default_items` (existing zero master
   replacement) and `backfill_missing_purchase_snapshots` (four historical UPDATEs).
   Remove inference/reset and the backfill helper/call. Create missing defaults only.
   Preserve round master normalization, additive DDL and existing prototype import
   compatibility; no new import/adoption/reconstruction. Existing recorded rows stay
   exact, even unusual round costs or inconsistent totals/profit.
3. **FH-03:** `admin_statistics` paid rows use truthiness fallback; paid branches in
   `build_report_rows` always derive; `export_item_summary` sums stored profit for
   every kind. Use present stored paid profit (including zero), fallback only when
   absent/None. Keep consumption expense, consumption potential margin, OPEN and
   ROUND_DEDUCTED expense formulas. Reconcile paid-only like-for-like subsets, not
   entire exports/consumption/payment/round populations. Keep shapes/rounding/CSV.
4. **FH-04:** trace edit request → single decision/payment resolution or negative
   adjustment → `remove_from_order_line` → transaction audit, with no negative TI.
   Characterize lifecycle, replay, authorization, quantity/debt and rollback faults.
   Do not add signed correction TI unless existing semantics are unambiguous; current
   consumers select CONSUME and round kinds, so leave policy-dependent gap open.
5. **Evidence:** failing regressions first; convert RL-03/RL-01 defective expectations
   (retain former receipts in docs), full-state synthetic repeat/adoption/recovery,
   both import/startup modes, network-disabled installed-image rehearsal, full local
   Python 3.12/3.13 gates and exact-final-head branch/PR/container/DR CI.

## Invariants and deliberate differences

Recorded O prices/costs and TI identifiers/signs/prices/costs/totals/profit/timestamps
are not rewritten by current product/default changes or startup. Zero is recorded,
not missing-data provenance. T/RE/entitlement/provider/client/event/invoice/audit and
sequence relationships remain intact. Operational quantity/tally/payment/status fields
still change through legitimate operations; new bookings snapshot current master data.
Audit failure rolls master edit back. Defaults initialize missing products, not existing
zero EK. No schema/ledger/version/fingerprint/default-mode/deployment/UI change.

Paid reports now expose inconsistent recorded profit faithfully rather than deriving
a replacement. Aggregate rounding remains existing binary REAL/round/decimal-comma.
NULL/absent fallback is defensive read compatibility, not support for nullable schemas.

## Explicit exclusions / owner decisions remaining

OQ-06 stays open for historical correction/reconstruction/inferred-cost storage,
round accounting, correction detail/report-period semantics and additional authentic
legacy adoption. FH-04 and FH-05 remain open. No fabricated before-images/refunds,
historical invoice/export regeneration, production data/migration/deployment/publication,
real SumUp/SMTP, updater/schedule activation or merge. EF-08a Windows WinError 5 and
MV-01..05/operational MV-06 remain unresolved. No agent delegation.
