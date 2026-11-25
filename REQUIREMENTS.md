# Drink-POS requirements — observed baseline and approved product target

## Current interpretation — 2026-11-25

Verified main `613ff7195428063e875b9b5d301273c1b4613407` includes RL-01–06 and
EF-03/03b; dated baselines below identify their source inspection, not current HEAD.
Product Experience & Functional Completion priorities and the mockup/design-review
gate are in IMPLEMENTATION_PLAN. Existing workflows are the baseline; agreed targets
DP-026–040 remain planned. No additional unnamed functionality or commercialization
policy is inferred. Owner-reported isolated DS224+ initialization/install/startup/
health/reverse-proxy/access success at `3f9e9d3...` is recorded in HANDOFF; it does
not close full DP-025 device/recovery acceptance or any planned PO-V gate.

## Owner-approved product operability — planned (2026-11-24)

Inspected main: `7a6aa5dff411c8fb5601b87758a0fc64810aa0c3`, RL-06 integrated
via PR #11. **Binding:** ordinary association administrators must install, configure,
maintain and recover without SSH/CLI, manual SQLite/YAML/.env work or developer
assistance. Target: one simple Compose in Synology Container Manager, start, browser,
guided setup and GUI operation; support other Docker-compatible self-hosting.
Minimal infrastructure image/port/volume/host trust stays outside the app; routine
settings do not. No shared default PIN, activation on mere start, privileged
container or Docker socket. One service by default unless safety-critical isolation
demonstrates a need. Existing RL-06 CLI test delivery is valid and unchanged, not
the final user experience.

Measurable acceptance is specified in
[`docs/product-operability.md`](docs/product-operability.md). These functional and
nonfunctional requirements are **approved target, planned-not-implemented**; no
runtime implementation or real-device/provider acceptance is claimed or authorized.

| ID | Target requirement | Acceptance / package |
| --- | --- | --- |
| DP-026 | Simple safe installation and GUI routine operability | PO-V01; RL-07, final RL-11 |
| DP-027 | Guided strong admin/identity/settings/data/backup/optional-integration setup; DB-independent bootstrap | PO-V02; RL-07 |
| DP-028 | Explicit incomplete/unverified/activated/unavailable/intervention states; cash-only optionality | PO-V03; RL-07/08 |
| DP-029 | Classified typed/versioned GUI settings, precedence and safe migration | PO-V04; RL-07 |
| DP-030 | Protected masked server credentials, encryption/rotation/backup/new-NAS recovery | PO-V05; RL-07 foundation, RL-08/09 integration |
| DP-031 | Fresh action-bound PIN/warnings/confirmation/audit and active/unresolved config holds | PO-V06; RL-07/08 |
| DP-032 | Dedicated SumUp settings/discovery/pairing and restricted endpoint editing | PO-V07; RL-08 |
| DP-033 | Complete card/Self-Pay/fee UI and backend gating; production fake-provider rejection | PO-V08; RL-08 |
| DP-034 | Independent no-charge connectivity diagnostics, no HTTP-ready inference | PO-V09; RL-08 |
| DP-035 | Durable isolated acceptance operations, immutable config/request identities and safe replay | PO-V10; RL-08 |
| DP-036 | Authorized EUR 1.00 success/manual terminal cancellation/timeout tests; exact outcomes and UNKNOWN safety | PO-V11; RL-08 |
| DP-037 | Guided report, exact-config acceptance/activation and unresolved blockers | PO-V12; RL-08 |
| DP-038 | Complete encrypted backup/controlled restore and DB-unavailable recovery GUI | PO-V13; RL-09 |
| DP-039 | Exact update/health visibility and approval/backup/rehearsal/restricted install/recovery | PO-V14; RL-10 |
| DP-040 | Real DSM/mobile/installed-PWA/offline/financial/operator independent recovery acceptance | PO-V15; RL-11 |

All PO-V checks are pending, not existing test methods. Catalog schema v1 preserves
DP-001–025 in `requirements`; DP-026–040 use an explicit `planned_requirements`
partition with pending verification, no fictitious tests. The existing 25-ID CI gate
does not inspect that partition; supplemental documentation audit is required now,
combined lifecycle validator/test evolution is an explicit RL-07 prerequisite.

Preserve server-calculated totals, immutable snapshots/audit/idempotency, exact round
provenance/blocks, ordinary-only offline writes and EF-08/release/migration contracts.
Acceptance tests never affect member debt/beverage revenue; real funds/fees still
need reconciliation. Unready SumUp means hidden normal features/no provider calls;
cash remains usable only for eligible debt, not an uncertainty override. Restore
holds all writers, retains old/failed/post-backup activity and keys, then reconciles;
a GUI cannot recover total storage/key loss without independent copies. Architecture
options in DECISIONS are unapproved; implementations need separate authorization.

## Baseline and confidence

RL-06 adds DP-025: isolated non-publishing exact-image Synology test delivery,
explicit synthetic v2 initialization, no automatic updates/seeding, read-only
preflight versus explicit backup/new-root recovery, and German operator/device
acceptance. Hardware/HTTPS/PWA/offsite acceptance remains pending.

