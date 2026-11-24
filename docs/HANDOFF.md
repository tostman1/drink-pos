# Handoff and protected work

## Current checkpoint — EF-03 governance / deterministic CI waiting, 2026-11-24

**Integrated:** PR #13 https://github.com/tostman1/drink-pos/pull/13 MERGED,
2026-11-24T16:46:46Z, normal exact-head guarded merge
`07e0207d401cf192ef5e1ff578078ad886f36cfe`. Owner explicitly reviewed reported
implementation/local results and authorized controlled delivery/integration;
actual scoped final review complete, GitHub additional reviews/threads empty,
MERGEABLE/CLEAN, protection absent/active rules empty, no bypass/settings changes.
Parent 1 exact `7a6aa5d...`, parent 2 reviewed candidate
`e88fe4fa7f5232c507c2ef131ee60fb41413219a`; both merged/reviewed trees
`d4c0d5aefac349c574de61870a4cdc1ae24a01c9`.

- Exact candidate branch `45440033641` / PR `45440074259` success; both Linux
  matrices and container passed, publication intentionally skipped. Actual branch
  quality evidence: each 351/350 passed/one Windows-only skip, all 33 helper tests
  and previously Windows-skipped POSIX cases executed. Windows local 351/345/six
  POSIX skips and Git Bash 33 tests remain separate; macOS unverified.
- Exact merge-main https://github.com/tostman1/drink-pos/actions/runs/45441083613
  success, attempt 1, exact merge SHA, both quality matrices/container success,
  publication skipped. No production/deployment/Synology/provider/mail operations.
- Governance worktree is on synchronized main; unrelated clean docs branch
  `ac5b7e73...` / OPEN PR #12 unchanged. Original feature and protected history retained.
- **Current receipt is documentation-only.** Its own final SHA is the commit
  carrying this section (read HEAD after commit); final-main helper CI is pending.
  Final SHA/run/metrics recorded in PR #13 receipt/report after verification, not
  recursively committed or inferred from predecessor/same-tree evidence.
- Next action: commit/push this authorized integration receipt, wait once for its
  exact final-main CI with fresh outside-Git result/metrics, post final PR receipt
  and stop. No new package/product epic/release/deployment. Existing Windows
  WinError 5, DSM/mobile/PWA/provider/operator acceptance remain unresolved.
- All candidate/merge monitors completed. Three deterministic operations so far:
  17 gh invocations, seven run-status reads, zero model polling/extra metric probes,
  no timeout/rate limit observed. Timings/paths in PROGRESS. Final receipt monitor
  will be the fourth operation; no model token/request usage measurements available.

This integrated checkpoint supersedes the following retained pre-delivery notes.

- Branch `feature/governance-ci-wait`; HEAD/base
  `7a6aa5dff411c8fb5601b87758a0fc64810aa0c3`, uncommitted scoped governance/helper/tests.
  Worktree `C:/Users/fritz/AppData/Local/Temp/opencode/drink-pos-governance-ci-wait`.
  Original clean `docs/product-operability-requirements` / `ac5b7e7` checkout left
  untouched. Do not import its unmerged product requirements or begin RL-07.
- Owner scope: mandatory token-efficient repository governance + read-only helper,
  DP-018/019; no unrelated product/runtime/UI/migration/Compose/workflow changes.
  Owner now explicitly authorizes commit/push/new PR/candidate CI and controlled
  integration subject to all review/protection/check gates. No release/deployment/
  Synology/product epic authority. No merge/publication/deployment yet.
- Completed: source governance/helper audit; fresh fetched main exact baseline;
  existing run `45410477163` / https://github.com/tostman1/drink-pos/actions/runs/45410477163
  success/exact SHA, mandatory jobs success/publication skipped. Initial 20-test red
  run proved absent helper/policy; all 33 final focused methods pass through Git Bash.
  Full local Python 3.12.13/3.13.15 Standard Checks pass, each 351 discovered/345 passed/
  six POSIX skips (199.618s/207.236s), quality/25-ID traceability/audit/Chromium/diff pass.
  Initial Node PATH failures retained; existing lifecycle/TestClient/LF-to-CRLF and
  EF-08a Windows WinError 5 gaps remain, not fixed by passing tests.
- Pending: authorized committed-tree/final-head branch/PR/container CI and review.
  Completed baseline-run AND existing OPEN PR #12 helper
  compatibility exit 0 (run `45423092675`, exact unrelated `ac5b7e73...`); main
  refetched unchanged. This is not governance candidate CI.
  New branch/PR/final-head CI
  pending authorized commit/push; local Docker unavailable.
- Next action: commit with `git commit -F`, push this branch, create new PR, then
  verify exact candidate branch AND PR CI once each via the helper. Use fresh
  outside-Git result/metrics files `governance-delivery-branch-*` / `-pr-*`. Persist
  resolved candidate SHA/run/PR in the authorized PR receipt after commit, avoiding
  recursive receipt commits. Before merge verify review/protection/base/head gates;
  stop for any unmet approval. Post-merge exact main CI is mandatory, no deployment.
  All recorded local/compatibility jobs completed; no active monitor or external
  wait. No merge or deployment occurred for this package. Original OPEN PR #12 is unrelated; its
  monitor verifies helper compatibility only, not governance branch CI evidence.

Binding future workflow: `docs/PROCESS.md` and `docs/standard-checks.md`, primary
discovery in `AGENTS.md`. Waiting is not reasoning; one deterministic helper call,
automatic background completion or clean checkpoint, never LLM polling. This ONE
current checkpoint is updated on meaningful transitions; historical receipts below
are preserved evidence, not instructions to repeat watcher/recheck/log/context loops
or renewed authority. Final-head/post-merge/local/manual/approval gates stay intact.

## RL-06 integrated handoff — 2026-11-24

PR #11 https://github.com/tostman1/drink-pos/pull/11 **MERGED** with explicit owner
approval after independent technical/artifact review. Supersedes historical OPEN/
UNMERGED notes below for PR #11 only; repository integration, not NAS/production
authorization. **Stop after final verification; do not start RL-07.**

- Reviewed head **`3f9e9d36f572072600390dbdfff3dc611a1e24e6`** and expected base
  **`25a78ba6606e74760969cce7c993d60d3a139f2e`** matched fresh fetched/GitHub state.
  No newer reviews/unresolved threads/changed required checks; MERGEABLE/CLEAN.
  Main protection absent (404), active rules empty; no bypass/configuration change.
  Required branch https://github.com/tostman1/drink-pos/actions/runs/45402852539
  and PR https://github.com/tostman1/drink-pos/actions/runs/45402863286 success:
  both Linux matrices 318 discovered/317 passed/one Windows-only skip, all nine
  RL06 methods executed and complete image/migration/financial/recovery/DR/audit
  gates passed; publication skipped. Original delivery receipt retained at
  https://github.com/tostman1/drink-pos/pull/11#issuecomment-7132981565.
- Normal GitHub `--merge --match-head-commit` (no squash/rebase/admin/force):
  merge **`d647cfc958b7d23d917904af00ef166b7fecef14`**, 2026-11-24T13:59:26Z.
  Parent 1 expected base, parent 2 exact reviewed head; merged/reviewed tree both
  **`0e2281573bef362d28bc26e64be69f972aae773e`**. Primary main fast-forwarded,
  clean/synchronized; feature/handoff branches and prior owner merges preserved.
- Exact merge-main CI https://github.com/tostman1/drink-pos/actions/runs/45409146142
  success: both Python matrices 318/317/one Windows-only skip; actual Docker/test
  Compose/restart/persistence/fresh v2/migration/net corrections/round reversal/
  isolated update/full recovery/age-encrypted source+owned-image-loss DR/image
  dependency audit pass. Publication skipped, deployment query zero. Local full
  Python 3.12.13/3.13.15 Standard Checks 318/312/six POSIX skips, 175.239s/181.087s,
  Ruff/syntax/25-ID traceability/security/Chromium pass. Visible Node-action/
  lifecycle warnings and existing EF-08a Windows WinError 5 gap remain unchanged.
- **Reviewed installation artifact remains the original branch artifact**:
  https://github.com/tostman1/drink-pos/actions/runs/45402852539/artifacts/14924980940
  (ID `14924980940`, source/tag `3f9e9d36f572072600390dbdfff3dc611a1e24e6`).
  Available/expiry confirmed **2026-12-08T13:25:50Z**. Fresh pre-merge download
  independently verifies all 13 checksums/TAR/config/platform/source/tag. TAR SHA
  `67781222ccc0c7b16c3ba42f2989f612496d245eca0fdb0b741d14ad934577d3`;
  config `sha256:d55086d9c2259d4d48358caed54eaa63ce91aef41146a36557878fe2e9ac29a4`;
  CI Docker index `sha256:4560aa33c6df7da07b5235cccc43d50f3f3f660849542160821a4027b3c6fed6`.
  Retained outside Git in approved temp `rl06-premerge-preserved-14924980940/`
  alongside `VERIFICATION-RECEIPT.json`; owner should copy this complete artifact/
  receipt to trusted private retention before expiry (local copy is not offsite/
  immutable-storage acceptance). Do not retag stable or mix receipts/images.
- Merge-main artifact `14925933170`, source `d647cfc...`, is **different**, with
  TAR `67ca7cd2d42f5de8e452d3f94183a7b11daa1a7299833efa24165d2b98336f26` and
  config `sha256:5ba0dfa61054b0077c917bab9572fc4fad5521d28109ab66f2223f391dc1fc77`.
  Independently downloaded merge-main artifact/13 checksums/config/source/tag/
  platform and exact CI receipt verified; no byte-identity claim against branch.
  Final documentation-only main commit gets its **own** exact-head CI/artifact;
  final SHA/CI/independent validation recorded in PR integration comment/final
  handoff after commit. Never assume same-tree images/archive bytes identical.

German guide **`docs/synology-test-deployment.md`** is unchanged and packaged.
Actual DSM/Container Manager, test-share UID/GID/ACL, non-overlapping subnet/fixed
internal-IP reverse-proxy connectivity, trusted HTTPS/certificate, desktop/tablet/
mobile/installed-PWA, ordinary-only offline queue/cache, full round cancellation/
overlap/paid/closed/settled/uncertain/unattributed blocks and operator independent/
encrypted recovery/key/post-backup reconciliation remain **PENDING**. No manual
success inferred from CI. Existing FH-05/OQ-06/Windows/operational gaps retained.
Production Compose/updaters/timer/Dockerfile/runtime/migrations/UI/service-worker
zero diff from expected base. No NAS install/share/production data/network/DSM/
certificate/firewall/provider/refund/SMTP/release/publication/schedule operation.


