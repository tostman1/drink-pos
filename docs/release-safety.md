# Release identity, preflight and controlled upgrade runbook (RL-01)

This is **optional offline tooling**, not a deployment approval or automatic gate
inside startup. Existing UI, REST metadata, Compose files, update scripts and timer
remain unchanged. See [verified baseline/risk inventory](rl-01-contract.md).
Do not run the old updater as a rehearsal: it pulls, recreates and prunes.

## What a release means

`python -B -m app.release_identity --commit <40-hex-actual-checkout-SHA>
--channel <explicit-channel> [--version <assigned-label>]` prints deterministic
JSON without importing the app, creating a database, using Git/network commands or
reading environment configuration. From the image use `/app/release_identity.py`.
There is no mandatory registry for local work. The commit argument is an assertion:
the operator/CI must verify it against a clean checkout or actual inspected image
APP_BUILD_COMMIT, never label unrelated source with a desired SHA.

| Identity component | Source checkout | Build | Publication / operator receipt |
| --- | --- | --- | --- |
| git_commit | Verify exact HEAD/clean tree separately | Existing BUILD_COMMIT/APP_BUILD_COMMIT unchanged | Must match image inspection and checked release tree |
| version | Explicit assigned human label, nullable if none | No fabricated product version or HTTP change | Owner chooses release naming/support policy |
| channel | Explicit label (local/verification/candidate/stable) | Existing BUILD_CHANNEL retained | A channel is not a compatibility rule |
| migration_code_sha256 | Hash of named startup dependencies, normalized LF | Same installed files hashed without importing them | Diagnostic binding, NOT a schema or complete executable/supply-chain hash |
| image_ref | null until independently known | Build cannot know its own eventual manifest digest | Exact `repository@sha256:<64 hex>` only after publication/inspection; caller supplies `--image-ref` |
| python | Current supported baseline 3.12/3.13 | Docker baseline 3.12 | Patch/native/SQLite/dependency compatibility also requires actual rehearsal |
| schema_version | null: no maintained ledger | Never manufacture a migration number | Existing PRAGMA user_version/application_id are observations, not authoritative versions |
| application_bundle_version | EF-08b v1 | Existing recovery interfaces unchanged | EF-08c v2 envelope is a DIFFERENT format, not DB migration version |

Schema identity is EF-08b `database.schema_sha256`: SHA-256 of ordered
`sqlite_master(type,name,tbl_name,sql)` JSON (including indexes, triggers, sequence
table). Exact schema text/order matters; logically equivalent CREATE statements
can differ. A match does **not** imply safe data migrations; a mismatch is not
automatically harmless/additive. No arbitrary upgrades or downgrades are supported
by RL-01. Short sha tags remain mutable. OCI manifest digest, local image config ID,
Git commit, archive checksum and schema hash are different identities.

Current gated publishing rebuilds separately from the tested image, uses mutable
base/dependencies and does not emit a signed retained compatibility/release receipt.
RL-01 does not claim reproducibility, artifact authenticity or published-digest
availability. No image/release was published. Future promotion of the exact tested
artifact/provenance is a separate decision, not implemented release automation.

## Explicit compatibility evidence

Preflight requires a completed, safely copied EF-08b whole-application bundle.
It verifies the complete DB/events/messages/configuration inventory plus SQLite
integrity/FKs and logical state. It accepts no loose DB path or installation
defaults. For EF-08c, first use its separate trusted full-key verifier in private
scratch to prepare an unchanged decrypted EF-08b bundle; preflight does not decrypt
or create scratch. Do not supply a restored/relocated root as an unchanged bundle.

The input directory must be a trusted **isolated offline copy**, free of all writers,
SQLite sidecars, symlinks/reparse points and external mutable mounts. The flag is an
operator attestation, not a lock or discovery mechanism. A copied main DB file from
an active WAL installation is NOT adequate. Use EF-08b's all-writer-quiesced backup
and SQLite Backup API snapshot; preserve complete installation separately.
Preflight checks rollback-journal header/absence of sidecars BEFORE any SQL opens.
Immutable reads are only used for that completed isolated snapshot. Never use
`immutable=1` on live WAL state. Trusted parents/read-only mount/permissions are
required: observed-change checks do not defeat hostile TOCTOU writers.

Prepare two identity JSON files and an independently reviewed evidence JSON object:

```json
{
  "format": "drink-pos-upgrade-evidence",
  "format_version": 1,
  "deployment_id": "operator-selected-installation-ID",
  "current_identity_sha256": "<canonical-full-current-identity-hash>",
  "candidate_identity_sha256": "<canonical-full-candidate-identity-hash>",
  "source_schema_sha256": "<verified-bundle-schema-hash>",
  "target_schema_sha256": "<explicit-reviewed-target-schema-hash>",
  "supported": true,
  "approved_by": "named-compatibility-reviewer",
  "permitted_changes": [],
  "candidate_configuration": {"DRINK_POS_ENV": "production", "SUMUP_CURRENCY": "EUR"},
  "target_python": "3.12",
  "secrets_recovery_verified": true,
  "encryption_required": true
}
```

