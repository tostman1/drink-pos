# Portable application recovery — EF-08b

The [ready gate/inventory](ef-08b-contract.md) defines scope and risks. This is an
**offline, operator-quiesced** recovery mechanism, not a live financial snapshot
protocol. No services are stopped/started by the recovery tool. EF-08a's database
bundles and CSV restore remain unchanged; see [recovery.md](recovery.md).

## Versioned format and guarantees

Application bundles use `format: drink_pos_application`, integer `format_version: 1`
(a different namespace from EF-08a). A completed directory is named
`drink_pos_application_<UTC timestamp>_<UUID>/` and contains:

```text
manifest.json             full payload inventory, SHA-256/byte sizes
COMPLETED.json            verified marker binding manifest hash/size and backup ID
configuration.json        explicit allowlisted non-secret JSON, empty by default
state/database.db         standalone SQLite snapshot, no WAL/SHM/journal dependency
state/events/...          all regular event artifacts, including orphan files
state/messages.json       explicit runtime catalog (absence needs acknowledgement)
```

Manifest records start/completion UTC, operator-selected deployment ID, exact
source application Git commit, optional pinned image digest, SQLite library version,
schema fingerprint, SQLite user/application versions, all-table logical fingerprint
and counts (including sequence), event path mappings, directories and consistency
label. There is no independently versioned migration history in the current app;
SQLite `user_version` alone is **not** a schema compatibility guarantee.

Require **all** app processes/workers, event/payment work, message editors and
imports to be stopped/drained before creation and remain stopped until completion.
The tool checks logical DB and file inventories/checksums before/after copy, and
verifies copied files. Changes observed in that interval abort. This does not
detect every transient/ABA change, partial artifact left *before* maintenance, or
prove that an operator actually stopped writers. A recovered active event plus
orphan files reflects source state, not proof an invoice was delivered/completed.
Do not treat `--quiesced` as an online-write lock or automatically pass it to the
existing live Friday scheduler. No app blocking/deadlock risk was introduced.

Each operation uses exclusive-create lock and private same-filesystem staging.
Concurrent creation at one destination fails promptly (exit 3); independent
destinations are allowed **only under the same maintenance precondition**. Completion
marker plus successful verification identifies bundles for external transport.
Linux `renameat2(RENAME_NOREPLACE)` and Windows non-replacing rename atomically
publish without clobber, including empty target races. Unsupported OS/filesystem
fails closed; no fallback copy/replace. Normal prepublication failures remove only
owned staging/locks. Process death leaves hidden staging/stale lock, never a
completed selectable bundle. Do not remove locks until confirming no owner runs.
On Windows only, transient access/sharing-denied rename failures retry the **atomic
no-replace filesystem operation** up to six attempts/1.5 seconds, with sanitized
retry events on stderr; target appearance immediately fails. Persistent denial
fails, and no backup creation/payment/mail operations are retried.
Publication succeeded but parent fsync/lock cleanup failed can report I/O failure
with an already fully verified bundle: inspect/verify rather than retry blindly.
Controller/power-loss durability and remote filesystem lock/rename/fsync semantics
require storage-specific testing. Do not use unreliable mounts as the only copy.

POSIX new directories 0700/files 0600 from creation; existing parent modes unchanged.
Use trusted restricted parent directories. Windows NTFS ACLs/inheritance are not
verified or managed; select and test restricted ACLs independently. Symlinks,
junctions/reparse points, special files, traversal, reserved Windows names and
case-colliding paths are rejected. Empty event subdirectories are not application
state and are omitted. Arbitrary hostile concurrent filesystem owners/root remain
outside the security boundary. File inventories/checksums are **not signatures**;
an attacker replacing files and metadata can forge a valid bundle. Protect metadata
or add independently managed trusted signatures (not implemented).

## CLI and isolated runbook

Repository: `python -m app.application_recovery`; image: `python
/app/application_recovery.py`. No application startup/import or migrations to inspect
bundles. Explicit paths avoid environment-default/wrong-installation selection.

