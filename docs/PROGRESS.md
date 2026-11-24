# Engineering foundation progress

## RL-05 active — 2026-11-24

Verified clean/fetched main `2cc36fd69ec56dbdfe65ffb7ed98600d7c33b7c4`, dedicated
feature/rl-05-transaction-integrity; all earlier branches preserved, no agents.
Mandatory docs/runtime inspected; owner addendum incorporated before persistence
design in `docs/rl-05-contract.md`. Original test-first run 17 discovered/12 failures/
five errors proves missing new contracts (`rl05-red.log` outside Git). Initial expanded
22 targeted correction/round/migration tests pass; full gates still pending.

New source-linked signed corrections/committed receipts, net original-period reports,
correction-only HTTP success, serialized requests/pay/cashup and exact round unit/
deduction/reversal model implemented under review. Additive v2 empty extension,
no old historical links inferred; paid/closed/unknown/unassigned round states block.
Worker v109/vanilla first-party action IDs; APIs intentionally require negative
purpose/ID and manual round unit. Existing defect tests converted, financial originals
still compared. Whole application/source-loss fixture extended with reversal state.

Broad runs failed (not passes): first lacked age PATH and exposed compatibility/
count expectations; subsequent run used age but found unpopulated new recovery tables,
old person-history expectations/traceability and concurrent code-edit schema mismatch.
Fixes/populated served recovery tests and frozen model verification in progress; no
production data/provider/network operations, no commits/push/PR yet. Full Python
3.12/3.13/browser/security/container/migration/DR/exact-head CI required before delivery.
FH-04 not closed yet, FH-05/OQ-06 broader/WinError 5/device/operational gaps retained.

Model expanded: nine provenance/receipt/round tables with exact v2 hash
`39dbd90c2aaefdc7437aef27e5ad16bb21db8b1583d2c51d855e50bec32209c5`, immutable
provenance/snapshot/permanent cancellation guards. Actual prepared v1 transition
keeps all old tables/sequence/ledger; direct v2 establishes actual history only.
29 targeted tests pass including admin/member replay, net 5−2=3, original-period cost,
round cancellation versus cashup/payment concurrency, SQL stage faults and interrupted
v1 migration. Existing broad failed receipts retained: formatting failed first full
Standard Checks; later checks overlapped code/model additions and produced stale
PayRequest attribute/schema failures, not accepted evidence. Frozen-tree rerun in
progress; no guards weakened. Chromium expanded to first-party keyed removal/replay;
worker v109/manual device acceptance remains pending.

Frozen broad Standard Checks reached 292 tests with only one remaining old
unqualified recovery SELECT expectation failing; now explicitly selects original
historical row, preserving assertion. First-party Chromium correction/replay passes
after synthetic session PIN reset before separate admin login (initial smoke failed
hidden login field, not application correction failure). Formatted changed files only.
Installed-style migration script additionally prepares original exact v1/ledger then
executes real v2 and proves no invented correction/unit rows, full independent recovery,
network_attempts=0; local actual-container verification still unavailable.

### Local review candidate gate

Full Standard Checks **exit 0** Python **3.12.13/3.13.15**, **292 discovered/286
passed/six POSIX skips** each, **161.748s/163.662s** unittest. Ruff/82-file format/
syntax/24-ID traceability/real age/financial+29 new RL-05 tests/migration/recovery/
audits (**no known vulnerabilities**)/Chromium first-party keyed correction replay/
diff pass; actionlint passes. Logs `rl05-gate312.log`/`rl05-gate313.log` outside Git.
Earlier failed runs retained, no WinError 5 during successful gate (not a fix).
Model/code stable; installed-style script adds actual prepared v1 rehearsal and passes,
exact-head CI/actual Docker/final committed-tree gates still required. Refetched main
unchanged exact baseline; deployment/Compose/provider/EF08 tool code unchanged.

### First committed-head verification and reservation review

PR #10 https://github.com/tostman1/drink-pos/pull/10 OPEN at implementation/doc
`33c0d82e7374c4e1c0d378558a7a460421af58bb`, four commits `a013878`/`e50ba38`/
`62464be`/`33c0d82`. Exact branch `45365814913` and PR `45365827911` **success**:
Linux each 292 discovered/291 passed/one Windows-only skip, all 29 new tests ok;
actual Docker/4 Compose/legacy upgrade/prepared v1→v2/repeat/financial net+round
reversal/independent recovery/encrypted source+owned-image-loss DR/image audit pass,
publication skipped, network_attempts=0. Prior eight-table model yielded 25 tables;
current reservation extension below changes model/evidence needs final rerun.

Final review found pending round approval could select a newer unit after another
booking aggregated into same O. Added `round_request_units` immutable request↔unit
reservation at creation, approval uses exact IDs, conflicting direct cancellation
blocks; focused regression before final delivery. Current genuine v2 DDL updated
(not another migration of published state, no production adoption), nine tables/26
total. Pending-round approved sources not reconstructed for legacy requests. Also
serializes old pending round-add decision. No other new policy; exact final-head
gates rerun required after this correction. Committed-head local 3.12/3.13 pass
retained, new head/local counts follow after verification. FH-04 closure deferred
until final evidence; original financial and deployment boundaries unchanged.

## RL-04 final integration — 2026-11-24

- Owner independent review complete, no approved-scope merge blockers; explicit
  conditional authorization for PR #9 only. Clean fetched/local reviewed head
  **`94104001c50e11f87341489e607b655c5f19b6da`** and expected base
  **`8dd961bfb23d7fe090a8cf2895a269bb544db09e`** matched. Specified exact-head branch
  https://github.com/tostman1/drink-pos/actions/runs/45343434976 and PR
  https://github.com/tostman1/drink-pos/actions/runs/45343450131 success, publication
  skipped; both Python matrices/all 21 integrity tests/actual container+financial+
  migration/recovery/DR/image audits verified. Final pre-review delivery receipt:
  https://github.com/tostman1/drink-pos/pull/9#issuecomment-7124732342.
- PR MERGEABLE/CLEAN; reviews/inline comments/review threads empty, no conflicts.
  Branch-protection API reports unprotected (404), active main rules empty; no checks
  bypassed/settings changed. PowerShell quoting caused initial GraphQL/tree-query
  inspection errors; explicit JSON input/quoted revision corrected, no Git mutation.
- Normal `gh pr merge 9 --merge --match-head-commit 94104001...`:
  **`b6dc46e6414812089c434ef315177aa7af50826d`**, 2026-11-24T07:18:16Z.
  Parent 1 exact base, parent 2 exact reviewed head; whole tree equals reviewed
  **`25ef9ae03f7314a8bf7eaf57751ad834733a2504`**. Primary checkout switched to main
  and fast-forwarded clean/synchronized; all prior branches retained. No app/test/
  workflow/config changes after review, no reset/rebase/force push/delegation.
- Exact merge-main https://github.com/tostman1/drink-pos/actions/runs/45346957268
  **success**: Linux 3.12/3.13 each **263 discovered/262 passed/one Windows-only skip**;
  all 21 new financial-integrity/correction tests execute ok. Ruff/format/syntax/
  traceability/browser/security/real-age and existing financial/migration/recovery
  gates passed. Four Compose configs, actual Dockerfile image/start-restart-persistence/
  EF-08a-b recovery/legacy synthetic upgrade/strict fresh-adoption-repeat/served financial
  scenario/independent recovery/encrypted source+owned-image-loss DR/image audit passed.
  Publication **skipped**, merge SHA deployment query zero. Exact installed evidence
  binds merge SHA: 17 original tables preserved/history_rewritten=false/both modes/
  recovery_verified=true/network_attempts=0/two safely mocked card creations. Complete
  logs/validated summary outside Git `rl04-main-45346957268-ci.log`/`-summary.json`.
- DR: public-only producer, owned image unavailable before retained archive load,
  shared image preserved, source storage removed, one post-snapshot commit not replayed;
  network-disabled startup. Synthetic RPO age **0.330150s**, RTO **2.392196s**, not
  operational guarantees/geographic/immutable/timed-human reconciliation evidence.
- Full merged-main local Standard Checks **exit 0** Python **3.12.13/3.13.15**:
  **263 discovered/257 passed/six POSIX skips** each, **114.789s/119.386s** unittest.
  Ruff/79-file format/Python-JS-data syntax/24-ID traceability/real age/audits (**none
  known**)/Chromium/diff/actionlint pass. Outside-Git logs `rl04-merged-main312.log` /
  `rl04-merged-main313.log`. Lifecycle/TestClient/Node-action warnings retained;
  local Docker unavailable, actual container evidence from exact main CI.
- Integration receipt changes **only docs/HANDOFF.md and docs/PROGRESS.md**; final
  main SHA is this descendant's HEAD after commit/push. Its own exact-head CI MUST
  pass independently and final SHA/run/result be recorded in PR #9 integration
  delivery comment/report, not inferred from merge CI or self-referential SHA.

FH-01/02/03/06 implementation integrated: no routine O/TI historical financial
UPDATE remains after admin backfill/startup inference/round-reset removal; default
creation only preserves existing zero masters; present paid stored profit including
zero is authoritative in stats/preview/report export. Current master/new bookings,
consumption/OPEN/round operational formulas, quantities/status/payment/idempotency/
audit/entitlement/event/invoice/sequence behavior stay within reviewed contracts.
No automatic historical repair/reconstruction/inference or already-overwritten
original recovery, no schema/v2/new fingerprint/adoption/default-mode change.

**FH-04 OPEN, characterization only; FH-05 OPEN.** `/api/pay` correction-before-
HTTP-400 commit without payment and non-idempotent negative admin adjustments remain;
exact audit-coverage/follow-up acceptance contract retained. **OQ-06 resolved only
for approved routine historical preservation**, remaining historical correction/
inferred storage/round accounting/report-period/adoption choices open. EF-08a Windows
**WinError 5 remains unresolved** (successful checks are not a fix). MV-01..05 remain
pending; operational MV-06 partial for real geography/hardware/immutable/encrypted
storage/scratch/Windows ACL/secure key-image acquisition/timed human payment-mail
reconciliation/acceptance. No production data/migration/financial correction, real
SumUp/SMTP, deployment/release/publication/updater/schedule change. No FH-04 or new
package begun. Supersedes historical open/no-merge/pending PR #9 notes below only;
stop after exact final-main verification.

## RL-04 active scoped financial integrity — 2026-11-24

- Clean local/fetched exact main `8dd961bfb23d7fe090a8cf2895a269bb544db09e`;
  dedicated `feature/rl-04-financial-integrity`, all prior branches/merges preserved.
  Mandatory docs and served main/application/registry/legacy paths inspected; ready
  gate `docs/rl-04-contract.md` before implementation. No delegation.
- Initial converted DP-002/004/013 regressions: **10 tests, five expected failures**
  prove master zero replacement, admin backfill, round reset, signed inference and
  statistics zero fallback (`rl04-red-history.log` outside Git). Expanded reporting
  tests reproduced paid derivation; fixture errors corrected (archived master lookup
  rejects editing, Bier klein fresh default 1.00, actual SMTP helper/mock signature).
  Defective former evidence retained in RL-03/RL-01 historical sections below.