## RL-06 verified test deliverable — 2026-11-24 (supersedes in-progress notes)

PR #11 https://github.com/tostman1/drink-pos/pull/11 **OPEN/UNMERGED**.
Exact baseline/main `25a78ba6606e74760969cce7c993d60d3a139f2e`; verified implementation
`8ca880b7ac48d1d26ad2570c20bd707a598f1297`. Branch CI
https://github.com/tostman1/drink-pos/actions/runs/45401715029 and PR CI
https://github.com/tostman1/drink-pos/actions/runs/45401726644 **success**. Publication
skipped. Both Linux matrices 318 discovered/317 passed/one Windows-only skip;
all nine RL06 methods executed. Local 3.12.13/3.13.15 318/312/six POSIX skips,
176.660s/178.719s; browser/security/traceability pass.

Download branch artifact `drink-pos-test-amd64-8ca880b7ac48d1d26ad2570c20bd707a598f1297`,
ID `14924186574`, https://github.com/tostman1/drink-pos/actions/runs/45401715029/artifacts/14924186574,
14-day retention. Downloaded independently: all 13 file checksums and archive/
config/source/platform/tag verification pass. Archive SHA-256
`73ae5ce76255dcb86c41ec6baa7690bfb4527499ba17ca32491a4a46a084941a`;
config ID `sha256:0429d3f9dd17d28dae8d2679f3cfa09211cbee06a6f1647f6ccc5c1742e8baf2`.
CI Docker index ID is separately
`sha256:d218b0549be9e712a9036469dd9aab053d9392a4f43f2fe058ab9aa90006c025`, not config.
No OCI registry digest/publication or reproducibility claim. Final documentation
commit will receive its own exact-head CI/artifact; final PR receipt identifies it.

Actual **delivered Compose** verifies isolated non-root internal network/fixed IP,
outbound blocking, explicit fresh v2/no reseed/persistence, baseline→candidate
same-schema full-table/ledger/receipt comparison, round cancellation/net/replay,
paid/event CSV/PDF recovery, unsupported older v1 startup without state mutation,
independent full recovery and original post-backup activity preservation. Existing
full encrypted image/source-loss EF-08c and financial/migration image gates pass.
The older initial failures were correctly blocked, retained and fixed without
weakening verifier. Production Compose/updaters/timer/runtime/UI unchanged.

Operator guide `docs/synology-test-deployment.md`: archive via browser/Windows
Get-FileHash, DSM file import/project/env differences/NAS CLI, test-owned UID/GID,
non-overlapping subnet/fixed IP to DSM HTTPS reverse proxy (no unreliable host
app-port mapping), one-time v2, controlled update/full recovery and manual rounds.
NAS/DSM GUI/ACL/HTTPS/trusted certificate/tablet/mobile/installed-PWA/offline/cache/
round blocks/offsite/key/operational reconciliation acceptance **PENDING**; no real
NAS/deployment/payment/mail/production DB/publication performed. Existing FH-05,
OQ-06, EF-08a Windows `WinError 5` and operational gaps remain open.


## RL-06 in progress — 2026-11-24

PR #11 OPEN/UNMERGED, implementation `67ec1a89b756713045f9545aef09bab0a1e5ff27`.
First actual deliverable CI found internal-only Docker host-port publication failure
(app healthy); artifact withheld. Follow-up preserves internal network/single-service,
uses fixed internal IP as DSM reverse-proxy target, no host app port. Fix pending CI.
Network-fixed follow-up passed reachability; next rehearsal issue was copying
EF-08b under wrong directory name. Preserve exact backup ID (verifier unchanged),
capture copy-name regression; actual final artifact gates still pending.
`28e0068` actual Compose full rehearsal now passes, export blocked on Docker
containerd `.Id` versus config hash mismatch. Follow-up separates actual CI image
ID/descriptor from archived config digest, binds Config/rootfs and reimport; pending.

Owner requested RL-06 after approved RL-05 integration. Verified clean HEAD/fetched
main `25a78ba6606e74760969cce7c993d60d3a139f2e`; created
`feature/rl-06-synology-test-deployment`. Ready gate `rl-06-contract.md` records
inspection/plan. Scoped isolated Compose, explicit synthetic v2 tool, non-publishing
AMD64 archive/export and actual Compose rehearsal under implementation; German
guide `synology-test-deployment.md`. Initial failing regressions captured before
implementation. Verification/PR/artifact receipts still pending, no NAS/production
execution or publication. Real devices/HTTPS/operator/offsite/key acceptance OPEN.
Local full 3.12.13/3.13.15 gates pass 318/312/six POSIX skips, 172.711s/182.238s,
browser/security included; exact-head actual Compose/artifact CI still required.


## RL-05 integrated handoff — 2026-11-24

PR #10 https://github.com/tostman1/drink-pos/pull/10 is **MERGED** after completed
second independent owner review, verified R5-01/02 resolution, no approved-scope
blockers and explicit conditional merge authorization. This supersedes historical
open/no-merge/review-pending notes below for PR #10 only. No RL-06/production authority.

- Clean local/fetched reviewed head **`0b5972404ab94bb59d49c299a75260260baa5713`**
  and exact main/base **`2cc36fd69ec56dbdfe65ffb7ed98600d7c33b7c4`** matched Git/GitHub.
  Specified exact branch https://github.com/tostman1/drink-pos/actions/runs/45382286868
  and PR https://github.com/tostman1/drink-pos/actions/runs/45382296704 success:
  both Linux matrices 309 discovered/308 passed/one Windows-only skip; all 30 RL05
  plus 16 R5 review methods execute ok; full actual container/migration/recovery/DR/
  image audits pass, publication skipped. No new reviews/inline comments/threads or
  conflicts; MERGEABLE/CLEAN. Main unprotected/active rules empty, no checks bypassed.
- Normal `--merge --match-head-commit` integration, no squash/rebase/force push:
  **`e9204e88ad2faf6cb8919f9ef9824bb0f6a5b005`**, 2026-11-24T11:55:25Z.
  First parent exact base, second exact reviewed head above; whole tree equals
  reviewed **`eaa73817cfc3b410dd93030b5483fbbcf2ca3ef5`**. Primary checkout switched
  and fast-forwarded to clean synchronized main. All original branches/merges retained,
  no delegation/history rewrite or runtime changes after independent review.
- Exact merge-main CI https://github.com/tostman1/drink-pos/actions/runs/45388627081
  **success**: Linux Python 3.12/3.13 each 309 discovered/308 passed/one Windows-only
  skip; all 46 RL05/review methods ok. Quality/security/Chromium/real age plus actual
  Docker/four Compose/start-restart-persistence/legacy upgrade/prepared exact v1→v2/
  strict fresh-adoption-repeat/served financial net+round-reversal reporting/coverage/
  independent EF08 application recovery/encrypted source+owned-image-loss DR/image
  dependency audit pass. Publication **skipped**, merge SHA deployments zero.
  Installed synthetic evidence binds merge SHA: 26 tables preserved/no history rewrite/
  reporting+coverage/recovery verified/network_attempts=0/two mocked card creations.
- Local merged-main full Standard Checks **exit 0** Python **3.12.13/3.13.15**:
  309 discovered/303 passed/six POSIX skips each, 170.921s/177.010s unittest. Ruff/
  84-file format/syntax/24-ID traceability/real age/audits none known/Chromium/diff/
  actionlint pass. Outside-Git logs `rl05-merged-main312.log`/`rl05-merged-main313.log`.
  Existing lifecycle/TestClient/Node-action warnings retained; local Docker unavailable.
- This is a **documentation-only main descendant receipt**. Final main SHA is the
  commit carrying this section (read HEAD/origin/main after synchronization). Verify
  its **own** exact-head CI/local checks and record final SHA/run/results in PR #10
  integration comment/final report. No self-referential SHA/predecessor-CI inference.

**RL-05 implemented and integrated**: normal consumption is net after explicit
source-linked approved erroneous-booking corrections, attributed to original period;
gross/reversed/net transparent, actual correction timestamp separate. Originals remain
immutable. Durable operation receipts/provenance, mandatory negative ID/purpose,
idempotent request decisions and serialized writes/rollback retained. `/api/pay`
correction-only zero debt returns HTTP 200 without fake payment; explicit resolution-
only can report remaining payment-required debt, failure does not hide committed change.
Unkeyed legacy cash/request creation is not a blanket retry guarantee.

Stable round units/payment/deduction/reservation/cancellation/reversal relations:
safe tracked unpaid/current/unsettled cancellation restores only exact original drink
debt once, never new physical consumption or refund. Paid/closed/subsequently settled/
active-unknown/ambiguous historical reversals fail closed. Pending requests reserve
original units, hold eligibility/block cashup. R5-01 signed VK now offsets exact
reversal (6→0 / mixed-member 16→0); R5-02 complete ordinary/round coverage plus new
member receipt exact parent FK, no false complete classification from partial detail.
Historical T-only/NULL-parent gaps stay unverified and never reconstructed.

Real additive v1→v2 support integrated: exact v2 `39dbd90c…`, original ledger/financial
rows/sequence preserved, no table rebuild/backfill/extra historical fingerprint. Strict
opt-in/pre-write/clean DELETE/fail-closed/no WAL recovery retained; default legacy.
FH-04 **new-operation gap addressed**, R5-01/02 **resolved by independent review**;
**FH-05 OPEN**, broad OQ-06 inference/history repair/refunds/closed-period/additional
adoption decisions remain open. No automatic unsupported-history reconciliation.

EF-08a Windows **WinError 5 remains unresolved**. MV-01 target tablet/mobile, MV-02
installed worker v109, MV-03 real SMTP, MV-04 real SumUp, MV-05 offline/reconnect
pending; operational MV-06 geography/hardware/immutability/encrypted scratch/storage/
Windows ACL/key-image acquisition/timed human external reconciliation/acceptance partial.
Merge synthetic DR RPO age 0.357783s/RTO 2.312204s is not an operational guarantee.
No production financial data/migration/repair, real payment/refund/SMTP, deployment,
image publication/release/updater/schedule change or RL-06/new package. Stop after
successful exact final-main integration verification.

