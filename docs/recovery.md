# EF-08 database recovery contract

Scope: DP-014 and DP-013; SQLite recovery only. No production access, deployment,
mail/payment operations, automatic migration or invoice-side-effect redesign.

## Baseline evidence (main a218fcc, 2026-11-23)

- `backup_database.create_snapshot` uses the SQLite Backup API (WAL-consistent),
  but `export_backup` deletes that snapshot after exporting a fixed table list.
  CSV includes schema but omits `event_sessions`, `event_lines`, `sqlite_sequence`
  data and any future table. It is not a complete database recovery artifact.
- CSV is written directly to its final second-resolution name: collisions can
  overwrite; interruptions can leave apparently complete files. No checksum,
  integrity/FK checks or retention exist.
- CSV restore uses a predictable temporary filename, deletes a previous temp,
  skips unknown data columns/tables, checks integrity before commit but not FKs,
  then `os.replace` can overwrite a concurrently created target.
- Startup schema is additive and sets WAL; migrations are not an independently
  versioned/atomic migration framework. A pre-migration backup is needed; a valid
  SQLite file does not prove a partially applied migration is semantically valid.
- Both Compose schedulers run Friday 03:00 using the image's backup CLI and
  `./data:/app/data`. Backup and source are on the same NAS/filesystem. Failure
  is logged by Python but not alerted; no catch-up after a missed schedule.

## Acceptance defined before implementation

- Persistent all-table Backup API snapshot, integrity and FK verification,
  unchanged BOM/semicolon/JSON CSV, manifest with UTC ID/size/SHA-256/table counts.
- Publish a unique completed bundle atomically; incomplete staging is never a
  selectable completed backup. Clean only temporary resources owned by this run.
- New-target-only restore, including race/symlink/WAL-sidecar conflicts; verify
  checksums and recovered SQLite before atomic no-clobber publication.
- POSIX restore: pre-create the temporary database as 0600 before SQLite writes;
  create each missing target directory as 0700, leaving existing directories alone;
  enforce 0600 again before atomic publication. Never expose intermediate data.
- Retention disabled unless explicitly configured; keep at least two verified
  bundles, never touch legacy files, invalid bundles or another run's staging.
- Synthetic tests compare every table (including sequence state) and schema
  objects, exercise WAL committed/uncommitted state, corruption, interruptions,
  failed restores, concurrent destinations and conservative retention.
- Synthetic rehearsal retains separate event CSV/PDF and message artifacts and
  verifies them separately; actual image verification remains a required CI gate.

Rollback is code-only: do not modify the deployed pinned image. Existing legacy
CSV restore remains available with documented completeness limits. No generated
database, backup, invoice or credentials are committed.

## CLI/runbook (isolated resources only in this assignment)

Backup uses existing `DRINK_POS_DB`/`DRINK_POS_ENV` path resolution and
`DRINK_POS_BACKUP_DIR` (default: sibling `backups`). Run `python -m
app.backup_database` from the repository, or `python /app/backup_database.py` in
the image. The existing scheduler entrypoint needs no change. Each completed
`drink_pos_backup_<timestamp>_<uuid>/` contains `database.db`, `export.csv` and
`manifest.json`. Consumers must now look inside bundles rather than glob only
top-level CSV files. CSV headers, sections, JSON payloads, BOM and delimiter are
unchanged; the fixed CSV table list deliberately remains unchanged.

`DRINK_POS_BACKUP_KEEP` empty/unset disables deletion. An explicitly configured
integer >=2 keeps that many newest *verified* bundles (and always the just-created
bundle). Bundles for a different source DB path in a shared destination are never
pruned. Legacy CSV, invalid bundles, symlinks, foreign files and staging are never
pruned. Only one retention run may hold an exclusive lock; a crash leaves a stale
lock and disables further cleanup until an operator confirms no cleanup is running
and removes that specific lock. Never enable retention before owner-approved
offsite copies and recovery validation. Concurrent backup writers are supported;
completed directories must be treated as immutable by operators.