```sh
# Only after operator-approved maintenance/drain of ALL writers:
python -m app.application_recovery backup \
  --database <source.db> --messages <runtime-messages.json> \
  --destination <private-backup-root> --deployment-id <installation-id> \
  --app-commit <exact-source-40-hex-commit> --quiesced

python -m app.application_recovery verify <completed-bundle>
python -m app.application_recovery status --destination <backup-root> \
  --deployment-id <installation-id> --max-age-seconds 86400

# Into an explicitly selected NONEXISTENT isolated root:
python -m app.application_recovery restore <completed-bundle> <isolated-root> \
  --expected-commit <known-compatible-source-commit> \
  --expected-schema <trusted-expected-schema-sha256>
```

Obtain compatibility values from independently preserved source release/schema
evidence; `verify` reports captured values, it does not authorize compatibility.
Restore requires exact commit and schema match; mismatches fail, there is no unsafe
override/migration. Source commit/image is operator attestation; code does not
authenticate supplied identity. Image digest is optional for non-container installs;
if supplied it must be digest-pinned, not `stable/latest`. Preserve exact code/image
and deployment inventory independently. Schema fingerprints are exact SQLite schema
definitions, intentionally conservative (different-but-equivalent SQL may reject).

Optional `--configuration <json>` accepts only string values for `DRINK_POS_ENV`,
`TZ`, `PAYMENT_PROVIDER`, `SUMUP_CURRENCY`, `SUMUP_TIMEOUT_SECONDS`. Unknown keys fail;
never provide `.env` or credentials. No config is automatically applied on restore.
Missing runtime messages fail unless `--allow-missing-messages` explicitly records
bundled-default-only recovery; invalid JSON objects fail rather than disappear.

Restore verifies marker/manifest/all files/SQLite **before** copying, then verifies
all copied bytes and logical state. It relocates only event_sessions CSV/PDF path
columns into `<isolated-root>/state/events`; normalized DB fingerprint proves all
other tables, audit details, IDs, triggers/indexes and sequence remain unchanged.
No invoices are regenerated. Event-table triggers are unsupported for relocation
and reject restore, rather than executing unknown side effects. `RECOVERED.json`
records output inventory/checksums, relocation count and compatibility metadata.
The restored DB need not be byte-identical after relocation; non-DB artifacts are.
Select `<isolated-root>/state/database.db` and messages for a *later separately
approved* startup; normal startup re-enables WAL. No automatic start, migration,
payment retry or invoice resend occurs. Existing destination (including symlink)
is always rejected. Isolated trusted parent with no unrelated writers required.
Recovery targets inside their source bundle are rejected before creating staging
or locks, so the immutable backup itself is never changed by restore.

JSON stdout describes success/status; JSON stderr is bounded/sanitized without
credentials/member contents. Exit codes: **0** verified/recovered/fresh status,
**1** filesystem I/O failure, **2** invalid/incompatible state or argparse usage,
**3** overlapping/interrupted operation lock, **4** missing/stale/corrupt backup
status, **130** interactive interruption. Crash/kill exit is platform-dependent.
Invocation start/end and exit should be captured by external automation. No content
or database rows are logged. Fingerprinting currently sorts encoded rows per table
in memory; time/memory grows with data. Measure limits before operational adoption.

## Scheduling, transport and monitoring

Existing Friday 03:00 Compose loops remain unchanged: live **DB-only EF-08a**,
same failure domain, no catch-up, no alert, timezone-dependent minute polling,
sleep after a failed attempt, permanently running scheduler. They do not create
EF-08b application bundles. Keep weekly DB backups if useful, but do not equate them
with complete-state/offsite recovery. Adoption of a maintenance schedule requires
separate operational approval; no mandatory scheduler is added.

Cron, systemd timer (`Persistent=true` for catch-up), container/NAS/other task
schedulers may invoke a maintenance wrapper with noninteractive CLI/exit codes.
The wrapper must drain/stop all writers, create/verify, report outcome and release
maintenance only after operator policy allows. Keep service control outside core.
External monitor separately calls `status` with agreed RPO/max age per deployment;
it verifies all candidate contents, detects missed intervals and stale locks, and
fails conservatively for invalid candidate directories. This is read-only; large
histories cost full verification. Invalid foreign candidates in a shared root
also cause attention because attribution cannot be trusted. Separate destinations
simplify monitoring. No external provider is needed for successful backup.

