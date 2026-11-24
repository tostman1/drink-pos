# RL-03 — legacy schema compatibility and provenance inventory

Evidence date 2026-11-23; fixed reachable main baseline
`33c16979d2ae17a5d53c118c7f173f324e02e75b`. **Inventory, not new support.**
Policy proposal: [financial-history-policy.md](financial-history-policy.md).

## Sources inspected and authentication limits

- `git fetch origin`, `git ls-remote origin refs/heads/main` and local/fetched main
  agree on baseline; full local ancestry (`--is-shallow-repository=false`). 113
  commits reachable from this baseline, including merged feature ancestors.
- Only allowlisted `app/main.py`, `app/legacy_main.py`, `app/db/schema.py` Python
  blobs were read for schema derivation. Source commit/blob identifiers establish
  repository content/ancestry, **not signed releases or deployed DB provenance**.
  No old runtime DB, member records, messages, financial files or secrets were read.
- `git tag -n`, GitHub `GET /repos/tostman1/drink-pos/tags` and `/releases` returned
  empty lists. No tagged/published GitHub release artifact was available there.
- GitHub `/actions/artifacts` reported **8 unexpired `.dockerbuild` records** at
  commits `052c2bb`, `250a4e6`, `c3a78cd`, `fb08128`, `53eff93`, `4fdf277`,
  `1cb4763`, `04b9cdd`. These names/metadata were inspected only; contents were not
  downloaded/authenticated. A build record is **not** a retained runnable image,
  historical database fixture or signed digest/compatibility receipt.
- Registry contents/deployed images and real installations were **not inspected**;
  published historical images may exist, but no authentic immutable release image
  was verified here. Do not claim global absence merely from empty GitHub releases.
- Existing RL-01/02/recovery tests use synthetic data. Their success demonstrates
  bounded code behavior, not authenticity of any historical release/database.

**Authenticated historical DB sources: none established.** Known pre-EK claims are
not authenticated: the oldest reachable source `1ea2442` already contains all EK
snapshot fields, default backfills and prototype-import helpers. Helper comments and
minimal synthetic `drinks/orders` tests do not prove a prior release existed, its
schema, its cost interpretation, import totals or whether it was deployed.

## Independent metadata derivation

`python -B scripts/financial_schema_inventory.py` requires the exact baseline in
non-shallow local Git. It outputs JSON to stdout, opens **only in-memory SQLite**,
does not import/eval/exec historical code, run startup/normalization, open DB paths,
fetch network, change Git or add support. It extracts ordered literal CREATE TABLE,
missing-column definitions and indexes from initializer/ensure_indexes AST.
The extractor supports this observed idiom only; it is not a general migration
interpreter. Dynamic index/column definitions reject. Fresh source schemas exclude
the opt-in migration ledger, custom objects and leftover prototype tables.

Hash: ordered `sqlite_master(type,name,tbl_name,sql)` by type,name including NULL-SQL
autoindexes and sqlite_sequence, canonical compact UTF-8 JSON (`ensure_ascii=False`,
sorted keys), SHA-256. Output also includes exact SQL, PRAGMA table_info (ordinal,
name,type,notnull,default,pk), foreign_key_list, source blob/text hashes. Locally
derived with SQLite **3.53.1**. Independently matches RL-02 current hash; exact DDL
text/order remains significant. A future SQLite change needs evidence comparison.

[financial-schema-inventory.json](financial-schema-inventory.json) is the small
sanitized identity receipt; full schema-only metadata is reproducibly emitted by
the script, not a committed DB fixture. The script's single selected DDL sequence
is explicitly synthetic and incomplete for arbitrary upgrade paths.

## Eight source-defined fresh schema shapes

All table counts include `sqlite_sequence`. Dates/commits are source history, **not
release versions**. All earlier shapes remain unsupported by strict RL-02.

