# Technical audit — evidence, not a rewrite mandate

Audit of previous main `fb08128`, transfer `250a4e6`, and owner-merged main
`052c2bb`. Takeover/diff details in HANDOFF.md; requirements in ../REQUIREMENTS.md.
Observed results are dated in PROGRESS.md; no invented coverage percentages.

| Finding | Evidence | Risk / treatment |
| --- | --- | --- |
| Compatibility shell, partial extraction | main alias, application reload/copy lifecycle, registry mounts legacy APIRoutes | Authoritative runtime remains legacy; HTTP regression protects real seam |
| Extracted orders/payments/rounds differ | orders filters event_open debt, payments simplified, rounds creates PENDING | Do not mount/replace based on module naming; characterize per migration |
| Agent round-request immediately approves/charges | served create_round_request and agent delegation; test_round_and_cashup_flow | Confirmed contract, potential financial authorization risk; document/test, no silent change (OQ-01) |
| Financial debt differs from current tally | positive order_lines vs event_open, cashup/payment handlers | Guard historical debt through cashup, archived items and snapshot settlement |
| DB/audit invariants exist | explicit transaction/commit, FK/WAL/timeout, audit details, transfer correction tests | Add served HTTP rollback/stale/event tests; never use production DB |
| Core operational features already exist | exports, messages, sync polling, OpenAPI, backup/restore, named events/invoices | Historical "missing feature" claims are stale; do not implement duplicates |
| Config/import/schema globals persist | legacy reload, duplicate config, schema.configure_runtime | Tests isolate/restores globals; one-seam follow-up, not mass DI refactor |
| Startup lifecycle/TestClient deprecations | observed warnings under current dependency resolution | Retain visible warnings; dependency/lifecycle follow-up with parity |
| Static modules are scaffolding | no static/js references in current HTML | Syntax-check and preserve; no claim of completed frontend migration |
| Limited auth boundary | local-network PIN and token, rate limit in memory | Not public-product security; confirmed agent charge risk separately reviewed |
| Non-atomic artifacts/mail/DB | CSV→PDF→SMTP→close, existing failure tests | Keep ordering, uncertain-delivery risk; no blind retry/exactly-once promises |
| All-branch image publication in old CI | original container.yml push:true/packages:write/login | Split read-only checks from explicit approved publication; keep tags, no deployment |
| Device/external proof absent | backend mocks, original unfinished tablet/cache/SMTP items | Manual MV-01..06 remain pending despite owner merge or green CI |
| EF-08a intermittent Windows publication denial | PR #4 final integration local test: directory rename WinError 5, later full rerun passed | Unresolved reliability finding; EF-08c does not alter EF-08a or add retries. Separate disposable reproduction/correction proposal in disaster runbook |
| RL-01 observed updater/startup risks | Mutable stable/always, Podman force-recreate/prune/timer, no preflight/version ledger; early DDL/WAL/files persist on late failure; cost/profit backfills repeat | Existing defaults unchanged; optional offline preflight/rehearsal/runbook. No arbitrary upgrade/downgrade or live rollback claim; proposed RL-02 |

## RL-03 distinct financial-history findings — OPEN

### RL-05 implemented contract (independent review pending)

FH-04 new ordinary corrections append complete source-linked signed TI/metadata/
operation identity; normal net consumption at original period, serialized decisions,
keyed retries and correction-only pay. Round addendum replaces count/index allocation
for new tracked units with exact deduction/reversal provenance; unsupported old,
paid, closed or uncertain states block, not guessed. **FH-04 new-operation audit gap
addressed**, exact corrected-head branch/PR CI `45367327293`/`45367337289` passes
both matrices/all 30 new tests/actual-image net+round/v1 transition/full recovery+DR.
Historical T-only originals are not reconstructed. FH-05 still open; original
financial snapshots preserved. Final receipt head requires its own CI; independent
review/manual/operational acceptance not implied by implementation closure.
Former RL-04 T-only/replay/HTTP ambiguity receipts below are historical baseline.

### RL-04 current disposition — 2026-11-24 (review pending)