- Removed admin two historical UPDATEs, startup four UPDATEs/helper/call, existing
  default master zero replacement. No history repair/new adoption/schema/v2. Paid
  helper reads present stored profit including zero; paid preview and stats fixed,
  raw exports/operational formulas/populations unchanged. SQL insert failure rollback,
  concurrent booking/master snapshot and legacy full-state repeat covered.
- **21 new targeted integrity/correction tests pass** on Python 3.12.13; expanded
  synthetic served scenario passes legacy repeat, independently prepared strict
  adoption/repeat, new costs/payment/cashup, separate all-table recovery, paid/unknown
  mocked provider once-only creation, network_attempts=0. Current exact schema remains
  17 original tables; ledger additional only under adoption. No authentic old source.
- FH-04 remains open: contract `docs/correction-audit-contract.md` covers request/
  approve/reject/negative adjustment/pending payment/removal/audit/consumers/replay/
  rollback. Important existing no-debt `/api/pay` commits pending decisions before
  400 with no PAID record; negative adjustments not idempotent. No signed correction
  TI added; accounting/consumer/period/concurrency decision required.
- Full local Python 3.12/3.13 gates/final-head CI actual container+DR/PR still pending,
  not passes. Docker/Podman not installed locally; actual-image verification added
  to existing non-publishing CI. No deployment/default/schedule/image controls changed.
  OQ-06 broader questions/FH-05/EF-08a WinError 5/MV-01..05/operational MV-06 remain open.

### Full local implementation gates

Full Standard Checks **exit 0** Python **3.12.13/3.13.15**, 263 discovered/257
passed/six POSIX-only skips each; unittest **157.942s/165.859s**. Ruff/79-file
format/syntax/130 JS sources/24-ID traceability/real age/existing financial+recovery+
migration/new 21 tests/strict audits (**no known vulnerabilities**)/Chromium/diff
passed; actionlint passed. Logs `rl04-standard312.log`/`rl04-standard313.log` outside
Git. Existing lifecycle/TestClient/LF→CRLF warnings retained, no WinError 5 this run
(still unresolved, not a fix). Preservation `ac1eefa`, reporting `97d8cbe`, expanded
tests/scenario+non-publishing CI `a6f60d2`; final documentation/committed-tree/CI pending.

Complete app SQL UPDATE/dynamic-update review: no remaining O/TI financial UPDATE;
only operational quantities/tally, payment status/provider links, current master,
request decisions, event close/location and message/settings remain. Removed stale
legacy backfill facade as well as schema helper. No new independent financial
rewrite found; additive DDL/prototype import/round master retain documented limits.
Protected Dockerfile/production Compose/UI/worker/migration ledger/recovery trees
have zero diff. Main remote still exact baseline; all prior branches retained.
Temporary partial-hunk staging first rejected corrupt patch (no index mutation),
corrected newline/byte transport succeeded; no checkout/reset/worktree discard.

## RL-03 final integration — 2026-11-24

- Independent owner implementation/evidence review complete; no approved-scope merge
  blockers. Explicit conditional authorization for PR #8 only, no policy/production/
  future work. Clean fetched/local reviewed **`0b43f379f0b48dcd82e555287a3a301fe3838969`**
  and expected base **`33c16979d2ae17a5d53c118c7f173f324e02e75b`** matched Git/GitHub.
  Specified exact-head branch https://github.com/tostman1/drink-pos/actions/runs/45270641734
  and PR https://github.com/tostman1/drink-pos/actions/runs/45270653100 success, both
  Linux 242 discovered/241 passed/one Windows-only skip; all ten RL-03 methods ok and
  browser/security/actual image/container/migration/recovery/DR/image audit passed,
  publication skipped. No reviews/threads/inline findings/conflicts, MERGEABLE/CLEAN.
  No configured required checks, no checks/protection bypassed. Full 16-file scope
  exact allowlist verified; complete app/deployment tree parity versus base.
- Guarded normal `gh pr merge 8 --merge --match-head-commit 0b43f379...`:
  **`9d09015b2d83d652d88b283ef9f5ab45050128bf`**, 2026-11-24T05:55:46Z.
  Parent 1 exact base above, parent 2 reviewed head above; whole tree matches reviewed
  **`221909081ee78cff6173476805d69bf2eba786e8`**. Primary checkout switched to main /
  `git merge --ff-only origin/main`, clean/synchronized. No reset/rebase/force push,
  protected branches/owner merges/feature branch retained, no delegation.
- Exact merge-main https://github.com/tostman1/drink-pos/actions/runs/45336723411
  **success**. Both Linux Python 3.12/3.13 matrices: **242 discovered/241 passed/one
  Windows-only skip**, all ten characterization tests confirmed ok. Ruff/format/
  Python/JS/data/24-ID traceability/browser/security/real-age/financial/migration/
  recovery/POSIX tests passed. Four Compose validations, actual local-only Dockerfile
  image/start-restart-persistence/legacy synthetic upgrade/strict fresh-adoption-repeat/
  independent EF-08b recovery/encrypted source+owned-image-loss DR/image audit passed.
  Publication **skipped**, merge deployment query 0. Installed synthetic evidence
  history_rewritten=false/recovery_verified=true/network_attempts=0, no authenticity/
  compatibility/production guarantees. Log `rl03-merge-main-ci.log` outside Git.
- Full merged-main local Standard Checks **exit 0** Python **3.12.13 / 3.13.15**,
  Node 24.11.1/trusted age: **242 discovered/236 passed/six POSIX-only skips** each,
  unittest **122.929s / 126.518s**. Lint/format/syntax/traceability/real age/audits
  (**no known vulnerabilities**)/Chromium/diff/actionlint pass. Logs outside Git
  `rl03-integrated312.log` / `rl03-integrated313.log`; local Docker unavailable, actual
  container proof is exact main CI above. Lifecycle/TestClient/Node-action warnings
  retained. Initial inspection's uppercase exact-string proposal guard failed; case-only
  query corrected, verified original policy blob/NOT-approved meaning unchanged.
- Merged-main source-only inventory receipt reproduced: eight fresh schema/source
  identities, 113 original-baseline reachable commits, distinct illustrative ALTER
  hash. No historical DB/release/image artifact authenticated or support broadened.
  Exact app tree/financial/reporting/schema/migration/payment/invoice/recovery/UI/
  worker/.github/Dockerfile/production Compose/examples blobs unchanged vs base.
  Audit/decision/proposal severity records unchanged versus reviewed head.
- Integration receipt modifies **documentation only**, no app/test/source-tool or
  policy changes. Its final main SHA/own exact-head CI must be read after commit/push,
  independently verified and recorded on PR #8 integration-delivery/report. No
  predecessor-CI inference/self-referential SHA. Stop after final-main verification.

**OQ-06 OPEN; FH-01..FH-06 OPEN**, severities retained (FH-01/02/06 High,
FH-03/04 Medium, FH-05 High conditional adoption-readiness provenance risk).
Preserve-original recommendation **PROPOSED/NOT APPROVED**. Merge accepts evidence,
not rewrite prevention, financial/report policy, inference storage, append-only
correction, history repair, new migration/schema allowlist, default mode or production
rollout. Current behavior including documented historical rewrites remains unchanged.
No authentic historical installation evidence from source schemas/synthetic tests.

EF-08a Windows **WinError 5 remains unresolved** despite current successful runs;
earlier committed 3.13 backup-rename failure retained, no retry/suppression/fix.
MV-01..05 target-device/PWA/real SMTP/SumUp/offline reconnect pending. MV-06 automated
synthetic all-state/recovery/DR evidence exists, actual geography/hardware/immutable/
encrypted storage/scratch/Windows ACL/secure key-image retrieval/timed human external
payment-mail reconciliation/operator acceptance remain partial. CI is not operational
acceptance. No RL-04 or next package, production data/real migrations/member records,
financial repair/publication/release/deployment/updater/config/schedule/payment/mail
operations. All historical branches/owner merges preserved; stop after integration.

## RL-03 review-submission continuation — 2026-11-23

### Committed decision/evidence review receipt

PR **https://github.com/tostman1/drink-pos/pull/8 OPEN/unmerged**, base main unchanged
`33c16979d2ae17a5d53c118c7f173f324e02e75b`. Reviewed commits `3eb4d70` (source-only
inventory/receipt/ten tests) and `3f323b074478e5e5c9c94856f7b2efecbdd3570b` (decision/
findings/traceability/docs), pushed normally; clean synchronized tree. All prior
branches/owner merges intact. Git/GitHub diff exactly 16 reviewed files, no generated
state/secrets. Exact Git blob parity for app/financial/schema/reports/migrations/
recovery/UI/worker/Dockerfile/production Compose; no financial policy or behavior change.

Exact committed-head branch
https://github.com/tostman1/drink-pos/actions/runs/45269458940 and PR
https://github.com/tostman1/drink-pos/actions/runs/45269481996 **success**: both Linux
matrices **242 discovered/241 passed/one Windows-only skip each**; all ten RL-03 tests
execute ok, existing POSIX/financial/migration/recovery/real-age/security/browser gates
passed. Four Compose validations, actual Dockerfile/local-only image, start/restart/
persistence/legacy synthetic upgrade, strict fresh/adoption/repeat/independent recovery,
encrypted source+owned-image-loss DR and image dependency audit passed. Publication
**skipped**, head deployment query empty. Logs outside Git `rl03-initial-branch-ci.log`
and `rl03-initial-pr-ci.log`; synthetic history_rewritten=false/network_attempts=0/
recovery_verified=true. No authentic historical database/release/image support inferred.

PR watcher exited 1 on GitHub jobs API HTTP 500 after gate execution; direct completed
run/jobs query independently confirmed success. First log-inspection commands failed
on PowerShell UTF-16 encoding and multiline deprecation layout; corrected log parser
confirmed each new test's ok in both matrices. These inspection errors are not CI
failures or ignored tests. Node-action/lifecycle/TestClient warnings remain visible.

Committed-tree Python 3.12 Standard Checks **exit 0**, 242 discovered/236 passed/six
POSIX skips, **114.536s** unittest; audits none known, Chromium/all other gates pass.
Initial committed Python 3.13 run **failed**, 242 discovered/one error/six skips,
**120.871s**, in existing `SnapshotRecoveryTests.test_stale_retention_lock_disables_cleanup`:
`app/backup_database.py:340 staging.rename(completed)` **WinError 5 Access denied**.
Known EF-08a Windows reliability issue reproduced; no app/recovery/test changes,
retry/suppression or policy implementation. Retained `rl03-committed313.log`; full
unchanged Python 3.13 rerun **exit 0**, 242 discovered/236 passed/six POSIX skips,
**87.667s**, all lint/format/syntax/traceability/real-age/financial/migration/recovery/
audits (none known)/Chromium/diff stages passed. Log `rl03-committed313-rerun.log`;
successful rerun is **not a Windows reliability fix**, failed run remains evidence.
Committed-tree CLI deterministic on two
runs, all source blobs/eight canonical hashes/113 counts/ALTER receipt reproduced.

This final documentation receipt is a **descendant** of the successful head above.
Its own full local/final-head branch+PR CI must pass independently and be recorded
on PR #8 final delivery; read the actual final SHA/checks, no predecessor pass inference
or self-referential SHA. OQ-06 **OPEN**, recommendation **NOT APPROVED**. Owner independent
review next; no merge/publication/deploy/production data/real migration/SumUp/SMTP.

