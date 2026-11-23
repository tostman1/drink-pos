# RL-02 — ready gate, write inventory and bounded plan

Owner authorized implementation/tests/commits/push/open PR on 2026-11-23, **not
merge, deployment, publication, release or production access**. Clean fetched main
and local baseline `65d7a869854a15cfa5ef78c98153bc35306f629b`; exact-head CI
https://github.com/tostman1/drink-pos/actions/runs/45246034817 passed. Dedicated
`feature/rl-02-migration-safety`. DP-024 (new), DP-014/015/023 and financial
preservation DP-003..013. No agents delegated.

## Inventory before runtime edits

`main`/`app.main` → application copies legacy startup → legacy.init_db configures
schema globals → schema.init_db. Import itself reads configuration, not DB state.
Both connection factories open/create SQLite before applying FK/busy timeout.
The connection context closes but does not implicitly commit.

| Location / category | Frequency and risk |
| --- | --- |
| schema.init_db mkdir; messages.ensure_messages_file | Filesystem initialization, every start; missing catalog copied, errors swallowed, outside SQLite. Existing files not deliberately overwritten, but check/write race exists. |
| sqlite3.connect; journal_mode=WAL | DB/config initialization; file creation and journal/header/sidecars can persist independently of DML. FK and timeout are connection-local. |
| settings/people/items/all other CREATE; add_column_if_missing | Structure, intended once per missing object; implicit Python transaction does NOT start on DDL. Early DDL/ALTER persist independently. |
| migrate_people | Legacy data/repeated normalization; rewrites names and fills dates every start; UNIQUE conflicts possible. |
| ensure_default_people | Default initialization/repeated normalization; all-placeholder IDs renamed/reactivated; missing configured names inserted every start. Not pure idempotent historical adoption. |
| migrate_items | Prototype drinks import by missing name, retained source; current/default attributes, no verified release provenance. |
| ensure_default_items | Default initialization AND financial master-data backfill: zero product EK becomes positive configured default. Zero is ambiguous. |
| ensure_round_item | Repeated normalization/config: forces round active/admin, labels/price from setting, EK=0, unarchives. Potentially destructive. |
| migrate_old_orders | Legacy import while order_lines empty; positive quantities only, today's date/current price/EK, source retained. Can repeat if new lines later empty. Not factual old financial reconstruction. |
| backfill_missing_purchase_snapshots | Repeated financial backfill: zero order/detail EK gets current item EK; signed quantity × EK, profit=sales−cost; all round snapshots reset to zero/profit=sales. No provenance or completed marker. Valid zero indistinguishable from inferred default. |
| ensure_settings | Default/runtime config init; missing keys inserted, default admin PIN replaced from explicit environment. Repeated, configuration-sensitive. |
| ensure_indexes | Structure; unique payment-ID index can fail late. NULL IDs historically legal, duplicate non-NULL IDs unsafe. |
| commit/close | Only operations after first DML share implicit transaction; later DDL joins it. Late failure rolls those back, NOT prior filesystem/WAL/DDL. |

## Selected implementation (plan, not evidence of completion)

1. Write failing DP-024 regression tests. Add a small stdlib SQLite-native contract:
   one **new** baseline-establishment migration, not invented historical records.
   Recognize only the exact current schema fingerprint produced by verified synthetic
   current fixtures. Reject prototype/partial/extra/missing objects for strict adoption.
2. Separate opt-in `DRINK_POS_MIGRATION_MODE=versioned`, default `legacy` unchanged.
   Require explicit fresh-install permission and separate exact-fingerprint legacy
   adoption opt-in. Unknown policy values reject before writes. No deployment default.
3. Inspect existing DB using mode=ro/query_only within one read transaction, reject
   sidecars/WAL headers before opening (no immutable active-WAL evidence). Operator
   quiescence/checkpoint/clean rollback-journal snapshot is required for opt-in rollout.
4. After a positive decision only, acquire cooperating exclusive-create migration
   lock, open existing state mode=rw (never create missing state), BEGIN IMMEDIATE
   with no wait, and recheck prerequisites on that connection. Fresh file O_EXCL.
   Reuse original SQL/helpers inside explicit transaction through a tiny seam.
   Record completion/version atomically; verify schema/integrity/FKs before commit.
5. Keep all original normalizations for behavioral parity, but the opt-in path
   must **refuse before writes** when current startup would change financial costs.
   No new interpretation, correction or inferred history. Fresh empty state has
   no history. Existing legacy default remains unchanged; hazardous opt-in state
   requires owner decision, not an automatic conversion.
6. Run filesystem message initialization and WAL activation only after successful
   DB commit, isolated from atomicity claims. Failure there is not DB rollback.
   Subsequent strict starts require clean rollback-journal state, not active WAL.
7. Extend RL-01 inspection with verified ledger evidence without allowing unknown
   metadata or weakening isolated-bundle/sidecar/identity/config/key guards.
8. Inject schema/data/precommit/kill/lock/storage failures, repeat startup and use
   EF-08b new-target recovery. Run both Python matrices, full Standard Checks and
   actual non-publishing image/start/persistence/upgrade/recovery/DR CI.

## Risks / stop gates

No authentic historical artifacts established: synthetic fingerprints are NOT
universal release support. Exact SQL fingerprints conservatively reject equivalent
DDL and custom indexes/triggers. Strict mode is optional because mandatory adoption
would unexpectedly block legitimate installations. Active WAL/hot journal needs
operator recovery, never sidecar deletion or immutable reads. Lock death leaves a
stale lock requiring owner/process verification; abrupt SQLite transactions use
journal recovery before renewed read-only inspection. Filesystem/controller durability,
hostile directory-owner races, Windows ACLs and storage capacity remain operational
boundaries. No automatic retry, payment/mail/provider operation, reset or downgrade.
Financial-history OQ-06 stays unresolved despite green tests; future preservation
policy proposed: retain factual snapshots including zero, separate explicitly labelled
inference only after owner approval, never rewrite immutable originals.

## Bounded implementation decision superseding plan items 5–6

No existing-state normalization is invoked in strict mode: baseline adoption is
metadata-only, v1 repeat is read-only DB validation. This avoids any accounting
decision or preexisting-data writes rather than trying to infer safe financial
backfill predicates. Fresh initialization alone reuses all original helpers within
the transaction. Opt-in keeps DELETE journal mode; WAL activation is NOT implemented
there, allowing effective read-only repeat startup without immutable WAL reads.
Default legacy still runs original helpers/WAL. Tradeoff/rollout is explicit in
`docs/migration-safety.md`; this smaller seam is not a full historical migration
framework or v1→v2 transition. Nine initial DP-024 tests failed missing interface
before runtime changes; evidence and additional regressions follow in progress.
