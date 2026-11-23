# EF-08c ready gate — independent disaster recovery

Verified clean/fetched main `e8caeed029266764d5594c275ff769ccc7cf35c8`, base
CI `45171495944` passed. Owner approves branch/implementation/tests/commit/push/PR,
not merge, release, deployment or any real resources. Requirements DP-014/021,
DP-004/007/008/010/011/013/015/018/019; new DP-022 independent recovery evidence.

## Bounded architecture and acceptance (before implementation)

Preserve all EF-08a/b interfaces and bundle formats. Add a small optional one-shot
filesystem replica tool: verified EF-08b bundle → standard tar in private staging →
external **age** encryption → selected separate filesystem destination → decrypt
and verify independent bytes → atomic no-replace envelope publication. No crypto
implementation, provider abstractions, scheduler, runtime handler change or retention.
Age is an optional operator prerequisite, not in the application image. Pin official
age v1.3.2 tooling with SHA-256-verified downloads for reproducible Linux/Windows CI.
No secret key material in argv/output/Git; identity file path is not its contents.

Replica envelope has its own version, ciphertext/checksum/completion inventory and
non-sensitive backup/version/time identity. EF-08b inside is unchanged. Filesystem
and metadata are trusted/private; age detects encrypted-payload modification but
does not authenticate a sender. Verification decrypts into private isolated staging,
rejects unsafe/duplicate/nonregular tar entries and resource limits, then uses EF-08b
verification. Ciphertext-only hashing is not current decryption/recovery proof.
Ordinary failure removes owned staging only, abrupt death leaves attention markers.
Source bundle/keys cannot be inside replica destination; no existing target overwrite.
No immutable/offsite claims: permissions are restrictions, not WORM enforcement.

Minimal separate monitoring: sanitized optional operation journal, verification
timestamp/results, most recent creation/independent verification/rehearsal, age,
lock/staging attention, failed attempts, optional reliable `disk_usage` threshold.
Existing EF-08b status unchanged; no financial rows/secrets in logs. No deletion.

## Evidence required

- Failing regression tests before new behavior; real age synthetic keys in temp
  escrow independent from source/replica. Fail missing/wrong key and changed bytes.
- Full synthetic filesystem rehearsal proves recovery after deleting only its own
  source installation; exact normalized DB/schema/sequence/artifact parity.
- Actual local-only image CI starts fresh synthetic instance with network disabled,
  initializes representative debt/cashup/round/snapshot/payment/idempotency/event/
  messages state, confirms integrity, stops/drains all writers, creates bundle,
  encrypts/transfers/independently verifies, retains image/compatibility metadata
  and escrow outside source. Deletes owned source container/volume and local bundle.
- Recovery phase can access only independent replica/key/image/expected hashes,
  not source volume. Recover fresh root, verify normalized complete state and bytes,
  check synthetic reconciliation record (uncertain provider/payment/mail/offline/
  post-backup cases explicitly held, no automatic retries), then explicit fresh
  network-disabled startup with empty external credentials. Check readiness and
  unchanged financial/artifact IDs, restart/persistence as applicable.
- Machine-readable UTC timestamps and monotonic phase durations. Conservative RPO
  age uses backup **start** time, not publication time, at assumed loss. RTO loss→
  validated isolated startup; report recovery-only duration too. Targets are chosen
  test thresholds, not universal/production guarantees. Synthetic key/image retrieval
  is measured separately; real acquisition/reconciliation time remains unverified.
- Failure injection: missing/corrupt/incomplete replica, interrupt transfer/recovery,
  missing/wrong keys, invalid manifest/missing invoice/messages, version/schema
  mismatch, existing state/collision, unavailable/permission/ENOSPC storage, age,
  stale locks/staging. Never overwrite valid state or delete unknown resources.
- Mandatory full local and CI gates, actual image/Compose/startup/persistence/DR,
  vulnerability/browser/traceability; publication remains skipped.

## Boundaries, risks and rollback

Offline all-writer quiescence still essential. Exact image/schema/commit evidence
must be preserved independently; synthetic local Docker image archive rehearsal
does not prove access after remote registry/host loss. Protected metadata and key
escrow are operator responsibilities; wrong recipient encryption becomes unrecoverable
without corresponding identities. Private decrypted staging requires encrypted
scratch storage for at-rest confidentiality (ordinary unlink is not secure erase).
Same-host independent volumes simulate storage loss, not separate hardware/geography.
Linux/Windows atomic publication restrictions inherited; Windows ACLs unverified.
EF-08a intermittent Windows directory rename WinError 5 remains unresolved: report
any recurrence; no retries/suppression added to EF-08a or new operations. Existing
EF-08b bounded rename retry is inherited unchanged. Propose separate correction.
Rollback removes only new optional tools/examples; no production adoption/cleanup.
MV-06 automated encrypted independent-storage/loss/rebuild/timing evidence can
advance; real storage immutability/offsite/ACL/key/image retrieval/timed operator
external reconciliation and acceptance remain explicitly pending.
