# RL-06 ready gate — isolated Synology test deployment

Baseline: `25a78ba6606e74760969cce7c993d60d3a139f2e`, verified clean and
equal to fetched main on 2026-11-24. Branch:
`feature/rl-06-synology-test-deployment`. Owner authorizes feature commits,
push and one OPEN/UNMERGED PR, not a NAS installation or production operation.

## Inspection and concise implementation plan

- Served seam remains `main -> application -> routes/registry -> legacy_main`.
  Docker copies `app/` to `/app`; no host application-code mount is needed.
- Both existing Compose files pull GHCR `stable`, port 8088; production Podman
  updater pulls/recreates/prunes and its timer schedules daily work. **Unchanged
  and excluded**. New project/container `drink-pos-test`, AMD64,
  one application service, internal network, no pull/build/scheduler/socket.
  CI demonstrated internal-only Docker does not publish host ports reliably:
  no host mapping; fixed dedicated non-overlapping internal IP:8000 is the DSM
  reverse-proxy target. Optional DSM proxy listener 8089 is not an app mapping.
- CI already builds a local verification image and exercises financial,
  migration, EF-08b/c and dependency gates. Save **that tested image**, retagged
  with exact checkout SHA, only after all gates. Downloadable Actions artifact
  includes archive SHA-256, Docker config ID, runtime/release identity, CI receipt,
  deployment files and German guide. No registry publication or reproducibility
  assertion. PR checkout SHA may be GitHub's merge SHA, not branch head.
  Actual update evidence uses separately built immutable main baseline image
  `25a78ba...` and older v1 `2cc36fd...` for unsupported downgrade/startup rejection;
  only candidate is distributed, no old image publication.
- Dedicated absolute NAS test root with separate data/backups/recovery/evidence;
  private untracked `.env.test`. No production imports, secrets, invoices/messages,
  volumes or keys. Production runtime mode preserves PIN protection and ordinary
  behavior; no real provider/mail/Agent API. Internal network prohibits outbound
  provider/SMTP connections (including later UI configuration).
- New offline/test-only command entrypoint validates identity, strong PIN,
  timezone, fixed DB, isolation marker and strict v2. Explicit synthetic-only
  initialization accepts an empty target once; it reuses existing fresh v2/default
  synthetic seed, then writes marker. `serve` never grants fresh/adopt permission.
  Existing application entrypoint/startup/defaults stay unchanged.
- Read-only identity/inspection/verification/preflight are separate from explicit
  initialize/backup/restore mutations. Reuse unchanged EF-08a/b/c bundles and
  independent encrypted rehearsals. Backup requires stopped writers. Preflight
  operates only on an isolated verified backup, exact current/candidate identities,
  explicit compatibility/operator evidence; it never starts/migrates live state.
- Operator-controlled update: drain/stop, capture full state, independent verify,
  isolated candidate rehearsal, approve exact image, start without fresh permission,
  integrity/health/functional/financial checks, retain receipt. Failures preserve
  state; image rollback only with proven same-schema compatibility. Full pre-update
  restore uses new roots and old exact image, never overwrites post-backup activity.
- Add failing DP-001/008/009/016/024 regressions before behavior implementation,
  then actual deliverable Compose/image installation, persistence, isolation,
  update/preflight/downgrade and independent recovery checks in CI. Run complete
  Python 3.12/3.13 Standard Checks plus all existing container gates.

## Evidence boundaries and acceptance

Actual DSM/Container Manager documentation is checked against Synology Knowledge
Center: image file import, project Compose creation, Login Portal reverse proxy
and certificate assignment. Version-sensitive `.env.test` interpolation receives
an explicit NAS CLI alternative; Windows requires only browser/File Station and
PowerShell `Get-FileHash`, not Python/Node/Git/Docker. Never assert GUI testing on
hardware from documentation or CI. Desktop/tablet/mobile/installed-PWA, trusted
HTTPS, offline queue, cache transition, full round block/reversal matrix and
operator restore/key/ACL/reconciliation acceptance remain **PENDING** until owner
execution. No UI source change planned; service-worker version reviewed, not
gratuitously changed. Existing historical/OQ/Windows recovery gaps remain open.
