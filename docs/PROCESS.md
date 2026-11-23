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

1. Read the handoff and inspect Git state, base, affected code, tests, and CI.
2. Identify `DP-*` requirements and one `EF-*` work package.
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

## Traceability maintenance

`docs/requirements.json` is the machine-readable catalog; `REQUIREMENTS.md`
provides context and limitations. Each requirement has a stable ID, observable
statement, source paths, verification test references and/or manual checks, and
scope. Original PR #1 tests are now integrated local evidence; they were external
at takeover and remain preserved. Validate links
with `python scripts/check_traceability.py`; update references when tests move.
New unresolved requirements must be marked as such, never given fictitious tests.

## Integration / release boundaries

The owner merged PR #1 while foundation development was active; verified main
is now `052c2bbc54f05f7c7d850feb8ad597a4e4868670`. Preserve both histories.
Commit foundation increments first, then merge the verified main into this branch
without rewriting it, resolve overlapping documentation/tests deliberately and
verify the complete combined tree before delivery. This branch integration is
not approval to merge the foundation PR or release anything.

PR and main integration runs use the same non-publishing quality/container jobs.
An image publication requires separate owner approval, successful checks and an
explicit main workflow dispatch; production deployment remains a separate human
operational decision. Never dispatch publication during foundation verification.
