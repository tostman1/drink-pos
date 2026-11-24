# RL-02 — implemented migration contract and opt-in startup gate

## Deliberately bounded rollout

**Default `legacy` startup is unchanged.** It still enables WAL, runs all existing
helpers, and may rewrite historical zero purchase-cost/profit snapshots. RL-02
does not approve that accounting interpretation or silently change every deployed
installation. No production migration/deployment/updater activation is included.

`DRINK_POS_MIGRATION_MODE=versioned` selects the separate contract. It is NOT a
drop-in mandatory upgrade: strict mode requires clean rollback-journal SQLite,
exact schema recognition and explicit adoption. It uses SQLite DELETE journal
mode (fresh SQLite default); existing WAL state is rejected before SQL opens.
Journal-mode concurrency/performance is an opt-in operational tradeoff requiring
isolated rehearsal. Normal request connection FK/busy-timeout semantics remain.
Do not remove the flag to bypass failed metadata checks or start older code on
versioned state: legacy/older code does not enforce this ledger.

## State machine and supported transitions

| Observed state | Decision / implemented transition |
| --- | --- |
| Path absent, no sidecars | `fresh-permission-required`; only explicit `DRINK_POS_ALLOW_FRESH=1` permits authoritative initialization → v1 |
| Exact recognized current application schema; user_version/application_id=0; no ledger | `recognized-unversioned`; only explicit `DRINK_POS_ADOPT_LEGACY=1` permits **metadata-only** adoption → v1 |
| Exact application + ledger definitions, complete matching v1 record, PRAGMAs consistent | `versioned-current`; verify and start, **no migration or normalization repeated** |
| user_version > 1 | `future-version`; reject, no downgrade |
| Missing/contradictory/empty/unknown-ID/checksum/incomplete ledger, foreign application ID | Non-success; reject, never manufacture old records |
| Unknown/equivalent-but-different schema, custom object, prototype, partial/empty existing file | Non-success; no initialization/reset/automatic import |
| WAL header or any -wal/-shm/-journal file, including orphan sidecars without main DB | `recovery-required`; no SQL opens, preserve evidence |
| Corruption/FK violation, inaccessible path, concurrent observed change, links/reparse points | Non-success; preserve state and investigate |

No v1→v2 business/schema upgrade is implemented or claimed. The single ordered ID
`0001-establish-current-baseline` establishes a **new** contract, not fictional
historical execution. Source version 0 means unversioned recognized schema or fresh
absence, not a supported historical release number.

## Ledger / authority

SQLite `PRAGMA user_version=1`, `PRAGMA application_id=0x44504F53` and the exact
`schema_migrations` table/row must agree. None is authoritative alone. One row:

- target_version=1, source_version=0, ordered migration_id above;
- checksum: SHA-256 of frozen ID, recognized schema and exact ledger DDL;
- source_schema_sha256: exact current fingerprint for adoption, empty only fresh;
- target_schema_sha256: exact application fingerprint (ledger objects excluded);
- kind=`initialize` or `adopt`, actual timezone-aware completion timestamp.

Only complete records commit. There is no persisted `running`/failed record that
can be mistaken for completion; transaction failure leaves old metadata. The
filesystem lock/hot journal can identify interrupted execution. Unknown ledger
objects/rows/IDs/checksums/timestamps reject. Checksums are integrity evidence,
**not authenticity** or hash of all executed initialization/helper code. RL-01
release identity separately hashes named migration dependencies including the new
module. A future migration needs its own reviewed frozen ID/checksum/transition.

Recognized exact schema fingerprint:
`090ea55aa19289c833f2010950722d4eb443c1b567068cbdc04217e1a25256a2`.
It is SHA-256 of ordered sqlite_master(type,name,tbl_name,sql), canonical JSON,
including indexes/sequence, excluding only ledger objects. Verified synthetic
current schema from baseline `65d7a869854a15cfa5ef78c98153bc35306f629b`;
**no authentic published historical artifact has been verified**. Standard fixtures,
fresh initialization and actual image rehearsal independently reproduce it.
Custom audit triggers/indexes, missing payment index, equivalent SQL spelling and
prototype tables deliberately fail strict adoption. No universal release support.

## Read-only gate and execution boundary

`python -B -m app.db.migrations <explicit-state.db>` (image: `python -B -m
db.migrations <explicit-state.db>`) prints sanitized state/version/evidence JSON,
deployment_authorized=false. Exit 0 means recognized schema or valid ledger only,
NOT authorized migration/rehearsal/deployment; other states exit 2. No runtime or
environment-default DB discovery/import, no files created, no repair, no providers.

Before any write, guard explicit path/parents, sidecars and rollback-journal header;
open `mode=ro`, query_only/trusted_schema=OFF, BEGIN read transaction and verify
integrity/FKs/exact schema/ledger. No immutable reads. Observe size/mtime/identity
and recheck sidecars after read; trusted quiesced parent/storage remains necessary
(not hostile-directory-owner or arbitrary active-writer consistency proof).

Only after positive permission/compatibility: create parent if fresh, exclusive
0600 `<db>.migration-lock`, fsync PID, re-inspect. Existing SQLite opens `mode=rw`
so disappearance never creates replacement; fresh uses O_EXCL 0600. BEGIN IMMEDIATE,
timeout 0 rejects concurrent SQLite writers, recheck prerequisites inside transaction.
Fresh authoritative SQL/helpers execute without their old WAL/files/commit side
effects. Adoption executes **only ledger DDL/DML/PRAGMAs**, never business tables.
Verify exact target schema/full integrity/FKs/ledger before COMMIT. Rollback on
Python errors/interruptions; no retries. Ordinary cleanup removes only owned lock.

