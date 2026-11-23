# Standard Checks

## Local setup and single command

Python 3.12 (container baseline) or 3.13, Node 24 LTS. No npm install/build.
Dev tools are separate from runtime dependencies. From repository root:

```powershell
uv venv --python 3.12 .venv
uv pip install --link-mode copy --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe scripts/standard_checks.py
```

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python scripts/standard_checks.py
```

Put Node on PATH or pass `--node /absolute/path/to/node`. Missing tools/failing
stages return nonzero, never silent skips. Checks isolate inherited Drink-POS/
SumUp/SMTP configuration, using disposable DB/messages/artifact paths. Never use
production state or `.env`. `python -m unittest discover -s tests` remains useful
but is not the full gate and is less isolated from a caller's environment.

## Required stages

1. **Ruff:** `ruff check .` and `ruff format --check .`, conservative `E4,E7,E9,F`, no legacy
   ignores or auto-fixes. Correctness baseline, not full style/type/security lint.
   Formatter debt is corrected in mechanical, AST-equivalent isolated commits;
   rule expansion needs a separate reviewed increment.
2. **Python syntax:** `python -m compileall -q app tests`; also compile scripts
   without imports. Compileall creates ignored `.pyc`, never database state.
3. **JavaScript syntax:** Node parses all `.js`, executable inline HTML scripts
   and handlers, module mode where appropriate; JSON script blocks parse as data.
   Not DOM/UI/browser/accessibility verification.
4. **JSON/manifests and traceability:** valid data, stable IDs, source paths, exact
   local test methods and manual IDs. All nine original PR #1 tests now resolve
   locally after owner main integration. Optional `--handoff-root` supports future
   explicitly pending external evidence; never substitute it for executing tests.
   Manifest installability fields/icons must resolve locally; service-worker
   cache version and shell URLs must correspond to actual served GET routes.
5. **Regressions:** `python -m unittest discover -s tests -v` including original tests and assembled
   ASGI HTTP/startup/auth/serialization contracts, external services mocked.
   Existing startup deprecation warnings remain visible technical debt.
6. **Dependency/security:** `python -m pip_audit --strict --progress-spinner off`
   audits isolated installed runtime/dev dependencies including transitives.
   Advisory lookup needs network; failure/unavailable service is not a pass. No
   ignored advisories or application secrets; this is not a pentest. CI also
   audits exact installed runtime dependencies inside its built image.
7. **Browser smoke:** `python scripts/browser_smoke.py` runs headless Chromium
   against a disposable loopback app: member booking, admin login, event add/remove,
   kassa/self-pay render and uncaught page errors. Off-origin browser traffic is
   blocked. This does not close manual iPad/worker/offline/SMTP/SumUp checks.
   Service workers are blocked in this focused browser test to prevent caching
   from masking current source or bypassing off-origin routing; installed-worker
   behavior is explicitly MV-02. Missing browser installation fails.
8. **Diff hygiene:** `git diff --check` plus human review of tracked/untracked
   files; no generated state/secrets committed.

## Container verification — separate required CI gate

Docker/Podman is optional locally but container evidence is required for review
readiness. Do not `compose up` production templates: they pull stable/mount data.
CI validates both files with `docker compose -f <file> config --quiet` using
empty synthetic secrets without starting services. It builds the actual Dockerfile
to local tag `drink-pos:verification`, never logs in/pushes on branch/PR runs.

`python scripts/container_smoke.py --image drink-pos:verification` creates its own
named volume/container and synthetic PIN/member/booking, checks health/pages/
manifests/OpenAPI/production redaction/build metadata, restarts to check persistence,
and checks SQLite integrity/FKs/WAL. `finally` removes only its own resources.
EF-08 also runs the actual image's backup/restore CLIs inside that disposable
volume, verifies the new target and compares its SQL dump with the source.
No host DB or inherited credentials are mounted/passed. Optional local reproduction:
build this tag with BUILD_* args, then run the helper. Missing runtime = **not run**.

Verification permissions are read-only. Release publication is a separate explicit
`workflow_dispatch` boolean on main, dependent on passing checks and a
`production-images` environment. Owner must configure required reviewers there;
environment naming alone does not enforce approval. No automatic deploy exists.

## Manual register — all pending at takeover

Record commit/device/browser/tester/date/procedure/result, with redacted evidence,
on an approved isolated instance. Green CI never closes these checks automatically.

### MV-01 — target event tally controls

PR #1 tablet/mobile landscape/portrait: long names, large tallies, scroll/safe
areas, +1/-1/zero/busy rapid taps, network failure, multiple price snapshots and
return to ordinary list after close. Reconcile totals/quantities/audit.

### MV-02 — installed PWA upgrade

Install/cache main v106 then update isolated server to PR #1 v108. Confirm worker
activation/old cache cleanup/new controls, offline shell and preservation of
booking queue/payment recovery ID. Clean desktop load is not installed iPad proof.

### MV-03 — authorized SMTP delivery

Separate authorized account/inbox only. PR #1 independent recipient save/reload,
dirty edit protection, blank/invalid rejection, TLS/login, actual receipt and
invoice attachment/selected sender copy. Mocks are not delivery evidence.

### MV-04 — authorized SumUp test terminal

Separate approval/setup required: availability, fee/rounding, replay/double tap,
interruption/reload, cancel/late success, timeout/unknown reconciliation. Compare
provider and local once-only payment. No real charges in routine checks.

### MV-05 — ordinary offline/reconnect

Previously online PWA: queue ordinary member drinks; reload/reconnect/replay once.
Verify rounds/corrections/event controls/payments/admin writes never queue;
multi-device recovery and no forced reload in active dialogs.

### MV-06 — synthetic recovery rehearsal

Populate disposable debt/rounds/payment sessions/events; snapshot/export/restore
into a **new** disposable target. Verify integrity, audit/operational tables and
separately retained CSV/PDF artifacts. Existing CSV tests are not all operational
recovery proof, and no production restore is approved.

EF-08 synthetic evidence: `DatabaseRecoveryTests.test_full_database_and_separate_artifacts_recovery_rehearsal`
populates all 16 operational tables, snapshots/restores all tables and sequence
state, compares exact schema/data, verifies integrity/FKs/idempotency constraints,
and separately retains/restores generated event CSV/PDF plus message JSON by
checksum. Startup on the disposable recovered target re-enables WAL and keeps
debt/payment IDs. `SnapshotRecoveryTests` covers WAL/uncommitted writes, corruption,
incomplete migration rollback via prior snapshot, abrupt process exit, cleanup,
target races and retention. This is direct synthetic evidence, not a production
NAS/offsite rehearsal. MV-06 remains **partially pending** for coordinated
production-like filesystem/offsite restoration in an isolated environment and
operator acceptance of recovery procedures/RPO/RTO. See `docs/recovery.md`.

PR #3 permissions regressions check pre-created restore files on both platforms;
Linux CI additionally runs real POSIX 0600/0700 assertions under permissive umask,
preserves existing-directory/unrelated-file modes and checks chmod-before-link and
permission-failure publication. These three tests explicitly skip on Windows;
that is a local POSIX evidence gap, not a Windows ACL pass. Linux matrix results
must show them executing (no skips) before delivery.