| Finding | Current status / new evidence |
| --- | --- |
| FH-01 High | **Addressed in served implementation**: both admin historical UPDATEs removed; master/audit retained. Converted preservation regressions and repeated/unchanged/archived/SQL-audit-fault/concurrent-booking tests. Closure subject to final gates/review |
| FH-02 High | **Addressed**: all round snapshot resets removed with helper/call; zero/nonzero O/TI, RE and entitlements preserved; round master/operational rules unchanged |
| FH-03 Medium | **Addressed**: paid stored profit including zero read in stats/preview/report export; raw item export unchanged. Signed/inconsistent/subcent/period/archive/admin/operational-distinction/no-write regressions; no forced cross-concept reconciliation |
| FH-04 Medium | **OPEN**: exact lifecycle, replay/capped/insufficient debt, SQL rollback, no-debt committed correction before payment HTTP error characterized. T-only detail gap requires accounting/consumer decision; no negative TI introduced |
| FH-05 High conditional adoption readiness | **OPEN**: no authentic historical artifact/new fingerprint/support evidence |
| FH-06 High | **Addressed routine writes**: ordinary cost inference removed; existing default zero master retained. Existing additive defaults/prototype compatibility preserved, no historical repair or additional legacy adoption |

Current write inventory and reporting population rules: financial-history-policy;
FH-04 exact contract/proposal: correction-audit-contract. All data synthetic. Full
verification/closure receipt in PROGRESS/HANDOFF; no claim of recovering originals
already overwritten. OQ-06 broader correction/inference/adoption decisions remain
open. The following RL-03 table retains **former baseline evidence**, not present
code or a denial of current scoped owner authorization.

Severity is engineering impact/prioritization, **not CVSS**, observed production
loss, or approval to change accounting. **High**: stored financial originals can
be overwritten without a retained before-image, or missing compatibility evidence
would make adoption unsafe if assumed. **Medium**: reporting/audit interpretation
can be misleading or incomplete without rewriting the stored financial original.
All findings remain open; synthetic reproduction proves code behavior only.

| ID / severity | Distinct finding and affected code paths | Evidence at baseline `33c16979` | Recommended follow-up (NOT authorized implementation) |
| --- | --- | --- | --- |
| FH-01 — **High** | Admin item update overwrites historical zero EK, purchase totals and profit, including paid/closed rows and valid versioned state. `app/legacy_main.py::admin_update_drink`, `/api/admin/drinks/update`, lines 4978–5006. `ITEM_UPDATED` records master edit, not affected IDs/old values. | `FinancialHistoryTests.test_served_item_update_rewrites_legitimate_zero_even_in_versioned_mode`: accepted zero-EK item booked/paid, actual RL-02 metadata adoption, HTTP update to 1,25 changes all three TI to cost 1,25/profit 1,75 and both O snapshots; old audit rows/timestamps unchanged. `test_item_update_and_historical_backfill_roll_back_when_audit_fails` proves rollback boundary, not preservation after success. | After owner preservation decision, separate master editing from historical facts; test accepted legitimate zero and unchanged-positive-EK saves, all signs/dates/closed rows, both startup modes and audit-fault rollback. No correction/backfill within routine product edits. |
| FH-02 — **High** | Legacy startup unconditionally normalizes **nonzero** round snapshots: O unit EK=0; TI unit EK/purchase total=0, profit=sales. `app/db/schema.py::backfill_missing_purchase_snapshots`, lines 717–736; `_init_legacy` calls it every legacy start. Name or linked current round identity matches. | `FinancialHistoryTests.test_round_normalization_overwrites_nonzero_audit_without_correction_record`: original EK=4 overwritten at startup with no new T correction. Source shows no zero/date/kind predicate and no RE/EL adjustment. Existing RL-02 adoption test preserves unusual round master history during strict startup only. | Preserve recorded round snapshots until an explicit, evidenced, separately approved correction; do not assume nonzero is erroneous from helper semantics. Review relationship to deduction/RE cost without double counting. |
| FH-03 — **Medium** | Read-time zero-profit reinterpretation/report-basis divergence, **not a database write**. `app/legacy_main.py::admin_statistics`, line 5835 (`profit_eur or revenue-cost`); `build_report_rows` derives profit, `export_item_summary` sums stored profit. | `FinancialHistoryTests.test_report_zero_profit_fallback_is_read_time_not_a_database_write`: recorded paid-row profit 0 with sales 3/cost 1 produces statistics profit 2, DB remains 0. Formula/source inspection confirms preview/export distinction. | Owner chooses exact-stored versus formula-derived report basis and labels; characterize legitimate/inconsistent zeros and rounding before separately authorized report change. Do not silently restate old exports. |
| FH-04 — **Medium** | Approved member corrections and negative admin adjustments change remaining O quantity but omit signed TI details. `app/legacy_main.py::decide_single_change_request`, `resolve_pending_for_payment`, `admin_adjust_drink` negative branch, `remove_from_order_line`. T-only records exist, so this is **not absence of all audit**. | `FinancialHistoryTests.test_member_and_admin_negative_corrections_do_not_append_signed_item_details`: both served correction routes reduce quantity to 0; no negative TI; admin T total=−3. Source confirms payment-resolution approvals also omit `log_transaction_item`. Consumption reports select CONSUME TI, not T-only corrections. | Separate correction-audit completeness package after owner decides report reversal semantics; append snapshot-linked signed operation detail without rewriting originals, preserve debt/paid/refund boundaries. Do not fabricate prior missing correction details. |
| FH-05 — **High adoption-readiness risk** | Historical installation/release provenance not established. `scripts/financial_schema_inventory.py`, current `app/db/migrations.py::BASELINE_SCHEMA`/exact inspection and historical literal DDL. Not an unsafe-adoption defect: current strict gate rejects unrecognized shapes. | Eight source-defined fresh schemas from 113 reachable commits; source blobs and exact fingerprints reproduced. S5→S6→S7→S8 **synthetic DDL-only** ALTER shape `c07c9c55…` differs from fresh S8 `090ea55a…`. Three schema tests verify current reproduction, dynamic-index rejection and generic ALTER/fresh difference. Full inventory CLI separately reproduced the receipt. No authentic DB/image artifact verified; empty GitHub releases/tags and build-record metadata are not global registry absence. | Keep current support boundary. Obtain independently authenticated source/installation provenance and sanitized metadata before a separately approved one-fingerprint adoption investigation. No synthetic fixture, matching columns or mutable image tag is sufficient. |
| FH-06 — **High** | Ordinary legacy startup zero-cost inference/master default replacement affects all signs/dates and omits provenance; asymmetric history across linked TI, NULL-ID manual deductions, RE and named events. `app/db/schema.py::ensure_default_items`, `backfill_missing_purchase_snapshots` first two UPDATEs, `migrate_old_orders`. | `FinancialHistoryTests.test_backfill_changes_signed_details_but_not_null_ids_round_events_or_event_lines`: ID-linked negative details change to EK=1,25/cost=−1,25; NULL-ID detail/RE/EL stay zero. `test_legacy_default_item_zero_master_cost_is_replaced_not_authenticated_as_missing` plus `UpgradeMigrationTests.test_zero_cost_backfill_repeats_and_changes_cost_history_not_sales` prove default/repeat risks. Existing synthetic prototype test shows current-price/current-date import, not authentic old accounting. | Include both zero/default startup paths in the bounded preservation package with FH-01/02; no numeric-zero provenance inference, no current-cost historical reconstruction, no automatic prototype adoption or invented past facts. |