## Active RL-05 R5-01/02 review continuation — 2026-11-24

Owner authorizes bounded review fixes on existing PR #10, not merge/new package.
Incoming clean reviewed/local/remote `f4d56ffcb4992dfbef813f05ab5feafc19a88f52`, main
`2cc36fd69ec56dbdfe65ffb7ed98600d7c33b7c4`. Preserve original RL05 work/branches.
R5-01 opposite round-reversal VK; R5-02 complete ordinary/round read-time provenance
classification. Narrow necessary new member receipt parent T field only, no old
receipt rewrite/DDL/v2/ledger change. 16 served tests pass after initial failing
regressions; actual full local/exact-final-head container+DR/PR gates still required.
Paid/physical net/source-period/idempotency/round safety untouched. Old incomplete
or NULL-parent approvals stay unverified; no reconstruction. FH-05/broader OQ-06/
WinError 5/MV01..05/operational MV06 remain unresolved. Leave PR open; second review
after complete delivery, no merge/deploy/publish/production/payment/refund/mail/schedules.

R5-01/02 implementation **`c26879f9c1a7b674d25acda5abf6a72f1a3a03bc`** passed exact
branch https://github.com/tostman1/drink-pos/actions/runs/45381146469 and PR
https://github.com/tostman1/drink-pos/actions/runs/45381154883; both Linux matrices
309 discovered/308 passed/one Windows-only skip, all 16 new regressions ok; actual
image financial reporting/coverage/v1→v2/recovery/DR/image-audit and all original
gates pass, publication skipped. Scope only reporting validation/new receipt parent
INSERT and synthetic tests/docs; original schema/ledger/financial snapshots untouched.
This final documentation-only evidence descendant must pass its own final-head
CI/local gate; read actual SHA and record final branch/PR links/results on PR #10
delivery receipt. No self-referential SHA/predecessor inference; stop after delivery.

## RL-05 review submission receipt — 2026-11-24

PR https://github.com/tostman1/drink-pos/pull/10 **OPEN/unmerged**, exact base remains
`2cc36fd69ec56dbdfe65ffb7ed98600d7c33b7c4`. Core/UI/tests/docs `a013878`/`e50ba38`/
`62464be`/`33c0d82`, final reservation fix **`23420966af12044b16dd3320a03ef16e4f9ff6f8`**.
Exact branch https://github.com/tostman1/drink-pos/actions/runs/45367327293 and PR
https://github.com/tostman1/drink-pos/actions/runs/45367337289 success; Linux both
matrices **293 discovered/292 passed/one Windows-only skip**, all 30 new tests execute
ok. Actual Docker/4 Compose/restart/legacy upgrade/prepared v1→v2/fresh-adoption-repeat/
net consumption+round cancellation financial scenario/EF08 recovery/encrypted source+
owned-image-loss DR/image audit pass, publication skipped. 26 tables preserved,
history_rewritten=false/recovery_verified=true/network_attempts=0/two mocked card calls.
Synthetic only, not authentic historical or production evidence. PR image binds merge-
test SHA `63b9a72f83ebb61f71dad6145ae3b24340c8612d`, branch image exact head.

FH-04 new operations addressed through source-linked signed correction/provenance,
durable keyed retries, exact original-period net reporting and round-unit/deduction/
reservation/cancellation/reversal relations. Paid/closed/unknown/legacy attribution
fail closed; no reconstructed missing old details/refunds/stock return/new physical
consumption. FH-05/broader OQ-06/EF-08a WinError 5/manual/operational acceptance remain.
Real v2 additive nine-table schema, no original rebuild/backfill/additional old schema
fingerprint; default legacy retained. First-party IDs/preview/worker v109 compatibility
changes documented. No production/deploy/publication/real provider/mail/schedule/merge.

This documentation-only descendant receipt must pass its **own** final-head CI and
full local gates; resolve final SHA/links/results after push and record on PR/report,
not a self-referential SHA or predecessor inference. Retain current reservation/full
gate logs including initial local Ruff-cache stale-format warning/failure (formatter
rerun changed no Git bytes); Linux exact-head quality passed without suppression.
Stop after complete review delivery; independent owner review next, no next package.

Corrected-head local full gate: Python 3.12.13/3.13.15 **exit 0**, 293 discovered/287
passed/six POSIX skips, 149.388s/162.474s; all quality/browser/security/traceability/
real age pass. Final receipt descendant needs own exact-head local/CI verification.

## RL-05 active handoff — 2026-11-24

Owner authorizes net-consumption/source-linked correction/idempotency/transaction
integrity plus mandatory coordinated round cancellation, **not merge/production**.
Base `2cc36fd69ec56dbdfe65ffb7ed98600d7c33b7c4`, feature/rl-05-transaction-integrity.
Plan `docs/rl-05-contract.md`; round safe/blocked/legacy lifecycle in
`docs/round-cancellation-contract.md`. Existing work preserved/no delegation.
Implementation uncommitted, tests/gates in progress; do not treat initial failures
or targeted passes as full delivery. v2 real additive schema/zero historical inference;
net correction does not refund/return stock, round restoration not new consumption.
Paid/closed/uncertain/unattributed round reversals blocked. FH-04 closure pending,
FH-05 and broader OQ-06/EF-08a WinError 5/manual devices/operational recovery open.
Final complete local/exact-head container CI/open PR required; no new work/merge/
deploy/publication/production state/SumUp/SMTP/updater schedules authorization.

Current frozen candidate: 29 targeted RL-05 tests pass; full both-version Standard
Checks running, earlier formatting/stale in-flight model checks failed and retained.
No commits/push/PR yet. Full synthetic source-loss fixture includes corrected
consumption/cancelled round/exact reversal; actual-image CI still required. Use
current migration/schema (not prior interim hashes) and preserve all evidence gaps.

Full local candidate gate now passes Python 3.12.13/3.13.15, 292 discovered/286
passed/six POSIX skips each; quality/traceability/real age/audits none known/Chromium
keyed correction replay/diff pass. 29 new RL05 tests; previous failed logs retained.
Commit/open PR and exact-final-head CI/recovery receipts pending; do not infer actual
container proof locally. No merge permission or broader OQ/FH05/manual closure.

## RL-04 integrated handoff — 2026-11-24

PR #9 https://github.com/tostman1/drink-pos/pull/9 is **MERGED** after completed
independent owner review, no approved-scope blockers and explicit conditional merge
authorization. This supersedes historical open/no-merge/pending notes below for
PR #9 only; no new work package or production operations authorized.

- Clean local/fetched reviewed head **`94104001c50e11f87341489e607b655c5f19b6da`**
  and exact base **`8dd961bfb23d7fe090a8cf2895a269bb544db09e`** matched Git/GitHub.
  Branch https://github.com/tostman1/drink-pos/actions/runs/45343434976 and PR
  https://github.com/tostman1/drink-pos/actions/runs/45343450131 both success;
  full Python/financial/browser/security/Docker/migration/recovery/DR/image audits,
  publication skipped. No new reviews/inline comments/review threads/conflicts;
  MERGEABLE/CLEAN, no configured required checks/active branch rules, none bypassed.
- Normal `--merge --match-head-commit` integration:
  **`b6dc46e6414812089c434ef315177aa7af50826d`**, 2026-11-24T07:18:16Z.
  First parent exact base, second exact reviewed head above. Whole merged tree
  equals reviewed **`25ef9ae03f7314a8bf7eaf57751ad834733a2504`**. Primary checkout
  switched/fast-forwarded to clean synchronized main; all prior branches retained.
  No force push/rebase/history rewrite/delegation or app changes after review.
- Exact merge-main CI https://github.com/tostman1/drink-pos/actions/runs/45346957268
  **success**: both Linux Python matrices **263 discovered/262 passed/one Windows-only
  skip**, all 21 new integrity/correction tests execute ok in each. Actual Docker/
  four Compose/start-restart-persistence/legacy upgrade/strict fresh-adoption-repeat/
  served financial scenario/independent EF-08a-b recovery/encrypted source+owned-image
  loss DR/image-audit gates pass. Publication **skipped**; deployment query zero.
  Synthetic 17 original tables preserved/history_rewritten=false/recovery_verified=true/
  network_attempts=0/two mocked card creations. Not authentic historical adoption.
- Local merged-main full Standard Checks **exit 0** Python 3.12.13/3.13.15:
  **263 discovered/257 passed/six POSIX-only skips** each, 114.789s/119.386s unittest.
  Ruff/format/syntax/24-ID traceability/real age/audits none known/Chromium/diff/
  actionlint pass. Logs outside Git `rl04-merged-main312.log`/`rl04-merged-main313.log`.
  Lifecycle/TestClient/Node-action warnings retained; local Docker unavailable.
- This is a **documentation-only main descendant receipt**. Final main SHA is the
  commit carrying this section: read HEAD/origin/main after synchronization. Verify
  its **own** exact-head CI and record final SHA/run/result in the PR #9 integration
  comment/final report; no self-referential SHA or predecessor-CI pass inference.

**FH-01/02/03/06 scoped implementation integrated**: served admin two historical
UPDATEs removed; legacy four cost/profit inference/round resets and helper/facade
removed; missing defaults initialize, existing zero master retained; paid stats/
preview/export-report honor present stored profit including zero. Regression evidence
in FinancialHistoryTests/FinancialIntegrityTests plus full-state installed scenario;
current master/new bookings and legitimate debt/tally/payment fields remain operational.
No automatic historical repair/reconstruction/inferred-cost storage or recovered
before-images, no extra fingerprint/adoption/v2/default strict activation.

**FH-04 OPEN, characterization only**: T-only negative debt corrections, no new
signed TI semantics; `/api/pay` can commit all-debt-removing approvals then return
HTTP 400 with no PAID record; negative admin adjustments are **not idempotent**.
Exact lifecycle/proposal in `docs/correction-audit-contract.md`. **FH-05 OPEN**: no
authentic historical compatibility evidence. **OQ-06 resolved only for approved
routine historical preservation**; historical correction/inference/round accounting/
report-period semantics/adoption breadth remain open. No new policy from green CI.

