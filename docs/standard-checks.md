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

RL-06 adds `test_synology_test.py` boundaries and actual
`scripts/synology_test_rehearsal.py` against `compose.synology.test.yaml` in CI.
The tested local AMD64 image is saved only after all verification gates with
`scripts/export_test_image.py`; archive/config-ID/source/CI are distinct identities.
NAS/DSM/HTTPS/devices/offsite/keys remain manual in `synology-test-deployment.md`.

RL-05 adds served net-consumption/keyed correction/pay/round reversal and actual
concurrency/fault/v1→v2 interruption tests in test_transaction_integrity. Full all-table
recovery fixtures populate nine new tables through served operations; disaster fixture
includes cancelled/reversed round and corrected consumption before source loss.
Worker shell v109 review required; device/installed-PWA upgrade MV-01/02 still pending.

R5-01/02 add `tests/test_review_reporting.py`: served round VK/cost/profit/RE
preview/CSV reconciliation, paid stored-zero preservation, mixed-member snapshots,
replay/no-write and complete-versus-partial/legacy ordinary/round provenance. Installed
financial rehearsal asserts reporting and coverage before introducing mock provider
uncertainty; no UNKNOWN guard bypass. Existing v2/migration/browser/EF08 gates retained.
No UI/worker change in this review correction, no extra cache bump/device pass inferred.

RL-04 adds `tests/test_financial_integrity.py` (served snapshot/report/correction
faults and full scenario) and converts RL-03/RL-01 old-defect expectations into
preservation regressions; former failures/receipts stay documented. Actual-image CI
runs `scripts/financial_rehearsal.py --target <new-owned-root> --commit <actual-SHA>
--synthetic-only` with network none, current-code synthetic fixtures, both startup
modes, audit/provider/client/sequence preservation and independent recovery.
No historical-cost reconstruction/real providers/manual acceptance. UI/worker unchanged,
cache-version review needs no bump; EF-08a WinError 5 remains separately unresolved.

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
EF-08b additionally generates event CSV/PDF, stops only the owned synthetic app,
runs network-disabled image application-recovery tools, compares normalized full
DB/artifact/messages state and status, then restarts only original synthetic state.
The optional generic recovery Compose example is validated without starting it.
EF-08c installs checksum-pinned external age outside the application image, executes
real encrypted-replica tests in both quality matrices and runs
`scripts/disaster_rehearsal.py` against the local-only image: delete UUID-owned source
container/volume, decrypt independent copy, reconstruct fresh storage, explicitly
reconcile synthetic holds, then network-disabled startup and complete-state checks.
The resulting JSON records synthetic RPO/RTO/phase durations; no operational SLA.
No host DB or inherited credentials are mounted/passed. Optional local reproduction:
build this tag with BUILD_* args, then run the helper. Missing runtime = **not run**.

Verification permissions are read-only. Release publication is a separate explicit
`workflow_dispatch` boolean on main, dependent on passing checks and a
`production-images` environment. Owner must configure required reviewers there;
environment naming alone does not enforce approval. No automatic deploy exists.

## Deterministic CI waiting — EF-03

