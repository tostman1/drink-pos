# Drink POS Architecture — observed baseline

Current handoff inspection (2026-11-25): verified main
`613ff7195428063e875b9b5d301273c1b4613407`, documentation reconciliation only.
Served stack and all runtime/migration/financial/recovery/Compose/UI artifacts stay
unchanged. Dated descriptions below retain source history; RL-04/05 supersede their
old rewrite/T-only/no-v2 descriptions only within approved scope. Product GUI
rehabilitation keeps the vanilla PWA/runtime baseline and requires interactive
design review per IMPLEMENTATION_PLAN. No framework, ORM, auth/key layout or
maintenance executor chosen by this handoff; PO-ADR gates remain open.

## Approved target boundaries — planned, not implemented (2026-11-24)

Inspected main `7a6aa5dff411c8fb5601b87758a0fc64810aa0c3`; RL-06 integrated.
The GUI-only administrator journey is binding in
[`docs/product-operability.md`](docs/product-operability.md) (DP-026–040). This
section defines required boundaries, **not a selected implementation**. Existing
runtime/Compose/migrations/recovery tools are unchanged; dated RL descriptions
below retain history, with RL-04/05 scoped supersessions, not present defect claims.

```text
Container Manager / other Docker host GUI
  -> exact trusted image + port/exposure + independent persistent data
  -> protected bootstrap/recovery browser boundary (no main-DB dependency)
  -> explicitly initialized/versioned compatible application state
  -> admin GUI -> typed settings + protected secret references + redacted audit
              -> fresh action-bound authorization -> integration config revision
              -> diagnostics / isolated acceptance records / activation
  -> maintenance control -> durable journal + all-writer drain/hold
                         -> existing EF-08 verification/new-root recovery
  -> exact candidate + preflight/rehearsal readiness
                         -> separate restricted install/restart boundary
```

- **Deployment/bootstrap:** one Compose/minimal image/port/volume inputs, one app
  service by default, persistent data independent from image. No shared PIN/automatic
  ownership/production activation/socket/privileged container. Installation claim,
  strong credential verifier and browser recovery authority work without the main DB
  (PO-ADR-01/09/10). One service may contain mutually exclusive normal/recovery modes
  if safe; extra service requires a demonstrated safety need, not convenience.
- **Settings/secrets:** A infrastructure stays host-controlled; B operational GUI
  settings with C fresh authorization and D protected secrets. Typed/versioned atomic
  revision+audit+secret-reference persistence, explicit ENV precedence/migration; no
  empty-secret fallback/restart drift. Key hierarchy/old-backup retention/new-NAS
  restoration and settings migrations block persistence until PO-ADR-02–05 resolve.
  Existing SMTP/PIN TEXT settings are not the new secure persistence contract.
- **Payment:** server-only provider adapter, restricted endpoint/network trust,
  immutable config/merchant/reader binding per durable operation. Completeness,
  connectivity, acceptance and activation differ. Unready normal UI/creation fail
  closed; no production fake provider. Fresh authorization serializes changes against
  active/unresolved normal/test operations; retired identity/access survives disable
  for reconciliation. Tests are isolated from member debt/beverage revenue with real
  funds accounted separately. No secrets/raw sensitive responses in reports. Access
  policy/holds/test classification are PO-ADR-06–08, not inferred from old routes.
- **Recovery:** GUI orchestrates all-writer drain/hold, EF-08b full snapshots/EF-08c
  envelopes and verified new-root restore, never an active-DB overwrite. Journal/auth
  is independent of broken DB. Bounded uploads are data, not paths/commands. Preserve
  old/failed roots and post-backup financial/provider/mail/client activity; reconcile
  before activation. Settings/secret format evolution requires compatibility review,
  not a second archive. Independent keys/images/copies are necessities, not GUI magic.
- **Updates:** evidence-bound version/image/schema/backup/storage/pending operation
  visibility is not installation permission. Exact approval, verified backup/keys,
  isolated rehearsal, writer hold, restricted restart and health/full-state checks
  precede release. No general socket/host privilege/path injection/prune. PO-ADR-11/12
  select provenance/narrow host authority. Image-only incompatible-schema rollback
  forbidden; separate-root recovery/reconciliation is required where needed.