| ID / first reachable source | Exact fresh-schema SHA-256 | Known change / financial-state meaning | Adoption classification |
| --- | --- | --- | --- |
| S1 `1ea24429400baacf0fb8f6282fec0615d0a79837` (2026-05-09), app/main.py | `2907ec6eb4b4f146d9a575f39146d71cd998909af0df10120f13c542740246d3` | 10 tables: settings, people, items, order_lines, change_requests, round_requests, transactions, transaction_items, round_events, sequence. Purchase snapshots/profit already exist; zero backfill/round normalization/import comments cannot authenticate pre-feature data. | Source-derived only; unsupported; no real DB/image fixture |
| S2 `003a8b737c459ee1f12c07d2f8fb5841b6041ec9` (2026-05-14), app/main.py | `41848e9aa734e110642c0d2843d274a25f7f5dcf8b84ee24e84a6b1ecf764d6e` | Adds client_operations and PK autoindex (11 tables). Offline replay IDs/correlations must be retained; no accounting reinterpretation implied. | Unsupported |
| S3 `d3991f8c8a5fb7f47a55ebb9744ee65b05e073af` (2026-05-18), app/main.py | `8d2fe797224818b0e1ce21bb2e2e06464bc2469d218808798e2115cf624c7d17` | Adds four indexes: change-request line/status, order person/quantity/event, round-request person/status, transaction person/timestamp. Same financial fields; index equivalence is still exact schema difference. | Unsupported |
| S4 `bffb2ad3a268df39487424d39770692eb952e5b5` (2026-05-18), app/main.py | `e3ca98287e7ddda31ba5ff27924b7f65454f6ec29d5a482963ad2ffb09e3d05d` | Adds member messages/recipients and indexes/compound PK (13 tables). Full recovery includes acknowledgement relationships; not a change to historical EK meaning. | Unsupported |
| S5 `c5ce7367d8dba5a2162397b9cfb9cc5b81de7f27` (2026-06-10), app/main.py | `f4fce04befdc661275958a1cdb03f19a76ca948c7987808feaa430bb08d2e50f` | Adds self_payment_sessions and four indexes including unique client_payment_id (14 tables). Provider status/IDs/uncertainty become recovery-critical. NULL IDs allowed, duplicate non-NULL IDs not repairable by inference. | Unsupported |
| S6 `c101aede7ca2bc77a094107b9d1ea205ae4bddfb` (2026-06-10), app/main.py | `429e78a0c6afca5f6f2c6242a4d0db88863b619fe141da9c44942fb9e40e6638` | Adds base_amount_cents/card_fee_cents/rounding_mode/rounding_adjustment_cents to fresh session DDL and additive helpers. Missing-column defaults 0/none do not authenticate actual old fee breakdown. | Unsupported; ALTER-path variant differs |
| S7 `849228102574dc61c02748bee50b59cf3039cc32` (2026-06-12), app/main.py | `2ebc244c8260b07e161489585fccb32290acef8aac70e995d2fcf81851ff3a02` | Adds paid_round_units + event/source indexes (15 tables). Paid-round entitlement and original payer/sales snapshots require preservation. Later round-algorithm fixes can share this schema, so fingerprint alone cannot identify semantics. | Unsupported |
| S8 `c3a78cd334b47e9f45dec6c10fe26be2a26df8bb` (2026-09-09), app/db/schema.py | `090ea55aa19289c833f2010950722d4eb443c1b567068cbdc04217e1a25256a2` | Adds named event sessions/lines and two indexes (17 tables). Same current application shape through baseline; source extraction/formatting and RL-02 seam do not change application DDL hash. Financial/API changes can still share this hash. | Existing RL-02 exact-current metadata-only candidate **if all ledger/journal/integrity/path/permission gates pass**; not authentic-release support or production authorization |

S1..S8 reachable commit counts respectively **3,2,1,21,1,5,21,59** (113 total).
These counts are shapes across source ancestry, not installations or releases.

### Concrete upgraded-structure counterexample

Literal DDL applied in memory S5→S6→S7→S8 yields
`c07c9c5534c86438a34c431d5248d1518c138801ec0be763e039cd055fa95db0`,
not S8. ALTER added the four fee/rounding columns **after completed_at**, whereas
fresh DDL places them before amount_eur. `CREATE TABLE IF NOT EXISTS` retains old
sqlite_master SQL; column ordinals/text differ. Intermediate hashes after S6 and
S7 are `c92bb2016f7b6aa9bf6baeb67dedd26c2190836145c8b99c100fb77cc10519f7`
and `3e16a202ad3f50b40ca497a7b9bc9cf466f1f721f70dabe2548e75f8b88bedb5`.

**Synthetic DDL-only counterexample**, not an authenticated installation, full
legacy data migration, supported upgrade or recommended schema rewrite. Current
strict mode correctly rejects it. Candidate for a later **one exact fingerprint**
review only after owner policy/source/support decision; never rebuild tables/drop
audit objects merely to make a hash match. Other upgrade histories may differ.

## Additional candidates and unknown states

| State | Evidence / support |
| --- | --- |
| Exact S8 plus verified v1 ledger/PRAGMAs | Current RL-02 repeat path; ledger records baseline establishment only, not old migration execution. Schema match says nothing about zero provenance. |
| Fresh absent path | Current explicitly permitted RL-02 initialization, not legacy adoption. No preexisting facts to preserve. |
| Minimal `people/drinks/orders` | Synthetic repository tests authenticate helper behavior only. No exact authentic prototype fingerprint/support; strict adoption rejects, legacy import is not a historical reconstruction policy. |
| Missing EK columns / zero-default history | Unverifiable prior sources; earliest Git source already has EK. Missing column is not authenticated accounting evidence by itself. No support claim. |
| S8 with old prototype tables retained, custom audit triggers/indexes, missing unique payment index or equivalent DDL spelling | Different exact fingerprints, unsupported. RL-01 synthetic full-state fixture adds trigger/index and has hash `694d25ba64f7674a3e10b7402108417f0282aefa8c61fbc1a9ca922ff66ad264`; not S8 or a released schema. |
| WAL/sidecars/hot journals, partial/future/corrupt/FK-invalid/empty existing file | Recovery/intervention/rejection, not an adoption candidate; no sidecar deletion/reset/automatic repair. |
| Real DB values or historical image/default/settings combinations | Not accessed; provenance, prior backfills, fee breakdown, authentic costs, external refunds/mail and operator custom objects remain unknown. |
| Standalone old CSV | Partial reconstruction only, not exact DB/adoption authenticity; important-table list omits event tables/ledger, prototype tables and original sequence gaps. Full EF-08b state required for a new adoption rehearsal. |

## Evidence needed before widening support

Independently authenticated source/release tuple and sanitized metadata; exact
source schema with lifecycle history/known differences; explicit financial preservation
and reporting decision; synthetic edge fixtures and full-state repeat/HTTP/recovery
tests bound to candidate image. No support from same columns, empty schema alone,
mutable stable tag, build log or successful synthetic migration. Maintain unknown
classification until evidence/owner acceptance exists. No additional allowlist entry,
adoption tool, historical DB or migration implementation added by RL-03.