EF-08a Windows **WinError 5 remains unresolved** despite these successful checks.
MV-01 tablet/mobile, MV-02 installed PWA, MV-03 real SMTP, MV-04 real SumUp, MV-05
offline/reconnect pending; MV-06 automated synthetic evidence only, actual geography/
hardware/immutability/encrypted storage/scratch/Windows ACL/key-image retrieval/timed
human external reconciliation/operator acceptance remain partial. Synthetic DR RPO
age 0.330150s/RTO 2.392196s are not operational guarantees. No deployment/image
publication/release/production data or migration/real payment/mail/updater/schedule
change, and no new work package. Stop after exact final-main receipt verification.

## RL-04 active handoff — 2026-11-24

Current owner mission authorizes scoped implementation/commits/push/open PR/exact
head CI only, superseding historical no-RL04/proposed-only notes below. **No merge,
deployment/publication/real data/SumUp/SMTP/schedules or history reconstruction.**
Base local/fetched main exactly `8dd961bfb23d7fe090a8cf2895a269bb544db09e`; branch
`feature/rl-04-financial-integrity`. Ready gate `docs/rl-04-contract.md`, write/report
inventory in financial-history-policy, FH-04 lifecycle in correction-audit-contract.
Served admin/startup historical UPDATEs eliminated; existing zero default master
retained, fresh/current/new operation behavior preserved; paid reports honor stored
zero profit. Schema/fingerprint/v1/strict opt-in unchanged. No agents delegated.

21 new targeted tests pass; full local/final committed-head/container/DR/PR gates
pending until explicit receipts. Synthetic scenario both modes/separate recovery/
mocked paid+unknown with zero network attempts; not authentic historical adoption.
FH-04/05 remain open, OQ-06 only scoped routine preservation/report-zero authorized;
no correction/refund/inferred-cost/legacy support decision. WinError 5 unresolved,
manual device/real provider/operational recovery acceptance not implied by checks.
All earlier branches/owner merges preserved. Stop after reviewed delivery, PR open.

Local full gate receipt: Python 3.12.13/3.13.15 exit 0, **263/257 passed/six POSIX
skips** each, 157.942s/165.859s; Ruff/format/syntax/traceability/real age/audits none
known/Chromium/diff/actionlint pass. Implementation commits `ac1eefa`/`97d8cbe`/
`a6f60d2`; documentation descendant and exact-head branch/PR/actual-container/DR
receipts still required. No local Docker claim/WinError 5 fix/manual acceptance.

## RL-03 integrated handoff — 2026-11-24

PR #8 https://github.com/tostman1/drink-pos/pull/8 is **MERGED** after completed
independent owner implementation/evidence review, no approved-scope blockers and
explicit conditional merge authorization. This supersedes historical open/no-merge
notes below for PR #8 only; **no accounting policy or next work package approved**.

- Clean local/fetched exact reviewed head
  **`0b43f379f0b48dcd82e555287a3a301fe3838969`**, verified main/base
  **`33c16979d2ae17a5d53c118c7f173f324e02e75b`**. Specified branch
  https://github.com/tostman1/drink-pos/actions/runs/45270641734 and PR
  https://github.com/tostman1/drink-pos/actions/runs/45270653100 passed both Python
  matrices/ten RL-03 tests/browser/security/actual Docker/four Compose/migration/
  recovery/DR/image-audit gates; publication skipped. GitHub reviews/threads/inline
  findings empty, MERGEABLE/CLEAN, no conflicts. No configured required checks;
  none bypassed, no admin merge/force push/rebase/history rewrite or delegation.
- Normal `--merge --match-head-commit` integration:
  **`9d09015b2d83d652d88b283ef9f5ab45050128bf`**, 2026-11-24T05:55:46Z.
  First parent exact base, second exact reviewed head. Whole merged tree equals
  reviewed **`221909081ee78cff6173476805d69bf2eba786e8`**. Primary checkout safely
  switched/fast-forwarded to main clean/synchronized; all feature/handoff branches
  retained. Complete app/.github/Dockerfile/production Compose/examples trees unchanged
  vs base; financial/reporting/schema/migration/payment/invoice/recovery/UI untouched.
- Exact merge-main CI https://github.com/tostman1/drink-pos/actions/runs/45336723411
  **success**: Linux both matrices **242 discovered/241 passed/one Windows-only skip**;
  all ten new tests execute ok. Full browser/security/actual Docker/start-restart/
  legacy upgrade/strict fresh-adoption-repeat/independent recovery/encrypted source+
  owned-image-loss DR/image-audit gates pass, publication **skipped**, deployment
  query empty. Synthetic history_rewritten=false/recovery_verified=true/network_attempts=0;
  not authentic historical or production adoption evidence.
- Local merged-main full Standard Checks **exit 0** Python 3.12.13/3.13.15: **242
  discovered/236 passed/six POSIX skips each**, 122.929s/126.518s unittest. Ruff/format/
  syntax/24-ID traceability/real age/audits (none known)/Chromium/diff/actionlint pass.
  Outside-Git logs `rl03-integrated312.log`/`rl03-integrated313.log`/`rl03-merge-main-ci.log`.
  Lifecycle/TestClient/Node-action warnings retained; no local Docker installed.
- This is a **documentation-only main descendant receipt**. Final main SHA is the
  commit carrying this section (read HEAD/origin/main after synchronization). Verify
  its **own** exact-head CI independently and record resolved final SHA/run/result on
  PR #8 integration-delivery comment and final report; never infer predecessor pass
  or embed an impossible self-referential SHA. No app/test/tool code changed after review.

**RL-03 evidence package integrated; stop. OQ-06 remains OPEN/unresolved.** The
historical-snapshot preservation recommendation remains **PROPOSED/NOT APPROVED**;
merge grants no rewrite prevention, accounting/reporting policy, inferred-cost storage,
append-only correction mechanism, historical repair, schema allowlist/migration path
or rollout approval. FH-01..FH-06 remain OPEN with preserved severity: FH-01/02/06
High historical rewrites, FH-03/04 Medium reporting/audit detail gaps, FH-05 High
conditional adoption-provenance readiness risk (strict gate remains fail-closed).
Eight source-derived fresh schemas/113 fixed-baseline source commits and synthetic
ALTER counterexample do **not** establish historical installation/DB/release-image
authenticity or broader compatibility. No authentic historical artifact verified.

EF-08a Windows backup rename **WinError 5 remains unresolved**, reproduced during
RL-03 submission; successful reruns/current Linux/local gates are not a fix. MV-01
tablet/mobile, MV-02 installed-PWA upgrade, MV-03 real SMTP, MV-04 real SumUp, MV-05
offline/reconnect devices pending. MV-06 automated synthetic evidence exists; actual
geography/hardware/immutable/encrypted storage/scratch/Windows ACL/key-image retrieval/
timed human provider/mail reconciliation and acceptance remain partial. No new manual
acceptance or operational guarantee from CI. No RL-04/new package begun, production
data/migration/history repair, release/image publication/deploy/updater/config/schedule
change, real SumUp/SMTP or member-data access. Preserve history and stop after final CI.

## RL-03 authorized review-submission handoff — 2026-11-23

**Review receipt:** PR https://github.com/tostman1/drink-pos/pull/8 **OPEN/unmerged**.
Evidence `3eb4d70`, decision/doc head `3f323b074478e5e5c9c94856f7b2efecbdd3570b` at
unchanged base `33c16979…`; exact branch `45269458940` / PR `45269481996` success:
both Linux 242 discovered/241 passed/one Windows-only skip, all ten new tests ok;
quality/browser/security/actual Docker/four Compose/legacy upgrade/strict migration/
independent recovery/full encrypted source-image-loss DR/audit passed, publication
skipped. Actual image evidence synthetic only, no widened support. Direct completed
query confirmed PR success despite watcher jobs API HTTP 500. Local committed 3.12
full gate passes; 3.13 first committed run reproduced **existing EF-08a WinError 5**
in stale-retention-lock backup rename; unchanged full rerun passed (242/236/six POSIX
skips, all stages), **not a recovery fix** or suppressed error. See progress for exact
successful/failed receipts and outside-Git logs.

Final documentation-only descendant receipt needs **its own** final SHA/local/
branch+PR CI verification, recorded on PR/report after push; never infer pass from
`3f323b0`. Keep all 16 scoped files, no app/deployment changes. OQ-06 OPEN, policy NOT
APPROVED, FH-01..06 open, owner independent review next. Stop after delivery; do not
merge or begin proposed RL-04. No real data/migration/payment/mail/production activity.

Owner continuation authorizes reviewed commits/push/open PR and exact-final-head CI
on existing `feature/rl-03-financial-history-policy`, **not merge**. Supersedes initial
no-commit/push/PR notes below only for this decision package. Original 16 files/work
preserved, complete diff/new files reviewed, incoming HEAD/fetched/remote main at baseline
`33c16979d2ae17a5d53c118c7f173f324e02e75b`. No delegation/history rewrite.

Read open **FH-01..FH-06** severities/source/test/follow-up register in `docs/AUDIT.md`;
policy write matrix/A/B/C/examples now also has exact pre-correction owner decisions
and proposed next `RL-04 — Historical Snapshot Write Preservation`. Recommendation
**NOT APPROVED**, OQ-06 **OPEN**. No implementation, runtime/report/deployment/default
mode change, added fingerprint, correction or v1→v2 transition. No real financial DB
or installations; mandatory tests use existing migration routines only synthetically.

Final local Standard Checks/reviewed commits/PR/exact-head CI receipts follow in
progress and PR final delivery. Do not infer completion from old local/base receipts.

Continuation pre-commit Standard Checks passed both Python 3.12.13/3.13.15, 242
discovered/236 passed/six POSIX skips each; ten new methods/financial/migration/
recovery/real-age/lint/format/syntax/traceability/audits/Chromium/diff passed. Final
committed-tree local checks and head-specific branch/PR/container CI still required;
receipt updates are documentation-only. No implementation or policy approved.
Leave PR open for independent owner review; stop after final delivery. No merge,
release/image publication/deployment/updater/real SumUp/SMTP authority. All prior
branches/owner merges/MV-01..05/partial MV-06/EF-08a Windows WinError 5 preserved.

## RL-03 local decision-package handoff — 2026-11-23

Current owner request authorizes financial-history/adoption evidence for OQ-06 only,
superseding historical no-next-package instructions for RL-03. **No new financial
policy, v1→v2 migration or production upgrade.** Supplied message ends at section 5
heading; safe-adoption proposal provided, no omitted authority inferred.

