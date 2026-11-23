# Handoff and protected work

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
