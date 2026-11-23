# EF-08c — independent encrypted disaster recovery

Scope/acceptance: [ready gate](ef-08c-contract.md). This complements, not replaces,
[EF-08b application recovery](application-recovery.md). No deployed configurations,
image digests, application handlers or EF-08a/b formats change.

## Architecture and lifecycle

```text
quiesced source -> EF-08b verified bundle -> private standard tar staging
  -> external age encryption -> independent filesystem staging
  -> decrypt destination bytes + full EF-08b verification -> no-replace publication
  -> transport/protect externally -> periodic independent verification receipt
  -> source loss -> independent key + compatible image retrieval
  -> decrypt/verify -> isolated EF-08b restore -> reconciliation -> approved startup
```

`app/independent_recovery.py` is an optional one-shot filesystem adapter for native
age X25519 recipients. The standard EF-08b bundle is unchanged inside standard tar;
the external mature age implementation handles encryption/authenticated decryption.
No custom cryptography, provider interfaces, network APIs, retention, scheduler or
mandatory monitoring server. Age is **not** embedded in the Drink-POS image.

An encrypted replica directory `<backup-id>.replica/` contains exactly:
`payload.tar.age`, `replica.json`, `COMPLETED.json`. Separate envelope version 1
records public backup ID/deployment/commit/schema/times and ciphertext size/SHA-256.
It intentionally does not expose rows/member details, source paths or keys. The
timestamp/identity metadata is sensitive operational information and **not signed**.
Completion requires decrypting from destination bytes and verifying complete inner
DB/artifacts. Missing/wrong identity or recipient mismatch fails before publication.
Envelope is never an EF-08b bundle; decrypt it before ordinary EF-08b inspection.

Encryption protects confidentiality of payload at rest/in transport against parties
without the identity. Age authenticated decryption detects changed encrypted bytes;
public-key encryption does **not authenticate the sender**, nor authenticate public
envelope metadata. Protected independent metadata/expected hashes or separate trusted
signatures remain necessary against malicious replacement. Checksums alone cannot
provide authenticity. Private permissions are **not immutable/WORM storage**.

Creation/replication/verification/recovery/monitoring remain distinct. Only completed
replica directories qualify; no copy-on-name-only success. Interrupted copies lack
matching inventory/marker and fail inspection. Normal failures clean owned staging;
process death leaves stale lock/hidden staging. Never delete others' staging/locks
or unknown files; confirm ownership/process state before any separately approved
cleanup. No retention/deletion implemented. Shared write authorities can still
delete all backups; use independently controlled protected/immutable copies with
actual enforced retention, not just chmod/read-only flags, before production adoption.

## Tooling and portable examples

Install a trusted official age binary (example tested v1.3.2). Repository helper
`python scripts/install_age.py --destination <new-tool-dir>` verifies pinned official
release SHA-256 for Linux amd64/Windows amd64 and extracts only age/age-keygen.
It is reproducible-download integrity, not a complete supply-chain signature proof.
Other supported age platforms may be installed independently; EF-08b publication
currently supports Linux/Windows only and fails closed elsewhere. No automatic tool
installation in backup CLI; missing executable is a nonzero failure.

```sh
# Trusted private offline escrow; NEVER log this key or keep it in the image/Git.
age-keygen > <separate-private-escrow>/identity.txt
age-keygen -y <separate-private-escrow>/identity.txt
# Public recipient is the resulting age1... string. Backups need no secret in argv.

# First create EF-08b bundle after stopping/draining ALL writers (see that runbook).
python -m app.independent_recovery --age <trusted-age> --journal <private-journal> \
  replicate <completed-application-bundle> <independent-filesystem-root> \
  --recipient <age1-recipient> --identity <separate-private-escrow>/identity.txt \
  --scratch <private-encrypted-scratch>

python -m app.independent_recovery --journal <private-journal> verify <replica> \
  --identity <separate-private-escrow>/identity.txt --scratch <private-encrypted-scratch>
python -m app.independent_recovery --journal <private-journal> status <replica> \
  --max-age-seconds 86400 --max-verify-age-seconds 86400 --max-used-percent 90
python -m app.independent_recovery --journal <private-journal> recover <replica> \
  <explicit-new-isolated-root> --identity <separate-private-escrow>/identity.txt \
  --scratch <private-encrypted-scratch> --expected-commit <trusted-commit> \
  --expected-schema <trusted-schema-sha256>
```

