# Handoff and protected work

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
Remote main matches this SHA, and run `45071103604` passed. The handoff branch
still points to `250a4e6`. The foundation will preserve these changes through an
explicit branch integration before final checks/PR delivery. Do not undo the
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

## Next safe actions

Finish EF-02/EF-03, commit reviewable increments, integrate verified `052c2bb`
into this branch, run expanded Standard Checks/combined regressions, push and open
the separate foundation PR. Verify actual PR CI, record evidence and leave the
foundation PR unmerged. Owner approval is required before PR merge, real accounts,
deployment, or publication.

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