- Verified clean incoming local/fetched/remote main
  `33c16979d2ae17a5d53c118c7f173f324e02e75b`; exact base CI `45260937868` success,
  publication skipped. Separate `feature/rl-03-financial-history-policy`, HEAD still
  baseline with uncommitted evidence/tests/docs. All prior branches/owner merges
  preserved, no delegation/rewrite. Refetched origin/main unchanged.
- Read `docs/rl-03-contract.md`, `docs/financial-history-policy.md` (field write matrix,
  A/B/C/report examples/owner questions/adoption stop gates),
  `docs/legacy-adoption-inventory.md` and `docs/financial-schema-inventory.json`.
  `scripts/financial_schema_inventory.py` derives literal schema-only metadata in
  memory from fixed full Git ancestry; no old code execution or DB input.
- Critical scope: RL-02 startup metadata preservation **does not protect later
  admin item API writes**; zero costs/profit still rewritten. Nonzero round history
  reset, RE/EL/NULL-ID divergence, read-time zero-profit fallback and incomplete
  signed member/admin correction detail documented. Do not fix them without approval.
- Eight fresh schema shapes/113 source commits and one synthetic ALTER-fee counterexample
  authenticated as source content only, **not databases/releases/installations**.
  No authentic historical DB/image established; tags/releases empty, eight build-record
  metadata entries not downloaded/verified. No additional fingerprint support.
- Recommend **A exact preservation + B separately authorized labelled inference**;
  C deferred/prefer append-only if needed. Recommendation **not approval**; OQ-06 stays
  open. Never equate legitimate zero with missing cost or current EK with past fact.
- Ten targeted characterization tests pass; full Python 3.12/3.13 Standard Checks
  rerunning after initial 120-second tool timeout (not pass), results in progress.
  No actual local container or new branch/PR CI evidence; base CI is separate.

**Final local receipt:** both full Standard Checks exit 0 on Python 3.12.13/3.13.15:
242 discovered/236 passed/six POSIX skips each; Ruff/format/syntax/traceability/real age/
strict audits (none known)/Chromium/diff all passed. Source receipt/actual inventory CLI
reproduced and decision-doc links/actionlint pass. Logs outside Git `rl03-verified312.log`
and `rl03-verified313.log`; lifecycle/TestClient/LF→CRLF warnings retained. No new CI/
container/production evidence inferred; EF-08a WinError 5 remains unresolved. Subsequent
receipt edits documentation only; final traceability/diff checks recorded in progress.

No commit/push/open-PR/merge authority inferred. Do not stage/commit/push/merge until
explicit authorization. No app/schema/runtime/report/UI/recovery/deployment edits,
new financial policy/adoption/v1→v2 implementation, real resources/mail/payments or
production scripts accessed/run. No service-worker bump needed. MV-01..05/partial
MV-06/EF-08a Windows WinError 5 remain open. Next: owner chooses policy/report basis/
source scope, then separately authorizes bounded implementation; no production adoption.

## RL-02 integrated handoff — 2026-11-23

PR #7 https://github.com/tostman1/drink-pos/pull/7 is **MERGED** after completed
independent owner review, no approved-scope blockers, and explicit conditional
merge authorization. This supersedes historical open/no-merge notes below only
for PR #7 integration; **no production adoption or next work package** is authorized.

- Clean local/fetched reviewed head `9b3385991641b9ef330d6f5830884a6f723b5afd`,
  exact base/main `65d7a869854a15cfa5ef78c98153bc35306f629b`. Specified branch
  https://github.com/tostman1/drink-pos/actions/runs/45257800656 and PR
  https://github.com/tostman1/drink-pos/actions/runs/45257811471 passed all Python/
  Node/browser/security/Docker/migration/recovery/DR/image-audit gates. Publication
  skipped. No reviews/threads/inline findings/conflicts; MERGEABLE/CLEAN. No
  configured required checks; none bypassed. Owner review authorization is explicit.
- Normal `--merge --match-head-commit` integration, no admin bypass/history rewrite:
  **`b3f2a5c5c9bb761705bb10810e4f4a53554d899f`**, 2026-11-23T20:31:30Z.
  First parent exact base above, second exact reviewed head. Whole merged tree
  equals reviewed tree `7a5d0a89450f528ffc41e35b5166f781b745a358`. Primary checkout
  switched/fast-forwarded to main clean/synchronized; all feature/handoff branches
  preserved. No app code changed after review. Protected handlers/UI/PWA/financial/
  invoice/recovery/production Compose/Dockerfile/updater/timer code unchanged vs base.
- Exact merge main CI https://github.com/tostman1/drink-pos/actions/runs/45260262831
  **passed** both full Python 3.12/3.13 matrices, browser/security/24-ID traceability,
  actual Docker/four Compose/start-restart-persistence/legacy upgrade/strict fresh-
  adoption-repeat/independent EF-08b recovery/encrypted source+owned-image-loss DR/
  image-audit gates. Linux 232 discovered/231 passed/one Windows-only skip each;
  new real POSIX read-only permission test executed ok. Publication **skipped**;
  merge-head deployment query `[]`.
- Strict actual-image synthetic adoption preserves all 17 original tables (16
  application + sequence), history_rewritten=false, repeat_startup_verified=true,
  recovery_verified=true, network_attempts=0; image evidence binds exact merge SHA.
  DR public-only producer/owned image unavailable before retained archive load/
  shared image untouched/source storage removed/post-snapshot commit not replayed.
  Synthetic RPO age 0.250959s/RTO 1.919433805s, not operational guarantees.
- Local merged-main full Standard Checks exit 0 on Python 3.12.13/3.13.15:
  232 discovered/226 passed/six POSIX-only skips each; all lint/format/syntax/
  traceability/real age/audits (none known)/Chromium/diff passed, actionlint passed.
  Existing warnings/Windows EF-08a issue retained; container proof is actual main CI.
- This is a **documentation-only main descendant receipt**. Final main SHA is the
  commit carrying this section: read `git rev-parse HEAD` / `origin/main` after
  synchronization. Verify its own exact-head CI separately and record resolved
  final SHA/run/result in PR #7 integration-delivery comment and final report;
  no self-referential hash or predecessor-CI pass inference. No runtime changes.

**RL-02 integrated; stop after final-main receipt verification.** Default legacy
startup remains default/unmodified in behavior, including its characterized early
DDL/WAL/files and repeated historical purchase-cost/profit backfill risk. Versioned
migration contract is **opt-in only**, NOT enabled on production. Strict exact-current
metadata-only adoption/repeat preserves historical/master financial values, zeros,
round costs, payment/audit/debt/sequence records; no financial policy approved.
Fresh initialization is the other bounded path. Strict mode requires exact schema
fingerprint and clean DELETE-journal state; WAL/sidecars/unknown/custom/partial/future
state reject before SQL. No arbitrary historical-release support, v1→v2 transition,
mandatory rollout or image-only DB rollback. Files/lock/recovery remain separate.

OQ-06 financial zero/round/prototype-history interpretation and adoption breadth
remain **unresolved**. Actual historical artifacts/support policy, operator/production
adoption, storage/key/image/provenance and external business reconciliation remain
open. EF-08a Windows directory-rename `WinError 5` remains unresolved; successful
reruns/Linux are not a fix. MV-01 tablet/mobile, MV-02 installed PWA upgrade, MV-03
real SMTP, MV-04 real SumUp, MV-05 offline/reconnect devices remain pending. MV-06
automated synthetic evidence exists; real geography/hardware/immutable storage/
encrypted scratch/Windows ACL/key-image retrieval/timed human reconciliation and
acceptance remain partial. Never equate green CI with operational acceptance.

No production mode/config/digest/schedule change, deployment/publication/release/
dispatch, production DB access/real migration, SumUp or SMTP operation occurred.
Disposable synthetic verification only. No new package begun; preserve history
and stop. Merge permission grants no deployment/adoption/future-package authority.

## RL-02 active handoff — 2026-11-23

Owner now authorizes bounded RL-02, superseding earlier no-next-package notes for
this task only. Verified fetched/local main `65d7a869854a15cfa5ef78c98153bc35306f629b`,
exact base CI `45246034817` success; `feature/rl-02-migration-safety`.
DP-024 opt-in exact-schema ledger/pre-write gate; default legacy untouched.
Metadata-only current adoption/fresh transactional initialization → v1, no existing
financial/default normalization in strict mode, DELETE journal chosen explicitly.
Ready gate `docs/rl-02-contract.md`, contract/runbook `docs/migration-safety.md`.
Nine initial failing tests before code; targeted/initial synthetic rehearsal passed,
full local/final exact-head CI/PR/container/DR receipts pending. No authentic old
release support, mandatory rollout or v1→v2 transition. OQ-06 financial zero/round/
prototype inference and adoption breadth unresolved despite green tests.
Preserve all owner merges/handoff branches. No agents delegated. Only commit/push/
open PR authorized; **no merge/release/publication/deployment/production data/real
SumUp/SMTP/updater activation**. MV-01..06/EF-08a Windows WinError 5 unchanged.
After review-ready delivery stop; recommend separately approved policy/adoption path,
not automatic production upgrade. Final SHA/CI/PR must be read at delivery.

Full local Python 3.12.13/3.13.15 Standard Checks exit 0: 232 discovered,
226 passed/six POSIX skips each; audits none known, Chromium/Ruff/traceability/diff
passed; actionlint passed. Earlier Python 3.13 EF-08a Windows WinError 5 reproduced,
still unresolved, no backup-code fixes/retries. Actual container/Linux/final-head CI
and open PR evidence required next. Plan/core/rehearsal commits `4258ab5`/`3fdef64`/
`f61a40c`; no generated state committed. Production/merge authority unchanged.

**RL-02 implementation review receipt:** PR https://github.com/tostman1/drink-pos/pull/7
OPEN/unmerged. Exact implementation `4c68ab3b5e84b1f3133b235bed929f67692e816f`
passed branch `45254857601` / PR `45254875390`: both Linux matrices 232 discovered,
231 passed/one Windows-only skip, real new POSIX permission test ok. All actual
Docker/4 Compose/start-restart-persistence/legacy upgrade/opt-in fresh-adoption-repeat/
independent EF-08b recovery/encrypted source+owned-image-loss DR/image audit passed;
publication skipped. Migration original 17 tables preserved/history_rewritten=false/
network_attempts=0/recovery_verified=true. Synthetic only, no historical release claim.
This receipt is documentation-only; final HEAD/its own CI must be verified separately
and recorded on PR/report (read Git/GitHub, not predecessor inference). Main refetched
unchanged at baseline; no production/real services/merge. Owner independent review
next; stop after final delivery. Default legacy historical-backfill risk remains;
strict optional DELETE-journal/exact schema/no-existing-normalization contract only.
OQ-06 and MV-01..06/Windows EF-08a WinError 5 unresolved. No v1→v2 or mandatory adoption.