This is a **template**, not usable compatibility evidence. Never copy `supported`
or secret attestation as true without a review. Canonical identity hash uses
`application_recovery.digest_json(identity)` (UTF-8, sorted keys, compact separators,
ensure_ascii=False). It binds version/channel/runtime/migration hash/image/commit
and all identity fields. Do not authorize wildcard schema/commit paths. The bundle
must match current commit/image and evidence installation ID. Candidate version,
schema, data changes and provider/mail configuration require explicit approval.
Unknown schema transitions fail closed, even if called additive. `permitted_changes`
is an operator-reviewed description, **not** an executable migration allowlist;
the rehearsal must implement independent exact state comparisons for each change.

Portable configuration is the EF-08b allowlist, not secrets, DB/message paths or a
complete Compose environment. Candidate must exactly match captured nonsecret
configuration; differences require intervention. Actual mount/path/secret/SMTP/
SumUp settings and conflicting env_file/inline/operator overrides need separate
review. Preflight never reads `.env` or private keys. Secrets recovery is trusted
attestation of independently available configuration/credentials, not a provider
probe. Production mode requires assigned versions and both exact image references;
local mode permits no image digest/no version but only approves a local rehearsal.

For required encryption, `--key-receipt` accepts protected JSON from EF-08c
`verify_replica` including exact backup/installation/commit/schema,
`verification_level=decrypted-application-verified`, independent/offsite scope,
named verifier, valid verification timestamp at/after bundle creation. This means
trusted full-key retrieval/decryption evidence, NOT transfer/hash completion. Old
ambiguous/local-only receipts fail. It is not a cryptographic signature, automatic
proof of geography/immutability, or current private-key availability; preserve and
validate actual ciphertext/envelope and escrow via EF-08c before approval. Preflight
does not inspect ciphertext or key material and must not be described as doing so.

```sh
python -B -m app.upgrade_preflight \
  --bundle /private-isolated-input/drink_pos_application_EXACT_COMPLETED_ID \
  --current /private-evidence/current.json \
  --candidate /private-evidence/candidate.json \
  --evidence /private-evidence/approved-compatibility.json \
  --key-receipt /private-evidence/full-independent-verification.json \
  --isolated-copy --mode production --max-backup-age-seconds 3600
```

All paths/policy are explicit. Run `-B`/PYTHONDONTWRITEBYTECODE=1; no output files,
startup, migrations, container commands, pull/publish, provider/mail operations,
deletion, bytecode cache writes by the command, or replacing targets. JSON is stdout,
sanitized codes contain no DB values/secrets/input paths. Exit codes:

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | rehearsal-ready | Evidence sufficient ONLY for separately approved isolated rehearsal |
| 3 | intervention-required | e.g. stale backup, configuration/runtime/secrets issue |
| 2 | unsafe | corrupt/incomplete/sidecar state, mutable/mismatched image, explicit unsupported path |
| 4 | unknown | unavailable/malformed identity/evidence/input or unapproved schema transition |
| 130 | unknown | interrupted CLI; no successful result |

CLI syntax errors use argparse exit 2; operational assessments are structured JSON.
Unsafe takes precedence over unknown, unknown over intervention; no nonzero status
is successful. There is no `--force` or deploy command. Successful input validation
cannot attest compatibility of the current LIVE installation after its snapshot;
write activity/configuration drift requires a new boundary/backup/review.

## Synthetic rehearsal and migration evidence

`python -B scripts/upgrade_rehearsal.py --target <new-disposable-root>
--commit <candidate-SHA> --synthetic-only` runs a fresh subprocess with inherited
Drink-POS/SumUp/SMTP/build config cleared. Existing targets refused, no live inputs,
no old images. The actual candidate application seeds debt/current tally, rounds,
cashup/paid/unknown provider IDs/idempotency/history/event CSV/PDF/messages, then
creates explicitly synthetic zero-cost/pre-feature-like rows. Source identity is
the candidate's code plus synthetic historical state, **not an authentic old release**.
It verifies a complete bundle/preflight, restores a disposable candidate copy,
executes actual assembled startup handlers, tests in-memory ASGI debt/event/health
GETs, checks full schema/sequence/all-table state against independent permitted
purchase-cost SQL expectations, repeated startup, artifacts/unknown payment hold,
integrity/FKs/WAL and restores pre-upgrade state to a second nonexistent target.
Network socket connections are blocked; only Windows event-loop self-pipe creation
precedes the application network guard. HTTP runs in memory, no listening server.
RESULT.json/PREFLIGHT.json and failed synthetic roots are retained for inspection;
no cleanup/deployment is performed. Runtime/dev dependencies are not added.