All source/replica/scratch/escrow/recovery/journal roots must be nonoverlapping;
existing recovered state always rejected. Private trust boundaries still required:
checks are not protection against root/hostile directory owner races. The adapter
decrypts before safe manual tar entry copying (no `extractall`, links, sparse/special
files, duplicates, traversal or unbounded inventory). Limits: 20 GiB unpacked,
100,000 entries, external age execution 20-minute timeout. These are implementation
limits, not capacity planning. Decryption output is private scratch; use encrypted
scratch volumes for confidentiality on disk. Deleting temporary files does **not**
securely erase SSD/controller copies. Windows ACLs must be selected/verified by
operator; POSIX newly created dirs/files 0700/0600. EF-08b no-replace rename and
filesystem/hardware fsync durability boundaries apply unchanged.

For network transfer, copy **encrypted** completed envelope bytes using established
tools (SSH/SFTP/rsync over SSH, TLS-secured service, offline removable media).
Authenticate destination/transport, use separate copying accounts and atomic remote
staging, then inspect and **decrypt-verify at that destination**. Encryption does not
provide transport endpoint authentication or ensure geographic separation. Plaintext
tar is local scratch only. No NAS/cloud API or automatic network copying in core.
External tools may copy envelope or EF-08b bundles with their own at-rest encryption;
this adapter is an optional example, not a required proprietary archive platform.

Generic container layout stays `examples/compose.recovery.yaml`: persistent app
volume, external backup volume, separate rehearsal volume and protected config/
secret files. Run backup tools only during approved maintenance, network-disabled.
Use the adapter on an operator host with age and an independent filesystem root.
Reconstruct a fresh container with the independently preserved **exact image digest**,
new persistent volume, explicit recovered DB/messages paths. Preserve digest-pinned
image archive, commit/schema inventory and configuration separately (encrypted where
sensitive), and verify image archive hashes before `docker image load`. Never switch
existing production volumes/images merely to try these examples. No production
Compose/image/runtime dependency change is included in EF-08c.

## Key escrow and loss of original credentials

Keep recipient/public metadata available to backup automation; private identity is
separate secure escrow with independently controlled access, preferably offline or
another failure domain. This example checks recoverability using a selected private
identity during publication; separate read-only verification host can hold escrow
instead. Never expose identity contents in command line/logs. POSIX identity permissions
must have no group/world access. Windows ACL verification remains manual. Protect
key retrieval procedures, spare identities/rotation, access approvals and trusted
compatible images independently of original system and backup data. Lose every
matching identity and encrypted data is unrecoverable. Wrong/missing keys fail closed.
Synthetic keys are random and disposable; no real credentials in tests/CI.

## Monitoring and exit reference

CLI JSON success/stdout and sanitized failure/stderr; no raw tool stderr, exceptions,
credentials or financial content. Codes: 0 success, 1 I/O/tool unavailable, 2 invalid/
incompatible/decryption failure, 3 operation lock, 4 status attention, 5 ENOSPC,
130 interruption. Scheduler owns invocation/timeouts/alerts and captures exit code;
never infer successful offsite replication from local EF-08b creation.

Optional explicit journal stores private per-operation start/success/failure events
with UTC, operation ID, checksum and duration. `status` reports backup creation,
replication time, last matching encrypted-byte full-verification receipt, backup/
verification age, successful rehearsal timestamp, recorded failures, unfinished
operations, locks/hidden staging and `disk_usage` used-percent threshold where
measurable. Invalid metadata/unavailable capacity causes attention. Full `verify`
decrypts again; `status` only hashes current ciphertext and checks **historical**
matching decryption receipt, not current key availability. Journal must be retained
and protected; no journal/no verification receipt means attention, not success.
All recorded historical failures remain visible; acknowledge externally, don't erase
evidence to produce green. Capacity measurement is the selected mount's reported
filesystem, not remote quotas/object-storage/global guarantees. Replica/verification
state is per explicit replica; external automation selects newest/expected backup.

