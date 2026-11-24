# Historical financial preservation and legacy adoption decisions

## RL-05 scoped owner decisions — 2026-11-24

Normal consumption is current net consumption after approved erroneous-booking
corrections, attributed to original consumption period. Original T/TI financial
snapshots remain unchanged; corrections append source-linked detail and actual audit
timestamp. Round cancellation separately cancels durable unit entitlement and reverses
only exact linked deductions when unpaid/current/unsettled; paid/closed/unknown/legacy
attribution blocks. Paid revenue/profit snapshots stay authoritative; restoration is
not new physical consumption. See correction-audit/round-cancellation/rl-05 contracts.
No old correction inference, historical export/invoice regeneration, refunds, as-of
reports or extra historical fingerprint. FH-05 and broader OQ-06 remain open.

R5-01/02 review corrections: round-finance VK uses original deduction +abs(total)
and compensating reversal −abs(total), matching its signed expense/profit and separate
round-event totals. Physical net consumption/paid snapshots unchanged. Audit coverage
recognizes complete source-linked round as well as ordinary corrections; incomplete
or historical T-only/NULL-parent receipts remain unverified. New member receipts
record the existing approval parent FK, never backfilled. See correction/round contracts;
no storage/migration/historical financial UPDATE or provider/refund change.

## RL-04 scoped owner authorization — 2026-11-24

**Routine snapshot preservation is approved and implemented for review**, baseline
`8dd961bfb23d7fe090a8cf2895a269bb544db09e`. The owner authorizes preventing routine
historical rewrites, not all of A/B/C or OQ-06. Recorded zero is not automatically
missing. FH-01/02/06 served cost/profit UPDATEs removed, existing default-item zero
master retained; new bookings use current master. No historical repair/inference,
additional adoption, schema/version change or production migration.

FH-03 paid snapshots use present stored profit including zero in statistics and
both paid preview/export-report branches. Missing/None defensively falls back to
sales−cost; exact schema disallows NULL profit, so this does not widen adoption.
Consumption potential margin/expense, OPEN, event tally and ROUND_DEDUCTED expense
retain operational formulas. Raw item export retains all-kind stored profit; no
attempt to reconcile unlike concepts. See `docs/rl-04-contract.md` and
`docs/correction-audit-contract.md` for inclusion rules/acceptance and FH-04 OPEN.

### Current historical-write inventory (supersedes baseline matrix below)

| Path | Current write / preservation boundary |
| --- | --- |
| `admin_update_drink` | Current master UPDATE + ITEM_UPDATED T only; failure rolls back master. No O/TI UPDATE, unchanged or repeated EK save cannot backfill |
| `_init_legacy` | No backfill helper/call. No UPDATE of recorded O/TI costs/profit or round snapshots. Missing default inserts only; existing default EK=0 retained |
| `ensure_round_item` / round settings | Existing **master** normalization intentionally retained (EK=0/settings VK/active/admin); no O/TI/RE/paid-unit rewrite |
| Additive column DDL | Existing supported legacy compatibility adds absent columns with schema defaults; does not infer values from current costs. Missing-column provenance is not reconstructed; not immutable-schema/whole-startup atomicity |
| `migrate_items` / `migrate_old_orders` | Existing prototype compatibility still inserts only under old guards using current values/date; no extra import/adoption/meaning approval, not a historical correction process |
| `add_order_line`, transaction logging/payment/round/event | New snapshot INSERTs; legitimate matching quantity/tally/status updates unchanged. Debt/payments/corrections may alter remaining quantities, never original unit financial fields |
| RL-02 adoption/repeat | Exact-current metadata-only/no normalization; same fingerprint/v1/DELETE-journal/fail-closed gate, fresh initializes missing defaults |
| EF-08 recovery / old CSV | Separate target recovery, bounded event-path relocation only; CSV remains partial reconstruction, not exact recovery/history authentication |

Search of app SQL UPDATEs and dynamic updates finds no remaining routine historical
cost/profit UPDATE. Prototype services still unserved. External SQL/custom triggers
remain unknown. No immutability DB trigger or freeze of operational fields is added.
Already overwritten originals cannot be recovered from current masters; no repair
is attempted. Fresh/legacy/versioned/API/recovery evidence is synthetic only.