Owner completed the truncated mission and explicitly authorized reviewed commits,
push of the **existing** feature branch, open PR against main and exact-head CI;
**no merge/publication/deployment/policy implementation**. This supersedes the
initial no-commit/no-push delivery notes retained below. OQ-06 remains OPEN.

Preserved all 16 existing modified/new RL-03 files; complete tracked diff and new
files reviewed. Verified incoming HEAD/origin/main/remote main at exact original baseline
`33c16979d2ae17a5d53c118c7f173f324e02e75b`; no remote feature branch/PR existed at
continuation. Actual source and all ten tests support findings. Added distinct
severity register **FH-01..06** in `docs/AUDIT.md`: High historical API/round/startup
rewrites; Medium read-time report/correction-detail gaps; High conditional adoption-
readiness provenance risk (current strict rejection remains safe). Full exact owner
adjustment decisions and proposed next preservation-only package recorded in policy.
No application/test-policy behavior changed; no agents delegated or work discarded.

Final two-version Standard Checks/receipt reproduction, reviewed commits/open PR/
exact-head CI receipts pending below; previous local passes are not final-head proof.
Only mandatory synthetic tests may execute existing migrations on disposable state;
no live or production migration/adoption, financial correction, report/runtime/config
change or historical artifact access. No new support or approval inferred from CI.

**Continuation pre-commit gate:** full Standard Checks exit 0 on Python 3.12.13/
3.13.15: **242 discovered/236 passed/six POSIX-only skips each**, **110.440s /
115.876s** unittest time. All ten RL-03 methods discovered; original financial/
migration/recovery/real-age suites pass. Ruff/format/syntax/24-ID traceability/audits
(none known)/Chromium/diff pass. CLI reproduces all eight hashes/source blobs/counts/
ALTER counterexample; actionlint/link checks pass. Logs outside Git `rl03-submit312.log`
/ `rl03-submit313.log`. Only audit/catalog/receipt documentation finalized afterward;
final committed-tree local gates and exact-head CI will be verified independently.
Lifecycle/TestClient/LF→CRLF warnings remain; Windows EF-08a not fixed by this pass.

## RL-03 decision package — 2026-11-23

Owner authorizes bounded financial-history/adoption **decision evidence**, not
policy implementation, v1→v2 migration or production upgrade. Supersedes historical
no-next-package notes for RL-03 only. Request ends at “5. Safe Adoption Proposal”;
proposal prepared without assuming omitted authorization. No delegated agents.

- Clean incoming main/local/fetched/remote ref exactly
  `33c16979d2ae17a5d53c118c7f173f324e02e75b`; exact baseline CI
  https://github.com/tostman1/drink-pos/actions/runs/45260937868 success for both
  quality matrices/actual image/migration/recovery/DR/audit, publication skipped.
  Feature `feature/rl-03-financial-history-policy` created from this main; all
  previous feature/handoff branches/owner merges retained. Refetch remains unchanged.
- Ready gate before edits `docs/rl-03-contract.md`; actual import/served registry/
  schema/snapshot/prototype/round/payment/cashup/audit/export/recovery paths inspected.
  Field write-impact matrix and A/B/C comparisons/examples/sign-off gates in
  `docs/financial-history-policy.md`. Recommend A invariant + separately authorized
  B estimates; defer C, prefer additive correction if needed. **OQ-06 not approved.**
- Newly characterized: served admin item update rewrites historical zero costs/profit
  even after valid versioned adoption; unchanged positive EK save can trigger it.
  Startup round reset rewrites nonzero history; linked TI can change while NULL-ID
  manual deductions/RE/event lines retain old cost. Zero-profit statistics fallback
  is read-time only, item exports/preview differ; member/admin negative corrections
  omit signed TI. No implicit immutable-history guarantee or refund support claimed.
- Source-only schema inventory scans 113 full reachable source commits, derives eight
  fresh shapes in memory from literal DDL (SQLite 3.53.1) and reproduces RL-02 hash.
  Synthetic S5→S6→S7→S8 ALTER-fee shape differs (`c07c9c55…`) despite same columns;
  unsupported, not an authentic installation or full data migration. Exact hashes/
  source blobs/known changes/provenance in `docs/legacy-adoption-inventory.md` and
  `docs/financial-schema-inventory.json`; full metadata stdout from
  `scripts/financial_schema_inventory.py`. Receipt independently reproduced.
- GitHub tag/release APIs empty. Eight unexpired `.dockerbuild` artifact **metadata**
  records found, not downloaded/authenticated images/DBs. No registry/installation
  access, historical runtime blob reading or authentic historical DB/release image
  established. Earliest reachable source already has EK; pre-EK/prototype release
  provenance unknown. No added adoption fingerprint or synthetic-authenticity claim.
- Ten targeted tests in `tests/test_financial_history.py` pass on Python 3.12.13,
  including real assembled HTTP after actual strict metadata adoption and audit-fault
  rollback. They characterize exceptions, not implement a proposed financial rule.
  Initial test-harness failures: broad import guard caught stdlib ast.walk import;
  replaced with source-exec guard; uppercase APPROVE rejected by actual Pydantic
  enum; fixture corrected to accepted `approve`, not API changed. Traceability 24 IDs
  passes with exception links; no approved business requirement added.
- Initial full 3.12/3.13 runs stopped by tool 120-second budget (exit 143 during
  tests), **not passes**. Rerun with 600-second budget underway; final local gate
  receipts follow. Logs `rl03-standard312.log`/`rl03-standard313.log` and
  `rl03-verified312.log`/`rl03-verified313.log` outside Git in approved temp root.
  Existing lifecycle/TestClient warnings retained; no app/UI/worker/cache change.

No commit/push/PR/merge permission inferred; package remains uncommitted local work.
No production access, actual migration/adoption, policy/config/default change,
deployment/release/publication/updater/payment/SMTP activity. Container runtime is
unavailable locally, new branch/PR CI not run; baseline CI is not RL-03-head proof.
MV-01..05 pending, MV-06 real operational acceptance partial, EF-08a Windows rename
WinError 5 unresolved. Owner decision and separately authorized implementation next.

### RL-03 completed local verification receipt

Full Standard Checks **exit 0** on Python **3.12.13 / 3.13.15**, Node 24.11.1,
trusted external age v1.3.2, private disposable approved temp roots: **242 discovered,
236 passed/six POSIX-only skips each**, unittest durations **102.487s / 103.639s**.
Ruff lint/format (77 files), Python/all-JS/data syntax, 24-ID traceability, real-age/
existing migration/recovery tests, strict dependency audits (**no known vulnerabilities**),
Chromium booking/admin/event/kassa/self-pay/no-page-errors and diff hygiene all passed.
Logs `rl03-verified312.log` / `rl03-verified313.log` outside Git. Initial timeouts are
retained as unsuccessful runs, not hidden. No EF-08a WinError 5 encountered in completed
runs, still unresolved/not fixed. Lifecycle/TestClient and Git LF→CRLF warnings retained;
PowerShell wraps native stderr warnings as NativeCommandError text, child exit is 0.

Source identity receipt reproduced independently on Python 3.12/3.13; actual inventory
CLI exit 0, eight schema hashes/113 counts/source blobs/synthetic ALTER hash match.
New decision-doc links resolve, actionlint passed. Final receipt/traceability edits
are documentation-only after full gates; no application code or dependencies changed.
Protected app/.github/Dockerfile/Compose/updater/rehearsal/recovery files have zero diff.
New scripts/tests remain synthetic/source-only; no generated state or secrets tracked.
Fresh branch/PR/container checks remain **not run**, no commit/push authorization.
Stop after local delivery; owner policy/report-basis/source-scope decision next.

## RL-02 final integration — 2026-11-23

- Independent owner review completed, no approved-scope merge blockers. Owner
  explicitly authorized PR #7 merge subject to exact-head gates. Clean fetched
  reviewed head `9b3385991641b9ef330d6f5830884a6f723b5afd`; main/base exactly
  `65d7a869854a15cfa5ef78c98153bc35306f629b`. Specified branch `45257800656` and
  PR `45257811471` passed all quality/browser/security/Docker/migration/recovery/DR/
  image-audit gates, publication skipped. No reviews/threads/inline findings, no
  conflicts, MERGEABLE/CLEAN. No configured required checks; none bypassed.
- Normal exact-head guard `gh pr merge 7 --merge --match-head-commit 9b338599...`:
  **`b3f2a5c5c9bb761705bb10810e4f4a53554d899f`**, 2026-11-23T20:31:30Z.
  Parents exactly verified base/reviewed head; entire merged tree equals reviewed
  `7a5d0a89450f528ffc41e35b5166f781b745a358`. Primary checkout switched to main
  and fast-forwarded safely; clean/synchronized, all feature/handoff branches
  preserved, no force push/reset/rebase/bypass. All 14 original non-init schema
  helper ASTs unchanged; financial handlers/UI/PWA/recovery/production configs/
  Dockerfile/updaters/timer untouched vs base. Opt-in dispatch only startup seam.
- Exact merge main https://github.com/tostman1/drink-pos/actions/runs/45260262831
  **passed** full Python 3.12/3.13 (232 discovered/231 passed/one Windows-only skip
  each), Node/Ruff/format/syntax/24-ID traceability/strict audits/Chromium; new POSIX
  read-only-file permission test actually ran ok. Actual local-only Dockerfile image,
  four Compose validations, startup/restart/persistence/EF-08a-b recovery, installed
  identity/legacy synthetic upgrade, strict fresh/adoption/repeat/all-table history
  preservation/independent EF-08b recovery and complete encrypted source+owned-image
  loss disaster recovery/image audit passed. Publication **skipped**, deployments `[]`.
- Exact merge-image RL-02 JSON: original_tables_preserved=17 (16 app + sequence),
  history_rewritten=false, repeat_startup_verified=true, recovery_verified=true,
  network_attempts=0, historical_release_evidence='none; exact synthetic current
  fixture only'. Strict historical/master/audit/payment/debt state preserved.
  DR public-only producer/owned image unavailable before archive load/shared image
  preserved/source storage removed/one post-snapshot commit not replayed. Synthetic
  RPO age 0.250959s/RTO 1.919433805s, not operational performance guarantees.
  Outside-Git logs `rl02-premerge-branch-ci.log`, `rl02-premerge-pr-ci.log`,
  `rl02-merge-main-ci.log`; existing lifecycle/TestClient/action warnings retained.
- Local merged-main Standard Checks **exit 0** Python 3.12.13/3.13.15: 232
  discovered/226 passed/six POSIX-only skips each, 110.360s/115.608s. Ruff/format/
  syntax/traceability/real age/strict audits (none known)/Chromium/diff passed;
  actionlint passed. Outside-Git logs `rl02-merged-main312.log`/`rl02-merged-main313.log`.
  Docker unavailable locally; direct actual-container proof is the exact main CI
  above, not inferred local execution. Windows EF-08a reliability remains unresolved.
- Receipt changes documentation only. Its final main SHA/own exact-head CI must
  be checked after push and recorded on PR #7 integration-delivery/report, not
  inferred from merge CI (self-referential hash cannot be embedded in its own commit).
  No application changes after review, no deployment/image publication/release or
  production adoption/data/payment/mail/config/schedule operations.

