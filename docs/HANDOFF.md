# Handoff and protected work

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
