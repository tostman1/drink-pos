# Engineering process

## Scope and authority

The owner authorized the foundation: reconstructed requirements, truthful
architecture, agent rules, work packages, repeatable checks, regression protection,
and safe CI. This does not approve a framework migration, ORM, database redesign,
new product behavior, or every task in the historical review/prompts.

Evidence order: current owner instructions; verified commits/PR descriptions;
served code plus tests; current operational docs; historical YAML/review/ideas.
Contradictions are recorded, not silently turned into requirements. Automated
tests characterize behavior; they do not prove target-device usability or real
external-service behavior.

## Ready gate

1. Read the current handoff checkpoint and inspect Git state, base, affected code,
   tests, and CI once. Refresh only state that may have changed; expand historical
   context when a real dependency or contradiction requires it.
2. Identify `DP-*` requirements and one bounded `EF-*`, `RL-*` or documentation package.
3. Describe scope, acceptance, risks, exclusions, and verification before editing.
4. For structural work, first demonstrate behavior parity at the actual runtime
   seam; do not substitute an extracted prototype based only on its name.
5. Anything changing business rules, deployment, or destructive recovery needs
   owner approval. Requirements in this baseline are reconstructed observations,
   not a claim of separate stakeholder sign-off.

## Implementation loop

- Characterize the old behavior, then make the smallest change.
- Run targeted tests, then Standard Checks. Keep CI read-only/non-publishing for
  branches and PRs. Do not hide errors with `continue-on-error` or skipped tests.
- Update requirements/test references and architecture when applicable.
- Record command, environment, result, warnings, and manual gaps in progress.
- Review `git diff --check`, the full diff, and tracked-file status for secrets or
  generated data. Commit coherent increments with intent and evidence.

## Done gate and handoff

An increment is implemented when its acceptance checks pass and gaps are named.
Review-ready additionally requires successful branch/PR checks and a clear PR
description. Merge/release readiness requires owner's approval plus any relevant
manual/device/integration evidence. These states are not interchangeable.

`docs/PROGRESS.md` records completed/active/blocked work and evidence. `docs/HANDOFF.md`
records branch/base/PR relationships, protected changes, unresolved verification,
and the next safe action. Never clear an unfinished check because an unrelated
lint/test job passed. No automatic merge or deployment is part of this process.

## Mandatory token-efficient GitHub and CI workflow

**Waiting is not reasoning. An LLM must not repeatedly reason, generate commentary,
invoke tools or reconstruct context solely to wait for an external operation.**
Binding for all sessions, agents, epics and packages, including Actions, PR checks,
mergeability/protection updates, final-head and post-merge CI, artifacts, rate-limit
recovery and other asynchronous external systems. Repetitive waiting is mechanical
work for deterministic non-LLM automation, normally one invocation and one final result.

### Sequence and unchanged safeguards

1. Complete implementation; freeze the candidate while verification is running.
2. Run relevant local regression and full Standard Checks; retain failures/warnings.
3. With owner authorization, commit (`git commit -F`) and push the verified commit.
4. Capture the full intended HEAD SHA and explicit repo/branch or PR. Identify its
   Actions run once, or let the helper discover by workflow/event/exact SHA/PR identity.