Restore: `python -m app.restore_database <completed-bundle-or-database.db>
<explicit-new-target.db>`. Both positional arguments are required. It checks both
artifact checksums, snapshot integrity/FKs/table counts, copies with Backup API,
checks the recovered DB and publishes without replacing an existing target.
Targets with an existing DB, symlink or WAL/SHM/journal are rejected. Restore to a
private directory with no running application/writers; no file protocol can safely
coordinate arbitrary external writers creating WAL sidecars at that target.
Hard-link support on the *target* filesystem is required (normal Synology local
ext4/Btrfs and Windows NTFS); unsupported network filesystems fail closed.
Restore produces a standalone DELETE-journal database; normal approved app startup
re-enables WAL. Restore never starts the application or migrates the database.

On POSIX, every newly created target-directory component and restore staging
directory is private (0700, subject to a more restrictive umask). SQLite writes
into a pre-created 0600 file; publication enforces 0600 before the no-clobber link.
Existing directory modes/ownership are **not** modified. Use a trusted parent
directory: this is not protection against root or a hostile directory owner.
On Windows, POSIX mode bits are **not** an owner-only file-ACL guarantee; effective
access depends on NTFS/Windows ACLs and inheritance. Some Python/Windows versions
apply a restrictive ACL when creating a directory with mode 0700, but the CLI does
not explicitly manage or verify ACLs, including those on published files or existing
parents. Operators must select and verify a restricted destination ACL before
restoring; Linux mode-test results are not Windows ACL verification.

Standalone old CSV remains accepted, with post-commit integrity/FK checks and the
same safe target publication. Missing tables/data (especially named events),
sequence high-water marks and absent checksums cannot be reconstructed. Unknown
data columns/tables now fail instead of silently dropping data. Only restore
trusted operator-created CSV: its schema is executable SQL, not an untrusted
upload format. A checksum detects accidental changes, not malicious replacement
of both backup and manifest; manifests are not signed.

Normal failures/interrupt exceptions remove owned staging. SIGKILL/power loss can
leave hidden `.drink-pos-backup-*` or restore staging; these are not completed
artifacts and must not be selected or automatically pruned. File fsync plus Linux
directory fsync precedes/follows publication; storage/controller power-loss
guarantees remain a filesystem/hardware responsibility. Retention failure after
publication returns an error but leaves the verified new bundle intact.

## CSV layout compatibility assessment and operator migration

Repository inspection for PR #3 found:

- Both Compose schedulers execute `backup_database.py`; neither parses output nor
  searches for a CSV filename. Dockerfile/.env defaults and README NAS folder
  instructions still select the same backup root. These entrypoints remain compatible.
- `scripts/container_smoke.py` and recovery tests use the returned CSV path, not a
  top-level filename assumption. No repository copying/cleanup/report script was
  found that depends on `drink_pos_backup_YYYY-MM-DD_HHMMSS.csv` at the root.
- The operational YAML's `backup_and_recovery.output.filename_pattern` described
  the old top-level filename; it now distinguishes legacy and bundled outputs.
  README configuration wording now describes database/CSV bundles, not CSV-only.
- External Synology tasks, spreadsheets, NAS backup filters and other integrations
  are **unknown/unverified**. No production inspection was performed and no claim
  is made that any external consumer has migrated. A root-only `*.csv` filter will
  silently miss new backups; an exact timestamp filename parser also needs review.

Keep the current pinned deployment unchanged. Before separately approved adoption:

1. Inventory each consumer with its owner: recursive/root-only filter, filename
   parser, restore command, permissions, retention and offsite destination. Do not
   infer that copying `data/backups` is recursive or includes hidden-file exclusions.
2. Prefer updating consumers to discover completed `drink_pos_backup_*` **directories**,
   verify `manifest.json` and both checksums via `verify_bundle`, and copy the entire
   immutable bundle. Ignore `.drink-pos-backup-*`; never rename/edit bundle artifacts.
   Select `export.csv` for CSV-only accounting imports; select the bundle/database
   for full recovery. Continue preserving legacy top-level CSV files.