- **Transport/acceptance:** trusted HTTPS for admin secrets/PWA, private LAN/VPN
  default; TLS lifecycle stays host infrastructure unless approved (PO-ADR-13).
  Actual DSM/mobile/PWA/financial/key-loss/offsite/immutable journeys remain RL-11
  pending (PO-ADR-14). No service-worker bump: no UI change in this package.

State machines/measurable gates are in the focused specification; options/owners
in DECISIONS. RL-07→RL-11 are not implementation authorization. D-01 retains the
served stack; no framework/ORM/architecture transplant.

Drink POS has a modular runtime shell around the original production handlers.
The stable production entrypoint is `app/main.py`, which loads the FastAPI app
through `app/application.py`. Runtime routes are grouped by `app/routes/registry.py`
into public, static, payment, admin, and agent routers before being mounted.

## Runtime and dependency map

```text
Browser: index.html / admin.html / kassa.html / self-pay.html
  -> same-origin REST (ordinary offline bookings queued locally)
  -> main.py -> application.create_app -> route registry -> legacy handlers
     -> schema/security/events/messages/statistics/sync + legacy query helpers
     -> sqlite3 / filesystem CSV-PDF-message artifacts / server-only SumUp-SMTP
```

Both `uvicorn main:app` from `/app` and package import `app.main` are supported.
`main.py` aliases its module to the legacy catalog for test/monkeypatch compatibility.
`application.py` reloads the legacy module, creates the served FastAPI instance,
copies startup/shutdown handlers and mounts categorized legacy `APIRoute`s. The
registry does **not** mount the independent routers in `routes/public.py`, etc.
Routing category is organizational, not an authorization boundary; the actual
handler enforces PIN/token/rules. OpenAPI is generated by FastAPI.

## Layers (partial extraction, not a completed migration)

- `app/config.py` owns environment values, defaults, and constants.
- `app/db/` owns SQLite connection setup and database initialization facades.
- `app/models/` owns Pydantic request models and typed response shapes.
- `app/utils/` owns parsing, formatting, validation, and general helpers.
- `app/services/` owns business logic with no FastAPI request or response types.
- `app/routes/` owns APIRouter modules and the legacy route registry.

Important qualifications: `config.py` and legacy environment constants are
duplicated; schema receives runtime globals through `configure_runtime`; active
connections are supplied by legacy `get_conn`. Services for events, messages,
audit and sync are used by served handlers. Other helpers are incomplete seams:
`services/orders.py` filters open lines by `event_open=1`, unlike actual debt;
`services/payments.py` cash payment omits richer round/revision behavior;
`services/rounds.py` creates PENDING requests unlike the served immediate approval.
Do not replace working handlers with these functions without parity tests.

Current pages contain their own inline JS/CSS. `app/static/js` and `static/css`
are extraction scaffolding, not referenced by those HTML pages or mounted as a
static directory. Keep them and syntax-check them, but do not claim the PWA uses
their modular boot/state flow. Service worker caches shells, not a full offline
financial system; network status/revision polling controls refresh.

## Persistence and transactions

SQLite/WAL, foreign keys per connection, 15-second busy timeout, explicit handler
commits and connection closure. Failed uncommitted writes roll back on closure;
financial conflict-sensitive paths use `BEGIN IMMEDIATE`. Startup migrations use
`CREATE TABLE IF NOT EXISTS`, additive columns and prototype-table migration;
unreadable DBs produce actionable errors rather than being silently replaced.

| Table group | Meaning / critical relationship |
| --- | --- |
| `people`, `items`, `settings` | Stable IDs, archival master data, TEXT settings |
| `order_lines` | Person/item snapshots; positive quantity = debt; `event_open` = current member tally |
| `change_requests`, `round_requests` | Correction decisions and historical round-confirmation record |
| `transactions`, `transaction_items`, `round_events` | Append-only operational audit and signed detail snapshots |
| `paid_round_units` + signed `transaction_items` | Paid rounds and per-person deductions since last CASHUP prevent repeat entitlement use |
| `client_operations` | Ordinary booking replay protection keyed by client operation ID |
| `self_payment_sessions` | Unique payment IDs, revision/amount/status, provider correlation and audit reference |
| `member_messages`, `member_message_recipients` | Per-member acknowledgements |
| `event_sessions`, `event_lines` | Separate named-event status/artifacts and line snapshots |

