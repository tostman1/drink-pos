# FH-04 — served correction lifecycle and audit coverage

## RL-05 current contract (supersedes RL-04 characterization below)

Owner approved normal **net consumption after erroneous-booking correction** and
separate coordinated round cancellation. Original audit remains immutable. New
CONSUMPTION_CORRECTION detail links exact new booking source/O/person/item snapshots,
original consumption date, signed quantity/VK/EK/cost/profit, actual correction time,
reason/purpose/admin authorization/member request, parent TI/T and committed operation.
New source correlation is recorded at booking, never inferred for old rows.

Negative admin corrections require `correction_operation_id` and
`correction_purpose=erroneous_booking`. Same key+same canonical payload replays exact
stored result; changed payload 409, absent key/purpose 400. New key can intentionally
remove again up to remaining debt. Legacy callers must update; identical unkeyed
requests cannot safely distinguish retries. First-party IDs persisted in sessionStorage
for unresolved online retries, busy guard; no offline correction queue. New bookings
avoid merging into old untracked O. Archived item IDs/persons may be corrected using
their original snapshots; no current-price debt reconstruction.

Member request creation is serialized; optional operation ID replay; pending capacity
enforced. Approval/rejection identity derives from request ID, same decision replays,
opposing decision conflicts; old already-decided requests retain old rejection/unknown
history. Approval requires full current requested quantity (no payment-time silent cap).
Source uncertainty/active or unknown card blocks without mutation. Rejection changes
request status/audit only. Round requests use the special contract, not ordinary TI.

`/api/pay`: all correction decisions and payment effects share BEGIN IMMEDIATE.
Remaining payable debt → actual payment, ordinary paid response retained. Approved
`corrections_only=true` explicitly resolves without payment and returns
`corrections_applied`, payment_required=true and remaining debt when payment remains.
corrections removing all debt → HTTP 200 `status=correction_only`, total=0,
payment_required=false, pending_handled; no fake PAID record. No debt/no work → HTTP
400 detail.status=no_work without committed change. Validation/late-payment failure
rolls decisions/details/quantities/receipts/payment back. `payment_operation_id` supports
exact successful replay; unkeyed cash calls retain legacy semantics (not retry-safe
after new intervening bookings). First-party dialog carries one ID per action.

Reports: normal consumption/top quantities use positive CONSUME plus explicit
CONSUMPTION_CORRECTION, original consumed_date for correction, actual timestamp for
audit. Gross/reversed additive components exposed in stats; current corrected view
can change historical-date counts, not old exported files/as-of snapshots. Debt/tally
uses remaining O once, no double subtraction. Paid profit still reads RL-04 snapshots;
round expense/reversal distinct, no refund/inventory return. Person audit shows original
and signed corrections separately, no historical name/time heuristic subtraction.
Historical ambiguous T-only corrections explicitly flagged unverified in statistics;
no precision manufactured. Details and receipts have FK/uniqueness and immutable
UPDATE/DELETE guards. SQL failure at any stage rolls whole operation back.

Round lifecycle/blocks/reversal/abuse matrix: `round-cancellation-contract.md`.
Real additive schema/version/compatibility: `migration-safety.md`. FH-04 implementation
is under verification, closure only after final full local/exact-head container/CI.

## Retained RL-04 baseline evidence (not current policy)

RL-04 characterization at baseline `8dd961b`; implementation deliberately unchanged.
DP-004 has a known **item-detail exception**; FH-04 remains **OPEN (Medium)**.
Actual runtime: application/registry → `legacy_main`; not prototype orders service.

## Operation contract

O = original remaining order line, with stable person/item/line IDs, snapshot VK/EK,
names/admin/date; T = transaction audit; TI = item audit. Every operation below
retains O's recorded snapshot fields; only quantity/updated_at change on removal.
Existing T/TI are never corrected, deleted or relabelled. No operation here is a
provider refund, payment reversal or inventory return.