3. Rehearse old and new inputs on synthetic data; validate BOM/semicolon/JSON,
   filenames, restricted access, whole-bundle checksums and offsite restore. Keep
   retention disabled until verified, independent copies exist.
4. If a consumer cannot change immediately, use an **owner-approved explicit
   CSV adapter into a separate private compatibility directory**, after bundle
   verification. Copy bytes to a 0600 temporary file in a 0700 staging directory,
   fsync and atomically no-clobber publish a legacy timestamp `.csv` name. Preserve
   the authoritative bundle and do not treat this partial CSV as full recovery.
   Reject timestamp collisions instead of replacing an existing legacy export.
   An example for one explicitly selected bundle/target (not an automatic scheduler):

   ```python
   import os
   import shutil
   import tempfile
   from pathlib import Path
   from app.database_recovery import create_private_directories, publish_new_file, verify_bundle

   bundle = Path("/isolated/backups/drink_pos_backup_<timestamp>_<uuid>")
   target = Path("/isolated/legacy-csv/drink_pos_backup_<timestamp>.csv")
   verify_bundle(bundle)
   create_private_directories(target.parent)
   with tempfile.TemporaryDirectory(dir=target.parent) as staging:
       fd, name = tempfile.mkstemp(dir=staging)
       with os.fdopen(fd, "wb") as output, (bundle / "export.csv").open("rb") as source:
           shutil.copyfileobj(source, output)
       publish_new_file(Path(name), target)
   ```

   Select restrictive Windows ACLs separately. Compatibility copies are not managed
   by bundle retention; inventory their protected storage/cleanup with their owner.
   Avoid symlinks into bundles (retention could break them), automatic duplicate
   root exports or unverified `cp` overwrites. No adapter or consumer migration was
   run here; adoption requires separate owner approval.

This explicit migration keeps the bundle's one-step atomic publication intact;
there is no silently generated secondary CSV that could fail independently and
mislead an unchanged consumer about recovery completeness.

## What SQLite recovery does not recover

- `app/services/events.py` stores invoice CSV/PDF under the DB parent's `events`
  directory; DB rows contain paths/flags, not the file bytes. Retain exact artifacts,
  not regenerated invoices using changed settings. Existing CSV→PDF→SMTP→DB close
  ordering is unchanged and cannot provide a cross-filesystem transaction.
- Runtime message JSON (`DRINK_POS_MESSAGES`), deployment `.env`/credentials,
  Compose configuration and the known-good pinned image digest require protected
  independent copies. Settings/payment sessions in the DB can contain sensitive
  information; backups need restricted directory permissions, encryption/access
  controls and a separate failure-domain/offsite copy. This CLI does not encrypt.
- Browser offline queues exist on clients only. A DB snapshot predating a payment
  or booking loses later identifiers: reconcile with independent audit/provider
  evidence before resuming. Never retry uncertain SumUp charges or invoice mail.
- Weekly schedule means up to a week of normal data loss; missed slots increase
  it. Alerting, catch-up, RPO/RTO policy and offsite verification remain operational
  gaps, not solved by keeping DB and backups on the same NAS.
- Migration recovery requires a known-good pre-migration bundle and compatible
  pinned application. Integrity checks cannot diagnose semantically incomplete
  migrations. No automatic rollback/configuration switch is implemented.

## Separate owner-approved operational steps (not performed)

Review the new bundle layout with existing backup consumers; retain the currently
deployed image digest unchanged until a separate approval. If later adopted,
select a verified image, mount a protected backup destination, explicitly pass
retention only if approved (current Compose does not pass KEEP), and configure
offsite copying/monitoring. For coordinated artifact copies, quiesce writes and
invoice closure, snapshot DB and copy `events`/messages/config with a common
inventory/checksums, store offsite, then rehearse into a separate isolated root.
Switching the running DB, restoring secrets, reconciling payments/mail and starting
production all require separate owner authorization. No Compose/digest changes
are included in EF-08a.
