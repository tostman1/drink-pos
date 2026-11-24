# RL-05 coordinated round cancellation and abuse-prevention contract

Owner addendum 2026-11-24; implementation under verification, no production rollout.
See `rl-05-contract.md`, `correction-audit-contract.md` and migration safety.

## Identity and lifecycle

Every new served round booking appends individual `round_units` linked to original
O and booking TI with unit_number; a multi-unit O has distinct durable IDs. New
ordinary booking correlation is `booking_sources` (O↔CONSUME TI/date). New deductions
append `round_deductions`: unit/person/O/TI/RE/date, UNIQUE(unit,person). Original
deductions never updated/deleted. Effective reversal is a separate `round_reversals`
row with unique original deduction FK and new TI/RE/operation receipt. Cancellation
has `round_cancellations` signed ROUND_CANCELLATION detail and reason/operator/request.
No identity from current round_index/name/price/count/description.

New tracked state: BOOKED/ELIGIBLE → per-person DEDUCTED; pending change request
holds the entire affected round O (all its units) → APPROVED cancellation or
REJECTED release. CANCELLED is permanent and never planned; CLOSED after CASHUP
never automatically reopened. Paid unit↔original unit mapping lives in
`round_unit_payments`; payment never shifts the unit identity. `round_index` is
presentation only. Cumulative counts remain display information, never allocation.

## Implemented safe and blocked states

| State | Automatic behavior |
| --- | --- |
| New tracked unpaid/current round, no deductions | Cancel specified units, signed round detail, reduce exact original round O; no fictitious drink restoration |
| New tracked unpaid/current round, attributable deductions, affected people not subsequently settled | One atomic cancellation restores each original O by 1, preserves member/item/VK/EK/date, appends ROUND_DEDUCTION_REVERSAL and separate compensating RE; one reversal per deduction |
| Multiple rounds/multi-unit line | Explicit unit list or deterministic newest units of one requested O; only linked deductions reverse, other unit allocations stay fixed |
| Pending request | Whole source line held from deduction planning; approve uses same cancellation, reject releases eligibility; active requests serialize with writes |
| Paid round (with or without deductions) | intervention_required, no refund/revocation/history change |
| Completed cashup/closed original round or affected O | intervention_required, no reopening |
| Affected person paid after original deduction | intervention_required, no new debt for settled person |
| Active/unknown card state on payer or any affected member | intervention_required, all state retained; no provider calls |
| Old/untracked unit, current unassigned ROUND_DEDUCTED, conflicting snapshots | intervention_required, no attribution guesses; new deduction blocked if unassigned current history exists |

Manual `/api/deduct-round` now requires `round_unit_id` obtained from preview and
a booked eligible round. Unkeyed/manual-without-booking prior behavior is intentionally
not retained: it lacked causal entitlement and could create free deductions. Reusing
the same unit/member cannot deduct twice, even after cancellation/restoration/restart.
First-party manual UI carries preview ID. Admin/PIN-only cancellation endpoint and
preview; members can request, never approve a reversal. Agent cannot cancel.
Manual commit also records a durable per-unit operation receipt; same still-valid
unit replays its original response, rather than applying to newly booked drinks.
Cancelled/closed units are blocked before any further deduction. Pending round
requests block cashup, so pending → rejected can release the same current units
without silently closing the cancellation period.

## Reconciliation example

A books one 10,00 round, B/C each have a 3,00 drink (EK 1,00/0,00). Attributed round
deducts their drinks: B/C open debt 0. Before any payment/cashup, A's authorized
cancellation reduces A's round debt by 10,00 and restores B/C open debt to 3,00 each.
Original CONSUME remains +1 each; gross/net physical consumption stays 2, not 4.
Original negative deduction TI/RE retained. Reversal TI values +3,00, costs +1,00/
0,00; profit report's round expense offsets explicitly, paid revenue unchanged.
ROUND_CANCELLATION is never ordinary CONSUMPTION_CORRECTION or paid/refund detail.

## Atomicity and abuse invariants

BEGIN IMMEDIATE serializes cancellation, corrections, cash payment, manual deduction
and cashup. All validation precedes committed effects; O updates/cancellation state/
new T/TI/RE/provenance/receipt commit together. Same key+canonical payload returns
stored committed response, different payload conflicts. Failure rolls back receipt
and every restoration. UNIQUE(unit,person), UNIQUE(reversed deduction), FK/snapshot
guards and provenance UPDATE/DELETE triggers survive backup/recovery. No source-less
payment/inventory effect or original financial rewrite.

Test matrix: book→deduct→cancel→replay→attempt deduction; two rounds cancel one;
multi-member exact restoration; partial multi-unit/pending reject; concurrent duplicate;
each table write fault; paid/cashup/unassigned current history blocks; net/gross/paid
report separation. Further device/operational acceptance required; tests are synthetic.

## Unsupported legacy/manual reconciliation

Old paid_round_units and ROUND_DEDUCTED records may have NULL item/O/unit IDs and
aggregate RE. No startup/migration reconstructs them. Preserve old audit and whole
EF-08 snapshot; administrator must identify original booking/deduction/member/payment/
period evidence under separately authorized reconciliation. Do not match approximate
order/prices/counts or delete old paid records to bypass. Refund/closed-period policy,
authentic historical artifacts and operational authorization remain outside RL-05.