`scripts/wait_for_ci.py` is the only CI-waiting mechanism: Python 3.12/3.13 standard
library + authenticated GitHub CLI `gh` on PATH; PowerShell, Windows Git Bash or
Linux/macOS; no Bash, jq, pip package, LLM or OpenCode dependency; github.com
OWNER/REPO only. Read-only: explicit `gh api --method GET --include` requests, never
mutations. The top-level branch/PR workflow is `container.yml` (quality `ci.yml` is
reusable, not separately triggered). The policy it serves is in
[PROCESS](PROCESS.md#delivery-and-ci-waiting): one deterministic invocation per CI
phase, no LLM polling.

### Usage

Capture HEAD once after the authorized commit/push, then invoke the helper ONCE per
distinct required run/PR (never as a sequence of polling invocations):

```powershell
$sha = git rev-parse HEAD
python scripts/wait_for_ci.py --repo tostman1/drink-pos --run-id RUN_ID --sha $sha --result-file OUTSIDE_GIT_PATH
python scripts/wait_for_ci.py --repo tostman1/drink-pos --pr PR_NUMBER --sha $sha --result-file OUTSIDE_GIT_PATH
python scripts/wait_for_ci.py --repo tostman1/drink-pos --branch BRANCH_NAME --sha FULL_SHA --result-file OUTSIDE_GIT_PATH
```

(POSIX: same arguments with `$sha=$(git rev-parse HEAD)` and POSIX quoting.)
`--run-id` may be combined with `--branch` or `--pr` for explicit binding; otherwise
explicit run mode expects a push event. Branch discovery also finds exact
main/post-merge push runs. PR mode verifies the PR HEAD before waiting, discovers
only `pull_request` runs bound to that PR/SHA, checks all observed latest commit
check runs/status contexts after workflow success, and rechecks the PR HEAD before
accepting success. It never treats the synthetic merge-test SHA as the feature HEAD;
artifact/image binding to that SHA is a separate verification.

Mandatory jobs (always required, no removal flag): `checks / Python 3.12 / Node 24`,
`checks / Python 3.13 / Node 24`, `Non-publishing container verification`. Extra jobs:
repeatable `--require-job NAME`; new required check contexts: `--require-check NAME`
(verify the current rule inventory once at the integration boundary; the helper does
not infer protection/review rules). Only `Explicit owner-triggered main publication`
may intentionally be skipped in non-publishing runs. A run selection is pinned once:
no silent substitution of a cancelled run, different commit, or rerun; a newly
authorized rerun is a new verification event. Unknown/fork PR association (empty
`pull_requests` metadata) fails closed. Pagination is bounded to 1000 evidence rows;
incomplete evidence returns unavailable, not success.

### Flags, defaults, and result contract

All time options are seconds; delays happen inside Python:

| Flag | Default |
| --- | --- |
| `--initial-delay` | 90 (0 only for an already completed run or justified verification) |
| `--discovery-delay` | 30 |
| `--interval` | 60 |
| `--long-interval` / `--long-after` | 120 / 600 |
| `--max-wait` | 1800, includes delays and bounded requests |
| `--max-retries` | 3 additional attempts (0..3) |
| `--retry-base` | 15, exponentially 15/30/60 for transient failures |
| `--request-timeout` | 30 or remaining overall budget, whichever is shorter |

Rate limits use the later of `Retry-After` (seconds/HTTP date), exhausted-primary
reset (+1s margin) and 60s exponential secondary backoff; a successful response with
exhausted quota also delays the next call. No reset endpoint probes; if the permitted
retry falls outside the budget, the helper returns `rate_limited` with
`retry_at_epoch` immediately.

| Exit | JSON `status` | Meaning |
| --- | --- | --- |
| 0 | success | Exact-head terminal success and mandatory evidence; NOT merge permission |
| 1 | failed | Workflow/PR check failed or needs action |
| 2 | cancelled | GitHub terminal cancellation, not success/retry authorization |
| 3 | timed_out | GitHub timed_out or local overall deadline expired; no pass |
| 4 | rate_limited | Bounded retries exhausted or permitted API retry outside budget |
| 5 | unavailable | Missing gh/auth/permission/target, transient exhaustion, insufficient/malformed evidence or local output failure |
| 6 | invalid_input | Bad target/options or already-existing result path |
| 7 | interrupted | Ctrl-C; no resource mutation |

stdout is one JSON line at terminal completion (except `--help`): schema version,
PID/start/finish, repo/expected SHA, run ID/URL/attempt, PR identity, status/exit/
reason and, on success only, verified SHA plus job names/conclusions. Raw headers,
secrets, full API bodies and logs are never output. `--result-file` must be a NEW
outside-Git path: it is reserved with pending identity immediately and atomically
replaced by the terminal result; existing results are never overwritten, forced kill
can leave a pending record (never success), and result persistence failure is
nonzero. Verify the recorded process identity once on interrupted resume, not a loop.

Harness execution: one supported blocking/background shell invocation with timeout
covering the 1800s budget plus cleanup margin, correct workdir, absolute Python
executable, outside-Git result path; the harness delivers completion automatically.
Do not poll/sleep/read the result file while it runs. If the environment cannot
reliably outlive the wait, checkpoint and stop; do not recreate the wait as repeated
model invocations.

Failure diagnostics: for the recorded attempt, query failed jobs/steps first, then
`gh run view RUN_ID --repo OWNER/REPO --attempt ATTEMPT --job FAILED_JOB_ID
--log-failed > OUTSIDE_GIT_FAILED_JOB_LOG` once; search that saved log targetedly and
escalate to complete logs only when root cause is not established. For success,
report compact evidence (run/SHA/checks/conclusion), not full logs or PR JSON.

Focused mocked tests (no network/workflow/sleep/model calls):

```sh
python -m unittest discover -s tests -p test_ci_wait.py -v
python scripts/standard_checks.py
```

The tests run in the existing Python matrices via unittest discovery; CI definitions,
required jobs, permissions, timeouts and publication gates are not weakened.

## Manual register — all pending at takeover

RL-03 adds `tests/test_financial_history.py`: existing served financial rewrite/
report/correction exceptions and independently derived literal-DDL metadata only.
`python -B scripts/financial_schema_inventory.py` reproduces source-only inventory
from exact baseline/full Git ancestry; it is not a migration/adoption command.
No application/UI/cache change, new financial policy or supported fingerprint;
owner decision and authentic release/DB evidence remain open. Local/CI/manual
results must remain separate; no new device or production check completed.

RL-02 DP-024 adds `MigrationContractTests` and `VersionedRuntimeTests`: explicit
fresh/exact-current/ledger/future/unknown pre-write rejection, atomic metadata/schema/
data rollback, real concurrent processes/SQLite writer, abrupt kill and EF-08b new-root
recovery, simulated ENOSPC/permission, actual POSIX read-only failure (Windows skips).
Served booking/round/cashup/event/invoice/uncertain-payment tests additionally run
under fresh strict mode. CI runs `scripts/migration_rehearsal.py` in actual image
network-disabled alongside unchanged existing startup/persistence/upgrade/recovery/DR.
No UI/worker changes: cache-version review requires no bump; MV-01..06 still open.

RL-01 adds `ReleaseSafetyTests` and `UpgradeMigrationTests`: explicit offline
identity/bundle/config/image/key safety failures, no-write/pre-SQL sidecar rejection,
partial DDL/repeated financial-cost backfill/duplicate payment-ID/abrupt migration
characterization and complete synthetic existing-startup/ASGI/recovery rehearsal.
Container CI additionally runs installed offline identity and network-disabled
synthetic upgrade in actual local-only image; validates optional upgrade Compose
example without starting it. No authentic historical-image compatibility, production
upgrade or automatic rollback proof; MV-06 remaining operational acceptance unchanged.

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

EF-08b `ApplicationRecoveryTests` cover all-table two-installation generated-artifact
rehearsal, exact schema/sequence/payment/audit identities, traversal/corruption/
missing files, observed source changes, ordinary/abrupt interruption, OS lock
overlap, no-replace races, compatibility, CLI age status and EF-08a compatibility.
POSIX modes/FIFO/case-sensitive/symlink guards execute in Linux CI (Windows mode
test skips; Windows symlink privilege is not assumed). MV-06 remains partially
pending only for independently managed encrypted/offsite/storage/ACL/timed RPO/RTO
and operator reconciliation/acceptance rehearsal; no production data required.

EF-08c requires trusted `age`/`age-keygen` on PATH for full checks; missing tools
fail rather than skip. Install optional pinned binaries outside Git with
`python scripts/install_age.py --destination <new-tool-dir>` and extend PATH.
`IndependentRecoveryTests` execute real encryption/decryption/source-loss and key/
storage/archive/interruption/status failures. Linux runs private ciphertext/key mode
assertions; Windows effective ACLs remain operator evidence. `DisasterMeasurementTests`
verify deterministic metrics and synthetic reconciliation-gated startup without
network attempts. MV-06 may advance only on actual successful independent-loss drill;
real immutable/offsite hardware/storage/ACL/key-image retrieval and timed human
external reconciliation acceptance remain pending. EF-08a Windows WinError 5 remains
unresolved despite successful reruns; don't suppress or arbitrarily retry failures.

EF-08c automated MV-06 evidence receipt: reviewed implementation `beb4e494` passed
PR CI `45181321303` including encrypted independent replica verification, original
source container/volume/local-copy deletion, new compatible storage reconstruction,
complete financial/schema/artifact parity and explicit synthetic holds before
network-disabled startup. RPO age 0.368372s/RTO 2.250698623s for that synthetic run;
targets 3600s/300s. This closes the automated independent-loss/timing portion only,
**not full MV-06**. Remaining manual evidence: actual offsite/geographic/hardware
separation, enforced immutable retention, encrypted scratch/storage and Windows ACLs,
secure key/image acquisition under loss, timed operator/provider/mail reconciliation
and acceptance. Production adoption remains separate authorization.

PR #5 correction adds public-key-only production with no identity file, real age
producer decryption denial, separate local/independent/offsite verification/status,
explicit combined wrong-key failure and conservative v1/old receipt handling.
The actual image drill now removes only its uniquely owned derived image config,
asserts original ID unavailable, reloads retained archive and verifies identical
ID/owner label before recovery; shared input/base image is never removed. Mock
ownership/order tests execute locally, actual no-image archive evidence requires CI.