## RL-01 integrated handoff — 2026-11-23

PR #6 https://github.com/tostman1/drink-pos/pull/6 is **MERGED** after the owner's
completed independent implementation/security review and explicit conditional
merge approval. This supersedes historical open/no-merge notes below, not production
restrictions. No RL-02 or other package was begun.

- Clean local/fetched reviewed head `03853fde50ac1dbf31e83b2b522704acd115ec62`,
  exact base/main `dbc314e0790534ee44f362be4a194143385eb071`. Specified branch
  https://github.com/tostman1/drink-pos/actions/runs/45211470701 and PR
  https://github.com/tostman1/drink-pos/actions/runs/45211487658 passed both Python/
  Node matrices, browser/security, actual Docker/4 Compose validations, upgrade/
  recovery/DR/image audit. Publication skipped. No reviews/threads/inline findings,
  GitHub MERGEABLE/CLEAN; no configured required checks, none bypassed.
- Normal `--merge --match-head-commit` integration, no admin bypass/history rewrite:
  **`09a27a8866392cc7cdcf2b1006d31cfaccee571c`**, 2026-11-23T17:40:50Z.
  First parent is exact base above, second exact reviewed head above. Entire merged
  tree matches reviewed tree `93363456e0515bc761aceaad166907c14cd1a5d2`.
  Primary checkout safely switched/fast-forwarded to main, clean/synchronized;
  all feature/handoff branches preserved. Existing handlers/UI/REST/payment/invoice,
  production Compose/updaters/timer, migration implementation and recovery interfaces
  have zero diff against base; RL-01 adds offline tools, tests/guidance/CI only.
- Exact merge main CI https://github.com/tostman1/drink-pos/actions/runs/45230274124
  **passed** all gates, including actual containerized synthetic upgrade/separate
  recovery and encrypted full source/image-loss disaster recovery. Linux 208
  discovered/207 passed/one Windows-only skip each matrix, POSIX guards executed.
  Upgrade verifies 17 tables, permitted cost changes, recovery_verified=true,
  network_attempts=0. DR restores retained owned image after proven unavailability,
  public-only producer, shared image preserved, network-disabled gated recovery.
  Synthetic RPO age 0.352007s/RTO 2.300773869s; not operational guarantees.
  Publication **skipped**; deployment query for merge returned `[]`.
- Local merged-main full Standard Checks exit 0 on Python 3.12.13/3.13.15:
  208 discovered/203 passed/five existing POSIX-only skips each, 99.795s/101.868s.
  Ruff/format/syntax/23-ID traceability/real age/audits (none known)/Chromium/diff
  passed; actionlint passed. Existing lifecycle/TestClient/action warnings retained.
- This is a **documentation-only main descendant receipt**. Final main SHA is the
  commit carrying this section (read `git rev-parse HEAD` / `origin/main` after
  synchronization); its own exact-head CI MUST be checked separately at delivery.
  The resolved final main SHA/CI is recorded in the PR #6 integration-delivery
  record and final report, avoiding an impossible self-referential commit hash.
  Do not infer the receipt's pass from merge CI or edit code to obtain it.

**RL-01 integrated; stop after final-main verification.** Deterministic offline
release identity and read-only isolated EF-08b-bundle preflight remain opt-in.
Preflight success approves **only a separately authorized disposable rehearsal**,
never deployment; unknown never succeeds. Isolation/configuration/secrets/key/
compatibility receipts are operator trust, not signed authenticity/live-state proof.
No reliable existing migration ledger, arbitrary historical-release compatibility,
reproducibility or automatic DB rollback is claimed. Switching image alone does
not revert database/files/configuration or reconcile post-snapshot business activity.

Startup can persist early DDL/WAL/message-file changes after late DML rollback,
and repeatedly backfill financial purchase-cost/profit history from current costs;
RL-01 preserves this implementation and exposes its risk. Existing unattended
updaters remain **unsafe/unmodified**: mutable stable/always/newer selection,
force-recreation/pruning without verified backup/compatibility/health/rollback gates.
Operator-managed deployments/schedules were not inspected, changed or activated.

RL-02 version ledger/transactionality/pre-write gate/supported transitions and
legitimate zero-cost history treatment require separate decisions/authorization;
release naming/support, authentic historical fixtures, exact tested-image promotion/
digest provenance/protection and operator adoption also remain open. MV-01 devices,
MV-02 installed PWA upgrade, MV-03 real SMTP, MV-04 real SumUp and MV-05 offline/
reconnect devices remain pending. MV-06 synthetic automated evidence exists, but
actual geography/hardware/immutable storage/encrypted scratch/Windows ACLs/secure
key-image retrieval/timed human external payment-mail reconciliation acceptance
remains partially pending. EF-08a intermittent Windows directory rename `WinError 5`
remains unresolved; successful reruns/Linux gates are not a fix.

No production deployment, release/image publication/dispatch, deployed digest/config/
schedule change, production DB access or migration, real payment or mail occurred.
Only disposable synthetic migrations/startup ran in verification. Merge approval
authorizes no deployment/adoption/new package. Preserve history and stop.

## RL-01 active release-safety handoff — 2026-11-23

Owner selected RL-01, superseding previous 'stop/no next package' notes only for
this bounded implementation. Base/fetched main `dbc314e0790534ee44f362be4a194143385eb071`,
exact base CI `45199604894` passed, branch `feature/rl-01-release-safety`.
Ready gate `docs/rl-01-contract.md`, contract/runbook `docs/release-safety.md`.
DP-023 isolated-bundle-only read-only preflight/identity, actual synthetic startup/
ASGI/full-state/recovery characterization; no app/migration/UI/REST/payment/deployment
defaults changed. Current partial DDL/repeated cost-history mutations documented,
arbitrary upgrade/downgrade compatibility unproven. Full local/final CI/PR evidence
pending until receipts; Docker unavailable locally. No production data/resources,
publication/release/deploy/SumUp/SMTP/merge. Keep PR open, independent review next;
propose RL-02 versioned migration contract/pre-write gate, not authorized here.
Preserve all owner merges/handoff branches and EF-08a/b/c guarantees. MV-01..06,
real operational evidence/Windows EF-08a WinError 5 remain unresolved. Stop at delivery.

**RL-01 review delivery:** PR https://github.com/tostman1/drink-pos/pull/6 OPEN.
Implementation `fdbdb5627c4fae61c41bd7e0a99c3e1a85655052` passed exact branch
`45209356414` and PR `45209479532`: both full Linux matrices 208/207 passed/one
Windows-only skip; actual image/4 Compose validations/installed identity/network-none
synthetic upgrade/separate recovery and EF-08a/b/c DR/image audit passed, publication
skipped. Local Python 3.12/3.13 full gates 208/203 passed/five POSIX skips each.
No runtime/migration/recovery/default deployment/UI/business changes. Evidence receipt
is documentation-only; verify its own final HEAD/CI before delivery. Read progress
for actual synthetic tree/schema distinctions; no authentic historical or production
upgrade proof. Owner review next, no merge permission; stop after delivery.

## EF-08c integrated handoff — 2026-11-23

PR #5 https://github.com/tostman1/drink-pos/pull/5 is **merged** after the owner's
independent security/implementation review and explicit conditional merge approval.
This supersedes historical open/unmerged notes below, not production restrictions.

- Clean local/fetched reviewed head:
  `982dbf101c15e78ff7cb2eb3a6fafe557925b84a`; verified main/base:
  `e8caeed029266764d5594c275ff769ccc7cf35c8`. Both specified exact-head runs
  https://github.com/tostman1/drink-pos/actions/runs/45195265860 and
  https://github.com/tostman1/drink-pos/actions/runs/45195281503 passed quality,
  security, actual container/disaster recovery and image audit; publication skipped.
  PR MERGEABLE/CLEAN, no review threads or inline findings. No configured required
  checks; none bypassed. No unexpected handler/payment/EF-08a-b/production-file diff.
- Normal `--merge --match-head-commit` workflow, no admin bypass/history rewrite:
  **`34cc06a1f287348af32caa173796afc512485342`**, 2026-11-23T14:50:50Z.
  Both parents are that verified base/reviewed head, whole merged tree identical to
  reviewed tree. Primary checkout safely fast-forwarded to main; feature/handoff
  branches preserved, no reset/rebase/force push.
- Exact merge main CI https://github.com/tostman1/drink-pos/actions/runs/45198599811
  **passed**: both Python/Node full Standard Checks, all three Compose validations,
  actual local-only Docker build/start/restart/persistence/EF-08a-b recovery,
  complete encrypted source-loss/owned-image archive reconstruction/gated offline
  startup and image vulnerability audit. Linux 187 discovered/186 passed/one
  Windows-only retry-test skip each; real POSIX guards executed. Publication
  **skipped**; deployment query for merge SHA returned `[]`.
- Security correction complete: ordinary backup producer uses only public age
  recipient, no private identity. V2 marker means encrypted transfer only; separate
  private-key full verification plus explicit trusted independent/offsite receipts
  control monitoring. Combined verification opt-in; v1 old markers/ambiguous receipts
  cannot imply current recoverability. Receipt protection/labels are operator trust,
  not signatures or automatically proven geography.
- Main disaster flags confirm producer private key not required, original UUID-owned
  image unavailable before loading retained archive, shared input not removed.
  Synthetic RPO age 0.285082s/RTO 2.018970907s/total 6.311423030s; not operational SLA.
- Both local Python 3.12.13/3.13.15 Standard Checks exit 0 on merge main:
  187 discovered/182 passed/five POSIX skips, Ruff/format/syntax/22-ID traceability,
  real age regressions, dependency audit (none known), Chromium/diff all passed.
  Actionlint passed. Existing lifecycle/TestClient/action warnings retained.
- This handoff receipt is documentation-only, a main descendant. Final main SHA
  and its own CI result must be verified/read from Git/GitHub at delivery, not
  inferred from merge CI. No runtime/production configuration changes after review.