**RL-02 integrated; stop after final-main verification, no next package started.**
Default legacy path remains unchanged (including known historical backfill/partial
DDL risk); versioned migrations remain opt-in only, not activated on production.
Strict exact-current adoption is metadata-only, preserving historical zeros/round/
master/audit/payment/debt/sequence values; exact-schema/DELETE-journal/WAL-sidecar
rejection/independent recovery prerequisites apply. No universal historical-release
or v1→v2 support/mandatory rollout/automatic DB rollback. OQ-06 accounting/adoption
breadth remains unresolved; authentic fixtures, operator adoption/storage/provenance/
key-image retrieval/provider/mail reconciliation acceptance remains open. EF-08a
Windows `WinError 5` unresolved despite successful reruns. MV-01..05 pending;
MV-06 actual geography/hardware/immutable/encrypted storage/scratch/Windows ACL/
secure retrieval/timed human reconciliation acceptance partial. Green CI is not
financial-policy approval, production adoption or closure of manual acceptance.

## RL-02 active bounded migration safety — 2026-11-23

- Clean local/fetched main exactly `65d7a869854a15cfa5ef78c98153bc35306f629b`;
  exact-head CI `45246034817` passed. Dedicated `feature/rl-02-migration-safety`,
  no delegation/history rewrite/production activity. Ready gate/write inventory
  before runtime changes `docs/rl-02-contract.md`, DP-024 added.
- Nine first regressions failed missing contract before implementation. Smaller
  seam selected: optional versioned mode, default legacy unchanged; explicit fresh
  transactional initialization and exact-current metadata-only adoption → v1;
  no repeated existing financial/default normalizations. DELETE journal opt-in,
  read-only pre-write guard refuses WAL/sidecars/unknown/future/inconsistent state.
  OQ-06 accounting/adoption breadth still unresolved, synthetic-only fingerprint.
- Initial targeted 14 contract + five served financial tests passed; exact original
  table/state zero-cost preservation/repeat/new-root EF-08b recovery rehearsal
  passed locally, network_attempts=0. First transient full-stat atime comparison
  rejected read-only own access; corrected to size/mtime/file identity (not atime).
  Existing-message failure test corrected to compare preexisting bytes, not absence.
  Original 14 RL-01 preflight regressions pass with verified-ledger integration.
- Additional actual-process contention/DDL/source-change/POSIX permission/ASGI
  tests and actual-image fresh/adoption/recovery CI added. Full local Python 3.12/
  3.13, final branch/PR CI/container/DR evidence pending until receipts; Docker
  unavailable locally. Existing lifecycle/TestClient/MV-01..06/Windows EF-08a
  WinError 5 gaps retained. No UI/worker cache bump, REST or handler changes.
- No commit/push/PR merge/release/publication/deployment/real state/payment/mail
  has occurred at this initial receipt. Authorized commit/push/open PR follows
  passing gates; no merge authority. Implemented contract `docs/migration-safety.md`.

Review expansion: partial ledger views cannot masquerade as unversioned state;
unknown IDs/prerequisites/future timestamps/custom ledger triggers reject. Financial
adoption also preserves intentionally changed round master cost/archival/person
normalization fields. 18 contract tests (one POSIX skip locally), six served tests,
installed-image fresh/repeat/adoption/new-root recovery helper. Initial full checks
failed Ruff formatting in two changed files; formatted only those files and reran.
Initial actionlint wrong tool path was not a pass; resolved `tool/actionlint.exe`
and actionlint passed. Refetched main remains exact expected baseline. Protected
handlers/HTML/PWA/models/events/production Compose/Dockerfile have zero diff.

First full-suite reruns discovered the second existing hardcoded catalog range
guard (23→24 IDs); corrected without weakening exact-ID checks. Python 3.13 also
reproduced known EF-08a backup `staging.rename(completed)` WinError 5 in
`test_same_timestamp_never_overwrites_completed_bundle`. No backup-code changes,
retry or suppression; Windows reliability issue remains unresolved. Both runs
failed (232 discovered, six POSIX skips); corrected full reruns required, not passes.

### RL-02 full local verification

Full Standard Checks **exit 0** on Python 3.12.13/3.13.15: **232 discovered,
226 passed/six POSIX-only skips** each (91.888s/100.530s). Ruff/format/syntax,
24-ID exact traceability, real age/encrypted recovery, migration/legacy/full served
regressions, strict dependency audits (none known), Chromium/diff all passed.
Actionlint passed. Logs outside Git `rl02-verified312.log` / `rl02-verified313.log`.
One intervening rerun failed changed catalog-file formatting; formatted that file,
no ignores. Earlier Windows EF-08a WinError 5 remains unresolved despite successful
reruns. Existing lifecycle/TestClient/action warnings retained; no UI/cache changes.
Plan `4258ab5`, core `3fdef64`, installed-image rehearsal `f61a40c` committed.
Actual-image/Linux permission/branch/PR final-head evidence still pending, not inferred.

### RL-02 implementation review receipt

PR https://github.com/tostman1/drink-pos/pull/7 **OPEN/unmerged**. Implementation
head `4c68ab3b5e84b1f3133b235bed929f67692e816f` passed exact branch
https://github.com/tostman1/drink-pos/actions/runs/45254857601 and PR
https://github.com/tostman1/drink-pos/actions/runs/45254875390. Both Linux matrices:
**232 discovered/231 passed/one Windows-only skip**, real new POSIX read-only-file
permission test executed (ok), all prior POSIX/real-age/security/Chromium gates pass.
Actual Dockerfile/local-only image, four Compose validations, startup/restart/
persistence/EF-08a-b recovery, installed offline identity/legacy upgrade, opt-in
versioned fresh/repeat/metadata adoption/independent EF-08b recovery, encrypted
complete source+owned-image-loss DR and image dependency audit **passed**.
Publication **skipped**, implementation-head deployments `[]`. No production inputs.

Installed migration result: original_tables_preserved=17 (16 application + sequence),
history_rewritten=false, repeat_startup_verified=true, recovery_verified=true,
network_attempts=0; historical_release_evidence='none; exact synthetic current fixture
only'. Branch image binds exact implementation head; PR image binds GitHub synthetic
merge tree `2c91fb670ac49496632661e61c6eef9efeca8073`, not a released artifact.
DR confirms public-only producer, original owned image unavailable before archive
load, shared input image preserved, source storage removed, post-snapshot commit
not replayed. PR synthetic RPO age 0.400362s/RTO 2.607613010s, NOT operational SLA.
Logs outside Git `rl02-pr-ci.log`/`rl02-branch-ci.log`; existing warnings retained.

Refetched main still exact baseline, feature clean/synchronized before this
documentation-only receipt. Protected handler/UI/PWA/payment/invoice/recovery/
Dockerfile/production Compose/updater code unchanged. Final receipt SHA/its own
branch/PR CI MUST be verified separately and recorded in PR final delivery/report;
do not infer final-head pass from predecessor or embed self-referential SHA.
No merge/release/publication/deploy/production DB/payment/SMTP/schedule operation.
OQ-06 accounting/adoption breadth, actual MV-01..06 and EF-08a Windows WinError 5
remain open. Stop after final-head delivery; independent owner review next.

## RL-01 final integration — 2026-11-23

- Owner completed independent implementation/security review, no merge blockers,
  explicitly approved PR #6 subject to exact-head gates. Clean fetched head
  `03853fde50ac1dbf31e83b2b522704acd115ec62`; main/base exactly
  `dbc314e0790534ee44f362be4a194143385eb071`. Specified branch `45211470701` and
  PR `45211487658` passed all matrices/browser/security/Docker/Compose/upgrade/
  recovery/DR/image audit, publication skipped. MERGEABLE/CLEAN, no reviews/threads/
  inline findings; no configured required checks, none bypassed. Initial Windows
  GraphQL command quoting error corrected via explicit JSON input; query succeeded.
- Normal exact guard `gh pr merge 6 --merge --match-head-commit 03853fde...`:
  **`09a27a8866392cc7cdcf2b1006d31cfaccee571c`**, 2026-11-23T17:40:50Z.
  Parents exactly verified base/reviewed head, entire merged tree identical to
  reviewed `93363456e0515bc761aceaad166907c14cd1a5d2`. Primary checkout switched
  to main and fast-forwarded safely; clean/synchronized, feature/handoff branches
  preserved, no reset/rebase/force push. Protected runtime/UI/payment/invoice/
  production Compose/updater/timer/migration/recovery files zero diff against base.
- Exact merge main https://github.com/tostman1/drink-pos/actions/runs/45230274124
  **passed**, Python 3.12/3.13 full Standard Checks (208 discovered/207 passed/one
  Windows-only skip each), browser/security/23-ID traceability/POSIX guards;
  actual local-only Docker build, all four Compose validations, startup/restart/
  persistence/EF-08a-b recovery, installed identity/synthetic upgrade/all-table/
  API/second-start/separate recovery, EF-08c encrypted source+owned-image loss/
  archive reconstruction/gated network-disabled startup, image audit all passed.
  Publication **skipped**, merge-head deployments `[]`. No release/deploy dispatch.
- Actual merge image upgrade binds merge SHA, 17-table synthetic schema
  `694d25ba64f7674a3e10b7402108417f0282aefa8c61fbc1a9ca922ff66ad264`,
  recovery_verified=true/network_attempts=0, historical_release_evidence='none;
  synthetic fixture only'. DR public-only producer, original owned image unavailable
  before archive load, shared image untouched, all source storage removed; one
  post-snapshot commit remains lost/no replay. Synthetic RPO 0.352007s/RTO
  2.300773869s/total 7.27795965s, not production SLA/real human reconciliation proof.
- Local merged-main full gates exact exit 0 Python 3.12.13/3.13.15, 208 discovered/
  203 passed/five existing POSIX-only skips, 99.795s/101.868s. Ruff/format/syntax/
  traceability/real age/strict audits (none known)/Chromium/diff passed, actionlint
  passed. Outside-Git logs `rl01-merged-main312.log`, `rl01-merged-main313.log`,
  `rl01-merge-main-ci.log`; existing lifecycle/TestClient/action deprecations retained.
- Receipt is documentation-only; final main SHA/its own CI must be read/verified
  after push and recorded in PR #6 final integration record/report, not inferred
  from merge CI (self-referential SHA cannot be embedded in its own commit).
  No reviewed code changes after merge. No next work package or production activity.

**RL-01 integrated; stop after final receipt/main CI verification.** Preflight is
read-only isolated-bundle evidence validation, success only permits a separately
authorized rehearsal, unknown non-success; no deployment/live compatibility/key
authenticity/schema-ledger/automatic rollback claim. Current startup partial early
DDL/WAL/files and repeated financial cost/profit backfill remain; existing mutable
unattended force-recreate/prune updaters remain unsafe/unmodified. Release/support/
provenance/operator-adoption and RL-02 versioned transactional/pre-write migration
decisions remain unresolved, RL-02 not begun. MV-01..05 pending; MV-06 actual storage/
geography/immutability/encryption/ACL/key-image retrieval/timed human payment/mail
reconciliation acceptance partial. EF-08a Windows WinError 5 unresolved, no fix
inferred. No production deploy/release/publication/digest/config/schedule change,
production DB migration/access, real payment/mail; disposable synthetic verification
only. Owner PR #6 merge approval is not future-package/production authorization.