### Reporting reconciliation boundary

Paid basis = PAID_CASH/PAID_SUMUP signed TI quantity, total_eur, purchase_total_eur,
profit_eur at TI timestamp; archived records retained. Compare preview revenue
(or profit absent deductions), raw export filtered to paid kinds, statistics finance
with identical period and include_admin_items=True. Preview paid kinds do not filter
current admin flags; stats can. All-kind raw export, consumption, fees in T totals,
named invoices and round_events are not this paid population. Aggregates round once
at presentation; raw grouped export rounds per group, so subcent grouped sums can
differ from one rounded global sum. No money-storage/rounding policy changed.

Regression fixtures cover recorded zero with positive **and negative** derived
profit, stored signed/nonzero/subcent values, period endpoints/archive/admin filters,
round expenses and consumption margins; reports never write DB state. FH-04 detail
semantics and FH-05 authentic adoption evidence remain open; OQ-06 unresolved.

## Retained RL-03 decision/evidence record (historical baseline, not current runtime)

**RL-03 status at its baseline: proposed, NOT approved or implemented.** Decision owner: repository owner.
Evidence date: 2026-11-23. Baseline `33c16979d2ae17a5d53c118c7f173f324e02e75b`.
Ready gate: [rl-03-contract.md](rl-03-contract.md). Addresses remaining **OQ-06**;
RL-01/02 are integrated, not authorization for accounting or production adoption.

## Executive decision

Recommend **A as the preservation invariant, B as a separately authorized analytical
extension**: keep every recorded original cost/total/profit, including zero and
unusual round costs; keep uncertainty explicit. If estimates are needed, append
separate provenance-labelled estimates and expose an explicit estimated report,
never overwrite originals or use estimates for debt/payment. Defer **C** unless an
owner-approved correction workflow is demonstrably required; prefer append-only
adjustments rather than rewriting audit rows. No option is approved by this document.

The current app does **not** guarantee immutable financial snapshots: both default
startup and the served item-update API rewrite them. RL-02 metadata adoption/repeat
preserves existing state **during startup**, but does not neutralize that API.
Preservation needs a later, separately authorized behavior package at both seams.

