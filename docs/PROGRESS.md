# Engineering foundation progress

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