## RL-01 active release-safety foundation — 2026-11-23

- Clean fetched main/base exactly `dbc314e0790534ee44f362be4a194143385eb071`;
  exact CI `45199604894` passed both matrices/container/DR/audit, publication skipped.
  Dedicated `feature/rl-01-release-safety`; no history rewrite/user changes/delegation.
- Ready gate/risk inventory written first in `docs/rl-01-contract.md`; DP-023 added.
  Initial ten preflight tests failed missing interface before implementation.
  Existing startup risks characterized: early DDL/messages/WAL persist after late
  failure, DML rolls back, no maintained ledger, purchase cost/profit backfill repeats,
  late duplicate payment index fails. Migration implementation untouched.
- Optional offline identity + isolated completed EF-08b bundle-only preflight added;
  exact identity/image/schema/config/installation/key evidence, no successful unknown.
  11 targeted tests pass; read-only connection/byte parity/pre-SQL sidecar/WAL guards.
  Six migration/rehearsal tests pass; missing rehearsal failed first. Full synthetic
  startup/ASGI/state/artifact/second-start/recovery comparisons implemented.
- Rehearsal test initially failed because Windows asyncio self-pipe uses socketpair;
  corrected infrastructure initialization before app network guard, in-memory ASGI
  requires no new runtime/dev dependency. No live provider/email/network use.
- Optional no-pull/no-restart digest-pinning Compose guidance; old deployment scripts/
  Compose/timer/Dockerfile/handlers/UI/worker/recovery formats unchanged. New actual
  image identity/rehearsal CI stages non-publishing. Docker/Podman unavailable locally;
  actual image/Compose evidence pending CI. Full local gates pending until recorded.
- Ruff passes; initial actionlint path missing (not pass); resolved path/full checks
  follow. MV-01..06/Windows EF-08a WinError 5/real operator adoption remain open.
  Only commit/push/open PR authorized, no merge/release/publication/deploy/real state.

### RL-01 final local verification

Both full Standard Checks exact exit 0, Python 3.12.13/3.13.15: **208 discovered,
203 passed/five existing POSIX-only skips**, 102.162s/105.981s. Ruff/format/syntax,
23-ID traceability, real age recovery, full migration/preflight/rehearsal suites,
strict dependency audits (none known), Chromium/diff all passed. Logs outside Git:
`rl01-final312.log`, `rl01-final313.log`. Actionlint passed at resolved tool path.
Concurrent Windows Ruff cache write warning (Access denied) retained; lint/format
exit 0, cache acceleration not required. Existing lifecycle/TestClient deprecations
retained; no UI/worker changes/cache bump required. Docker/Podman unavailable;
actual image/Compose/Linux permission and exact-head CI evidence pending, not inferred.
Final review adds strict metadata/future/unassigned version, full 16-table inventory,
FK corruption, observed-change/interruption/Linux read-only permission and optimized
interpreter refusal guards. No recovery/financial/startup/default deployment changes.

### RL-01 reviewed implementation / CI evidence

PR https://github.com/tostman1/drink-pos/pull/6 **OPEN/unmerged**, core `f6c5ae3`,
rehearsal `b8a8682`, contract implementation head
`fdbdb5627c4fae61c41bd7e0a99c3e1a85655052`. Exact branch CI
https://github.com/tostman1/drink-pos/actions/runs/45209356414 and PR CI
https://github.com/tostman1/drink-pos/actions/runs/45209479532 **passed** all gates.
Linux both matrices: **208 discovered/207 passed/one Windows-only retry-test skip**;
POSIX/read-only permission guards executed. Four Compose configs validated, actual
Dockerfile/local-only image built, startup/restart/persistence/EF-08a/b recovery,
installed offline release identity and network-disabled synthetic upgrade/state/API/
second-start/separate recovery passed; existing encrypted DR/image-loss reconstruction
and image dependency audit passed. Publication **skipped**, deployment query `[]`.
Actual upgrade result: 17 tables, recovery_verified=true, network_attempts=0,
historical_release_evidence='none; synthetic fixture only'; exact synthetic schema
`694d25ba64f7674a3e10b7402108417f0282aefa8c61fbc1a9ca922ff66ad264` (fixture adds
audit trigger/payment index, NOT universal application schema). PR image records
GitHub synthetic merge tree `b5847d072c4d4fd06419709f229a475a53d46f76`; branch image
records exact implementation commit. No published digest fabricated. Logs outside
Git `rl01-pr-ci.log`, `rl01-branch-ci.log`; existing warnings retained.

Refetched main remained exact `dbc314e`, clean synchronized feature tree; protected
runtime/migration/recovery/UI/build/production Compose/updater/timer/dependency files
have zero diff. This is a documentation-only receipt; final receipt HEAD/checks
must be verified separately at delivery, not inferred from predecessor. No merge,
publication/release/deployment/real-state/provider/mail activity. Stop after delivery;
owner independent review next. RL-02 versioned migrations/pre-write gate is proposed,
not started/authorized. Release support/provenance/operator acceptance and MV-01..06/
EF-08a Windows WinError 5 remain open; image reversion is not state rollback.

## EF-08c final integration — 2026-11-23

- Owner completed independent security/implementation review and approved PR #5
  merge subject to exact head/checks. Clean fetched head
  `982dbf101c15e78ff7cb2eb3a6fafe557925b84a`; base/main remained
  `e8caeed029266764d5594c275ff769ccc7cf35c8`. Required engineering gates in
  branch `45195265860` and PR `45195281503` passed, publication skipped. GitHub
  MERGEABLE/CLEAN, no review threads/inline findings; no configured required checks.
  No checks/protections bypassed, no changes to reviewed history or sensitive runtime.
- Merged normally with `--merge --match-head-commit` as
  **`34cc06a1f287348af32caa173796afc512485342`**, 2026-11-23T14:50:50Z.
  Parents verified (expected base/reviewed head), whole tree identical to review.
  Primary worktree switched to main and fast-forwarded safely; branches preserved.
- Post-merge main CI https://github.com/tostman1/drink-pos/actions/runs/45198599811
  **passed on exact merge SHA**: both Python matrices/full gates, three Compose
  validations, actual image/startup/restart/persistence/recovery, complete encrypted
  disaster/source-storage and owned-image loss→archive reconstruction/offline startup,
  image security audit. Linux 187/186 passed/one Windows-only skip each, all POSIX
  guards executed. Publication **skipped**; deployments query returned `[]`.
- Security correction verified and integrated: public-recipient-only producer,
  encrypted-transfer-complete v2, separate private-key full verification plus trusted
  independent/offsite receipts, explicit combined opt-in, conservative old envelopes/
  receipts. Main drill `producer_private_key_required=false`, owned image unavailable
  before archive load, shared input not removed; source storage removed, uncertainty/
  post-snapshot loss held/no replay. Synthetic RPO age 0.285082s, RTO 2.018970907s,
  total 6.311423030s (3600s/300s targets met; not production performance guarantees).
- Both local full gates on merged main **exit 0**, Python 3.12.13/3.13.15:
  187 discovered/182 passed/five POSIX skips, 85.443s/85.050s. Ruff/format, all
  syntax/PWA/22-ID traceability, actual age, strict audits (none known), Chromium and
  diff passed; actionlint passed. Logs outside Git `ef08c-merged-main312.log`,
  `ef08c-merged-main313.log`, `ef08c-merged-main-ci.log`. Deprecations retained.
- Documentation-only receipt follows; its final main SHA and own CI must be checked
  at delivery. No implementation after reviewed merge. No production deployment,
  release/publication/image digest/config change, production data/payment/SMTP use.
- **Stop: EF-08c integrated; no next work package.** MV-06 automated synthetic
  encrypted independent loss/rebuild/owned-image archive/timing proof complete;
  actual geography/hardware/WORM/storage/ACL/secure escrow/timed human external
  reconciliation/acceptance pending. EF-08a intermittent Windows WinError 5 still
  unresolved, no fix inferred from successful gates. MV-01..05 unchanged.

## PR #5 security boundary correction — 2026-11-23

Continued clean reviewed `fe012099998d41ac3dd3d15e90cc754c8715e0c0` on existing
`feature/ef-08c-disaster-recovery`; fetched main unchanged `e8caeed`, PR OPEN/CLEAN.
Owner review identifies private-key prerequisite on producer. DP-022 correction
ready gate written in `docs/ef-08c-contract.md` before implementation, failing public-
only regression reproduced missing identity error. Default producer now public-only,
new v2 encrypted-transfer-complete envelope (EF-08a/b unchanged), separate explicit
full/private-key and independent/offsite verifier attestations. Combined creation/
verification explicit opt-in only; status cannot infer full recovery from encryption,
copy/hash or old ambiguous receipts. Protected verifier journal remains trust boundary,
not a sender signature/geographic proof. Tests cover real producer decryption denial.
Image review: original drill loaded archive while original image remained available.
Correction uses unique UUID-owned labelled image, removes only that config without
force, asserts unavailable before archive load and exact ID/label after; shared image
untouched. Mock safety/order and actual-image CI evidence required. No runtime/
financial/production changes; no merge, release/publication/deploy authorized.

Security-correction targeted suite: **22 discovered/21 passed/one POSIX-only skip**
on Windows. Both full local Standard Checks exit 0, Python 3.12.13/3.13.15:
**187 discovered/182 passed/five POSIX skips**, 97.984s/101.100s; Ruff/format,
Python/JS/PWA/traceability, real age/public-only/decryption denial/state transitions,
combined wrong-key/v1 handling, Chromium and strict vulnerability audits passed
(none known). Traceability links updated and revalidated. Logs outside Git:
`ef08c-security312.log` / `ef08c-security313.log`. Actual owned-image removal/archive
reconstruction and final corrected-head container CI remain required, not inferred.

Corrected implementation `6af9cae5aefe33423d13c1c8e84f490f337c0b6e` passed
branch `45192886047` and PR `45192900590` full gates. Linux each: **187 discovered/
186 passed/one Windows-only retry-test skip**, public-only/decryption denial/full-
independent state transitions/v1/ownership tests executed. Actual image/three Compose
configs/complete encrypted source-loss/owned-image removal+archive reconstruction/
network-disabled startup/image audit passed; publication skipped. PR drill flags:
`producer_private_key_required=false`, `original_owned_image_unavailable_before_archive_load=true`,
`shared_input_image_removed=false`. Synthetic RPO age 0.358806s/RTO 2.318645502s,
total 7.378924705s, not operational SLA. Final small test review directly verifies
wrong/missing private-key verification also fails without modifying valid transfer.
Final evidence receipt/head must pass its own gates; no inferred pass from predecessor.
Final reviewed test/docs local gates both exit 0: 187 discovered/182 passed/five
POSIX skips, Python 3.12/3.13 full lint/format/syntax/traceability/security/Chromium.
Logs `ef08c-security-final312.log` / `ef08c-security-final313.log` outside Git.
No EF-08a Windows rename recurrence in these checks; unresolved finding unchanged.

## EF-08c active — 2026-11-23

- Clean fetched main `e8caeed029266764d5594c275ff769ccc7cf35c8`; exact base CI
  `45171495944` passed. Branch `feature/ef-08c-disaster-recovery`, owner approves
  bounded implementation/commit/push/PR only, not merge/deploy/publication.