Replication is **not inferred from local creation**. Copy only completed verified
directories; upload/copy to destination staging, verify there, and publish/mark the
remote copy only after successful verification. Preserve original bundle basename.
Run remote `verify/status` after copying and periodic isolated restore. Track
replication last-success, destination age and restore-test age separately. Replication
tool owns retries (file copies only), credentials, transport and logs. No S3/NAS/cloud
API in core; optional future object storage needs its own narrow adapter contract.

- Use ordinary local persistent volumes or validated remote filesystems. Keep at
  least one independent failure-domain/offsite copy; same host/NAS is insufficient.
- Protect immutable copies via storage snapshots/object lock/write-protected account;
  source/admin compromise must not erase all copies. Metadata needs same protection.
- Encrypt sensitive bundles at rest and in transit (e.g. encrypted storage/archive,
  SSH/TLS replication). Core does **not** encrypt. Keys must be securely escrowed
  independently of backups and source, with access rotation and recovery rehearsal.
- Bundle DB includes member/financial/provider metadata and can include SMTP/PIN
  secrets from settings. Redaction would destroy exact recovery; restrict access.
  Environment secrets, encryption keys and release inventory need independent escrow.
- Application retention is deliberately absent/disabled. Existing opt-in EF-08a
  retention never selects these distinct bundles. Any future retention must be
  scoped to verified owned bundles, preserve unknown/staging/foreign copies and
  require independently verified surviving copies plus owner-approved deletion.

## External reconciliation — before approved activation

Keep recovered instance isolated/network-disabled. Establish snapshot time, compare
independent audit/receipts and provider records for post-snapshot transactions.
Review pending/unknown/cancelled payment sessions and IDs with provider evidence;
never charge/retry or mark debt paid based only on local uncertainty. Reconcile
browser queues and identifiers lost after the backup before reconnecting clients.
For invoices compare saved artifacts, event status and audit with delivery mailbox/
SMTP evidence; files or `invoice_mail_sent` are not exactly-once proof. Do not
blindly close active events, regenerate invoices or resend mail. Credentials should
remain disconnected until reconciliation and separate operator approval. Document
unresolved cases; invoice/SumUp side-effect redesign is not part of this package.

## Portable container example and evidence boundaries

`examples/compose.recovery.yaml` is optional, not a change to current deployments.
Named application/rehearsal volumes, external selectable backup volume, digest-pinned
image selection, separately selected config/secret env files, offline tools service:

```sh
# Config vars required by example; never use real files during CI/rehearsal.
docker compose -f examples/compose.recovery.yaml config --quiet
# After manually approved maintenance/drain (example only, NOT executed here):
docker compose -f examples/compose.recovery.yaml stop app
docker compose -f examples/compose.recovery.yaml run --rm recovery backup \
  --database /app/data/database.db --messages /app/data/messages.json \
  --destination /backups --deployment-id example --app-commit <source-commit> --quiesced
docker compose -f examples/compose.recovery.yaml run --rm recovery verify /backups/<bundle>
docker compose -f examples/compose.recovery.yaml run --rm recovery restore \
  /backups/<bundle> /rehearsal/new-isolated-root --expected-commit <commit> --expected-schema <hash>
```

Container synthetic CI stops only its owned original test container, runs image
tools network-disabled over disposable state, verifies generated CSV/PDF/messages,
normalized complete DB, restores into a new root, then restarts **original** synthetic
instance and verifies persistence. It never starts recovered data. Full unittests
cover all 16 operational tables in two independent paths/deployments and real
generated invoice bytes, failures/interruptions/overlap/security and EF-08a parity.
Local Windows POSIX and symlink-privilege evidence remains Linux CI's responsibility.
MV-06 remains **partially pending**: independently managed offsite/immutable encrypted
copy restore, storage-specific failures/ACLs, timed RPO/RTO, and operator acceptance/
external reconciliation drill require separately approved isolated operational work.