**EF-08c implemented, security-corrected and integrated. Stop; no new work package.**
No production deployment/release/image publication, deployed digest change, live
payment/SMTP or production access occurred. MV-06 operational acceptance remains
partially pending: actual geographic/hardware separation, enforced immutable storage,
encrypted scratch/storage/transport and Windows ACLs, independent secure key/image
retrieval and timed human external payment/mail reconciliation. Synthetic metrics
are not operational promises. EF-08a Windows directory rename `WinError 5` remains
unresolved; successful reruns/Linux gates are not a fix. MV-01..05 unchanged. Merge
approval authorizes no deployment/adoption/future PR. Preserve history and stop.

## Active PR #5 security correction — 2026-11-23

Continue EF-08c existing branch from reviewed `fe012099998d41ac3dd3d15e90cc754c8715e0c0`,
main `e8caeed` unchanged. PR #5 remains OPEN; no merge/deploy/publication permission.
Producer-private-key concern reproduced by failing test before code. New envelope
v2 marks encrypted transfer only; ordinary producer uses public age recipient.
Separate full decryption verification and explicit trusted independent/offsite
attestation required by monitoring. Explicit combined controlled workflow retained;
v1 readable but old markers/ambiguous receipts never imply fresh full verification.
Owned-image archive drill now removes only UUID-labelled derived image, asserts
unavailable then exact ID reconstructed, preserving shared input. Full gates/final
CI pending until recorded. EF-08a/b formats/handlers/financial/production configs
unchanged; remaining MV-06/Windows/authenticity/ACL/operator limits preserved.

Security implementation `6af9cae` passed branch `45192886047` / PR `45192900590`:
Linux 187/186 passed/one Windows-only skip, public-key-only/state/v1 tests and actual
owned-image unavailability→archive reconstruction passed; shared input untouched,
network-disabled full DR/image audit passed, publication skipped. Synthetic RPO
0.358806s/RTO 2.318645502s (not SLA). Direct wrong/missing verifier-key guard added
in final test review; verify final head/checks, not only predecessor. Stop after
delivery, PR remains OPEN for owner approval; no merge or production adoption.

## Active EF-08c independent disaster recovery — 2026-11-23

Branch `feature/ef-08c-disaster-recovery` from clean fetched/CI-verified main
`e8caeed029266764d5594c275ff769ccc7cf35c8`. Owner authorizes implementation,
tests/docs/commit/push/open PR **not merge/release/deploy/publication**. Ready gate
`docs/ef-08c-contract.md`, runbook `docs/disaster-recovery.md`. Preserve EF-08a/b
formats/interfaces and all served financial/mail behavior. Optional external age
filesystem envelope + independent decryption verification and journal/status,
actual-image source-volume-loss reconstruction/reconciliation-gated offline startup.
Full local/CI final evidence pending until receipts; don't infer Docker locally
(not installed). Windows EF-08a rename WinError 5 unresolved, follow-up only.
MV-06 synthetic encrypted independent loss/rebuild/timing can advance with direct
evidence; actual geographic/immutable/storage/ACL/escrow/timed operator/provider/mail
acceptance remains pending. No production data/accounts, real SMTP/SumUp or images.
Preserve all owner merges/handoff branches; deliver open PR for review.

EF-08c PR https://github.com/tostman1/drink-pos/pull/5 OPEN/unmerged. First
`25766e6` branch/PR CI `45179952940` / `45180047138` passed both quality matrices,
actual image/Compose/installation-loss/independent encrypted reconstruction/audit;
publication skipped. Linux 181 tests/180 passed/one Windows-only skip. First PR
synthetic RPO age 0.113042s/RTO 1.875316774s, total 5.198156745s (not operational
guarantees). Final post-snapshot-loss/no-replay evidence correction follows; final
HEAD/checks remain authoritative. No real resources or production adoption.

Reviewed implementation `beb4e494bc565029113b33f2b1929b8714b8a384` passed branch
`45181307115` / PR `45181321303`: Linux 182/181 passed/one Windows-only skip,
actual image/Compose/start-restart/encrypted source-storage loss/fresh recovery/
network-disabled gated startup/audit passed; publication skipped. Explicit one
post-snapshot commit remained lost/no replay, unknown card session held. PR synthetic
RPO 0.368372s/RTO 2.250698623s/total 6.576092409s (not production guarantee).
MV-06 automated encrypted independent loss/rebuild/timing proven; actual geographic/
immutable/storage/ACL/secure key-image retrieval/timed operator reconciliation remains
pending. Documentation-only receipt follows: verify final HEAD/checks on OPEN PR #5.

## EF-08b integrated handoff — 2026-11-23

PR #4 https://github.com/tostman1/drink-pos/pull/4 is **merged** after the owner
completed independent review and authorized exact-head-guarded integration only.
This supersedes historical open/unmerged instructions below, not production limits.

- Clean local/fetched PR head matched reviewed
  `0fbd743320db4b61bd279220a09062b04dad1cb1`; main remained
  `b8cb4870d90f75b9dbc2668246788c5aa24ee8a5`. Exact-head branch/PR CI
  `45164310541` / `45164321226` passed. No conflicts, review threads or inline
  findings; GitHub MERGEABLE/CLEAN. No configured required checks; none bypassed.
- Normal merge workflow, `--merge --match-head-commit`, no admin bypass/history
  rewrite: **`6f5e280b090c9bb915dfabe88db9329dea31da80`**,
  2026-11-23T11:53:25Z. Parents are verified base/reviewed head; merged tree is
  byte-identical to review. Feature/handoff branches preserved.
- Primary checkout switched to main and fast-forwarded safely. Exact merge main
  CI https://github.com/tostman1/drink-pos/actions/runs/45169203989 **passed**:
  both Python/Node full gates, all three Compose configs, actual local-only image
  build/startup/restart/persistence/offline application recovery and image audit.
  Linux 165 discovered/164 passed/one Windows-only retry-test skip; POSIX guards
  and complete two-installation rehearsal executed. Publication **skipped**;
  deployments query for merge SHA returned `[]`.
- Both local Python 3.12.13/3.13.15 Standard Checks passed on merged main:
  165 discovered/161 passed/four POSIX skips each, Ruff/syntax/traceability,
  dependency audit (none known), Chromium and diff passed. Existing lifecycle/
  TestClient/action deprecation warnings retained; no gates weakened.
- This integration receipt is documentation-only. Read final main HEAD and its
  own CI from Git/GitHub before delivery; no runtime/image/config changes after
  reviewed merge. No release/publication dispatch, deployment, production access,
  live payments/mail or deployed image-digest change occurred.

**EF-08b complete and integrated; stop. No next work package started.**
Recovery remains operator-quiesced/offline, not an online coordinated snapshot.
MV-06 remains partially pending: independent encrypted/immutable/offsite copy,
storage/Windows ACL validation, measured RPO/RTO and operator/external payment/mail
reconciliation acceptance. MV-01..05 remain pending. Checksums are not authenticity;
independent secrets/code/image preservation and storage guarantees remain operator
boundaries. Merge approval does not authorize adoption/deployment or future PRs.

## Active EF-08b portable recovery — 2026-11-23

Branch `feature/ef-08b-portable-recovery` from clean verified/fetched main
`b8cb4870d90f75b9dbc2668246788c5aa24ee8a5`; exact base CI `45152440365` passed.
Owner authorizes implementation/commits/push/open PR, **not merge/publication/deploy**.
Inventory/ready gate: `docs/ef-08b-contract.md`; runbook: `docs/application-recovery.md`.
New application-bundle namespace preserves EF-08a database contract. Explicit
all-writer offline maintenance, observed changes fail closed; no online consistency
claim or invoice/payment redesign. Exact state/artifacts plus narrow event-path
relocation, no automatic app startup/migration/payment retry/mail resend. Linux/
Windows atomic no-replace publication; other platforms fail closed. Windows ACLs
remain operator boundary. Local targeted 22 tests (21 passed/one POSIX skip); full
local/actual image/final CI evidence still pending until recorded below.
MV-01..05 unchanged; MV-06 independent offsite/storage/ACL/RPO/RTO/operator acceptance
remains partially pending. No production data/services/deployment configs touched.
Preserve all historical handoff branches/owner merges; no rewrite. Final PR/head
and checks must be read from Git/GitHub before delivery; leave PR open for owner.

Review delivery: PR https://github.com/tostman1/drink-pos/pull/4 **open/unmerged**.
Core/image/docs commits `b120b65` / `06cb62c` / `46cf466`. Exact `46cf466` branch
CI `45160412546` and PR CI `45160481935` passed full Linux gates/container/build/
all three Compose configs/offline recovery/image audit, publication skipped.
Linux 162 tests: 161 passed/one Windows-only skip, all POSIX guards executed.
Final review transport/opposite-host-path/permission/interruption regressions add
two tests; local final Python 3.12/3.13 gates **164 discovered, 160 passed/four
POSIX skips**, exact exit 0 each. Final pushed-head checks remain authoritative.
No production/publication/merge. Stop after delivery and wait for owner review.
Recommended next: separately approved isolated encrypted/offsite/timed operator
recovery acceptance drill for remaining MV-06, not automatic adoption/deployment.

Final reviewed code/test head `59fdf9d896fd00595c9232f86f021b5e52966430` passed
branch `45161242647` and PR `45161253638`: Linux 164 discovered/163 passed/one
Windows-only skip, all POSIX guards and actual image/Compose/offline recovery/
image audit passed, publication skipped. PR #4 OPEN/CLEAN at verified base
`b8cb487`. Documentation-only receipt follows; read final HEAD and its checks,
not merely predecessor CI. Worktree clean before receipt, no generated state.

Final isolation correction: failing DP-021 test reproduced restore-inside-bundle
mutation; early descendant-target rejection preserves the source. Full local
Python 3.12/3.13 gates exit 0 with 165 discovered/161 passed/four POSIX skips.
Read final corrected head/CI on PR #4; still no merge/adoption authorization.

## EF-08 integrated handoff — 2026-11-23

PR #3 https://github.com/tostman1/drink-pos/pull/3 is **merged**. The owner approved
merging only after final review/gates; this supersedes the historical open/unmerged
notes below, not the production restrictions.