- Ready gate `docs/ef-08c-contract.md` before implementation; DP-022/021/014 and
  financial/state contracts. EF-08a/b preserved. External mature age v1.3.2 chosen,
  optional filesystem envelope/standard tar/no provider API; exact official Windows
  archive SHA-256 verified outside Git/image. First seven new regressions all
  failed (missing interface), then passed with real temporary synthetic keys.
- Added independent encrypted publication/decryption/full-bundle validation,
  no-clobber isolated recovery and sanitized operation journal/status. Source/key/
  scratch/journal/destination roots separate; no crypto implementation or retention.
  Actual-image installation-loss drill added; full local/CI gates pending, not passes.
- Targeted 13 tests passed locally (before final extra guards); fixture populates
  real served synthetic round/payment/cashup/price/event/idempotency state and
  explicitly gates isolated startup on synthetic reconciliation, no network attempts.
- Windows EF-08a WinError 5 remains unresolved, no correction/retry in this package.
  MV-06 real geography/hardware/immutable/encrypted-storage/ACL/escrow/image retrieval/
  timed operator external reconciliation acceptance remains pending. No real resources.

### EF-08c local gates

Both full Standard Checks exact child exit 0 on Python 3.12.13/3.13.15:
**181 discovered, 176 passed/five POSIX-only skips**, 75.023s / 73.412s.
Ruff lint/format, compilation/all JS/PWA/data/22-ID traceability, real age synthetic
replica/key/failure tests, Chromium and strict dependency audits passed (none known).
Actionlint passed. Logs `ef08c-full312.log` / `ef08c-full313.log` outside Git.
No EF-08a WinError 5 recurrence in these runs, not proof of fix; no retry added.
No UI changes/cache bump needed. Docker unavailable locally; actual installation-
loss/image/Compose/CI metrics remain pending. Reviewed bounded diff: new optional
recovery/fixture/tooling only, production files and existing EF-08a/b unchanged.

### EF-08c first CI evidence and final review

PR #5 https://github.com/tostman1/drink-pos/pull/5 OPEN. Core `ead0522`, image
rehearsal `d38928d`, docs `25766e6`. Both exact-head branch/PR runs `45179952940` /
`45180047138` passed quality and actual image/Compose/DR/audit; publication skipped.
Linux 181 discovered/180 passed/one Windows-only skip; POSIX key/ciphertext modes
executed. PR workflow runs synthetic merge tree `57b8a5ee03131f05309eb0f20361421906a2dd77`
for image metadata; run head is `25766e6f573ead4326d6bc8548ad30c5ff18ed8f`.
Actual source volume/container/local bundle removed, independent age copy/escrow/
image reconstruction + complete state/network-disabled startup passed. First PR
synthetic RPO age **0.113042s**, RTO **1.875316774s**, total **5.198156745s**,
backup **0.568106799s**, replica verify **0.028775162s**, synthetic key/image
retrieval **0.556097483s**, recovery validation **0.024410730s**, startup synthetic
reconciliation **0.801495107s**. Targets 3600s/300s met; not production performance.
Final review adds explicit post-snapshot lost synthetic commit and no-replay assertion
(outside backup boundary, snapshot preserved) to strengthen RPO/reconciliation evidence.
Final local/CI head must rerun; first-pass evidence is not final-head proof.
Final local full gates exit 0 on both Python versions: **182 discovered/177 passed/
five POSIX-only skips**; Ruff/format/syntax/22-ID traceability/security/Chromium/diff
passed. Logs `ef08c-final312.log` / `ef08c-final313.log` outside repo. No Windows
EF-08a rename failure encountered in these reruns, finding remains unresolved.

### EF-08c reviewed implementation evidence

Exact implementation head `beb4e494bc565029113b33f2b1929b8714b8a384` passed
branch `45181307115` and PR https://github.com/tostman1/drink-pos/actions/runs/45181321303.
Linux both matrices **182 discovered/181 passed/one Windows-only skip**; actual
Docker/three Compose validations/EF-08a-b/start-restart/full encrypted source-loss
reconstruction/image audit passed; publication skipped. Post-snapshot synthetic
commit was not recovered/replayed, uncertain payments remained held. PR rehearsal:
RPO age **0.368372s**, RTO **2.250698623s**, total **6.576092409s**; backup
**0.688306717s**, replica verification **0.047257094s**, synthetic key/image
retrieval **0.399142310s**, recovery validation **0.039346896s**, gated startup
**1.165725736s**. These are CI synthetic measurements, not an operational SLA.
MV-06 automated encrypted independent-copy/source-loss/full-state rebuild/timed
isolated startup evidence demonstrated; actual geography/hardware/WORM/ACL/secure
escrow acquisition/timed human external payment/mail reconciliation remains pending.
Documentation-only final receipt follows; its own final-head CI is authoritative.
No production/live services/accounts/publication/deploy/merge. PR #5 OPEN/CLEAN,
base remains `e8caeed`. Stop after review delivery; owner approval required to merge.

## EF-08b final integration — 2026-11-23

- Owner completed independent review with no merge-blocking findings and explicitly
  approved merging PR #4 subject to exact reviewed head/checks. Clean local/fetched
  head `0fbd743320db4b61bd279220a09062b04dad1cb1`, main `b8cb487`; branch/PR
  CI `45164310541` / `45164321226` passed, publication skipped. GitHub CLEAN/
  MERGEABLE; no review threads/inline findings, no required check configuration.
  No protection bypass, admin flag, history rewrite or unexpected diff.
- Merged normally with exact head guard as
  **`6f5e280b090c9bb915dfabe88db9329dea31da80`**, 2026-11-23T11:53:25Z.
  Parents and reviewed-tree equality verified. Primary checkout switched to main,
  fast-forwarded to origin/main; feature/handoff branches retained.
- Post-merge main run https://github.com/tostman1/drink-pos/actions/runs/45169203989
  **passed** on exact merge SHA: both Python/Node Standard Checks, all three
  Compose validations, actual image build/startup/restart/persistence/healthcheck,
  network-disabled complete application recovery and image vulnerability audit.
  Linux 165 discovered/164 passed/one Windows-only retry skip each; actual POSIX
  permissions, complete operational state and final isolation regressions executed.
  Publication **skipped**; deployments query returned `[]`.
- Local full Standard Checks on merged main **exit 0** for Python 3.12.13/3.13.15:
  165 discovered/161 passed/four POSIX-only skips (48.550s / 53.360s), Ruff/format,
  Python/all JS/data/21-ID traceability, strict vulnerability audits (none known),
  Chromium smoke and diff hygiene passed. Actionlint also passed. Logs retained
  outside Git as `ef08b-merged-main312.log`, `ef08b-merged-main313.log` and
  `ef08b-merged-main-ci.log`. Existing lifecycle/TestClient/action warnings retained.
- Documentation-only integration receipt follows; final main receipt HEAD/checks
  must be verified separately, not inferred from predecessor CI. No runtime changes,
  production/deploy/release/publication, real DB/payment/mail or image-digest changes.
- **Stop after integration; no new work package.** MV-06 independent encrypted/
  immutable/offsite/storage/ACL/timed RPO/RTO/operator reconciliation acceptance
  remains partially pending. Offline all-writer quiescence, independent secret/image
  escrow and checksum-only authenticity limitations remain. MV-01..05 unchanged.

## EF-08b active implementation — 2026-11-23

- Clean fetched local/remote main exactly `b8cb4870d90f75b9dbc2668246788c5aa24ee8a5`;
  exact base CI `45152440365` succeeded. New branch `feature/ef-08b-portable-recovery`.
- Ready gate/state inventory/consistency/acceptance/rollback written before code in
  `docs/ef-08b-contract.md`. DP-014/010/011/013/018/019 and new DP-021 engineering
  contract. Served CSV→PDF→SMTP→audit/commit and external message editors rule out
  a DB-only coordination lock. Choose explicit all-writer offline maintenance,
  not business-logic changes or online guarantees.
- Initial new regressions: **10 failures/one POSIX skip** (missing interface),
  existing EF-08a 23 tests: 20 passed/three POSIX skips. New separate bundle core,
  no-clobber isolated restore, exact non-location logical parity, portable path/
  symlink/reparse checks, private permissions, sanitized JSON/age CLI implemented.
- Targeted expanded suite **22 discovered, 21 passed/one POSIX skip** locally.
  Two real synthetic installations/all 16 operational tables + sequence, generated
  invoices/messages, failures/kill/overlap/legacy checks. One local run encountered
  transient Windows directory rename permission denial; rerun passed, no retries
  added to hide storage failures. Test-fixture default text encoding/case-sensitive
  assumptions corrected; Linux permission/special-file evidence still requires CI.
- Generic optional Compose example and network-disabled image recovery rehearsal
  added; existing deployment configs/digests/schedules untouched. No runtime handler,
  schema/payment/mail/UI behavior change. Full local/CI gates follow; no pass inferred.
- MV-06 remains partially pending: independent encrypted/offsite/storage/ACL/timed
  RPO/RTO/operator reconciliation acceptance. No production/live service use.

### EF-08b local gate receipt

- Initial full gates caught the catalog's hardcoded 20-ID guard; updated to 21
  explicit IDs (DP-021 added), no traceability validation weakened. Ruff formatting
  failures corrected before reruns. Windows publication failures repeated across
  both Python versions, not dismissed as a pass: wrote failing regression then
  added Windows-only six-attempt/1.5-second **atomic no-replace rename** retry with
  sanitized logs/target recheck; persistent denial fails, no application operations
  or side effects repeated. The test covers transient, persistent and target cases.
- Full Standard Checks now **exit 0** on Python 3.12.13 and 3.13.15 via UTF-8
  exact-child-status runner, isolated approved temp root: **162 discovered,
  158 passed/four POSIX-only skips** each. Ruff lint/format, Python/JS/data/21-ID
  traceability, full tests, strict dependency audits (no known vulnerabilities),
  Chromium smoke and diff hygiene passed. Existing lifecycle/TestClient warnings
  retained. No UI/worker change (no cache bump needed).
- Logs outside repo: `ef08b-confirmed312.log` / `ef08b-confirmed313.log` in approved
  temporary tooling. Local Docker is unavailable; actual Compose/build/container/
  recovery/image audit and POSIX evidence must come from final CI, not this receipt.

### EF-08b review and CI receipt

- Commits `b120b65` core/tests, `06cb62c` actual-image rehearsal/example and
  `46cf466` docs/traceability pushed. PR **#4 open, not merged**:
  https://github.com/tostman1/drink-pos/pull/4. Refetched main still `b8cb487`.
- Exact `46cf466e386475f761c648141872d3859e9d4d1d` branch CI `45160412546` and
  PR CI https://github.com/tostman1/drink-pos/actions/runs/45160481935 **passed**.
  Linux matrices: **162 discovered, 161 passed/one Windows-only retry-test skip**;
  POSIX 0700/0600, FIFO/case-sensitive/symlink guards executed successfully.
  Existing EF-08a POSIX guards executed too. All three Compose files validated;
  actual local-only image build, startup/restart/persistence/offline application
  recovery and image dependency audit passed; publication **skipped** in both runs.
