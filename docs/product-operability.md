# Product operability specification — owner-approved target

2026-11-25 status clarification: verified main `613ff719...` and reconciled handoff
state are in HANDOFF. Owner-reported listed DS224+ baseline steps succeeded at
`3f9e9d3...`; this does not establish GUI-only operability or close any PO-V gate.
Product Experience & Functional Completion / interactive HTML mockup and design
approval gates are in IMPLEMENTATION_PLAN. Targets/architecture choices below
remain respectively approved-planned / OPEN, not implementation authorization.

Approved product requirements, 2026-11-24; **planned, not implemented**. Inspected
baseline: `7a6aa5dff411c8fb5601b87758a0fc64810aa0c3` (RL-06 integrated through
PR #11). This documentation package authorizes no RL-07 implementation, runtime,
migration, UI, Compose, NAS, production-data, provider, SMTP or release operation.

## Authority and reading map

The binding goal is **Paste Compose → Start → Open Browser → Complete Setup →
Operate Drink-POS**. An ordinary association administrator must install, configure,
maintain and recover the product without SSH, CLI commands, manual SQLite editing
or developer assistance. Technical runbooks remain useful for maintainers, not a
prerequisite for routine use. Prefer concise, guided German workflows with explicit
states and actionable messages; preserve EUR and decimal-comma presentation.

This is the focused acceptance specification for DP-026–DP-040. The authoritative
catalog is [requirements.json](requirements.json); context is
[REQUIREMENTS.md](../REQUIREMENTS.md), architecture boundaries are
[ARCHITECTURE.md](../ARCHITECTURE.md), binding decisions and **unapproved options**
are in [DECISIONS.md](../DECISIONS.md), sequencing/gates in
[IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md). A requirement approval is not
approval of a recommended technical solution or permission to implement/deploy it.

## Inspected implementation versus target

Source inspection only; no running NAS, financial database or provider was accessed.
The served seam is `app/main.py → app/application.py → app/routes/registry.py →
app/legacy_main.py`; independent prototype routers/services are not substitutes.

| Surface at the inspected baseline | Implemented evidence and limits | Future delta |
| --- | --- | --- |
| Installation | `compose.yaml` / `compose.synology.yaml`: app plus Friday DB-backup service, ENV settings, mutable stable pulls. `Dockerfile` owns code; only data mounted. | One simple safe bootstrap project; no manual operational ENV maintenance. Existing templates are not the new product experience. |
| RL-06 test delivery | `compose.synology.test.yaml`, `app/synology_test.py`, exact tested AMD64 archive, isolated internal network, explicit synthetic v2 initializer and CLI recovery/preflight. | Preserve these artifacts unchanged. Their safety-focused CLI procedure is valid test tooling, not the final administrator journey. DSM/device acceptance is pending. |
| Administrator | `app/core/security.py`, served settings update/login and `app/admin.html`: PIN checks, production default/placeholder rejection, in-memory login limit; stored `admin_pin` TEXT and browser-held PIN. | Strong identity/credential bootstrap, action-specific fresh authorization and independent recovery authority. Existing checks do not establish this stronger model. |
| Settings | General settings, invoice settings and SMTP GUI exist via served `/api/admin/settings/update`, `/api/admin/invoice-settings/update`, `/api/admin/mail-settings/update`. SMTP uses DB values with per-field ENV fallback. | Versioned secure settings foundation; do not duplicate the existing invoice/SMTP interfaces. SMTP password currently stored as TEXT, not encrypted credential persistence. |
| SumUp configuration | `sumup_payment_settings` / `sumup_config_from_settings` read all nine payment values from ENV. Admin page states ENV configuration and offers status, not editable provider settings. | Dedicated secure GUI with draft/verification/activation and configuration identities. |
| Reader APIs | PIN-protected `/api/admin/sumup/readers`, `/api/admin/sumup/pair-reader`, `/api/admin/sumup/status`; service supports list/pair/status/checkout/terminate/transaction polling. Pair response does not persist selected reader. | GUI discovery/pairing, independent diagnostics and safe reader replacement. Existing status route returns provider data, not a complete readiness assessment. |
| Gating | `require_self_payment_available` rejects disabled/incomplete creation; public config separates enabled/configured/available. Normal-list member panel uses enabled, cashier buttons can remain visible disabled; kassa rounding controls depend on amount/selection. Admin labels completeness as “SumUp bereit”. | Complete UI/backend activation gating; completeness must never mean terminal readiness. |
| Fake provider | `test_card_payment_mode` supports test/dev modes and an explicit allow-test flag; the flag can select a test provider even with production APP_ENV. | Production must reject test/mock/demo regardless of that flag. This is a source-observed gap, not an authorized fix here. |
| Payment records | `self_payment_sessions` stores durable client ID, amount/currency/revision/provider reference, status and raw results. Once-only creation by client ID and settlement transaction exist; known mismatches leave debt open. | Immutable configuration/merchant/reader binding, stricter exact success evidence and isolated acceptance records; no claim the current session model meets these new requirements. |
| Uncertainty | Existing statuses include CREATED/SENT_TO_READER/PENDING/PAID/FAILED/CANCELLED/TIMEOUT/UNKNOWN/EXPIRED. Local cancel is recorded before terminate acknowledgement; late success can still settle. Poll deadline returns TIMEOUT; old active states expire locally. | Cancellation/expiry/deadline cannot establish a definitive provider failure; unresolved identities and holds survive until reconciliation. Missing amount/currency fallback in current success handling is not the future exact-evidence contract. |
| Backup/recovery | EF-08a SQLite/CSV bundles and EF-08b whole DB/events/messages/config bundles; EF-08c external-age encrypted replicas and independent verification; all standalone tools. Admin CSV exports are not a whole-application restore GUI. | Orchestrated GUI over these contracts, independent DB-unavailable recovery and protected secret/key recovery. Age is currently external, not embedded in image. |
| Updates | `app/core/build.py`, `/api/config`, admin build labels, offline release identity/preflight and synthetic rehearsals. Runtime image-ref ENV is an assertion, not authenticated installed digest. Podman updaters pull/recreate/prune without the full safety protocol. | Readiness/identity center plus restricted execution boundary; no existing safe one-click updater claimed. |

Prior contracts remain authoritative for their implemented scope:
[release safety](release-safety.md), [migration safety](migration-safety.md),
[EF-08a](recovery.md), [EF-08b](application-recovery.md),
[EF-08c](disaster-recovery.md), [RL-06](rl-06-contract.md),
[existing SumUp usage](self-payment-sumup.md). Historical descriptions in those
documents are dated evidence, not instructions to restore former defects.

## DP-026 — simple safe installation and routine operability

### PO-V01 — planned acceptance: installation

- A first-time association administrator uses DSM Container Manager **Project →
  Create**, one understandable Compose YAML, starts the service, opens the browser
  and finishes setup. No SSH, shell, `.env` file, SQLite editor or developer step.
- Require only unavoidable infrastructure inputs: trusted exact image/platform,
  port/exposure and persistent volume/location/access. Prefer fixed safe defaults
  and one application service; justify an extra service only for a demonstrated
  safety-critical isolation need. No privileged container or Docker socket by default.
- Data survives image replacement and container restart; no host application-code
  mount, automatic reseed, shared default PIN or production activation on mere start.
- Verify image identity/version rather than trusting mutable names. Other
  Docker-compatible self-hosting uses the same product contract; DSM is principal.
- Ordinary ongoing configuration, backup, recovery and maintenance use guided GUIs,
  not YAML/ENV/DB/Docker editing. Infrastructure replacement may use Container
  Manager GUI; a running app cannot change every Docker-level setting.

## DP-027 — first-run setup and safe bootstrap

### PO-V02 — planned acceptance: setup

Wizard steps: installation/association identity; initial named administrator and
strong credential/PIN; language (German default) and IANA timezone; currency (EUR
default and initially supported) and financial defaults; basic display/booking
settings; intentional initial members/items/data; backup/recovery preparedness;
optional SumUp; optional SMTP; final review and explicit operational activation.

- Show defaults and consequences before saving. No hard-coded association identity
  or demo members silently become production data. Resume interrupted steps without
  duplicate creation or losing the administrator's draft; reject conflicting setup.
- Until ownership is securely claimed, normal production and sensitive APIs remain
  unavailable. Claiming bootstrap is not “first visitor owns it”: PO-ADR-01 must
  establish installation-specific proof, concurrency protection and credential
  recovery without SSH or a public default secret. Credentials use an approved
  strong verifier, never casual plaintext PIN storage; lost credentials have a
  separately protected recovery path.
- Skipped or incomplete SumUp/SMTP never blocks cash-only use after core setup.
  Explicitly state that mail and card operations remain off. Validate timezone,
  currency/support and financial defaults without relabeling historical records.
- The wizard uses reviewed versioned initialization/migrations and exact compatibility
  checks. Existing/unknown/corrupt/future/WAL state cannot be treated as fresh or
  reset to get through setup. Migration permissions are scoped and revoked after use.
- Bootstrap and recovery must start a protected browser surface even if the main DB
  cannot open. The independent authentication/state/execution design is a blocking
  RL-07 choice, not an implemented guarantee (PO-ADR-01/09/10).

## DP-028 — visible configuration, activation and intervention states

### PO-V03 — planned acceptance: state matrix

Represent these states independently for core setup and each integration:

| State | Required meaning / next action |
| --- | --- |
| Not configured | Missing required values; guided setup available, integration off. |
| Partially configured | Draft incomplete; identify missing fields; no readiness inference. |
| Configured but unverified | Valid persisted values, no sufficient current verification/acceptance; off. |
| Operational and explicitly activated | Required policy met for exact configuration; administrator approved activation. |
| Degraded or unavailable | Previously configured/activated but current communication, terminal or storage evidence inadequate; state why and block unsafe operations. |
| Intervention required | Unresolved payment, failed migration/restore/update, key loss or contradictory evidence; preserve evidence and guide reconciliation. |

Persistence completeness, activation permission, freshness of diagnostics and current
capability are distinct. Missing/stale/unsupported diagnostic evidence cannot be ready.
Offline or busy terminal is explicitly unavailable for a new checkout. Cash can remain
usable during integration failures **only** if core/financial holds allow it; never
use cash as an override for an unresolved payment on the same debt.

## DP-029 — GUI-managed operational settings and transition

### PO-V04 — planned acceptance: settings inventory and precedence

A/B describe placement; C/D are additional protection classes, not alternatives.

| Class | Setting candidates / boundary |
| --- | --- |
| A — bootstrap/infrastructure outside GUI | Image acquisition/exact identity/platform, container port/bind, persistent volume/host permissions, network/firewall/reverse proxy/TLS trust, host limits and restricted executor installation. Build identity and DB/migration paths are diagnostic/internal authority, not editable business settings. Infrastructure uses Container Manager/host GUIs; no promise of web-app control of host settings. |
| B — normal operational GUI | Association/app identity, supported language/timezone/currency/defaults, member/item initialization, display settings, invoicing, SMTP, payment provider, reader, timeout/affiliate options, backup schedule/preferences, supported retention, optional integration activation, bounded maintenance options. Existing invoice/SMTP settings are reused. No arbitrary path or command input. |
| C — fresh administrator authorization | All payment changes (including disable/activation, endpoint, merchant/reader, timeout/currency, affiliates, keys), admin identity/credential/recovery changes, SMTP credentials/delivery destination, bank/invoice identity, backup export/restore, retention deletion, key/escrow changes and update approval. Harmless display settings need normal authorization. |
| D — protected server secrets | SumUp API/affiliate keys, SMTP passwords, agent tokens, private encryption/recovery keys and any later integration credential. Admin credential verifiers are protected authentication data, not exportable secret settings. |

Transition inventory: `DRINK_POS_IMAGE`/`DRINK_POS_IMAGE_REF`/`APP_BUILD_*`, container
ports/mounts/network/UID/GID, `DRINK_POS_ENV`, DB/messages/backup root paths and
migration mode/permissions remain A/internal deployment authority, not GUI-editable
arbitrary paths or bypass switches. `DRINK_POS_PIN` bootstrap becomes the secure
enrollment/credential flow (C; no continuing ENV PIN management). `DRINK_POS_AGENT_TOKEN`
is a B/C/D optional-integration candidate with unchanged narrow authority pending
separate review. All nine SumUp values below are B/C (keys D). Existing
`DRINK_POS_SMTP_*` values become B/C/D as applicable, reusing invoice/SMTP settings
and replacing unsafe per-field secret fallback deliberately. `DRINK_POS_BACKUP_KEEP`
and current Friday scheduler/timezone become bounded B/C preferences under the
reviewed maintenance/retention contract. Test-only flags and RL-06 isolation markers
are not production GUI switches. External TLS keys/registry/executor credentials
stay in their independently managed infrastructure trust boundary.

- Review every current ENV/YAML operational setting as a migration candidate; document
  each exception. Host `TZ` is infrastructure today; intended application timezone
  becomes operational only after consistent timestamps/schedules/report boundaries
  are defined. Currency choices beyond EUR require separate financial approval, not
  a relabel of existing amounts. Retention cannot remove immutable financial audit.
- Use typed, validated, versioned settings with installation/config revision, source
  and effective value. Atomic changes include secret references and redacted audit;
  stale concurrent edits fail rather than overwrite. Failed validation leaves prior
  effective settings intact. Restart-required items are explicit, never silently ignored.
- ENV→GUI precedence/import is **unresolved** (PO-ADR-04/05). Preview effective
  sources/conflicts, explicitly approve import, protect existing secrets and active
  provider operations; a blank GUI secret is keep, not implicit erase/fallback.
  Restart/update/restore cannot silently select different payment credentials.

## DP-030 — protected credentials, persistence and recovery

### PO-V05 — planned acceptance: secret lifecycle

- Use reviewed established cryptography/credential storage, server-only decryption
  and least privilege. Do not put API keys/passwords in plaintext `settings` TEXT or
  embed the decrypting key in the same ordinary settings/backup payload. Define key
  hierarchy, installation binding, key IDs and independent protected recovery material
  before persistence implementation (PO-ADR-02/03).
- Stored secrets are write-only in GUIs: set/not-set/masked state, replacement and
  explicit deletion, never read-back. Never expose stored provider credentials in
  ordinary API responses, JavaScript, browser persistence/state, logs, CSV or evidence
  receipts. A newly entered secret may transit a dedicated HTTPS input/request only;
  no echo, caching, local/session storage or analytics. Minimize its input lifetime.
- Redact error/provider data with an allowlist, not raw credential-bearing responses;
  audit actor/time/config ID/changed field names and non-secret identifiers, not
  secret values or low-entropy secret hashes. Credentials must not enter source/docs.
- Encrypted export/backup, independent key escrow, new-NAS restore/rebinding, rotation,
  revocation and loss reporting must be designed and rehearsed. Preserve old key
  versions needed to decrypt retained backups; key rotation must not strand them.
- Missing/wrong/revoked keys cannot silently yield empty/default/live credentials.
  Restore starts integrations disabled/unverified until recovery and reconciliation
  are approved. Plaintext legacy SMTP/PIN data are a controlled migration risk; do
  not redact/rewrite original recovery bundles or claim they were already encrypted.

## DP-031 — fresh sensitive-action authorization and configuration holds

### PO-V06 — planned acceptance: fresh authorization

Every sensitive payment configuration change requires **fresh server-side admin
PIN verification**, explicit confirmation and prominent warnings. Existing login
or a browser-reused PIN/session alone is insufficient. Verification is action- and
configuration-revision-bound, short-lived, non-replayable, rate-limited and invalid
after credential/config change; missing/wrong/expired/reused authorization rejects
before any mutation/provider call. Exact protocol/expiry is an RL-07/08 decision.
Apply CSRF/origin protections, online-only access and least privilege; member,
cashier and token-agent access cannot change provider administration implicitly.

Warn that wrong settings may disable card payments, prevent terminal access, fail
new checkouts, interrupt ongoing work, make results uncertain and require manual
reconciliation. Show affected configuration and unresolved operations before approval.
Audit successful and rejected sensitive changes without secrets.

Serialize settings commits against checkout creation/active tests and maintenance.
Reject unsafe changes while active **or unresolved** provider work exists, including
local TIMEOUT/CANCELLED/EXPIRED without definitive provider evidence. Disabling may
stop **new** work but cannot discard reconciliation capability/old configuration.
No silent overwrite of merchant/reader/checkout identities; PO-ADR-07 resolves the
exception/hold policy and concurrency proof. Key rotation/reader replacement:
drain new work → inventory/reconcile old operations → retain required restricted
old identity/access → verify replacement → rerun affected acceptance → explicit
activation. If immediate credential revocation is necessary, retain metadata and
intervention state; never mark unknown debt paid/failed to unblock a change.

## DP-032 — SumUp settings, discovery and endpoint protection

### PO-V07 — planned acceptance: SumUp administration

Target navigation: **Administration → Settings → Card Payments → SumUp**
(localized German UI; this is not a claim those menus currently exist).

| Compatibility name | GUI intent / default |
| --- | --- |
| `PAYMENT_PROVIDER` | Disabled/cash-only default; explicitly select SumUp; production never selects fake/test. |
| `SUMUP_API_BASE` | Official `https://api.sumup.com`; advanced restricted endpoint policy only. |
| `SUMUP_API_KEY` | Write-only protected credential; no shared default. |
| `SUMUP_MERCHANT_CODE` | Validated merchant identity. |
| `SUMUP_READER_ID` | Discover/select/pair reader where supported; ID is not serial number. |
| `SUMUP_AFFILIATE_KEY` | Optional protected credential when required by provider. |
| `SUMUP_AFFILIATE_APP_ID` | Optional validated affiliate identity; validate required key/app pairing. |
| `SUMUP_CURRENCY` | EUR default/initial supported currency. |
| `SUMUP_TIMEOUT_SECONDS` | 120s default; validated range with provider contract (current parser clamps 30–600s; not proof of provider-accepted limits). |

Do not require ENV edits/restart for ordinary supported payment changes. Show
validation, draft/effective configuration identity, key-set flags, selected merchant/
reader, pairing outcome and exact state. Discovery/pairing may communicate with
provider but must not create a charge. Preserve unresolved identities on replacement.

Advanced endpoint editing is separate from ordinary setup, with fresh authorization,
explicit credential-exfiltration warning and a reviewed allowlist/HTTPS policy.
Prevent localhost/private/metadata endpoints, userinfo, malicious DNS rebinding,
cross-origin redirects or forwarding secrets to unapproved endpoints. Provider test
endpoints cannot be silently used in production. Endpoint permission is not an
arbitrary URL fetcher; unsupported customization fails closed (PO-ADR-06).

## DP-033 — complete card/self-payment feature gating

### PO-V08 — planned acceptance: fail-closed matrix

For unconfigured, partial, unverified, disabled, degraded/unavailable or intervention
states, normal member/list/admin-cashier/kassa card buttons are **not displayed**;
Self-Pay entry links are not advertised and direct page visits cannot start payment.
Hide card fee/rounding controls where no card payment can be used. Keep configuration/
diagnostics in administration visible and explain status there, not via misleading
normal-view “ready” or unexplained silently disabled controls.

All card-creation APIs independently enforce effective activation/current capability,
online access, exact configuration and financial holds. Stale UI/cached PWA/direct
HTTP requests cannot bypass them. Rejection creates **zero provider requests, zero
fake PAID records and no member-debt mutation**. Production rejects fake/test/mock/
demo providers even with a development/test flag accidentally set. Preserve existing
server fee/rounding rules for ordinary supported card payments; changing fees is not
authorized by this package.

Cash remains available for eligible debt without card fees. Historic unresolved
provider work remains readable/reconcilable by authorized admins after disabling;
normal creation gating cannot hide it or charge again. Refresh capability on config/
availability changes, recheck on each create and invalidate stale readiness; no
provider call merely to render hidden normal controls.

## DP-034 — connectivity diagnostics without payment

### PO-V09 — planned acceptance: Test connection

Provide **Test connection** in SumUp administration. Independently report, where
provider API supports it: completeness, authentication, merchant validity, API
communication, reader discovery, pairing, availability and idle/busy state. Give
timestamp/config identity, supported/unsupported/unknown results and actionable
German guidance. A HTTP 2xx is connectivity evidence only, not payment readiness or
transaction success. Missing capability must be explicit, not a fabricated pass.

Sanitize sensitive responses/credentials; no charge, refund or member-debt operation.
Keep diagnostics separate from the explicit live acceptance wizard. Verify official
provider API behavior/permissions/limits in RL-08 before promising unsupported
discovery, cancellation or transaction evidence; none was probed here.

## DP-035 — isolated durable acceptance-test operations

### PO-V10 — planned acceptance: records and replay

Provide a clearly labeled administrator-only **live-terminal payment acceptance
wizard** requiring fresh PIN and separate explicit live-test authorization. Tests
use an isolated acceptance-test record model, **never a member/drink debt** or normal
beverage revenue. Accounting treatment of real test funds/fees remains PO-ADR-08;
separation is not permission to omit them from financial reconciliation.

Persist before creating any checkout: durable unique operation identity/test kind,
installation and immutable config revision, non-secret merchant/reader identity,
amount/currency/timeout and relevant exact request parameters, expected outcome,
start time/operator authorization. Persist provider checkout/transaction references,
observed status/evidence, observation/completion UTC timestamps, reconciliation
state and operator guidance. A local workflow completion timestamp is **not** final
provider completion; record provider-final time separately or unknown.

No secrets in test records/reports. Preserve immutable original request/evidence and
append reconciliations. Reload/restart/replay returns the same operation; conflicts
on same ID/changed parameters reject. A lost checkout response may mean money was
charged: retain UNKNOWN/intervention, block unsafe duplicate creation, no blind
POST retry. Each A/B/C is a new separately identified operation. Resolve provider
identity and stale/recovered-session access before moving on; never discard an
unresolved test to finish the wizard. Serialize terminal ownership with normal
payments; no competing cashier/member checkout during acceptance.

## DP-036 — guided successful, cancellation and timeout tests

### PO-V11 — planned acceptance: live tests A/B/C

All three default to **EUR 1.00**, configurable only within independently verified
provider-accepted limits; no guessed minimum or “free test”. Show money/fees and
potential uncertainty warning **before each** separately authorized checkout.
This documentation assignment authorizes **none** of these tests or credentials.

**A — successful payment:** explicitly authorize/start new transaction; instruct
operator to pay with real card/supported method on terminal; reconcile definitive
SumUp SUCCESSFUL status and **exact amount, currency, merchant and transaction
identity** against immutable request/config. Missing/mismatched evidence is not a
pass. Only verified matching success passes A. No automatic refund; no member debt
change or beverage-revenue entry. Real charged money/provider fees remain visible.

**B — manual cancellation on terminal:** authorize a new checkout, instruct
operator to cancel directly on SumUp terminal, observe/reconcile supported definitive
result and verify no successful payment. Pass only the explicitly documented
provider cancellation contract; terminate request acknowledgement or local CANCELLED
alone is not final proof. Any success is a failed cancellation objective and must
remain reconciled as real money; unresolved result is intervention required.

**C — timeout:** authorize a new checkout, instruct operator not to interact, wait
configured deadline, observe/reconcile provider response and validate application
timeout behavior. A local deadline proves neither failure nor cancellation. If no
definitive result exists, outcome is **UNKNOWN / intervention required**, no paid
debt and no unsafe duplicate attempt. C may pass its **safety objective** for correct
UNKNOWN preservation/holds while remaining unresolved and blocking activation.
Do not fake provider cancellation/success; a late definitive success must be
matched/reconciled even after a timeout/cancel, never lost or blindly charged again.

## DP-037 — final acceptance report and explicit activation

### PO-V12 — planned acceptance: activation policy

Report connectivity, A success, B cancellation and C timeout results separately;
expected/observed outcomes and safety-vs-business objective; all unresolved operations,
provider references, amount/currency/time details, installation/configuration identity,
operator confirmation and final readiness/blocker list. Exported evidence is redacted,
not a secret/config dump. Records survive restart, config disable and backup/restore.

Enable card payments only after the required documented acceptance policy for the
**exact effective configuration** is met, current readiness is adequate, no unresolved
blocker remains and a freshly authorized admin explicitly activates. Defaults are
off. Successful diagnostics alone cannot activate; a passed C safety objective with
UNKNOWN cannot activate. Stale evidence/material config changes invalidate relevant
readiness and require revalidation. RL-08 must resolve policy freshness, which tests
are mandatory and evidence for definitive cancellation/timeouts; no generic skip/
force-green bypass. Owner approval for real tests is independent from PR review.

## DP-038 — application backup, controlled restore and DB-unavailable recovery

### PO-V13 — planned acceptance: Backup & Recovery

Target **Administration → Backup & Recovery**: create consistent complete backups,
history with creation/verification/independent-copy/rehearsal status, encrypted
download, upload, integrity/compatibility/source-target version/schema preview,
consequences and post-backup loss window, fresh authorization, controlled restore,
progress/result and preserved old state for rollback/investigation. Download/export
is sensitive even without restoration. No arbitrary filesystem paths/commands.

Reuse EF-08a DB and EF-08b complete application contracts plus EF-08c encrypted
envelope; no incompatible second backup format or silent claim CSV is complete.
Any settings/secret payload extension requires a reviewed versioned compatible
evolution with old-bundle handling. Encryption/key loss handling follows DP-030;
retain independent compatible image/provenance and protected recovery keys.

Planned control flow: **requested → authorized → draining → writes-held →
backup/staging/validation → isolated restored-not-started → verified →
reconciliation-required → activation-approved → operational**. Failure/interruption
transitions to held/intervention, not “restore successful” or auto-resume. Durable
operation journal outside the failing main DB records stage/identity, not secrets.
This is the restore path; backup-only creation instead completes verification/
protected publication and explicitly releases maintenance after its own checks,
without selecting/restoring any state. Diagnostic read-only checks never grant
restore permission. Fresh approval binds backup ID, installation and selected target.

- Stop/drain **all** writers, workers/schedulers, event artifact/mail/payment work,
  imports and client queue acceptance; prove held state before complete backup or
  restore. SQLite-only locks/observed change checks are insufficient orchestration.
- A running DB must never overwrite itself while serving writes. Use isolated
  maintenance execution (PO-ADR-09), restore to a new root via existing verifier,
  verify full tables/ledger/audit/IDs/events/messages/settings, then controlled state
  selection/restart. Preserve original DB/sidecars/files, no silent destructive replace.
- Upload has bounded size/entry/resource limits, safe archive parsing, no traversal/
  links/reparse/commands, private encrypted scratch, exact installation/version/schema
  compatibility and authenticity/integrity checks. Checksums alone are not sender trust.
- Inventory post-backup bookings/payments/provider results/mail/browser IDs. Do not
  silently discard financial activity, auto-replay charges/offline queues, resend
  invoices or rewrite immutable history. Holds and reconciliation require approval.
- If normal DB/app fails, ordinary admin opens a protected recovery browser surface;
  if needed uses Container Manager GUI to start an exact trusted recovery-capable
  image/project with new storage, uploads independent backup and supplies protected
  recovery material, validates/restores and explicitly resumes after reconciliation.
  PO-ADR-10 must deliver this executable GUI-only journey, including authority when
  stored admin verifier is unavailable; no assumed main-DB login or SSH fallback.
- Complete NAS/storage/key loss is not magically recoverable by a GUI: independent
  restorable backups, compatible images and keys must survive. Report missing items
  as unrecoverable/intervention, never reset an installation to conceal loss.

## DP-039 — restricted updates and maintenance

### PO-V14 — planned acceptance: System & Updates

Target **Administration → System & Updates** shows installed human version, exact
application/image identity with evidence trust, candidate availability, compatibility,
DB schema version, backup verification, storage health, failed/pending maintenance
and recovery readiness. Unknown identity/quota/status is unknown, not healthy.
Update discovery uses authenticated metadata; unavailable registry access is explicit.

GUI-led workflow: candidate selected → exact identity/compatibility preview → fresh
admin approval → drain/hold writers → verified current complete/independent backup
and keys → isolated compatibility rehearsal → separately authorized restricted
installation/restart → health/schema/full financial+artifact verification →
reconciliation/approval → release writers. Drift invalidates approval/preflight and
requires a new boundary. Durable progress survives container replacement; failure/
interruption preserves old/failed state and enters intervention, not blind retries.

Readiness is not execution permission. No unrestricted Docker socket, privileged
container, shell/path/Compose injection, general host control or silent pull/prune.
PO-ADR-12 chooses a restricted external executor or Container Manager GUI approval
boundary; bind commands to one installation, approved digest, bounded action and
one-time authorization, authenticated channel/least privilege/replay protection.
An app must not directly replace its own running container under unrestricted trust.

Preserve compatible old image and full state, and all post-backup operations. An
image-only rollback is unsafe across incompatible schemas; use verified separate-root
recovery and human reconciliation when necessary. No unattended update/schedule is
approved. Existing updaters remain unchanged and are not the secure architecture.

## DP-040 — real operator, Synology, mobile and PWA acceptance

### PO-V15 — planned acceptance: operational evidence

RL-11 measures a nondeveloper administrator's GUI-only installation/setup/configuration,
backup, application-DB-unavailable recovery, new-hardware/key/image retrieval and
update/failure/reconciliation journeys. Record assistance/errors/time separately;
any mandatory SSH/CLI/manual DB or developer step fails the product journey. Use
synthetic financial data; operator-approved real integration tests require separate
explicit authorization/accounts. No real acceptance was performed by this package.

Verify actual DSM/Container Manager/volume permissions/security, nonprivileged
execution, HTTPS trust and private LAN/VPN access, supported desktop/tablet/mobile
portrait/landscape/touch/accessibility, installed-PWA upgrade/cache/ordinary-only
offline recovery, gating under stale clients and new states. Include net-correction/
round cancellation before/after deductions, overlap and paid/closed/settled/UNKNOWN/
unattributed blocks; cash/card/fees and external reconciliation remain distinct.

Test backup corruption/wrong key/unavailable DB/failed update/storage faults, retained
post-backup operations and independent/offsite/immutable copies where claimed.
Report actual RPO/RTO with retrieval and human reconciliation, not synthetic CI times
as an SLA. Keep [MV-01–MV-06](standard-checks.md) open/partial until their specific
evidence is actually obtained; RL-11 adds product journeys, not retroactive passes.

## Documentation-package verification and future gate ownership

All PO-V01–PO-V15 above are **planned acceptance, pending execution**, not fabricated
test methods. Every DP-026–DP-040 catalog entry maps to one PO-V ID and owning RL
package. Automated regressions must be written before implementing each behavioral
change; live-provider and target-device evidence cannot be supplied by mocks.

The schema-v1 catalog preserves its original `requirements` partition (DP-001–025)
byte-for-byte. New `planned_requirements` entries explicitly use
`status: planned-not-implemented`, empty `tests` and `verification_status: pending`.
The unchanged legacy traceability checker/tests inspect **only** `requirements`.
Their 25-ID pass is not validation of the new partition. For this docs-only package,
perform a supplemental JSON/source-reference audit of both partitions: unique IDs,
exact DP-026–040 set, pending status/no runtime evidence, spec PO-V headings, owning
RL mappings/dependencies and unchanged old catalog. Record results in PROGRESS/PR.
Do not weaken CI or alter Python tests to claim green. RL-07 must separately extend
the schema/checker/tests for combined planned/implemented lifecycle coverage before
any new requirement can be promoted; retain exact-ID/resolve/fail-closed assertions.

Required review gates: consistent binding-vs-proposed language across authoritative
docs; all unresolved PO-ADR choices have options/trade-offs/recommendation/owner;
no collisions/history loss; RL-07→08→09→10→11 prerequisites; preserve DP-001–025
financial/security invariants and EF-08a/b/c/release/migration guarantees while
explicitly distinguishing owner-approved future behavior from observed behavior.
Full Standard Checks and
unchanged branch/PR container CI remain separate software gates, not implementation
or device acceptance of the planned GUIs. No worker bump: no UI bytes change here.