`UpgradeMigrationTests` additionally characterize the oldest supported-by-code
prototype tables (not verified released fixtures), name/default normalization,
current-price/date import, repeated cost backfill, late duplicate payment-index
failure, partial early DDL vs rolled-back DML and abrupt process exit 37. Full
snapshot recovery restores exact pre-upgrade state elsewhere after interruption.
RL-01 leaves schema.py unchanged: every normal startup still can modify state
before validation. Guarded CREATE/ALTER, FK/WAL and green health do not establish
whole-startup transactionality, arbitrary compatibility, reversible migrations or
unchanging financial cost/profit history. RL-02 should introduce a separately
reviewed versioned/transactional migration plan and pre-write compatibility gate.

## Controlled deployment (guidance only; no commands executed)

1. Inventory operator-managed app AND backup containers, exact Git/image digest,
   image config/archive, configuration/secrets, DB path/mounts/messages/events,
   all writers/schedules and client queues. Preserve known-good references and
   independently verified source/key/image escrow. Do not infer deployed settings
   from this repository. Each installation gets separate evidence/roots/volume.
2. Obtain candidate image through a separately authorized acquisition/publication;
   validate digest/commit/platform/identity and CI. Preserve previous image/archive.
   Pulling is NOT performed by preflight. Keep image cleanup disabled.
3. Schedule explicit maintenance; drain/block all writers, backup jobs/editors/imports
   and business/provider activity. Prepare full EF-08b bundle and separate EF-08c
   verification/key-recovery evidence, retain configuration/secrets/images. Verify
   backup and age/RPO policy. Protect storage/Windows ACLs independently.
4. Run read-only preflight against isolated copy. Any nonzero result stops upgrade.
   Obtain compatibility review; rehearse candidate on disposable state with outbound
   network disabled and independently compare all business/state changes. Production
   schemas not covered by these synthetic tests need their own rehearsal decision.
5. Only with separate owner authorization, controlled replacement using exact
   previously acquired digest and explicitly reviewed state/config. Optional
   `examples/compose.upgrade.yaml` requires all inputs, pull_policy never, external
   state volume, loopback bind and restart=no. It is NOT a drop-in Synology config;
   pinning is validated by preflight/operator, Compose cannot regex-enforce digest.
   No backup scheduler/orphan removal/pruning/retry controller is included.
6. Keep traffic/writers held during startup. Check logs/exit/health/startup timeout,
   candidate commit/digest/DB identity, integrity/FKs/schema and complete financial/
   operational/artifact state. Health alone does not approve state. Detect container
   failure or unexpected migration changes; hold uncertainty rather than retrying
   payment/mail or repeatedly restarting an incompatible migration. Release traffic
   only after explicit acceptance; record final release/evidence references.

Old Podman scripts remain backward compatible but **unsafe for unattended upgrades**.
Their safer successor should be separately opt-in, require approved digest/bundle/
rehearsal, check every native exit, recreate only selected services after approval,
verify health/state and retain prior images. Do not activate/edit systemd schedules
or assume managed files match templates. No default prune was added in RL-01;
existing default prune remains a documented risk, NOT endorsed safe behavior.

## Rollback is not one operation

- Image reversion changes code only. It never rolls back SQLite, invoices/messages,
  configuration, startup writes or provider activity. Never start older code on
  newer/partially migrated state without a specific compatibility decision.
- Configuration reversion restores exact recorded configuration/secrets separately;
  it does not restore DB or undo provider/mail effects.
- State recovery uses EF-08a/b/c verified **pre-upgrade** DB/filesystem snapshot into
  a separate nonexistent target, preserving damaged/current state and sidecars for
  investigation. EF-08b permits event-path relocation only; no migrations/startup.
- After migration failure: hold all writers, retain failed state/logs, verify bundle
  and independent key/image/config availability; use EF-08c full verification and
  isolated recovery or EF-08b verified restore. Compare recovered complete state,
  bind the exact pre-upgrade compatible image, and obtain approval before startup.
  See [application recovery](application-recovery.md) and
  [disaster recovery](disaster-recovery.md). No overwrite/delete rollback commands.
- Transactions/provider completions/mail/browser writes after snapshot are NOT
  recovered automatically. Inventory/reconcile them under human approval: unknown
  card sessions held/no blind retry, invoices/mail held/no resend, booking queues
  held/no replay until deduplicated. Do not reverse financial audit transactions.
  Restoring snapshot loses post-boundary activity unless separately reconciled.

## Remaining release decisions

Owner approval/merge/release protection, supported version/channel/upgrade policy,
authentic historical release fixtures, migration ledger/transactions/zero-cost
history treatment, tested-image promotion/digest+provenance receipt, independent
operator-managed update adoption and actual MV-06 key/storage/RPO/RTO/business
reconciliation acceptance remain unresolved. Recommend **RL-02 — Versioned
Migration Contract & Pre-write Startup Gate**, first characterization/decision,
then one schema transition; not a general deployment orchestrator or financial rewrite.