Decision/options/write matrix: [financial-history-policy.md](financial-history-policy.md).
Exact schema/provenance evidence: [legacy-adoption-inventory.md](legacy-adoption-inventory.md).
Tests above are in `tests/test_financial_history.py` unless named otherwise. **OQ-06
OPEN**: findings are confirmed runtime/synthetic evidence or explicit evidence gaps;
recommended future behavior remains **NOT APPROVED**. None establishes live financial
impact, a legal accounting requirement, a supported refund API or production compatibility.

## Verification limits (retained)

RL-03 financial evidence: served `admin_update_drink` changes O/TI zero costs and
profit even after versioned metadata adoption; no affected-row before/after audit.
Startup round normalization rewrites nonzero snapshots, omits RE/event-line updates;
statistics treats zero profit as fallback, exports/report formulas differ; member/
admin negative corrections omit signed TI. Full matrix and proposed options in
`financial-history-policy.md`, no runtime fix or accounting approval. Source-only
inventory identifies an ALTER-fee fingerprint distinct from fresh current schema;
no authenticated historical DB/image fixture, no support expanded.

RL-02 optional gate/ledger addresses the pre-write boundary only for explicitly
selected fresh/exact-current paths. Default legacy repeated historical cost/partial
DDL risks remain. Strict unknown/custom/prototype/WAL state deliberately rejects;
no universal historical support or accounting approval. Synthetic rollback/kill/
lock/permission/independent recovery evidence: `docs/migration-safety.md`.

Previous main **87 tests**, handoff **96 tests**, initial foundation **100 tests**,
final combined foundation **115 tests** on local Python 3.12/3.13.
Those measured counts are not line/branch coverage percentages. HTTP tests add
assembled ASGI startup/routing/serialization coverage; browser smoke uses disposable
Chromium, not target iPad/mobile or installed-PWA upgrade proof. Container evidence
comes from actual successful GitHub run `45131190711` (startup, restart persistence,
SQLite and healthcheck), not local execution; no local runtime is installed. Dependency
audit is an advisory-database check, not penetration testing or full supply-chain
assurance. Hardware/real mail/account/database operations remain out of scope.