Valid v1 repeat startup is inspection-only for SQLite. Optional message initialization
runs **after** success/commit via unchanged helper (bundled defaults if I/O fails).
It remains outside SQLite atomicity and retains its old check/write race. WAL is
never enabled in the opt-in path. No financial/table/default normalization on repeat.

## Financial preservation: findings, not approved accounting policy

Legacy backfill predicate is zero/current item EK>0, not row provenance. It updates
order_lines.unit_purchase_price_eur, transaction_items.unit_purchase_price_eur,
purchase_total_eur and profit_eur; signed quantities are multiplied by current EK.
Nonzero snapshots are usually retained, but round-name/item-ID rows are unconditionally
reset to zero cost/profit=sales. Default product zero EK becomes configured default,
round product cost is forced zero/active/unarchived. Prototype positive orders use
current date/prices/EK; originals retained but this is inferred, not old evidence.

**Implemented preservation**: existing strict adoption/repeat never invokes these
helpers or changes historical/master financial data, including ambiguous zeros,
nonzero round snapshots, signed transaction details, payments, audit, debt and
sequences. Fresh initialization retains original defaults/calculations with no
preexisting history. No approved cost calculation rule is introduced. Missing
defaults/normalization in an adopted installation remain as found; runtime setters
and current booking/payment calculations remain unchanged. OQ-06 is still open.

**Proposal only**: retain all factual snapshots including zero; represent inferred
costs separately with provenance after explicit owner decision. No in-place history
repair or automatic old-prototype import is authorized/implemented in strict mode.

## Recovery and rollout prerequisites

1. Obtain separate operator approval, identify all writers/config/images/secrets/
   artifacts/queues. Stop/drain all writers; preserve exact DB AND sidecars before
   recovery. Never delete WAL/journal files merely to pass the gate.
2. Resolve journal/WAL recovery using SQLite and verified EF-08b/EF-08c procedures
   on isolated copies. Explicitly checkpoint/close/prepare clean DELETE-journal
   state for strict rollout; not performed by gate. Verify integrity/FKs/full state.
3. Create/verify EF-08b all-writer-quiesced bundle and independent EF-08c recovery
   evidence. Run unchanged isolated RL-01 preflight rules and a separately approved
   synthetic/installation-specific rehearsal. Strict extra-schema rejection requires
   its own fingerprint/path review, never dropping production audit objects.
4. Only with separate activation authorization select versioned mode and exact
   adoption flag. Remove fresh/adoption permissions after completion. Keep writers
   held until ledger/state/API/artifact/financial acceptance. No automatic upgrades.

Failure before decision/first-write leaves all state untouched. After permission,
new dirs/lock/empty fresh DB can remain independently of rolled-back SQLite; fresh
failure can leave zero-length or schema-empty file that is NOT fresh on next run.
Process kill before commit leaves hot journal/stale lock, no completed ledger; gate
refuses until explicit recovery. Ordinary lock cleanup failure after commit can
report failure with completed DB: inspect, don't blindly rerun. Prove no lock owner
runs before any separately authorized lock cleanup. No automatic deletion/reset.

Restore pre-migration EF-08b bundle into an **independent nonexistent root**, verify
all tables/sequence/schema and exact artifacts with bounded event-path relocation;
preserve failed original. Binding compatible image/code is separate. Image-only
downgrade is NOT DB rollback. Post-snapshot payment/mail/transactions/client queues
require human reconciliation, no payment retry/reversal/invoice resend. Controller/
power-loss fsync/locks/remote storage/capacity and Windows ACLs need operational proof.

## Evidence and limits

DP-024 deterministic tests cover fresh/current/missing ledger/valid/future/unknown/
prototype/partial/corrupt states, NULL and duplicate payment IDs, active WAL/journal,
DDL/data/precommit exceptions, abrupt exit 37, actual two-process migration contention,
existing SQLite writer, storage/permission faults and separate EF-08b recovery.
Real ENOSPC is **simulated**; no disk filling. POSIX read-only permission exercised
on Linux non-root; Windows ACL not inferred. Original legacy risk tests remain.
Served financial regressions run additionally under versioned fresh startup;
actual image rehearsal verifies all original tables, costs/zero snapshots/API/repeat/
independent recovery with network disabled. Full image/start/restart/DR gates remain.
Results/exact final SHA/CI receipts are in progress/handoff and PR, not assumed here.

### Recommended next bounded package (proposal only)

RL-03 owner-authorized decision package now documents the source-only compatibility
inventory and proposed A/B/C financial policy in `financial-history-policy.md` /
`legacy-adoption-inventory.md`. No option approved, no extra adoption fingerprint
implemented. **Important scope clarification:** strict adoption/repeat preserves DB
values at startup, but served `admin_update_drink` still rewrites historical zero
costs/profit in either mode. Exact preservation of all future API writes requires
a separately approved financial change, not merely the RL-02 flag.

RL-03: explicit owner decision for preservation of zero/nonzero round snapshots and
prototype inference; inventory only sanitized schema metadata or independently
authorized historical artifacts; approve one additional exact legacy fingerprint
and metadata-only adoption fixture if warranted. Prove an actual required v1→v2
transition with its own failing regression/atomicity/recovery contract only after
that policy. Do not manufacture a dummy accounting migration or turn this optional
gate into mandatory deployment orchestration. Tested-artifact promotion/provenance
and EF-08a Windows publication reliability can be separately bounded packages.
