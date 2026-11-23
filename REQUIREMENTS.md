# Reconstructed Drink-POS requirements

## Baseline and confidence

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

## Classification rules

**Confirmed behavior** has direct served-code and test evidence; it may still be
a risk, not the ideal product rule. **Inferred requirements** (private-network
intent, operator usability) are supported by documentation but not fresh stakeholder
sign-off. **Proposed improvements** live only in IMPLEMENTATION_PLAN.md; they do
not authorize runtime changes. **Unresolved decisions** live in DECISIONS.md.
Stable DP IDs and exact evidence stay in the catalog, not parallel duplicated lists.
