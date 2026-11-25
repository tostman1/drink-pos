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

1. Read the current handoff checkpoint and inspect Git state, base, affected
   code, tests, and CI once. Refresh only state that may have changed.
2. Identify `DP-*` requirements and one bounded `EF-*`, `RL-*` or documentation
   package.
3. Describe scope, acceptance, risks, exclusions, and verification before editing.
4. For structural work, first demonstrate behavior parity at the actual runtime
   seam; do not substitute an extracted prototype based only on its name.
5. Anything changing business rules, deployment, or destructive recovery needs
   owner approval. Requirements in this baseline are reconstructed observations,
   not a claim of separate stakeholder sign-off.

## Implementation loop

- Characterize the old behavior, then make the smallest change.
- Run targeted tests, then `python scripts/standard_checks.py`. Keep CI
  read-only/non-publishing for branches and PRs. Do not hide errors with
  `continue-on-error` or skipped tests.
- Update requirements/test references and architecture when applicable.
- Record command, environment, result, warnings, and manual gaps in
  `docs/PROGRESS.md`. Review `git diff --check`, the full diff, and tracked-file
  status for secrets or generated data. Commit coherent increments with intent
  and evidence (`git commit -F`).

## Delivery and CI waiting

The delivery path is: implement → test → commit → PR → CI → review →
conditional merge → exact main CI.

1. With owner authorization, commit and push the verified candidate.
2. Capture the full HEAD SHA once. Invoke `python scripts/wait_for_ci.py` exactly
   once per required CI phase — the branch/PR run for the candidate, then the
   exact merge-main and final-main runs after an approved merge — bound to that
   SHA and the required jobs. Usage, defaults, and the exit/status contract are
   in [Standard Checks](standard-checks.md#deterministic-ci-waiting--ef-03).
3. Success must match the exact HEAD, workflow, event, attempt and all mandatory
   jobs/checks. Missing, skipped, stale, neutral or unrelated checks are never
   passes; only the intentionally skipped publication job is exempt. A timeout,
   rate limit, or pending result is not success or merge permission.
4. On failure, get targeted failed-job/step evidence for the recorded attempt,
   diagnose, and change the actual problem. Repeat verification only for a
   changed commit, failed check, tooling fix or another meaningful state change;
   preserve failed evidence, never retry to hide it.

Waiting is mechanical work for the deterministic helper, not model turns: no
tight LLM-driven GitHub polling, no repeated `gh run view`/`gh pr checks` while
pending, no short sleeps followed by model turns, no re-requesting unchanged
status or full PR inspections, no repeated full CI logs, and no progress
commentary without an actionable state change. Use targeted files/searches,
concise outputs, and batched independent read-only queries. Use existing
DP/EF/RL/decision IDs; persist important knowledge in the authoritative docs
rather than duplicate lists. Quality, coverage and accurate reporting take
precedence over brevity.

If the execution environment cannot reliably outlive the wait, record a durable
checkpoint and stop; a timeout is not success and never restarts the wait as a
model loop.

## Review and merge

Before an approved merge, refresh HEAD/base, reviews, unresolved threads,
protection rules and mergeability exactly once at that boundary; use the
established normal merge with the exact-head guard and no bypass. If GitHub is
still computing mergeability, checkpoint or stop rather than polling. The
helper performs no dispatch, rerun, cancel, merge, or rule change; it does not
replace review, protection, artifact-authenticity, or deployment authorization.
Approval for one PR is not standing approval for future PRs or any
release/deployment.

## Durable checkpoint and recovery

Maintain ONE concise current checkpoint at the top of `docs/HANDOFF.md`;
completed/failed evidence belongs in `docs/PROGRESS.md`. Historical receipts
remain intact but are not automatically reread and are not renewed authority.
Update the checkpoint on interruption, a rate limit, a dependency or tool
failure, or a meaningful transition — not on each poll. On resume, read the
checkpoint first, verify branch/HEAD/worktree, refresh only external state that
could have changed, and perform one identity check after an interruption before
starting any watcher. Do not restart the package or repeat verified work without
a concrete reason. Never automatically resume a merge or deployment.

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

## Failure, limits, and diagnostics

The helper is read-only: explicit `gh api` GETs, bounded internal delays,
header-aware bounded retries, one final JSON line, distinct terminal statuses.
Its outside-Git result file records identity (PID/start/expected SHA) immediately
and is atomically replaced by the terminal result; an existing result path is
never overwritten, and a pending record after forced termination is not success.

| Limit/failure | Correct response |
| --- | --- |
| GitHub REST primary/secondary | Follow `Retry-After` and quota reset information; the helper waits until the latest permitted time, then bounded exponential backoff. No extra reset probes. |
| Transient API/network failure | Bounded backoff honoring retry instructions; authentication/permission/unrecognized evidence is unavailable, not a retry campaign. |
| LLM provider request limits | Stop unnecessary model interactions; preserve the checkpoint and resume when available; no quota bypass. |
| LLM provider token limits | Reduce context/output duplication; preserve the checkpoint and stop. A fixed delay never guarantees recovery. |
| Tool execution timeout | Execution boundary, not CI/provider failure: use the supported completion notification or a clean checkpoint; no repeated short polling. |

For a failed run, query failed jobs/steps for the recorded attempt first,
download `--log-failed` for only the failed job once, store large logs outside
Git, and search them once. Escalate to complete logs only when targeted data is
insufficient. For success, report run ID/URL, exact verified SHA, workflow/check
names and conclusion; do not dump complete logs or PR JSON.

## Traceability maintenance

`docs/requirements.json` is the machine-readable catalog; `REQUIREMENTS.md`
provides context and limitations. Each requirement has a stable ID, observable
statement, source paths, verification test references and/or manual checks, and
scope. Validate links with `python scripts/check_traceability.py`; update
references when tests move. New unresolved requirements must be marked as such,
never given fictitious tests.

## Integration / release boundaries

PR and main integration runs use the same non-publishing quality/container jobs.
An image publication requires separate owner approval, successful checks and an
explicit main workflow dispatch; production deployment remains a separate human
operational decision. Never dispatch publication during foundation verification.