## Complete installation-loss rehearsal and measurements

`python scripts/disaster_rehearsal.py --image <local-verified-image> --expected-commit
<commit>` requires Docker/age/age-keygen. Only UUID-owned disposable resources,
`--pull=never` and network-disabled containers. Creates synthetic member/product,
price snapshots/debt, round deduction/payment/cashup/audit, offline IDs, local
synthetic paid/unknown SumUp correlation, event invoice/message state. Verifies
schema/index/trigger/sequence, quiesces, creates EF-08b, independently encrypts/
verifies, retains keys/image archive/expected evidence separately. Removes original
container/source volume/local plaintext bundle. Recovery can access only independent
replica/escrow/image, reconstructs new storage, verifies full normalized state and
every artifact. Explicit synthetic reconciliation holds below gate startup; fresh
network-disabled startup asserts no network attempts and state invariants.

JSON reports start/end/failure UTC, each monotonic phase duration, backup/verification
timestamps, conservative **RPO age = assumed loss − backup start**, **RTO = loss
through validated isolated startup**, and decryption/recovery/startup/key-image
retrieval durations. Test target defaults RPO 3600s/RTO 300s are chosen CI bounds,
not product SLA. Target failures are nonzero. Actual test metrics depend on machine/
data size and include validation work. Real key/image acquisition and external
reconciliation durations are **null/unverified**, not assumed zero. No universal
production RPO/RTO promise. Offsite latency/bandwidth, approvals and source data
growth need a separate timed operational acceptance run.

## Operator acceptance and financial reconciliation checklist

- [ ] Identify exact backup/source snapshot time, independently verified copy,
  compatible trusted commit/schema/image and functioning escrow, without source access.
- [ ] Verify actual geographic/hardware failure separation and **enforced** immutable
  backup/metadata retention where claimed; test deletion resistance with proper roles.
- [ ] Verify restricted ACLs, encrypted scratch/storage/transport, recipient/key
  separation and retrieval when original credentials are unavailable.
- [ ] Restore to new isolated state only; record full integrity/FK/schema/audit/file
  evidence and elapsed RPO/RTO, retrieval and reconciliation separately.
- [ ] Uncertain card sessions/provider IDs: compare independent synthetic/provider
  receipts/status, hold uncertainty. Never create/retry a charge or mark debt paid
  merely because local state is unknown. No automatic payment remediation.
- [ ] Post-snapshot committed bookings/payments: independent audit/receipts identify
  loss window; do not blindly replay or bypass immutable audit/idempotency history.
- [ ] Browser queues/payment IDs are client-only; review lost server identifiers
  before clients reconnect or replay. Synthetic drill holds post-backup operations.
- [ ] Invoices near boundary: preserve exact files, event flags and audit; compare
  delivery mailbox/SMTP receipts. File existence/DB flags alone cannot prove mail
  delivery/exactly-once outcome. Hold unknown mail, no resend/regeneration.
- [ ] Only after reconciliation approval, start compatible isolated app; production
  activation, credentials and deployment are separate authorization.

## Evidence limits and Windows finding

Synthetic independent directories/volumes prove source-storage unavailability during
recovery, encryption/key failure handling and compatible reconstruction. They are
**not** geographically remote copies, independent hardware, real storage durability,
immutable enforcement, or human operator acceptance. MV-06 advances only for directly
executed automated evidence; those operational checks remain pending.

EF-08a intermittent Windows directory rename `WinError 5` remains unresolved (PR #4
integration receipt includes failure then successful check rerun). New adapter
inherits EF-08b tested no-replace publication, including its existing Windows-only
bounded atomic-rename retry; no new retry/suppression added. Proposed separate narrow
follow-up: reproduce EF-08a handle/indexer/ACL failure under disposable tests, define
filesystem-only bounded correction and fail-closed evidence before any code change.
Do not infer resolution from green Linux CI or a successful rerun.
