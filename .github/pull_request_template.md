## Outcome and scope

- Work package(s): EF-...
- Requirement(s): DP-...
- Behavior changed / preserved:
- Exclusions and migration/rollback considerations:

## Evidence

- [ ] Standard Checks: command, environment, result recorded in docs/PROGRESS.md
- [ ] Non-publishing container/Compose verification passed
- [ ] Exact final HEAD branch/PR CI: run IDs/URLs, SHA, workflow/checks and conclusions recorded
- [ ] Waited once per target with `scripts/wait_for_ci.py` (no LLM polling); failures diagnosed with targeted saved logs
- [ ] Relevant test links and architecture updated
- [ ] Full diff and generated-state/secrets reviewed
- Manual/device/external-service checks completed or explicitly pending:

## Safety and handoff

- [ ] Owner-merged PR #1 transfer intact; latest verified main integrated
- [ ] docs/HANDOFF.md / docs/PROGRESS.md updated
- [ ] No production DB, deployment, image publication, live payment/email activity
- [ ] No merge without owner's explicit approval
- [ ] Review/protection/manual gates unchanged; exact post-merge/final-main CI required if merge is authorized