Schema truth is `app/db/schema.py`; round entitlement counting is in legacy
runtime helpers. Monetary snapshots use SQLite REAL; card calculations use
cents. No storage-format migration is authorized here. Backups use SQLite online
snapshot plus unchanged legacy CSV sections in a checksummed atomic bundle.
Full snapshots retain all tables/schema/sequence state. Restore verifies SQLite
integrity/FKs and publishes only to a new target using an atomic no-clobber link;
it never runs migrations or connects to payments/mail. See `docs/recovery.md`.

Named-event close writes required CSV, then optional PDF, then optional SMTP and
finally closes DB state. Files/mail and SQLite are not one distributed transaction:
CSV may remain after PDF failure; delivery can be uncertain. Preserve tested
ordering/failure behavior and do not invent exactly-once mail guarantees.

EF-08b `application_recovery.py` adds a separate standalone maintenance CLI, not
a route/service replacement. All writers must be quiesced; logical DB/filesystem
before/after checks detect observed changes but do not establish online consistency.
It preserves full SQLite plus exact events/messages and explicit non-secret config,
with versioned manifest/completion marker and no-replace publication. Isolated
restore adjusts only mutable event file locations and verifies all remaining
logical state unchanged. Provider/mail/client queues and independent secrets/code
escrow stay outside local recovery; see `docs/application-recovery.md`.

EF-08c optional `independent_recovery.py` encrypts standard tar copies using trusted
external age and only the public recipient, atomically publishing a v2 envelope
marked encrypted-transfer-complete, not recoverability verified. A separate trusted
private-key verifier validates full decrypted state and explicitly attests independent/
offsite scope in protected receipts. Local combined verification is opt-in. It reuses EF-08b verification/restore, not
its format or runtime. Explicit journals complement status without financial data.
`scripts/disaster_rehearsal.py` removes owned synthetic source storage before fresh
independent encrypted-copy recovery and gated network-disabled startup. No crypto
implementation, storage-provider API, mandatory scheduler or retention. External
key/image escrow, geography/immutability/storage/ACL/operator acceptance remain
separate; see `docs/disaster-recovery.md`.

RL-01 standalone `release_identity.py` / `upgrade_preflight.py` inspect explicit
identities plus attested isolated EF-08b snapshots, without importing runtime or
migrating. SQLite sidecars/WAL headers rejected before inspection, complete state
inventory verified, exact operator-approved identity/schema/configuration required;
unknown never succeeds. `scripts/upgrade_rehearsal.py` executes existing served
startup/ASGI only on owned synthetic copies and restores pre-upgrade state elsewhere.
No startup gate/versioned ledger/default updater change is introduced. Current
startup can persist early DDL/WAL/files before late DML rollback and repeatedly
alter zero purchase snapshots/profits; arbitrary upgrades/downgrades are unproven.
See `docs/release-safety.md`, `docs/rl-01-contract.md` and proposed RL-02.

## Migration Strategy

RL-05 adds bounded correction persistence (`services/corrections.py`) and literal
additive DDL (`db/transaction_schema.py`), not prototype route replacement. Operation
receipts/source links/correction details and stable round units/payment links/
deductions/cancellations/reversals retain originals and provide relational audit.
Served write boundaries use BEGIN IMMEDIATE; helpers share caller transaction.
New exact v2 schema/frozen transition preserves v1 ledger and original rows; strict
still opt-in/fail-closed/no WAL recovery. Legacy initializer adds only empty tables/
indexes/triggers transactionally; no automatic historical source reconstruction.
Normal consumption reads explicit signed sources, paid snapshots distinct; person
history no longer heuristically subtracts old request names/time. See RL-05 contracts.

R5-02 adds read-only `services/correction_coverage.py` for complete ordinary/round
parent-audit linkage validation, not financial reconstruction or authorization. New
member decisions populate the existing receipt transaction_id; old receipts remain.
R5-01 round finance readers apply opposite VK signs to deduction/reversal, matching
their expense/profit convention; consumption/paid paths and v2 DDL are unchanged.

RL-04 scoped preservation supersedes former RL-01/03 rewrite descriptions below:
`admin_update_drink` is master-only plus audit; legacy initializer no longer calls
historical cost backfill/round reset and initializes missing default products only.
No recorded O/TI cost/profit UPDATE remains. Schema, both entrypoint modes, prototype
compatibility guards, round master normalization and opt-in exact v1 ledger remain.
Paid-report `recorded_paid_profit` reads a present snapshot including zero, fallback
only absent/None; operational consumption/OPEN/round formulas stay distinct. Actual
negative correction audit remains T-only, characterized in correction-audit-contract.
No ORM/replacement service/UI/REST/storage/deployment redesign; OQ-06 stays open.