This catalog reconstructs the application at verified main `fb08128`, plus the
PR #1 at `250a4e6`, now owner-merged into main `052c2bb`. It is not an imported product spec or a
claim that stakeholders approved every legacy behavior. Stable IDs and test/manual
references live in [`docs/requirements.json`](docs/requirements.json). `observed-main`
means implemented behavior with cited evidence, not complete end-to-end coverage.
`handoff-integrated` means preserved handoff behavior now included in main.
`engineering` means owner-requested
foundation controls. Any future business change needs an explicit decision.

## Actors and boundaries

- Members book ordinary drinks against people, confirm a round, request a
  correction, acknowledge messages, and start supported self-payment.
- Cashiers use the normal list or internal `/kassa` to inspect and settle debt.
- Admins use PIN-protected actions for master data, settings, corrections,
  payments/cashup, reporting, named-event close/invoices/mail.
- API operating agents have a narrow token-protected REST surface, not general
  admin access. Development agents follow root `AGENTS.md`; these are different roles.
- Deployment operators manage private-network hosting and backups. That is not
  authorization for a coding agent to deploy or inspect production state.

Local/private-network touch PWA; EUR; German presentation. No SaaS tenancy,
public-internet exposure, full offline POS, new roles/auth stack, ORM or SPA
framework is required by this foundation.

## Domain distinctions

Open debt includes positive `order_lines` regardless of `event_open`. Cashup
closes the current member tally, applies eligible round deductions, and does not
forgive remaining debt. The system item `1 Runde` is charged immediately by the
current round-confirmation route despite its historical request name.
Named event mode is a separate aggregate bill (`event_sessions`/`event_lines`),
with discounts, required CSV and optional PDF/SEPA QR/email on close. It is not the
member `event_open` flag, and event closure is not a card-payment confirmation.

Preserve consumption-time name/price/purchase-price/admin snapshots, archival
identity, additive audit corrections, offline booking IDs, payment IDs, revisions,
and server-calculated fees/rounding. An uncertain payment leaves debt open.
PR #1 adds audited aggregate event corrections/stale-event protection and a saved
SMTP test recipient independent from the cashier. Its owner merge does not close
manual verification. Round confirmation is a **confirmed API contract** but also
a potential authorization/business-rule risk: a token-authorized operating agent
can immediately incur debt. Foundation corrects documentation and adds HTTP
coverage, not approval requirements or a new authorization scheme; see DECISIONS.md.

## Evidence conflicts and gaps

| Historical claim | Observed reality / treatment |
| --- | --- |
| `main.py` is a single large app; extracted layers are complete | Main is a bootstrap/alias; served handlers remain legacy; prototype modules differ |
| No exports/restore/sync/OpenAPI/audit/tests | These exist; inventory current implementation rather than execute old review claims |
| Explicit events are a future optional feature | Named events/invoices are already on main; PR #1 adds corrections |
| Agent round request does not charge | Current route immediately books/approves a round; operating-agent docs corrected |
| Mount `./app:/app` | Current production templates mount only persistent `./data`; image owns code |
| Historical cache v88/v90, reset-by-deleting production DB | Historical snapshots, not instructions; previous main v106, integrated PR #1 v108; production deletion out of scope |
| Test counts/coverage percentages in old review | Measured takeover: previous main 87 tests, handoff 96; no coverage percentage measured |

Known gaps: no target-device automation/E2E suite; SMTP and SumUp tests are mocks;
prototype services are not safe replacement contracts; startup lifecycle is
deprecated; runtime config/schema state remains global. Browser usability,
installed-PWA upgrades, authorized integrations, and synthetic recovery rehearsal
are tracked manual checks, not claimed successes. Optional SSE/MCP/UI polish and
mail OAuth/IMAP ideas remain in existing TODO docs, not promoted to requirements.

## Approved EF-08 recovery increment (2026-11-23)

DP-014 now includes persistent all-table SQLite snapshots, integrity/FK checks,
checksummed atomic bundles, explicitly opted-in conservative retention and verified
new-target-only restore. DP-013 CSV contents/encoding are preserved; CSV now lives
inside the bundle as `export.csv`. Legacy CSV is partial recovery, not an all-table
backup. See [recovery contract/runbook](docs/recovery.md). This approval excludes
invoice/SMTP redesign, production operations, publication and deployment.
PR #3 security correction: POSIX restored DBs are 0600 from creation through
publication; new restore-directory components are 0700, existing directories are
untouched. Windows ACLs need operator verification. External root-only CSV consumers
are not assumed migrated; the runbook defines an explicit pre-adoption procedure.

## Approved EF-08b portable application recovery (2026-11-23)

DP-014/010/011 now include explicitly writer-quiesced application-state bundles
(separate from EF-08a), complete file inventory/checksums, exact SQLite/schema
compatibility, no-clobber isolated restore with bounded event-path relocation,
one-shot JSON CLI/age status and generic offline container examples. Full SQLite
settings can include secrets; environment secrets and external/provider/client
state remain excluded. See [application recovery](docs/application-recovery.md).
No runtime handler/migration/payment/mail behavior, existing schedule, deployed
configuration or production digest changed. MV-06 operational/offsite acceptance
remains partially pending, not implied by automated rehearsal.