- Final review adds explicit synthetic transport staging→completed verification,
  opposite-platform source-path relocation, publication permission failure and
  ordinary restore interruption tests (no runtime change). Full local gates rerun:
  **164 discovered, 160 passed/four POSIX skips** each, exact child exit 0 on
  Python 3.12.13/3.13.15; Ruff/syntax/traceability/security/browser/diff all passed.
  Logs `ef08b-final312.log` / `ef08b-final313.log` outside Git. Final pushed-head CI
  must be verified separately; predecessor evidence is not a final-head claim.
- No real resources/accounts, production image/digest/config change, release,
  publication dispatch, deployment or merge. Next bounded recommendation: isolated
  independently managed encrypted/offsite recovery and timed operator acceptance
  drill (MV-06), not online invoice/SMTP redesign without its own decision.

### EF-08b final reviewed-code evidence

Exact reviewed implementation/test head **`59fdf9d896fd00595c9232f86f021b5e52966430`**
passed branch run https://github.com/tostman1/drink-pos/actions/runs/45161242647
and PR run https://github.com/tostman1/drink-pos/actions/runs/45161253638.
Both Linux matrices: **164 discovered, 163 passed/one Windows-only retry skip**;
logs confirm POSIX modes, transport/opposite-host mapping and all safety guards.
All Compose validations, actual image build/start/restart/persistence/offline
recovery and image dependency audit passed; publication skipped. PR #4 is OPEN,
base still `b8cb487`, merge state CLEAN. This receipt is documentation-only;
final receipt HEAD requires its own CI verification at delivery. No merge,
publication/deploy/release or real data/service use. Owner review is next gate.

Final safety review found restore could be selected inside its source bundle,
modifying immutable backup inventory. DP-021 failing regression reproduced this;
early descendant-target rejection now preserves source bundle unchanged. Targeted
and full gates rerun; final exact head/CI at delivery remains authoritative.
Both local full gates exit 0: **165 discovered/161 passed/four POSIX skips**,
Ruff/syntax/traceability/audit/Chromium/diff passed. No extra exceptions suppressed.

## EF-08 final integration — 2026-11-23

- Owner approved PR #3 merge conditional on exact reviewed head/gates. Clean local
  and fetched remote head matched `e7a6073a0faae9659bcb9963995e96f74653d117`;
  remote main remained `a218fcc`. PR reported MERGEABLE/CLEAN; all established
  quality/container checks succeeded, publication skipped. GitHub has no configured
  merge-required checks; none were bypassed or weakened to merge.
- Merged PR #3 normally with `--merge --match-head-commit`, no admin bypass:
  **`212e6b6c20257dae532ecdbaf5d654beae7f44ab`**, 2026-11-23T09:59:42Z. Tree
  matches reviewed head exactly, parents verified. Primary worktree switched to
  main and fast-forwarded without discard/reset; feature branches preserved.
- Exact merge main run https://github.com/tostman1/drink-pos/actions/runs/45152008134
  **passed**: both Python/Node full gates, both Compose configurations, actual Docker
  image build, disposable container startup/restart/SQLite/backup/new-target restore
  and image runtime dependency audit. Publication **skipped**; merge deployment
  query returned `[]`. No release/deploy/publication dispatch or production access.
- Local merged-main Standard Checks passed Python 3.12.13: 139 discovered,
  136 passed/three POSIX skips, 29.944s; Ruff, syntax/traceability, Chromium smoke
  and dependency audit passed, no known vulnerabilities. Existing lifecycle/action
  deprecation warnings retained. Linux permission checks were executed in reviewed CI.
- This documentation-only final receipt is a main descendant; final main SHA/CI
  must be verified before delivery. No runtime/Compose/digest/deployment changes.
- Bounded EF-08 recovery complete/integrated. **No next work package started.**
  Next intended: coordinated DB/files/artifacts/config/offsite recovery and isolated
  operational rehearsal. MV-06 partially pending, external consumers/Windows ACLs,
  same-NAS/offsite/monitoring/RPO/RTO gaps remain; invoice/SMTP redesign excluded.

## PR #3 final recovery security/compatibility review — 2026-11-23

- Continued the approved EF-08 session on its clean branch at `6612924`.
  Prior exact-head PR run `45141076838` passed all quality/container/image audit
  jobs; publication skipped. Refetched main remains `a218fcc`; no integration drift.
- DP-014 failing regression written before code: SQLite previously created the
  restore file itself. Local baseline **one failure, three POSIX skips**; Windows
  has no installed WSL/Docker runtime, so real POSIX mode evidence requires CI.
- Small correction: mkstemp pre-creates 0600 restore DB; each missing directory
  component mkdir(0700), no chmod of existing dirs; enforce 0600 on owned file
  before no-clobber hard link. Private staging/cleanup, FK/checksum behavior and
  financial contracts preserved. Windows ACL limitations documented, not inferred.
- Targeted recovery rerun: **27 tests, 24 passed, three POSIX skips** on Windows.
  Linux CI must execute those POSIX tests; full local and final CI gates follow.
- Compatibility inspection: Compose schedulers just execute the backup CLI;
  current scripts/tests consume its returned CSV path, no root-name glob reader
  found. Operational YAML had a stale top-level filename and README said CSV-only;
  corrected both. External NAS filters/consumers unknown, no production inspection.
  Runbook defines inventory, synthetic validation, whole-bundle verification/copy,
  legacy preservation and explicit optional private CSV adapter for unchangeable
  consumers. No automatic duplicate export or presumed NAS migration.
- Same bounded scope, no deployment/publication/production access/merge; MV-06
  remains partially pending and manual MV-01..05 are unchanged.
- Full local Standard Checks passed Python 3.12.13 and 3.13.15: **139 discovered,
  136 passed, three POSIX skips** each (37.357s / 37.491s). Ruff lint/format,
  Python/all JS/data/traceability, Chromium smoke and strict dependency audits
  passed, no known vulnerabilities. Reviewed full correction diff; no generated
  state, secrets, financial/schema/REST/Compose/image/workflow changes. Real POSIX
  mode evidence and exact pushed-head container verification still require CI.

### Security/compatibility verification receipt

- Focused correction `1aa53856598a53d9b656f98b057979526477f579` passed push CI
  https://github.com/tostman1/drink-pos/actions/runs/45149972529 and PR CI
  https://github.com/tostman1/drink-pos/actions/runs/45149983134 on that exact SHA.
  Both Linux Python matrices passed **139 tests, no skips**. Retrieved logs show
  all four new permission/staging tests **ok**, including permissive umask,
  existing-directory preservation and chmod-before-link/failure checks.
- Actual Docker build, both Compose validations, disposable container recovery/
  restart/health and image runtime dependency audit passed; publication **skipped**.
  Existing FastAPI/Starlette and forced-Node24 action deprecation warnings remain.
- Documented one-bundle CSV adapter exercised synthetically on both local Python
  versions: identical CSV bytes/BOM, collision rejected, staging cleaned, bundle
  preserved. Operational YAML parsed and revised bundle inventory asserted.
  No real consumers were migrated; external NAS configuration remains unknown.
- This receipt is documentation-only; the final receipt HEAD must pass its own
  PR checks before delivery. PR #3 remains open/unmerged and owner approval is
  required. Code review/CI readiness is not production adoption readiness: MV-06,
  external CSV consumers and Windows ACL/operator checks retain documented limits.
  Stop after delivery; no next work package, merge, deployment or publication.

## EF-08a — bounded database recovery, 2026-11-23

- Owner authorized implementation, branch, commits, push and PR; **not merge**.
  Clean incoming main matched `a218fcc40599d5a19e53f2afee490238eeb7e910`.
  Fetched remote main matched; exact base quality Python 3.12/3.13 and container
  checks succeeded, publication skipped. Branch `feature/ef-08-database-recovery`.
  Broken workstation DNS was bypassed only per command with TLS-preserving address
  resolution, not system/repository configuration.
- Scope DP-014/DP-013, acceptance recorded before code in `docs/recovery.md`.
  First eight new regressions produced **seven failures** on baseline (one existing
  interruption behavior already passed); full snapshot absence/FK gap demonstrated.
- Implemented full Backup API SQLite snapshot, unchanged CSV in atomically
  published unique bundle, checksum/size/table-count manifest, integrity/FK checks,
  explicit new-target verification/no-clobber restore and opt-in conservative
  retention (minimum two verified bundles; stale lock disables cleanup).
- Synthetic rehearsal compares all 16 operational tables + sequence state and
  exact schema/index definitions; retains open debt, cashup/round history, financial
  snapshots, payment/session/client IDs, event state. Actual generated event CSV/PDF
  and message JSON are separately copied/restored by checksum. SQLite recovery
  alone does not recreate these files. Startup on recovered synthetic DB tested.
- Targeted recovery suite passed **21 tests** before final extra publication/startup
  assertions. First full Python 3.12 Standard Checks passed **130 tests**, Ruff/
  Python/JS/traceability, dependency audit (no known vulnerabilities) and Chromium
  smoke. Final reruns and actual container CI evidence follow below.
- Fixed Windows fsync writable-descriptor requirement and a test's unclosed SQLite
  handle; failures were recorded, not ignored. FastAPI/Starlette deprecations remain.
- No production resources/accounts, deployment, pinned image/digest, Compose or
  release workflow changes. Artifact/offsite protection, scheduling/alerting/RPO,
  secret copies and operator recovery remain gaps. **MV-06 partially pending**;
  MV-01..05 unchanged. Invoice/SMTP redesign remains outside EF-08a.

### EF-08a final local gates

- Full Standard Checks passed Python **3.12.13** and **3.13.15**, **134 tests each**
  (30.549s / 39.631s). Ruff lint/format, compileall,
  all JS/JSON/PWA/traceability, Chromium smoke and strict dependency audit passed
  both; no known vulnerabilities. No UI/worker changes, so no cache bump required.
- Recovery subset comprises **22 tests**, including deliberate process exit 37
  after snapshot creation: only unpublished staging remains; next run succeeds
  without deleting another run's files. New-target races/verification/publication
  failures preserve owner targets and clean owned temporary resources.
- Local Docker/Podman unavailable; actual Docker/Compose/image-runtime and image
  dependency verification require the final GitHub CI run, never a local pass.
- Reviewed tracked full diff plus new files; no generated state/secrets/runtime
  dependencies/REST/schema/business-rule/Compose/workflow changes. Existing CSV
  contents preserved; artifact location intentionally changes to bundled export.

### EF-08a review delivery

- Committed/pushed reviewable core `fbe61b4`, image verification `89cf426`, and
  recovery/traceability docs `0e36214`. PR **#3 open**:
  https://github.com/tostman1/drink-pos/pull/3. Main refetched and still `a218fcc`.
- Exact final HEAD/CI result must be read from PR checks after this receipt;
  CI is in progress at receipt creation, **not yet claimed passed**. No merge,
  release/publication dispatch or deployment performed. Working tree clean after
  commits; no generated DB/backup/invoice/message state tracked.
- Next package: coordinated artifact/offsite recovery plan and isolated operational
  rehearsal, with RPO/RTO, monitoring and protected configuration/image inventory.
  Adoption/deployment or cleanup requires separate owner-approved operational work.

### Final review correction

- Shared backup destinations now scope retention to the current source DB path;
  an additional synthetic regression guards other DB bundles. Final suite is
  **135 tests**, recovery subset **23**; full local reruns are recorded at delivery.