| Operation | Original state and requested change | Authorization / quantity and debt effect | T and TI / reporting | Replay / failure and rollback |
| --- | --- | --- | --- | --- |
| Member `/api/edit-request` | Own positive O; explicit `line_quantities` or legacy negative `changes`; reason retained in change_requests | Active member, enabled delete requests, no active card session; normal items or system round, other admin-only snapshots blocked. Available = quantity minus pending removal. O/debt unchanged; inserts PENDING requests | One CHANGE_REQUEST T total=0 with requested names/counts; **no TI**. Consumption and paid reports unchanged | No client idempotency key. Duplicate can create another request if capacity remains; beyond available fails. Multi-line validation or audit failure rolls all inserts back; request IDs/sequence not partially committed |
| Single admin approval `/api/admin/change-request/decide` | Existing PENDING request against O; requested q ≤ current remaining q | PIN; current quantity precheck, `remove_from_order_line` card lock; removes exactly requested q, debt decreases q×original VK. No payment | CHANGE_APPROVED T total=0, text actual q/name; decided_at/status set APPROVED; **no negative TI**. Original CONSUME still counted; later payment covers only remaining O | Non-PENDING replay returns 400. Missing request 404; invalid/insufficient/locked fails without decision/debt/audit commit. Audit SQL failure rolls removal/status/T back. Implicit transaction, not BEGIN IMMEDIATE; no claim of concurrency-idempotent approval |
| Single admin rejection | PENDING request; same original O | PIN; no quantity/debt change | CHANGE_REJECTED T total=0, text requested q/name; status REJECTED; **no TI** | Completed request replay 400. Audit insertion fault rolls status/T back. Does not call removal/card-lock helper |
| Negative admin `/api/admin/adjust-drink` | Positive O for person/item, may span multiple price/date snapshots or closed tally; request delta<0 | PIN; archived person allowed; archived item master is rejected by existing lookup. Newest consumed_date/created_at/id first. Each take=min(remaining request,O quantity); may remove less than requested; debt decrease uses each original VK | One ADMIN_ADJUSTMENT T total=−sum(actual q×original VK), text signed per-part names/VK. **No TI**. Consumption reports keep original CONSUME; open/cashup/payment reflect smaller debt | **Not idempotent**: same request removes again while debt remains; none open returns 400. Active card session blocks removal. Audit fault rolls all line changes back. No new operation ID/automatic retry; implicit transaction, no serialized concurrency guarantee |
| Positive admin adjustment (contrast) | delta>0; new/current snapshot or matching live O | PIN; current item values, adds q and debt q×current VK | ADMIN_ADJUSTMENT T plus **positive CONSUME TI** current cost/profit. Consumption reports include these, except current admin visibility | No replay key; booking/audit failure rolls back. Not a reversal of earlier negative adjustment |
| Pending resolution inside `/api/pay` | All current pending requests must be selected approve/reject (or all flag); unknown/overlap/incomplete selection fails | PIN, person including archived, no active card session. Approval calls removal capped to current quantity (unlike single decision's insufficient-q rejection); rejection leaves O unchanged | Per-request CHANGE_APPROVED/REJECTED T total=0, **no correction TI**; then PAID_CASH T/positive PAID_CASH TI for remaining O, paid-round entitlement and normal round details. Request and payment populations differ | Payment itself has no client replay key. Resolution + payment normally share implicit transaction; late round-pending/amount/audit/detail failure rolls both back. **Exception:** no O and no eligible deduction → explicitly commits resolutions, then returns 400 Keine offenen Posten; no PAID record. Do not infer failed HTTP means no correction was committed |
| `/api/kassa/pay`, card self-pay | Positive O with pending requests | Kassa PIN/current revision; card current revision and provider validation. Neither resolves pending corrections: rejects them first | No correction T/TI. Actual successful payment snapshots remaining O and appends PAID detail; unknown card never paid | Kassa stale rejects without change; card ID replay once/no create retry; state-machine uncertainty unchanged |
| `remove_from_order_line` helper | Existing O ID and positive requested q | Caller supplies authorization; helper itself checks card lock, q>0; actual=min(current q,request), sets floor 0 and updated_at; returns **pre-change row** + actual | **No T/TI by itself**; caller must audit. Original prices/costs/names retained. Quantity zero replay returns actual=0 | Missing 404/nonpositive 400; caller transaction determines commit/rollback. No payment/refund semantics or independent idempotency |

Member request capacity checks, single approval prechecks and negative adjustment
selection are read-before-write implicit transactions. SQLite serializes writes but
these routes do not implement revision/idempotency arbitration for simultaneous
corrections. Existing round/stale-payment serialization is a different contract.
RL-04 does not widen their concurrency guarantees or silently add BEGIN IMMEDIATE.

## Consumer coverage / decision

- Debt: positive O×VK, regardless of event_open; corrections alter remaining debt.
- Cashup: remaining tally plus normal eligible round deductions; does not pay/forgive
  residual debt. Removing a system round changes entitlement available from unpaid
  O; does not revoke already-paid units or reverse historic round_events.
- Consumption preview: CONSUME TI including positive admin additions; excludes T-only
  negative correction. Statistics additionally drops nonpositive CONSUME quantities
  and uses current item visibility. Raw item export includes all TI kinds and OPEN.
- Paid/profit: PAID_CASH/PAID_SUMUP TI (+ROUND_DEDUCTED expense for profit). Correction
  T total=0 or signed debt adjustment is not paid revenue. Transaction history shows
  those T entries, but cannot reconstruct exact snapshot costs/source line details.
- Named-event corrections have their separate EL/T contract; not FH-04 member debt.

**Implementation decision: characterization only.** Introducing negative CONSUME,
ROUND_DEDUCTED or REFUND details would redefine at least consumption, entitlement or
paid-report populations. No unambiguous existing kind covers debt-only correction
with original line provenance. Do not fabricate prior missing details or store estimates.

## Concrete follow-up proposal / owner acceptance gates

1. Choose debt-only detail kind and source-line/request/operation correlation; decide
   whether CONSUME is gross bookings or corrected consumption and whether correction
   reports post request/decision/original dates. Do not reuse payment/refund kinds.
2. Define per-snapshot signed VK/EK/cost/profit, zero/nonzero authority, capped versus
   insufficient-quantity behavior and system-round entitlement policy explicitly.
3. Define explicit operation IDs/replay/revision/concurrency (one operation cannot
   remove twice), insufficient state and the current no-debt commit-before-error API.
4. Acceptance: original O snapshot/T/TI unchanged; one new correlated detail per
   affected original O; requested/actual quantities retained; sum debt reduction
   matches original VK; chosen consumption effect proven separately from paid totals;
   no provider refund/inventory change; no historic backfill.
5. Regression: multi-price rows, mixed signs/zero EK, archived persons, round items,
   pending-payment approvals/rejections, no-debt case, duplicate/concurrent requests,
   active/unknown payment, item-detail/T insertion faults and rollback of all new
   effects; EF-08 complete recovery; unchanged HTTP compatibility unless approved.

## Evidence

`tests/test_financial_integrity.py::CorrectionAuditTests` tests request/approve/reject,
pending capacity, replay, newest/capped negative adjustment, insufficient approval,
payment resolution and no-debt commit boundary, real SQL audit faults, request fault,
active-payment guards and removal-helper snapshot preservation. Existing backend
round/payment/cashup/replay regressions remain. Synthetic only; no accounting policy
or concurrency safety inferred from sequential characterization or green CI.