5. Invoke `python scripts/wait_for_ci.py` once, as specified in
   [Standard Checks](standard-checks.md#deterministic-ci-waiting--ef-03).
6. Wait without model turns or status commentary. Receive one compact terminal result.
7. Success must match that exact HEAD, workflow, event, attempt and all mandatory
   jobs/checks. No stale/unrelated/missing/skipped/neutral checks accepted as passes;
   only the existing intentionally skipped publication job is exempt. Additional
   protection/external check contexts must be supplied with `--require-check` and
   independently reviewed against the current rules. The helper does not change rules
   or replace review/mergeability/protection/artifact authenticity checks.
8. Continue only the next authorized integration action. Before an approved merge,
   refresh HEAD/base/reviews/unresolved threads/protection/mergeability once at that
   boundary. Use the established exact-head guard and normal merge method, no bypass.
   If GitHub is still computing mergeability, checkpoint/stop or use one bounded
   deterministic watcher; never short-sleep/tool/model loops or assume mergeability.
9. On failure, obtain targeted failed-job/step evidence, diagnose and change the actual
   problem. Repeat verification only for changed commit, failed check, tooling fix or
   another meaningful state change; preserve failed evidence, never retry to hide it.
10. Apply the same helper to final-head branch AND PR CI and, after an explicitly
    approved merge, exact merge-main and final-main CI. Verify tree/parents separately.
    Documentation descendants get their own exact-commit CI; predecessor/same-tree
    success is not sufficient. Avoid creating endless receipt-only commits: retain
    final SHA/results in the authorized PR receipt/report after the final commit.

CI/review/security/migration/regression/manual gates, branch protection, release
traceability and deployment authorization are unchanged. A timeout, missing evidence
or pending result is never success or merge permission. Successful CI is not real
DSM/mobile/PWA/provider/operator acceptance. No dispatch/rerun/cancel/merge by the helper.

### Prohibited orchestration

- Tight LLM-driven GitHub polling, `gh run view` every few seconds, repeated
  `gh pr checks` while pending, or short shell sleeps followed by another model turn.
- Re-requesting unchanged status or full PR inspections, repeated full CI logs, or
  progress commentary without actionable state changes.
- Re-reviewing/rewriting unchanged implementation while CI runs, or reconstructing
  the entire repository context during one work package.
- Aggressive rate-limited retries, parallel agents watching identical CI, or elapsed
  waiting time as a reason for more model requests/tokens.

Use targeted searches/reads, concise tool output, cached verified session facts and
batched independent read-only queries. Do not redundantly repeat status/diff/branch/
remote commands, implementation summaries or unchanged code. Use existing DP/EF/RL/
decision IDs; persist important knowledge in authoritative docs. Deterministic scripts
handle repetitive work; LLM reasoning is for analysis/design/implementation/debugging/
meaningful review. Quality, coverage and accurate reporting take precedence over brevity.

### Timing, execution and distinct limits

Defaults: 90s after trigger/push, 30s discovery retry, 60s normal polling, 120s after
10 minutes, 30-minute overall budget including delays/requests, three retries after
the original failed request, transient backoff 15/30/60s. Internal delays only;
final JSON only. Configure supported values with justified evidence, not for tight polling.

| Limit/failure | Correct response |
| --- | --- |
| GitHub REST primary | Follow `X-RateLimit-Resource`, remaining/reset and `Retry-After`; helper uses REST through `gh api --include` and waits until the latest permitted time. No extra reset probes. |
| GitHub GraphQL primary | Separate budget/resource; do not infer availability from REST. Respect returned reset information; use one deterministic wait or checkpoint, not endpoint switching to evade quotas. Helper does not use GraphQL. |
| GitHub secondary | Respect `Retry-After`; absent that, at least 60s, then bounded exponential backoff. Stop with permitted retry timestamp if outside budget or retries exhausted. |
| Transient API/network failure | Bounded exponential backoff; honor retry instructions. Authentication/permission/unrecognized evidence is unavailable, not an automatic retry campaign. |
| LLM provider request limits | Stop unnecessary model interactions/repeated requests; preserve checkpoint, resume only when session/provider is available; no quota bypass. |
| LLM provider token limits | Separate from request limits and GitHub; reduce context/output duplication, preserve checkpoint and stop. A fixed delay never guarantees recovery. |
| OpenCode tool execution timeout | Execution boundary, not CI/provider failure. Use supported background completion notification or a clean checkpoint; no repeated short polling. |

In the current harness the shell defaults to **120000ms**; foreground timeout hands
off to background, while an explicitly background command is stopped at its timeout.
Use one `functions.shell` call with `background: true, timeout: 1860000` for the
1800s helper budget plus cleanup margin (or one foreground call with that timeout).
Use an absolute Python executable and correct workdir; do not launch an unmanaged
detached child/PowerShell job. Record returned tool/job identity plus the helper's
PID/start/expected SHA/result path. The harness delivers completion automatically:
do not sleep, poll, or check the result file while waiting. One notification then
one result read if needed. If this capability/timeout is not available, stop with
checkpoint; never recreate it through repeated model invocations or prompt reminders.

The helper bounds each `gh` request to 30s or remaining budget, uses no shell/child
watcher, and Python cleans up timed-out child requests. It writes a small pending
record immediately and atomically replaces it with a terminal result. Ctrl-C records
interrupted; forced process termination may leave pending, which is NOT success.
Do not start a second monitor on resume before checking the recorded process identity
once; PID alone can be reused, so compare start time/command/target. Only an identified
owned monitor may be stopped; GitHub runs are never cancelled. Retain evidence until
integration review; cleanup only that operation's outside-Git result/log after no
monitor is active. No recurring LLM jobs, sleeps or notifications for unchanged state.

### Failure diagnostics and compact evidence

First query failed jobs/steps for the recorded run attempt (commands in Standard
Checks). Download `--log-failed` for only the failed job once; store large logs outside
Git and search relevant errors/sections. Do not fetch successful-job logs or repeated
complete workflow logs routinely. Escalate to complete logs only when targeted data
is insufficient; retain all information needed for reliable root-cause analysis.
For success report run ID/URL, exact verified SHA, workflow/check names and conclusion,
plus test summary only where required. Do not dump complete logs or PR JSON.

### Durable checkpoint and recovery (existing documents, no new status files)

Maintain ONE concise current checkpoint at the top of `docs/HANDOFF.md`; completed/
failed evidence belongs in `docs/PROGRESS.md`, not a growing new family of documents.
Historical receipts remain intact but are not automatically reread or renewed authority.
Update on interruption/rate limit/dependency/tool failure or meaningful transitions,
not each poll. If model access is already lost, the helper's outside-Git identity/
result record plus existing checkpoint enables later completion without model calls.

```text
Work package: EF/RL/docs ID; implementation status; authorized scope
Branch / current full commit SHA: ... (uncommitted changes explicitly noted)
PR: number + URL / none; run: ID + URL / not yet discovered
Completed verification: exact SHA/tree/environment/result + evidence path
Pending verification: required local/branch/PR/final-head/post-merge/manual checks
Blocker: specific GitHub REST/GraphQL/secondary / provider request/token / tool / other
Next action: exact command/approval needed; permitted retry time if supplied
Monitor: tool job + PID/start/target/result/log paths / none
Integration: merge occurred? SHA / no; deployment/publication occurred? / no
```

On resume read the checkpoint first, verify branch/HEAD/worktree and only external
state that could have changed. Read one persisted result after known completion or
perform one identity check after interruption. Do not restart the package/repeat
verified work without a concrete reason. Never automatically resume a merge/deploy.

## Traceability maintenance

`docs/requirements.json` is the machine-readable catalog; `REQUIREMENTS.md`
provides context and limitations. Each requirement has a stable ID, observable
statement, source paths, verification test references and/or manual checks, and
scope. Original PR #1 tests are now integrated local evidence; they were external
at takeover and remain preserved. Validate links
with `python scripts/check_traceability.py`; update references when tests move.
New unresolved requirements must be marked as such, never given fictitious tests.

## Integration / release boundaries

The owner merged PR #1 while foundation development was active as
`052c2bbc54f05f7c7d850feb8ad597a4e4868670`; this was integrated into the foundation
branch without rewriting either history. The owner later approved PR #2 merge
conditional on final pushed-HEAD checks. Use the normal repository merge method
without protection bypass, then verify merged-tree and main CI evidence. Approval
for one PR is not standing approval for future PRs or any release/deployment.

PR and main integration runs use the same non-publishing quality/container jobs.
An image publication requires separate owner approval, successful checks and an
explicit main workflow dispatch; production deployment remains a separate human
operational decision. Never dispatch publication during foundation verification.
