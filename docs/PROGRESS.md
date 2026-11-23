# Engineering foundation progress

## Current scope

Independent review branch `feature/engineering-foundation-baseline`, based on
verified `main` at `fb0812837694949dc6d228b781f2aa7af2b29d98`.
PR #1 at `250a4e6` was subsequently merged by owner `tostman1` at
2026-11-22T21:15:45Z as `052c2bbc54f05f7c7d850feb8ad597a4e4868670`.
The original handoff branch is unchanged. Integration into this branch will be
done after current foundation increments are committed, not by resetting work.

| Package | State | Evidence / next step |
| --- | --- | --- |
| EF-01 Takeover, requirements, process, architecture | Implemented | Full handoff diff/PR inspected; branch isolated; catalog and documented seams |
| EF-02 Standard Checks and regression guards | Implemented / final verification | Mandatory commands, security/browser, integrated handoff/HTTP tests |
| EF-03 CI/container safety and review delivery | In progress | Safe workflow implemented; actual PR/container execution next |
| EF-04 Narrow legacy rehabilitation | Not started / approval gate | Select one characterized seam after foundation review |

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
Do not copy Notenarchiv architecture, introduce an ORM, change payment retries,
or run historical wide-refactor prompts. See architecture risks and EF-04 gates.
No deployments, production DB operations, live emails/payments, merges, or image
publication have been performed by this assignment.

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