## Approved EF-08c independent disaster recovery (2026-11-23)

DP-022 extends engineering evidence with optional external-age encrypted filesystem
replicas, unchanged EF-08b bundle contents, independent verification and lifecycle
monitoring, and complete disposable installation-loss/rebuild with measured synthetic
RPO/RTO. No crypto implementation, provider dependency, retention, handler/payment/
mail redesign or production adoption. Real encrypted storage/escrow/ACL/offsite/
immutable/operational acceptance remains MV-06; synthetic evidence is not a SLA.
See [disaster recovery](docs/disaster-recovery.md).

## Approved RL-01 release-safety foundation (2026-11-23)

DP-023 adds deterministic standalone release identity, explicit isolated-bundle-only
read-only preflight, non-success unknown/intervention/unsafe JSON results and
synthetic migration/full-state/API/recovery characterization. No app startup for
inspection, no fictitious schema ledger/published digest, no default deployment/UI/
REST/financial/payment/invoice/migration changes. Only rehearsal readiness is
reported. See [release safety](docs/release-safety.md) and
[ready gate/baseline inventory](docs/rl-01-contract.md). Versioned migrations and
pre-write startup gating require separately approved RL-02; MV-06 remains partial.

## Approved RL-02 bounded migration safety (2026-11-23)

DP-024 adds an **opt-in**, exact-schema version ledger and pre-write gate. Default
legacy behavior remains unchanged. Strict mode supports explicitly permitted fresh
transactional initialization and metadata-only exact-current adoption, verified v1
repeat, future/unknown/inconsistent rejection and isolated recovery evidence. It
does not import arbitrary historical/prototype state or rewrite historical costs.
OQ-06 financial policy remains unresolved. See [migration safety](docs/migration-safety.md).

## RL-03 decision evidence (2026-11-23; no financial-policy approval)

Existing DP-002 snapshot and DP-004 signed audit statements have characterized
exceptions: startup/admin product edits rewrite zero costs/profit; round normalization
also rewrites nonzero history; member/admin negative corrections lack signed item
details. DP-024 preserves metadata-adoption/startup state, not all later API writes.
See [decision/write-impact matrix](docs/financial-history-policy.md) and
[source-only adoption inventory](docs/legacy-adoption-inventory.md). No new accounting
requirement or supported migration is inferred; OQ-06 remains open.

## Approved RL-04 scoped financial integrity (2026-11-24)

DP-002/004/013/024: routine current-product edits/default initialization/startup
must preserve recorded historical financial snapshots, zero and unusual round
costs included. Missing defaults are initialized; existing default zero costs are
not replaced. New bookings use current master data; legitimate debt/tally/payment
operations continue changing quantity/status. Master edit and its audit roll back
together. No historical repair/inference, schema/fingerprint/v2/default-mode change.

Paid reporting reads stored profit including zero rather than a truthiness or
unconditional derived replacement; consumption/OPEN/round operational formulas
and population filters remain distinct. DP-004 has a retained FH-04 exception:
negative debt corrections create T-only audit, not signed item details; lifecycle
and follow-up gates in `docs/correction-audit-contract.md`. FH-05/OQ-06 historical
correction/inference/adoption/accounting decisions remain open. Prior RL-03 text
records the former baseline, superseded only by this scoped authorization.

## Approved RL-05 net consumption and coordinated rounds (2026-11-24)

DP-004/005/006/013/024: normal consumption reflects net after source-linked approved
erroneous-booking reversals, original period attribution, separate immutable audit.
Negative admin correction requires identity/purpose; keyed replay is once-only,
request decisions serialized/idempotent, correction-only pay is explicit HTTP success
without payment. New round units/deductions have durable attribution; safe unpaid
current cancellation restores exact drink debt once, never physical consumption.
Paid/closed/unknown/unattributed states fail closed. Genuine additive v2 migration,
no original rebuild/backfill or additional historical support. See rl-05 and round
contracts; legacy audit completeness and broad OQ-06/FH-05 remain unresolved.

R5-01/02 scoped review acceptance (DP-004/005/013): exact round deduction/reversal
nets zero round-finance VK/cost/profit, no paid revenue or physical-consumption change.
Report coverage distinguishes complete ordinary/round provenance from incomplete/
ambiguous historical parent audits, without inferring missing detail. New approval
receipts retain their exact parent T ID using existing fields; old records unchanged.

## Classification rules

**Owner-approved planned requirements** above have explicit product sign-off and
pending measurable acceptance, not runtime completion or implementation authority.
**Confirmed behavior** has served-code/test evidence; it may still be a risk, not
the ideal rule. Historical **inferred requirements** were not fresh stakeholder
sign-off; operator usability is now explicitly approved above. **Other proposed
improvements** stay in IMPLEMENTATION_PLAN.md, not runtime authorization.
**Unresolved decisions** live in DECISIONS.md.
Stable DP IDs and exact evidence stay in the catalog, not parallel duplicated lists.