- Predecessor receipt `2c0a507` passed push run `45140644113` and PR run
  `45140651475` (non-publishing). This is predecessor evidence, **not** a claim
  that the final retention correction passed CI; verify the final pushed SHA.

## Current scope

Independent review branch `feature/engineering-foundation-baseline`, based on
verified `main` at `fb0812837694949dc6d228b781f2aa7af2b29d98`.
PR #1 at `250a4e6` was subsequently merged by owner `tostman1` at
2026-11-22T21:15:45Z as `052c2bbc54f05f7c7d850feb8ad597a4e4868670`.
The original handoff branch is unchanged. Verified main was integrated with
branch merge `2ccb377`; no reset/rebase or transferred behavior removal.
Foundation integration: https://github.com/tostman1/drink-pos/pull/2 — **merged**
2026-11-23T08:15:59Z as `246e0967a889822eaaddb438ba523b87b29ffe31` after the
owner's conditional approval and successful final pushed-HEAD checks.

| Package | State | Evidence / next step |
| --- | --- | --- |
| EF-01 Takeover, requirements, process, architecture | Implemented | Full handoff diff/PR inspected; branch isolated; catalog and documented seams |
| EF-02 Standard Checks and regression guards | Verified | Mandatory commands, security/browser, 115 integrated regressions |
| EF-03 CI/container safety and review delivery | Complete / merged | Final branch/PR checks and post-merge main CI passed; publication skipped |
| EF-04 Narrow legacy rehabilitation | Not started / deferred | Next intended session is bounded EF-08 database recovery/data integrity |

## Verification log — 2026-11-22

- Git clean on arrival; expected incoming HEAD and remote main matched exactly.
- Python 3.12.13 via `uv`; dependencies in temporary venv outside repository.
  Windows cloud hardlink installation initially failed; `--link-mode copy` resolved
  it without changing runtime dependencies or the application.
- `python -m unittest discover -s tests`: **87 passed** on main baseline.
- Same command in detached handoff worktree: **96 passed** (including all nine
  transferred regressions). SMTP and SumUp calls are mocked there.
- Initial Ruff `E4,E7,E9,F`: one unused local (`created`) in schema migration;
  unused row lookup removed; SQL unchanged. Initial no-format scope was later
  expanded by owner to mandatory formatting in isolated mechanical commits.
- Node 24.11.1 unpacked to temporary tooling; no frontend build system introduced.
- Docker/Podman unavailable locally. Container build/runtime/Compose checks must
  run in non-publishing CI; do not claim a local container pass.
- FastAPI `on_event` deprecations are retained technical debt, not test failures.
- All six manual checks in `docs/HANDOFF.md` remain pending, especially PR #1 tablet,
  installed-PWA cache refresh, and authorized SMTP delivery.

## Decisions and exclusions

Keep FastAPI/SQLite/vanilla PWA, both import modes, and served legacy handlers.
Do not import another application's architecture, introduce an ORM, change payment retries,
or run historical wide-refactor prompts. See architecture risks and EF-04 gates.
No deployments, production DB operations, live emails/payments or image publication
have been performed. PR #2 was merged only after the owner's later authorization;
this does not authorize any other PR merge or production activity.

## Continued verification — 2026-11-23

- Remote main fetched and matched `052c2bb`; main CI run `45071103604` succeeded
  for that exact SHA. Owner confirmed the merge and continuation; no audit restart.
- Initial foundation Standard Checks passed on Python 3.12.13: **100 tests**,
  repository-wide conservative Ruff, syntax/data, all 20 requirement links and all
  nine original handoff references. Original handoff JS syntax also passed.
- Actionlint 1.7.12 (release archive checksum verified) passed both new workflows.
- User expanded mandatory gate to include Ruff formatting, compileall, verbose
  unittest, dependency/security audit and focused browser checks. These are being
  added; initial 100-test result is not a claim of the expanded gate passing.
- Formatting debt: 17 files initially differ from Ruff formatting; keep fixes
  mechanical in dedicated increments with AST equivalence, no runtime redesign.
- Starlette warns about httpx TestClient deprecation in current dependency
  resolution (FastAPI 0.165.0/Starlette 1.10.0); record rather than hide warning.
- Seven focused HTTP runtime regressions passed before integration, including
  immediate agent charge/no admin settlement rights and stale cash revision.
- Initial isolated installed dependency audit: **no known vulnerabilities found**.
- New tooling formatted; legacy formatting postponed to small mechanical commits
  after main integration to avoid overlapping transferred feature changes.
- Integrated owner main `052c2bb` with merge commit on this branch; clean merge,
  all eight transferred files and nine original tests preserved, no history reset.
- Chromium smoke on combined code passed member booking/admin/event +1/-1 and
  kassa/self-pay rendering with no uncaught page errors. Target-device checks open.
- Ruff formatter cleanup isolated: 10 module/import files, legacy runtime, then
  legacy suite in three dedicated commits; Python AST identical in each increment.
- Requirements catalog now uses verified `052c2bb` baseline with previous base
  retained and original PR #1 tests local (`handoff-integrated`), not fictitious
  external/pending evidence. Remaining manual IDs MV-01..06 still pending.
- Expanded gate: **113 unittests passed** on Python 3.12/3.13; both dependency
  audits clean. Python 3.12 full command passed. Python 3.13 browser assertions
  passed but Windows temporary log-handle cleanup failed, correctly failing the
  gate. Fixed helper to drain a pipe and explicitly use one server worker; no
  application change, no ignored cleanup failure. Rerun follows.
- CI `45130712250`: both Python/Node Standard Checks succeeded; both Compose
  configurations and actual Dockerfile build succeeded. Container initial startup,
  routes/metadata and synthetic booking passed, but restart probe used an obsolete
  dynamically allocated host port. Container logs showed healthy in-container
  probes. Fixed helper to rediscover port after restart and added regression;
  this run is **not** a full container pass. Publication job was skipped.

## Delivery evidence — 2026-11-23

Verified code commit: `57ad9cc39a54768cd9f278f9931a3618e0e2453b`.
Authoritative command: `python scripts/standard_checks.py --node <Node24-path>`.

| Check | Local Python 3.12.13 / 3.13.15 | CI |
| --- | --- | --- |
| `ruff check .` | Pass both | Pass Python matrix |
| `ruff format --check .` | Pass, 57 files formatted | Pass Python matrix |
| `python -m compileall -q app tests` + script compile | Pass both | Pass Python matrix |
| Standalone + inline JS/handlers, JSON/PWA assets | Pass, 130 JS sources/handlers | Pass Node 24 |
| Requirement source/test/manual links | Pass, 20 IDs; original nine tests local | Pass |
| `python -m unittest discover -s tests -v` | **115 passed** both (42.697s / 41.015s) | Pass matrix |
| Dependency audit including transitives | No known vulnerabilities both | Pass matrix and exact image runtime |
| Focused Chromium smoke | Pass both, no uncaught page errors | Pass matrix |
| Compose configs, Dockerfile build | Not run locally (runtime unavailable) | **Pass** |
| Actual container startup/restart/persistence/SQLite/healthcheck | Not run locally | **Pass** |
| Diff hygiene | Pass; no app HTML/worker/models/runtime dependency/Dockerfile/Compose changes vs main | Checks pass |

Successful branch run: https://github.com/tostman1/drink-pos/actions/runs/45131190711
for exact code SHA above. Verified step statuses include both Compose configs,
actual build, container smoke and image dependency audit; publication **skipped**.
PR-specific run https://github.com/tostman1/drink-pos/actions/runs/45131482792
also **succeeded**, including both quality jobs, Compose/build, actual container
startup/restart/SQLite/healthcheck and exact image runtime audit; publication
**skipped**. Local logs are temporary tooling, not runtime data in Git.

The initial 120-second all-in-one shell budgets and Windows log-handle/restart-port
helper failures were recorded and fixed; no skipped/soft-failed checks substituted.
Final direct AST comparison vs main confirms unchanged legacy runtime, event
service and original backend tests. Only nonformat app edit is unused row lookup.
Eight new served HTTP tests plus original handoff regressions protect actual
financial/auth/snapshot/revision/rollback behavior. All MV-01..06 remain pending.

CI warning retained: pinned checkout v4/setup-python v5/setup-node v4 declare Node
20 and GitHub forces Node 24. Their jobs passed; action-major refresh is EF-06
dependency maintenance, not suppressed evidence. Existing FastAPI lifecycle and
Starlette TestClient warnings also remain. No merge/release readiness inferred.
Final evidence commit changes documentation only; code verified above remains
unchanged. Final HEAD/PR-check state is reported by Git and PR #2 at handoff.

## Finalization and merge authorization

The owner authorized merging **PR #2 only**, provided final pushed-HEAD checks
pass, followed by merged-tree/main-CI verification and a clean synchronized main
checkout. This supersedes the earlier pending-owner-review handoff; it does **not**
authorize publication, release, deployment, infrastructure changes or real data.
Local `c47b73c` evidence commit was preserved and pushed during finalization.
Unrelated-project references removed; current requirements/process/handoff wording
reconciled without restarting the audit or changing the runtime.

Next session: database backup, restore and data integrity, the bounded recovery
portion of EF-08. No implementation in this session; preserve existing behavior,
use synthetic data and define acceptance before any future changes. Invoice-mail
side-effect redesign and production recovery require separate authorization.

## Final integration receipt — 2026-11-23

- Preserved/pushed `c47b73c`, then documentation consistency/reference cleanup
  committed and pushed as `64018bd23babe2a9cd995099178517c9ea4020f4`.
- Final local Standard Checks passed on Python 3.12.13 and 3.13.15, **115 tests
  each** (47.931s / 49.065s), no known dependency vulnerabilities; Ruff lint/format,
  compileall, all JS/PWA/traceability and focused Chromium checks passed.
- Final PR run https://github.com/tostman1/drink-pos/actions/runs/45136828301 and
  branch run `45136820988` passed on exact `64018bd`. Actual Compose/image/runtime/
  restart/SQLite/health and image dependency verification passed; publish skipped.
- PR #2 marked ready, then merged with normal merge-commit integration and exact
  head guard (no protection bypass): **`246e0967a889822eaaddb438ba523b87b29ffe31`**.
- Merged tree is byte-identical to checked `64018bd`; parents are previous verified
  main `052c2bb` and final PR head. No unresolved conflicts or new critical
  merge-blocking findings; documented legacy risks/manual evidence remain open.
- Post-merge main run https://github.com/tostman1/drink-pos/actions/runs/45137226115
  **passed** on exact merge SHA: both quality jobs, actual container verification
  and image dependency audit. Publication **skipped**; GitHub deployments for this
  SHA returned `[]`. No release or publication dispatch was issued.
- Primary checkout fast-forwarded to verified main. This final receipt updates
  documentation only; no database backup/restore/integrity work was implemented.
  Its commit is a main descendant; final main HEAD/status can be read with Git.
- Workstation DNS failures were handled with temporary per-command TLS-preserving
  address resolution/tunneling, not system/repository/production configuration.

Next recommendation: bounded **EF-08 recovery assessment** using synthetic DBs,
covering snapshot completeness, new-target restore, integrity/FK checks and event
artifact retention. Define acceptance first in the next session; no production
restore, invoice-mail redesign or infrastructure work is authorized here.