Distinct open findings, engineering severities, exact source paths, synthetic
evidence and proposed follow-ups are indexed as **FH-01..FH-06** in
[AUDIT.md](AUDIT.md#rl-03-distinct-financial-history-findings--open). The current
runtime facts, source-derived schema evidence, unavailable authenticated artifacts,
synthetic demonstrations and proposed future behavior are different evidence classes.
High findings prioritize owner decision/next engineering work; they do not claim
live financial loss or authorize fixes in RL-03.

## 1. Recorded facts, missing evidence and current values

| Field / state | Recorded meaning and evidence limits |
| --- | --- |
| `items.purchase_price_eur` / `price_eur` | Current editable product settings, not a dated purchase-cost history. Zero is accepted by admin API. Defaults may replace zero on legacy startup. |
| `order_lines.unit_price_eur`, `unit_purchase_price_eur` | Rounded master values when a booking row is created; matching subsequent bookings aggregate quantity. Positive quantities represent remaining debt, not immutable original consumption quantity. Offline/agent client dates can precede server receipt, but prices/costs come from server settings at processing time, not independently evidenced historical settings. |
| `transaction_items.unit_price_eur`, `unit_purchase_price_eur` | Operation detail snapshots. `log_transaction_item` defaults absent/NULL-like inputs to zero; no provenance records whether cost was known. Consumption uses current master; settlement/deduction uses then-stored order snapshots. |
| `transaction_items.quantity`, `total_eur`, `purchase_total_eur`, `profit_eur` | Signed quantity; initial detail totals are `round(q×VK,2)`, `round(q×EK,2)`, `round(q×(VK−EK),2)`. Backfill instead uses unrounded SQL multiplication and stored total minus cost. Stored profit can differ from a later report-derived profit. |
| `transactions.total`, `type`, `timestamp`, `details` | Operation audit, not a sum of all historical detail revenues. Card total can include fees/rounding absent from detail sales. Approval/cashup totals have operation-specific meaning. Text is not a complete before/after cost-correction audit. |
| `round_events.*` financial fields | Snapshot of a round operation: round price, deducted VK/EK, differences versus each; payment-time deduction writes zero round price and negative cost/VK differences. Not the system item's own purchase snapshot. |
| `paid_round_units.round_price_eur`, `payment_transaction_id`, `source_order_line_id` | Preserved paid-round entitlement and payer/sales snapshot; no independent purchase-cost field. |
| `event_lines.unit_purchase_price_eur`, `unit_price_eur` | Separate named-event aggregate snapshots; matching quantities aggregate. Not legacy member tally or member payment. Current historical backfills omit these rows. |
| `event_sessions.total_eur`, `discount_total_eur`, invoice flags/paths | Closing invoice sales/discount/artifact state. Not confirmation of payment; discounts have no new accounting cost-allocation policy here. |
| Historical missing EK column | Absence is evidence of missing storage capability **only for that independently authenticated schema**. Adding NOT NULL DEFAULT 0 erases the distinction in migrated rows. No authenticated pre-EK source/release was found. |
| Existing zero, NULL, missing item ID | Zero can be gifted stock, a legitimate configured zero, a default placeholder, import inference or prior normalization. Exact current DDL disallows NULL EK but accepts NULL item IDs; nonstandard nullable schemas are unsupported. No numeric sentinel proves provenance. |

**Never infer “unknown” from zero.** Conversely, preserving a zero does not certify
that cost was truly zero. Describe ambiguous stored values as “recorded zero;
provenance unknown”, unless separate evidence establishes known-zero status.
Missing evidence may justify an explicit uncertainty label, not a guessed value.
Already overwritten originals remain unrecoverable absent separately verified old
snapshots; current master settings and comments cannot reconstruct them.

## 2. Field-level write-impact matrix

Evidence references below are paths/functions at the fixed baseline, not line numbers
that drift. O=order_lines, TI=transaction_items, T=transactions, RE=round_events,
EL=event_lines. **Existing-value write** differs from a new operation snapshot.

| Path / trigger | Exact fields written and source | Existing history affected / audit / limits |
| --- | --- | --- |
| `db/schema._init_legacy` additive EK columns | `items.purchase_price_eur`, O/TI unit EK, TI purchase total/profit added with `REAL NOT NULL DEFAULT 0` when absent | Existing rows acquire default values; no row origin marker or correction record. Guarded DDL is not whole-startup atomicity. |
| `schema.ensure_default_items`, each legacy start | Existing `items.purchase_price_eur`: zero → positive `DEFAULT_ITEMS` value when matching name and configured default>0 | Master-only direct write, but precedes historical backfill. Legitimate master zero indistinguishable; no audit. Nonzero masters retained. |
| `schema.ensure_round_item` on legacy start; fallback from member/admin round routes | Existing round item's `name`, `short_label`, `price_eur`, `purchase_price_eur=0`, active/admin flags, archive reset; price from current round setting/default | Master normalization, not historical correction. New insert if missing. No cost-change audit. |
| `schema.backfill_missing_purchase_snapshots`, ordinary O predicate | O `unit_purchase_price_eur` ← current matching item EK where `item_id IS NOT NULL`, `COALESCE(unit EK,0)=0`, current EK>0 | **All** matching rows, including paid quantity-zero, old `event_open=0`, archived items/persons; no date/kind/provenance filter. Does not change `updated_at`, names, VK, quantity or debt. No audit. |
| Same helper, ordinary TI predicate | TI `unit_purchase_price_eur` ← current EK; `purchase_total_eur=quantity×current EK`; `profit_eur=total_eur−quantity×current EK`, same predicate | **All kinds**, signs and dates, even inconsistent existing purchase total/profit when unit EK=0. Nonzero unit EK is retained even if totals inconsistent. NULL item IDs cannot match; name is not ordinary-cost lookup. No correction audit/timestamp. |
| Same helper, round O predicate | O `unit_purchase_price_eur=0` where snapshot name exactly `1 Runde` **OR** linked current item name `1 Runde` | Unconditional **nonzero or zero** rewrite, all quantities/dates. Name-only rows with NULL ID also match. No audit. |
| Same helper, round TI predicate | TI `unit_purchase_price_eur=0`, `purchase_total_eur=0`, `profit_eur=total_eur`, same round predicate | Unconditional **nonzero** history rewrite, all kinds/signs. RE/EL are **not** adjusted; no audit or timestamp. |
| `legacy_main.admin_update_drink`, `POST /api/admin/drinks/update` | `items` current name/label/VK/EK/active/admin/sort; when submitted EK>0: O unit EK and TI unit EK/purchase total/profit, same item ID and zero-unit predicate | **Existing history changed in both startup modes.** No current-cost comparison, so saving an unchanged positive EK can trigger it. New `ITEM_UPDATED` T logs current master edit, not affected IDs/old values/counts; originals overwritten without TI correction. Names/VK/timestamps of old rows unchanged. System name edit blocked. |
| `legacy_main.admin_update_settings`, round-price setting | Setting plus round item's VK, EK=0, label/active/admin/archive | Master-only; new settings audit. O/TI/RE unchanged at this operation; later legacy start may normalize round history. |
| `schema.migrate_items` / `migrate_old_orders` | New items from `drinks` by missing name (purchase=0); new O only if O empty and `orders.drink` exists; positive quantity, current item's VK/EK/name/admin, today/current timestamps/event_open=1 | **New inferred rows**, not verified consumption-time history. Unmatched item inserted inactive with VK/EK=0. Old drinks/orders retained; no TI/T import audit, mapping/provenance marker or original date/price recovery. Can reimport if O later emptied; ignores negative/zero orders. |
| `legacy_main.add_order_line`: member `/api/add-drink`, agent `/api/agent/book-drink`, positive admin adjustment, round approval, debug additions | New O snapshot from current item values; only quantity/updated_at changes on exact matching active row | No existing cost rewrite. Rounded O values; TI raw unit inputs can have subcent differences. Debug additions lack item-level consumption audit. Round approvals explicitly pass EK=0 to TI but O uses stored item EK, so preserved unusual round master EK can produce differing new snapshots. |
| `services/statistics.log_transaction` / `log_transaction_item` | New T operation total, new TI snapshots and signed totals from caller | Append only at these helpers; no old TI writes. Booking failure rolls uncommitted financial/audit writes back. No DB immutability triggers in exact current schema. |
| `legacy_main.remove_from_order_line`; approved member correction, negative admin adjustment | O quantity reduced/zeroed and updated_at; T approval or negative adjustment totals/details | Retains cost fields, but changes **live remaining** cost/profit totals as quantity changes. Member approval T total=0; negative admin T sales total signed. Neither path adds signed TI correction. Do not claim consumption reports fully reverse corrections. |
| Payment handlers `pay`, `kassa_pay`, confirmed `self_pay` settlement | New PAID TI from remaining O snapshots, paid-round units, T; O quantity=0/updated_at; self-payment status/provider correlation | No old cost rewrite. Uncertain/mismatched/stale SumUp leaves debt open. Fees/rounding remain server-calculated, not cost inference. Cash and card operation totals need not equal raw detail sums. |
| `apply_person_round_deductions`, `apply_auto_round_deductions`, `/api/deduct-round` | O quantity decrement, signed −1 ROUND_DEDUCTED TI, new RE cost/VK/differences; auto closes paid-unit flags | Snapshot from selected O; manual deduction TI has **item_id=NULL**, auto/person retains ID. Later ordinary backfill can mutate ID-linked TI only; RE remains original. Cashup then closes tally flags, not remaining debt. |
| Named-event `services/events.add_event_item` / `remove_event_item` | New EL snapshot or quantity±1/updated_at, session updated_at; served EVENT_ITEM_* T audit signed sales amount | No EL cost changes; latest positive snapshot used for removal. No TI audit for event lines. `close_event` writes closing totals/discounts/flags/paths; required CSV→optional PDF→SMTP→DB ordering unchanged. |
| RL-02 `db/migrations.migrate` adoption / valid repeat | Adoption ledger DDL/row and version/application PRAGMAs; repeat validation only | **No existing business/financial field changes**; fresh only invokes original initializer with no history. No additional fingerprint enabled in RL-03. |
| EF-08a/b/c backup/recovery, `restore_database.restore_csv` | New-target copy or reconstruction; application restore relocates only `event_sessions.csv_path/pdf_path` | No in-place cost correction. Full DB snapshot preserves facts; legacy CSV inserts provided fields, defaults omitted fields and recomputes sequence maxima, excludes some tables; not exact all-state recovery. Restored state started in legacy mode can subsequently backfill. |
| Prototype `services/items.update_item`, `orders`, `payments`, `rounds`, separate route modules | Dynamic **master** item UPDATE; new order/payment snapshots or quantity updates | Not mounted by served registry; no additional historic cost/profit UPDATE found. Preserve but do not mistake them for served accounting contracts. |

Within repository app/runtime/recovery code, the direct existing historical cost/profit
mutators are **additive defaults**, the four SQL UPDATEs in
`schema.backfill_missing_purchase_snapshots`, and the two SQL UPDATEs in
`legacy_main.admin_update_drink`. Master normalizers/imports feed those changes or
new snapshots. Search covered SQL UPDATE/INSERT/DELETE plus dynamic master updates;
no served refund API or historical TI/T delete/update beyond those cost exceptions
was found. External scripts, custom triggers and direct operator SQL are **unknown**,
not guaranteed absent. Synthetic test/rehearsal UPDATEs deliberately construct edge
states and are not application policy or authentic financial data.

### Transactions and audit limits

Default legacy startup runs on each start without a completed-backfill marker;
early DDL/WAL/message effects can survive a later failure, while subsequent DML rolls
back on close. `admin_update_drink` master/backfill/audit share an implicit DML
transaction and commit; it is not a dedicated reviewed correction process.
Audit transaction text and RE snapshots may disagree with rewritten TI. There is no
automatic reconciliation. SQL costs are REAL, not decimal-ledger precision; do not
silently round/fix stored values or add an accounting-money migration in this package.

### Read-time derivation and reporting (no DB writes)

- `build_report_rows`: consumption uses CONSUME details (including positive admin
  additions), reports cost and **−cost**, not paid revenue. It does not include
  member/admin correction T-only operations. Revenue/profit use paid TI; paid profit
  is **sales−stored purchase total**, regardless of stored profit. ROUND_DEDUCTED
  profit is **−abs(stored purchase total)**, revenue zero; signed negative detail
  total is not treated as a cash refund.
- `admin_statistics`: paid profit uses `stored_profit or (revenue−cost)`; recorded
  **zero profit is reinterpreted at read time** if inconsistent with the derived
  value. No database rewrite, but exact preservation alone does not guarantee an
  exact-recorded report. Consumption visibility joins current `items.admin_only`;
  master edits can alter historical report inclusion even without cost writes.
- `export_item_summary` sums **stored profit**, while report preview derives paid profit.
  Member/open statistics use remaining O quantity×cost; round report uses RE fields.
  Named events/invoices use separate EL/session sales and discounts; general member
  profit reports are not a complete named-event profit ledger.
- Debt/payment base is positive remaining O quantity×VK independent of event_open.
  Cost changes alter open-cost/profit estimates but not VK debt, card charges or
  round choice (VK ordering). Cashup closes tally after eligible round deductions;
  it does not forgive residual debt. No estimate may settle payment or reverse it.

## 3. Options for owner decision

| Dimension | A — exact originals | B — originals + separate inference | C — controlled historical correction |
| --- | --- | --- | --- |
| Correctness | Truthful record of what was stored, including unknown/incorrect values; does not invent actual EK | Same factual integrity; estimates explicitly not proven purchase facts, unknown can remain unknown | Can improve an evidenced error; cannot infer truth from current EK or numeric zero alone |
| Auditability | Best baseline integrity; preserve raw values and acquisition evidence | Original + append-only inference/provenance/version/reviewer; distinguish every report basis | Require affected IDs, before/after, reason, evidence, authorization, effective/recorded dates and reconciliation; prefer additive adjustment with originals retained |
| Migration complexity | Low data complexity, but remove both implicit rewrite seams in later approved work; optional flags are not policy | Additional storage/model/reporting design and binding to source rows; estimates must survive snapshot recovery | Highest: authorization/idempotency/concurrency/report adjustment/period closure/rollback rules, immutable correction ledger |
| Backwards compatibility | Storage may stay unchanged initially; existing “autofix” behavior intentionally changes only after approval; raw API shapes kept | Existing APIs/exports stay recorded-value by default; new estimated view explicit, old code must not normalize originals | Existing reports need explicit revised/adjusted basis; older code must not bypass corrections or rewrite originals |
| Reporting impact | Existing ambiguous costs remain; separately decide whether exact recorded profit or current formula is displayed | Side-by-side recorded and estimated costs/profit; unknown coverage disclosed, never blend without label | Revised report version and adjustment trail; prior exports/invoices remain retained, not silently regenerated |
| Adoption | Metadata-only adoption preserves values but does not certify historical completeness | Capture baseline before inference; no estimate during adoption/startup | Adoption itself must not perform corrections; separately approved correction after preservation and reconciliation |

**C variants:** In-place rewrite with a retained immutable before-image is still a
rewrite of the audit table, risks existing consumers and is **not recommended**.
Append-only correction is safer but still requires owner choices about accounting
periods and report basis. Ordinary member tally correction, cost correction and real
provider refund are separate operations; none may automatically authorize another.

For B, a future design should retain source snapshot checksum/installation/schema,
table+row ID and operation correlation; recorded value/status (known zero/known
nonzero/unknown only when evidenced); inferred unit/total and method version; source
document/date or explicit current-cost assumption; author/reviewer/timestamps;
supersession link and report basis. This is a **design checklist, not a schema**.
Never set `known_zero` solely from a zero field, or collapse unknown into 0 EUR.

### Concrete report examples (EUR; hypothetical, not live data)

All examples hold VK debt/payment and original audit fixed. Existing raw reports
can differ as noted above; these are proposed **explicit bases**, not new outputs.

| Example | A recorded basis | B separate estimated basis | C evidenced revised basis |
| --- | --- | --- | --- |
| Two gifted-stock paid drinks: VK 3,00 each, original EK 0,00, current master EK 1,25 | Sales 6,00, recorded cost 0,00, recorded/derived profit 6,00; legitimate zero stays zero | Same recorded view. Confirmed gift evidence means no missing-cost inference; estimated view also cost 0,00 (known zero) | No correction justified merely by positive current EK; stays 6,00 profit |
| Same numeric row but unauthenticated old import/default: q=2, sales 6,00, recorded cost 0,00 | Cost displayed as recorded 0,00 with unknown provenance; do not claim actual profit known | Optional explicit “current-cost assumption”: estimated cost 2,50/profit 3,50; actual historical cost remains unknown. No change to recorded 6,00 | Without evidence, refuse correction. If authenticated period invoice supports EK 1,10, append adjustment +2,20 cost/−2,20 profit; revised profit 3,80 with original retained |
| Paid q=2, original EK 1,00, cost 2,00/profit 4,00; current EK later 1,50 | Keep 2,00/4,00 | Historical report 2,00/4,00; replacement-cost scenario 3,00/3,00 only separately labelled | No correction because current price changed. Evidenced original error could support a separate adjustment |
| ROUND_DEDUCTED q=−1, VK 3,00, original EK=0, current EK=1,25 | Recorded signed TI cost 0,00; profit report round expense 0,00; original RE stays 0,00 | Estimated signed cost −1,25, estimated round expense 1,25/profit −1,25; label assumption, do not overwrite RE | Only evidenced correction; require linking TI and RE treatment to avoid double count. Signed correction is not a cash refund |
| System round paid sales 10,00, original unusual EK=4,00, stored cost=4,00/profit=6,00; RE drink cost=2,00 | Preserve both records, flag relationship for review; do not summarily add costs from both report families | Originals remain 6,00 paid-row profit and RE difference 8,00. Separate scenario may assume helper EK=0, paid-row profit=10,00; explain costs belong to deduction records | If proved erroneous, adjustment −4,00 cost/+4,00 profit; retain original. Owner must decide report/double-count basis; no automatic normalization |
| Inconsistent paid row: sales 3,00, cost 1,00, stored profit **0,00** | Raw stored profit=0,00; existing preview/statistics show derived 2,00, while item export sums 0,00 | Both facts displayed; formula-derived 2,00 is not silently substituted for raw 0,00; no current-cost inference needed | Evidence/approved calculation rule required before explicit correction; preserve original 0,00 |

Synthetic REFUND-like q=−1 at VK=3,00/EK=1,25 yields signed sales −3,00,
purchase total −1,25, profit −1,75 in the logging helper. There is **no supported
served refund route**, and arbitrary refund kinds are excluded from paid reports.
Adding such a row is not proof of provider refund, cash returned or inventory returned.

## 4. Legacy evidence and support inventory

See [legacy-adoption-inventory.md](legacy-adoption-inventory.md) for exact source
commits, schema hashes, provenance limits, independently derived metadata and support
classification. No authentic historical DB/release-image fixture was authenticated.
Source history is available and authentic as reachable Git objects under the verified
repository baseline; that proves source contents/ancestry, **not signed release,
deployment provenance, old data values or a supported installation**.

## 5. Safe adoption proposal — NOT execution approval

1. **Decision gate:** owner records A/B/C choice and report basis, zero/unknown rules,
   signed corrections/round interpretation, previous overwrites and supported source
   scope. Separate authorization for later implementation, artifacts and operations.
   Pending decision, keep current strict allowlist and production defaults unchanged.
2. **Evidence gate:** use sanitized schema-only metadata and synthetic rows. A future
   authentic artifact requires independent origin/commit/digest/chain-of-custody and
   approved sanitization that preserves types, defaults, IDs/relationships/signs/zeros/
   sequence gaps without member/financial data. Same schema or synthetic CI success
   does not satisfy authenticity. Avoid old runtime DB blobs from repository history.
3. **Classification gate:** exact full sqlite_master fingerprint, column/FK/index/
   trigger metadata, ledger/PRAGMAs, integrity, journal/sidecar state, supported
   source→target identity tuple. Unknown/equivalent-but-different/partial/custom/future
   state stays non-success. Review custom audit objects; never drop them to pass.
   Fresh same-column and ALTER-history states require **different exact evidence**.
4. **Preservation gate:** independently verified whole-state EF-08b snapshot and
   separate EF-08c recovery/key/image/config evidence; preserve failed/source copies.
   All writers held; prepare/recover WAL only on separately authorized isolated copies
   using SQLite, not sidecar deletion. RL-01 preflight readiness permits rehearsal only.
5. **Proposal for next engineering package:** first stop implicit startup/admin-update
   financial rewrites under approved preservation policy with failing DP-002/004/024
   tests. Then, only if warranted, review **one exact additional fingerprint** (the
   ALTER-fee shape is a concrete investigation candidate), metadata-only adoption,
   no inferred data/defaults and no invented earlier migration records. No automatic
   prototype import; if ever needed, separate explicit opening-balance/provenance
   policy rather than historical transaction fabrication. No v1→v2 unless necessary
   approved storage changes require it; not a dummy transition.
6. **Rehearsal gate:** synthetic legitimate-zero/ambiguous/nonzero/round/signed/NULL-ID/
   inconsistent-profit fixtures plus authenticated-source schema metadata when available;
   exact all-table+sequence comparison after adopt/repeat; master/debt/tally/paid rounds/
   audit/provider/client IDs and CSV/PDF/messages untouched. Check API writes after
   adoption, not startup alone. Assert no providers/mail/replays; verify reports in
   explicitly selected basis, correction coverage and independent new-root recovery.
7. **Failure gate:** any unknown provenance/predicate, changed original, totals/report
   mismatch, stale writer, journal/corruption/lock/storage failure stops. Retain source
   and failed state; no blind restart/retry, automatic repair, sidecar removal or old
   image startup. Recover pre-boundary bundle into a separate nonexistent root with
   compatible image, then human reconciliation for post-snapshot activity. No payment
   reversal/resend/mail retry/queue replay or image-only DB rollback.
8. **Operational gate:** installation-specific authorization and acceptance, exact
   acquired image/digest/config, all-writer maintenance, effective ACL/storage/RPO/RTO
   proof and external reconciliation. No production run in RL-03. MV-01..05 pending,
   MV-06 operational portions partial, EF-08a Windows rename issue still unresolved.

### Owner sign-off checklist (leave unresolved until explicit response)

- Preservation baseline A? B estimates ever allowed? C required, and append-only or
  in-place? Which people may approve, and on what documentary evidence?
- Report basis: exact stored profit vs formula-derived profit; separate raw/estimated/
  corrected views, period/restatement and signed-cost/round double-count rules?
- Legitimate zero/ambiguous-zero labels and handling of previously overwritten values?
- Supported adoption breadth: exact-current only, separately evidenced ALTER variant,
  or authentic historical artifacts first? Prototype balances explicitly deferred?
- Scope/authorization of next engineering package and its acceptance fixtures?
- Separate production adoption/rollback/reconciliation approval? **Not granted here.**

### Exact decisions required before any historical financial adjustment

The owner must explicitly record **all applicable items**; a merge of this evidence
PR, the recommendation above or successful tests does not supply that approval.

1. **Purpose and original authority:** preserve originals including legitimate zeros
   and unusual nonzero round snapshots; identify the authoritative baseline/evidence
   for a particular alleged error. Decide treatment of unknown/previously overwritten
   facts; current EK and matching schema alone are not evidence of actual past EK.
2. **Adjustment authority and scope:** whether C is needed at all; named approver/
   operator permissions, exact affected table/row IDs, documentary evidence threshold,
   reason, effective/recorded dates and bounded amounts. Decide append-only versus
   in-place with retained immutable before-image (in-place not recommended), idempotency,
   authorization/concurrency controls and reversal/supersession audit requirements.
3. **Accounting/report interpretation:** exact-stored, formula-derived, estimated or
   corrected basis; whether a change restates the historical period or posts a current
   adjustment; signed-cost/quantity rules, round helper versus deducted-drink cost,
   double-count prevention, rounding and coverage of T-only corrections. Invoice/CSV
   retention and newly labelled report versions must be explicit. No new interpretation
   of member debt, paid state, cash refunds or inventory return is assumed.
4. **Inference authority (if B used):** approved provenance/status/method/source-date/
   reviewer requirements, separation from facts, visibility and unknown-coverage
   labels. Estimates cannot become corrections or payment facts without independent
   evidence and a separate approved adjustment.
5. **Preservation/reconciliation and compatibility:** exact source/schema/image tuple,
   complete recoverable pre-boundary state, all-writer hold, comparison/acceptance
   criteria and stop/recovery procedure. Human reconciliation of external payments,
   mail and queued/post-snapshot business activity; no blind provider retry/refund.
6. **Execution authorization:** separately approve the bounded implementation/test
   package; real installation/data access, migrations, deployment or operational
   financial correction require additional explicit authorization. None occurs here.

### Recommended next bounded implementation package (proposal only)

**RL-04 candidate — Historical Snapshot Write Preservation**, contingent on owner
decision for A: stop implicit existing-history cost/profit rewrites in routine admin
item editing and legacy startup (FH-01/02/06), preserve original defaults/fresh-booking
contracts except any separately approved master-zero treatment, both import modes,
REST payloads, debt/tally/payment/round entitlements, audit, idempotency and recovery.
Write failing regressions before code; include unchanged-positive-EK saves, legitimate/
ambiguous zero, nonzero round, signed/NULL-ID/closed rows, no-date/provenance inference
and exact all-table repeat/recovery comparisons. **No historical correction, reporting
change, inferred-value storage, extra adoption fingerprint, default mode change or
v1→v2 migration** in that candidate. FH-03 report-basis and FH-04 correction-detail
behavior should remain separate later packages after their own owner decisions.
The name/scope is a recommendation, not approval to begin RL-04.

## Verification

`tests/test_financial_history.py` adds characterization only, including actual
assembled HTTP item update after valid versioned adoption, signed/current backfill,
round nonzero rewrite, report zero fallback, correction-detail gaps and default-zero
master normalization. Schema tests use literal DDL only. Existing RL-01/02 full-state
and synthetic import/recovery tests remain unchanged. Results and gaps are recorded
in [PROGRESS.md](PROGRESS.md) and [HANDOFF.md](HANDOFF.md). No policy pass inferred
from green tests; no financial application code changed.