- Remote head remained the reviewed `e7a6073a0faae9659bcb9963995e96f74653d117`;
  base main was `a218fcc40599d5a19e53f2afee490238eeb7e910`. Exact-head PR CI
  `45150671583` and branch CI `45150663385` passed, publication skipped.
- Normal GitHub merge-commit workflow with exact head guard, no admin bypass:
  **`212e6b6c20257dae532ecdbaf5d654beae7f44ab`**, 2026-11-23T09:59:42Z.
  Merge parents are that base/reviewed head; merged tree is byte-identical to review.
- Primary checkout fast-forwarded to origin/main; post-merge main CI
  https://github.com/tostman1/drink-pos/actions/runs/45152008134 **passed** on the
  exact merge SHA, including Python matrices, actual Docker/Compose/container
  recovery/restart and image dependency audit. Publication **skipped**, deployment
  query for merge SHA returned `[]`. No release or publication dispatch occurred.
- Post-merge local Standard Checks passed: 139 discovered, 136 passed/three POSIX
  skips (Windows); Linux permission evidence remains successful as recorded below.
- This integration receipt changes documentation only. Read final main HEAD and
  its own CI receipt from Git/GitHub; no application change after reviewed merge.

**EF-08 bounded database recovery is complete and integrated; stop this session.**
Next intended work package (not started): coordinated DB/filesystem artifacts/
configuration/offsite recovery, including an isolated operational rehearsal.
MV-06 remains partially pending; MV-01..05, external CSV consumers, Windows ACLs,
offsite/RPO/RTO/monitoring and reconciliation boundaries remain documented.
No production access, deployment, image/digest change, release/publication or
consumer migration was performed. PR #3 approval grants no approval for future PRs
or production operations. Preserve feature/handoff branches; no history rewrite.

## PR #3 security/compatibility correction — 2026-11-23

Continuation on the existing `feature/ef-08-database-recovery` branch, not a new
work package. Incoming clean HEAD `6612924e72dfa96b1dcc6bfa80dde8f68fe33510` had
passed exact-head PR CI `45141076838`; main refetched and remains `a218fcc`.
POSIX restore pre-creates private 0600 SQLite files, creates all missing directory
components 0700 without chmod of existing directories, and enforces 0600 before
atomic no-clobber publication. Windows ACLs remain an explicit operator boundary.
No root CSV consuming script found; operational YAML/README updated and external
NAS consumers explicitly unknown. `docs/recovery.md` gives a pre-adoption migration
and optional separate private CSV adapter; neither was run against production.
Final gates/HEAD will be evidenced on PR #3; do not infer completion from the prior
CI receipt. Still no merge, publication, deployment or production access authorized.

Correction `1aa5385` is verified: push run `45149972529` and PR run `45149983134`
passed on its exact SHA, both Linux matrices **139 passed/no skips**, including
all four new permissions regressions; actual image/container recovery/audit passed,
publication skipped. Local Windows gates: 136 passed/three POSIX skips each.
CSV migration example validated synthetically on both local Python versions;
external NAS consumers and Windows destination ACLs remain operator-verification
boundaries. This evidence receipt changes documentation only; read final PR #3
HEAD/checks for its own final gate. **Stop after delivery, wait for owner review**;
no merge, deployment/image publication, consumer migration or new work package.

## Active EF-08a delivery — 2026-11-23

Branch `feature/ef-08-database-recovery` from clean verified/fetched main
`a218fcc40599d5a19e53f2afee490238eeb7e910`; exact base quality/container CI passed,
publication skipped. Owner authorized commit/push/PR **only**, no merge/deployment.
Full SQLite/CSV/checksum bundles and verified new-target-only restore implemented;
see `docs/recovery.md` for baseline weaknesses, usage, retention and limitations.
All recovery state is disposable/synthetic. Separate event CSV/PDF/message files
need independent coordinated/offsite protection; DB backup alone is not full
application recovery. MV-06 has direct all-table/artifact synthetic evidence but
remains partially pending for isolated production-like operational/offsite rehearsal.
MV-01..05 remain pending; invoice/SMTP side-effect redesign is excluded.
No production pinned image/digest/configuration was touched. Final commit/check/PR
evidence follows in progress and final delivery; do not infer CI before its result.

Review PR: https://github.com/tostman1/drink-pos/pull/3 — **open, not merged**.
Implementation commits `fbe61b4` (core/regressions), `89cf426` (image recovery smoke),
`0e36214` (runbook/traceability). Both full local Python gates passed 134 tests;
22 recovery tests include abrupt-process staging and separate CSV/PDF/message
recovery. Final pushed HEAD and CI are authoritative in PR #3 checks, not inferred
from these predecessor commits. Owner review is the next gate; do not merge,
dispatch publication or modify the pinned production deployment.

## Verified takeover — 2026-11-22

- Repository: https://github.com/tostman1/drink-pos
- Incoming branch: `feature/engineering-foundation`, clean and tracking origin.
- Exact incoming HEAD: `250a4e6d3e4180b469d4f2a91623b60f2fd1ed72`.
- Verified local/remote `main`: `fb0812837694949dc6d228b781f2aa7af2b29d98`.
- At takeover, draft PR #1: https://github.com/tostman1/drink-pos/pull/1 — **open, unmerged**;
  its existing `build` check succeeded. No PR comments were present at inspection.
- Independent foundation branch: `feature/engineering-foundation-baseline`,
  created directly from that verified main, not from PR #1.

## Full handoff diff reviewed

Eight files, 319 additions/47 deletions against `fb08128`:

| Files | Preserved intent on PR #1 |
| --- | --- |
| `app/index.html` | Responsive bounded-height event layout, tally quantities across price snapshots, +1/-1 controls, busy guard, event-ID requests, inline accessible feedback |
| `app/admin.html` | Removal audit labels, dedicated test-recipient field, dirty-edit protection, save-before-send; no cashier-recipient fallback |
| `app/models/requests.py` | Optional expected event ID, remove request, independent mail-test recipient |
| `app/legacy_main.py` | Atomic event writes and audit with `BEGIN IMMEDIATE`, per-operation signed amounts, remove endpoint, recipient validation/error mapping |
| `app/services/events.py` | Stale-event rejection, latest positive snapshot correction, nonnegative counts, saved/validated independent test recipient |
| `app/db/schema.py` | Additive default for `mail_test_recipient` |
| `app/service-worker.js` | Shell cache v106 → v108 |
| `tests/test_backend.py` | Nine regressions: signed auditing, zero floor, snapshot corrections, stale/closed event rejection, concurrent correction, rollback, recipient persistence/validation/selection |

These feature changes were subsequently merged by the owner, not this agent.
GitHub confirms `tostman1`, 2026-11-22T21:15:45Z, merge
`052c2bbc54f05f7c7d850feb8ad597a4e4868670`; owner confirmed continuation.
At inspection remote main matched this SHA, and run `45071103604` passed. The
handoff branch still points to `250a4e6`. The foundation preserved these changes
through branch integration `2ccb377` before final checks/PR delivery. Do not undo the
owner merge or rewrite the original handoff branch.

## Evidence retained

- Original PR report: all 96 tests passed after supplying declared QR dependency.
- Takeover rerun: all **96** handoff tests passed in detached disposable worktree,
  Python 3.12.13 with declared dependencies; baseline main passed **87** tests.
- Existing FastAPI startup `on_event` deprecation warnings remain. They are not
  fixed by a speculative lifecycle rewrite.

## Unfinished checks — never infer completion

See `docs/standard-checks.md` for detailed procedures and catalog IDs.

- **MV-01:** event tally layout/add/remove on target tablet/mobile browsers.
- **MV-02:** service-worker upgrade to v108 on an already installed PWA.
- **MV-03:** SMTP delivery using a separately authorized test account/recipient;
  automated tests use mocks, not live email.
- **MV-04:** real SumUp terminal cancellation/recovery with authorized test setup.
- **MV-05:** normal offline queue/reconnect and online-only exclusions on devices.
- **MV-06:** production-like backup/recovery rehearsal on synthetic data only.

## Final integration and next safe actions

PR #2 https://github.com/tostman1/drink-pos/pull/2 is **merged**, not draft/open.
Merge: **`246e0967a889822eaaddb438ba523b87b29ffe31`**, 2026-11-23T08:15:59Z.
The owner authorized this merge conditional on final checks; PR was marked ready
then merged normally with exact checked-head guard and no protection bypass.

- Final PR HEAD: `64018bd23babe2a9cd995099178517c9ea4020f4`, including the preserved
  `c47b73c` evidence and unrelated-reference cleanup. Merged tree matches exactly.
- Both local Python 3.12/3.13 full Standard Checks passed, 115 tests each.
- Final PR/branch runs `45136828301` / `45136820988` passed on exact final head.
- Post-merge main CI **`45137226115` passed** on merge SHA, including actual image,
  Compose, startup/restart/persistence/SQLite/health and dependency audit.
- Publication skipped in every final run; deployments for merge SHA are empty.
  No release, deployment, image publication, production data or real accounts used.
- Primary tree fast-forwarded to origin/main; final integration receipt is a
  documentation-only main descendant. Read final main HEAD/status with Git and
  ensure a clean synchronized checkout before the next session.

EF-01..03 are complete. Existing legacy/global/lifecycle/auth/file-mail risks and
manual checks above remain visible, not inferred fixed by merge or green CI.
Real accounts, publication, release, deployment, infrastructure changes and
production data remain forbidden without separate authorization.

The next intended session is the **database backup/restore/data-integrity portion
of EF-08**, not a compatibility rewrite or invoice-mail redesign. Do not implement
it during finalization. Start from verified main, review current backup/restore
code and synthetic fixtures, define acceptance/rollback and retain MV-06 until
direct rehearsal evidence exists. Existing MV-01..05 also remain pending.

## Cross-agent takeover procedure

1. Read `AGENTS.md`, this file, `docs/PROGRESS.md`, `REQUIREMENTS.md`,
   `ARCHITECTURE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `docs/AUDIT.md`.
2. Inspect status/local HEAD/remotes/PR state before edits; compare with recorded
   SHAs. Fetch without discarding local changes; classify remote advancement.
3. Preserve user work, partial verification and the nine transferred regressions.
4. Resume the active work package, not a fresh blanket audit. Record commands,
   evidence gaps and new decisions. Never equate green CI with manual completion.
5. Before delivery, reconcile latest verified main, run applicable gates, review
   diff, use Conventional Commits with `git commit -F`, and update handoff evidence.
