# RL-05 ready gate — transaction integrity and coordinated round cancellation

Owner mission and mandatory addendum 2026-11-24. Verified clean/fetched main
`2cc36fd69ec56dbdfe65ffb7ed98600d7c33b7c4`; branch
`feature/rl-05-transaction-integrity`. DP-002/004/005/006/007/013/014/024.

## Approved model / implementation plan before code

1. Preserve original T/TI/O financial fields. New booking-source rows correlate
   CONSUME TI to original O; corrections append source-linked signed
   CONSUMPTION_CORRECTION TI/details with operation ID, request/operator/purpose,
   original date/price/EK and actual correction timestamp. Distinct price/date
   sources stay distinct. Unknown old source attribution blocks automatic correction;
   no matching-by-description/current-price/date reconstruction.
2. New operation receipts store canonical payload + committed response. Negative
   admin removal requires ID and explicit erroneous_booking purpose; absent IDs
   rejected with actionable compatibility error, not unsafe best-effort retries.
   Member keyed creation additive; approval/rejection identity derives from request
   ID, same decision replays, opposing decision conflicts. Cash pay supports keyed
   outcome replay. First-party action IDs retained during unresolved retries, busy
   guard, no offline correction queue. Failed transaction never caches success.
3. Explicit BEGIN IMMEDIATE at served request/decision/adjust/pay/cashup/manual-round
   write boundaries; helpers participate, never start nested transactions. SQLite
   uniqueness plus conditional quantity changes enforce one effect, shared rollback
   of O/request/receipt/T/TI/provenance. Active/uncertain card guards remain.
4. Normal consumption = positive CONSUME + explicit approved ordinary correction
   detail. Correction reporting date = original consumed_date; audit date = actual
   operation time. Gross/reversed/net additive transparency; existing normal quantity
   becomes net. Paid snapshots/profit unchanged, round reversal never new CONSUME;
   named events/invoices separate. Current tally/debt O already reflects quantities,
   do not subtract correction again. Legacy T-only coverage explicitly unverified.
5. Real additive v1→v2 schema: operation receipts, booking-source correlation,
   correction details, individual round units, deduction attribution, and unique
   reversal records. No original table rebuild or historical row backfill. Frozen
   v1 recognition/ledger retained; v2 exact schema/ledger validates, fresh and current
   unversioned installs supported, unknown historical shapes still rejected in strict
   mode. Default legacy retained; transactional extension and compatible ledger gate.
6. All new round booking paths allocate stable unit IDs (not round_index). All new
   manual/person/cashup deductions link unit/person/original drink O/TI/round_event;
   UNIQUE(unit,person), UNIQUE(reversed deduction). Planning skips cancelled/pending
   units and exact existing allocations, never reallocates count/index offsets.
7. Unpaid/current-period tracked round cancellation: validate entire requested impact
   before writing; cancel units + restore exact O quantities + append reversal TI/
   provenance/compensating events atomically. Restoration does not increase physical
   consumption. At most one reversal; other rounds unchanged. Preview exposes impact
   before admin approval where feasible. New keyed cancellation endpoint and member
   approved round requests; generic round negative operation routes through same logic.
8. Paid round, cashup/closed, settled affected member or unknown/active provider,
   missing original unit/deduction/source: fail closed intervention_required without
   partial restoration. No refund/reopen-period authority. Admin instructions identify
   missing evidence; separately authorized manual reconciliation only.
9. Test-first served HTTP: net 5−2=3, cross-date/source/cost/zero, rejection/replay/key
   conflict, real concurrency, SQL faults, process interruption, paid/round abuse,
   partial multi-unit cancellation and unrelated round preservation. Versioned fresh/
   v1 migration/interrupt/recovery; both Python full gates, browser/worker review,
   actual-image reconciliation/EF-08a/b/c source-loss recovery and exact-head CI.

## Existing round attribution limitations (baseline evidence)

`current_event_round_units`: open O quantity expanded dynamically first by date/id,
then paid_round_units by created/id; no individual open unit ID. `round_index` shifts
when O paid/cancelled. `current_event_round_deduction_counts` sums ABS ROUND_DEDUCTED
per person since CASHUP, no unit membership. Person/auto planning slices/compares
that count; cannot distinguish two rounds. `preserve_paid_round_units` creates new
paid identities without linking individual pre-payment units. Person RE aggregates
multiple deductions; auto RE per dynamic round, no durable source relation. Manual
`deduct_round` independently removes cheapest current drink per person without
requiring any booked round; TI item_id=NULL, no O/unit correlation. Historical
records must stay untouched and must not be given inferred links.

## Outside authority / stop gates

No historical detail fabrication, new historical fingerprint, physical stock return,
debt-only waiver presented as consumption, provider/cash refund, paid entitlement
revocation, closed-period reopening or as-of reports. FH-05/OQ-06 broader choices
open, EF-08a WinError 5 unresolved, devices/real provider/storage acceptance gaps.
No production DB/deploy/release/publication/updater/schedule/real SumUp/SMTP or merge.
Keep PR open for independent review. Addendum is part of this package; unsupported
round reversals cannot masquerade as successful ordinary corrections.

## Independent review corrections R5-01/02 — 2026-11-24

Continue reviewed `f4d56ffcb4992dfbef813f05ab5feafc19a88f52` on existing PR #10.
DP-004/005/013; failing served tests before implementation. R5-01 keeps the original
ROUND_DEDUCTED +abs(VK) convention; its exact reversal contributes −abs(VK), just
as its expense/profit contribution already compensates. Read-only profit preview/
CSV/statistics finance and round-event reconciliation tested, physical consumption/
paid stored profit/debt/entitlements unchanged.

R5-02 coverage must validate complete source-linked ordinary **or** round operations,
not merely existence of a correction_details row. Recognize round cancellation,
every original deduction's reversal, member request/reservation and committed receipt;
missing/inconsistent/partial links remain unverified, old T-only rows never inferred.
Narrow necessary provenance discovery: member-decision receipt currently has NULL
parent transaction_id, so the exact CHANGE_APPROVED audit cannot be authenticated
relationally. Populate that existing field for new decisions only (no receipt UPDATE
or schema change); pre-fix NULL-linked approval audits remain unverified. Add failure/
partial-state fixtures and read-only state comparisons; retain strict v2 schema/
ledger, concurrency/replay/rollback and installed-image financial/EF08 gates.