RL-03 evidence (no runtime change): `docs/financial-history-policy.md` inventories
the historical-write exceptions. Legacy startup and the served admin item-update
API mutate cost/profit snapshots; RL-02 metadata-only adoption/repeat protects
startup state, not later API writes. RE/named-event costs are not backfilled; report
formulas can differ from recorded profit. `docs/legacy-adoption-inventory.md`
distinguishes source-derived fresh/ALTER schema fingerprints from authenticated
installation/release evidence. No new financial policy or adoption path approved.

RL-02 adds `db/migrations.py` as an optional SQLite-native contract selected by
`DRINK_POS_MIGRATION_MODE=versioned`; legacy default remains unchanged. Pre-write
read-only/header/sidecar inspection precedes directories/messages/DDL. Fresh exact
schema initialization or metadata-only baseline adoption commits ledger/PRAGMAs
atomically under BEGIN IMMEDIATE and exclusive migration lock; existing v1 repeat
does not run financial/default normalizations. Strict mode keeps DELETE journal,
rejects WAL/recovery/unknown/future/inconsistent state and requires explicit fresh/
adoption permissions. No historical-release migration framework or approved zero-cost
interpretation. See `docs/migration-safety.md`; prior RL-01 historical descriptions
above describe its baseline, not this optional implementation. Preflight now verifies
ledger evidence when present, retaining all isolated-bundle/security boundaries.

`legacy_main.py` is now a compatibility handler catalog rather than the app that
is served directly. New services accept `sqlite3.Connection` explicitly, which
makes them testable without an ASGI app.

This avoids changing all production handler bodies at once while still ensuring
the served ASGI app is assembled through modular routers. Retiring individual
legacy handler bodies remains a lower-risk follow-up in `docs/todos.md`.

## Compatibility Rules

- REST paths and payloads stay compatible.
- The SQLite schema stays compatible.
- Payment and cashup behavior must be covered by tests before route migration.
- The legacy module remains as a fallback until each domain is fully covered.

## Remote Access

Remote access is currently handled operationally through Tailscale. The app
therefore remains designed as a local/private-network service; no public
internet exposure is required for normal operation.

## Deployment and trust boundaries

Dockerfile: Python 3.12 slim, app code at `/app`, Uvicorn port 8000, `/health`
healthcheck, build metadata injected. Compose maps host 8088 and mounts only
`./data:/app/data`; a second container schedules weekly backup CLI execution
(full database plus CSV with the EF-08 image, CSV only with older pinned images). Never mount
an empty host app directory over image code. Secrets currently live in server ENV
or ordinary TEXT settings (SMTP/PIN), not frontend configuration; this is not
encrypted-at-rest persistence and does not meet planned DP-030. PIN-based local-network auth
and in-memory rate limits are existing limitations, not public-internet security.

Foundation CI verifies without publishing; explicit owner-triggered main release
is separate. Production Compose/update scripts are operational docs, not tests.

## Decision EF-ADR-001 — retain the existing stack and runtime seams

Accepted for this foundation (2026-11-22): retain FastAPI, direct sqlite3/WAL,
vanilla HTML PWA and the compatibility shell. Rationale: owner asked for
requirements-first rehabilitation; prototype extraction differs from production,
and changing financial behavior without parity tests is high risk. Tradeoff:
duplication/globals/large handlers remain temporarily. Revisit one seam at a time
through EF-04 after characterization and owner review, not a blanket rewrite.
This decision is also indexed in DECISIONS.md; future candidates and dependencies
are in IMPLEMENTATION_PLAN.md, not an instruction to replace current handlers.

## Verification and risks

Existing unittests primarily invoke handlers directly. Foundation HTTP tests also
exercise the actual assembled ASGI app/startup/auth/serialization. Neither is real
tablet, PWA-upgrade, SMTP or terminal proof. See `docs/standard-checks.md` and
requirements DP-001..DP-020. Remaining risks include module/global state, lifecycle
deprecation, prototype divergence, frontend inline coupling, REAL-money storage,
non-atomic file/mail side effects and private-network auth limitations.
