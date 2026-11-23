# EF-08b ready gate — portable application recovery

Verified base: clean fetched main `b8cb4870d90f75b9dbc2668246788c5aa24ee8a5`
(2026-11-23). Requirements: DP-014, DP-010, DP-011, DP-013, DP-018/019.
This extends, and does not redefine, EF-08a database format version 1.

## Observed inventory and consistency boundary

| State | Recovery treatment |
| --- | --- |
| SQLite tables, financial snapshots/audit, payment/session/replay IDs, schema/indexes/triggers/views/sequence | Entire Backup API snapshot, integrity/FK checks; WAL/SHM are source implementation details, not restored sidecars |
| Event CSV/PDF in resolved DB-parent `events/` | Exact bytes of all regular files (including orphan files left by failed closure); DB-referenced files required |
| Runtime messages (override can be outside DB-parent) | Explicit selected path, relocated to `state/messages.json`; absence recorded only when default overrides do not exist |
| Settings, including SMTP password/PIN in SQLite | Preserved without redaction to retain DB semantics; bundle therefore contains secrets and requires sensitive storage |
| Non-secret recovery configuration | Explicit JSON allowlist, never `.env` or automatic environment dump; operator-supplied deployment ID, source application commit and optional image digest |
| Bundled UI/default messages/code | Preserve independently as the exact source/image; not copied into the bundle |
| Existing backups, logs, temporary files, pycache, unknown files outside events | Excluded; backup-of-backups prohibited; no other persistent runtime writes found in served code |
| Environment secrets, TLS/transport/encryption keys | Independent secure escrow; never captured automatically |
| SumUp terminal/provider and delivered/uncertain mail | External, not recoverable locally; mandatory reconciliation before approved startup |
| Browser queues/payment recovery IDs/cache | Client-only, excluded; pre-snapshot lost identifiers need independent reconciliation |

Served `admin_event_end` calls CSV → optional PDF → optional SMTP → DB update →
audit → commit. Files are directly written, not atomic. No DB write transaction
covers the earlier filesystem/mail period. Messages are seeded at startup and
edited externally. A DB lock or in-process lock would not coordinate all writers;
blocking around mail could also delay the app for network timeouts.

**Chosen boundary:** explicit operator-confirmed quiescence: stop all app processes,
drain event/payment work and stop message/artifact editors/importers before backup;
keep them stopped through completion. Core never stops/starts services. No online
consistency claim. A separate exclusive destination operation lock rejects overlap;
source DB logical fingerprint and full filesystem inventory/checksums before/after
copy detect observed changes and fail closed. These checks are not a proof against
transient/ABA changes or hostile writers; the maintenance precondition is essential.
No runtime handler, invoice delivery, schema migration or SumUp retry changes.

## Bounded contract and acceptance

- New, distinct application bundle format/version, UTC UUID ID and timestamps,
  source deployment/application/image identity, SQLite schema fingerprint and
  user/application versions. Explicit compatibility expectations at restore.
- Manifest inventories every payload file with size/SHA-256; completed marker
  binds the manifest hash. Only verified, atomically published directories qualify.
  Staging never qualifies. Verification rejects extra/missing files, malformed
  manifests, unsupported formats, unsafe portable paths, symlinks/reparse points
  and nonregular entries. Checksums are not signatures/authenticity.
- Ordinary filesystem-only creation/transport; no provider or scheduler dependency.
  No retention/deletion in application CLI. EF-08a CLIs remain available unchanged.
- Isolated explicitly selected **nonexistent** restore root. Serialize cooperating
  restore operations with exclusive lock, recheck target, stage privately on same
  filesystem, verify all files/SQLite before atomic publication. Linux renameat2
  RENAME_NOREPLACE/Windows rename reject even empty destination races; other
  OS/filesystems fail closed. Trusted parent with no hostile writers required.
- Restore rewrites only `event_sessions.csv_path/pdf_path` to the isolated root;
  immutable transaction details remain byte-for-byte logical history. Record that
  narrow relocation and output checksums in a recovery receipt. Never regenerate
  invoices, run app code/migrations, start a service, retry payments or send mail.
- CLI JSON results, nonzero distinct failures, verified age/status per deployment;
  offsite verification tracked separately by transport/operator, not inferred.
- Synthetic all-table rehearsal, real generated artifacts, two deployments,
  corruption/missing files, incompatible schema/version, traversal/symlinks,
  changed source, ordinary and abrupt interruption, overlap, permissions and legacy
  recovery. Full standard/browser/security/Linux-container gates required.

## Risks, exclusions and rollback

Maintenance duration scales with DB/artifacts (measure operational RTO/RPO later).
Source app metadata is operator attestation, not independently authenticated.
Storage must support reliable same-filesystem rename/exclusive create; remote
filesystems require their own validation. Private POSIX 0700/0600, existing parent
permissions unchanged; Windows ACLs require operator evidence. Power-loss durability
depends on storage and directory fsync availability. Abrupt death leaves unpublished
staging/stale lock; never automatically delete another operation's resources.
Rollback is removal of new tools/examples on this feature branch, not modifying
deployed state. No production config/image/digest or EF-08a consumer migration.
MV-06 operational offsite, operator acceptance, Windows ACL, actual RPO/RTO and
external reconciliation evidence remain explicitly open until separately rehearsed.
