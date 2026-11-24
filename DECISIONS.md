# Decisions and open questions

## Product operability — explicit owner approval (2026-11-24)

Current inspected baseline `7a6aa5dff411c8fb5601b87758a0fc64810aa0c3` includes
RL-01–06 (PRs #6–11). Historical OPEN/UNMERGED/no-next-package notes below describe
their original approval boundaries; integration receipts in HANDOFF/PROGRESS take
precedence for their status. This package approves **requirements and documentation
only**. No RL-07 implementation/merge/deployment/provider/SMTP/publication authority.
Specification: [docs/product-operability.md](docs/product-operability.md), DP-026–040.

| ID | Owner-approved binding decision | Consequence |
| --- | --- | --- |
| D-18 | Ordinary association admin installs/configures/maintains/recovers without SSH/CLI/manual SQLite/YAML/.env/developer assistance | Compose → Start → Browser → Setup → Operate; DSM GUI principal, portable Docker self-hosting; runbooks supplementary |
| D-19 | One simple Compose/minimal infrastructure variables/one app service unless safety-critical isolation requires more; persistent data independent from image | No default socket/privilege/shared PIN/production activation on start; host image/port/volume/TLS boundary remains real |
| D-20 | Strong guided bootstrap, GUI operational settings, protected server secrets and independent recovery | Typed/versioned settings, explicit precedence/migration, masked values/rotation/key escrow; optional integrations do not block cash-only core |
| D-21 | Sensitive SumUp changes require fresh server-side PIN/confirmation/warnings/audit and active/unresolved-operation holds | Session/browser-reused PIN insufficient; retain old provider identities/reconciliation, no unsafe merchant/reader/key overwrite |
| D-22 | Unready SumUp hides normal card/Self-Pay/fee controls and rejects creation server-side | Completeness/connectivity/acceptance/activation distinct; no provider calls/fake payments; cash subject to financial holds; production fake providers forbidden |
| D-23 | Live acceptance uses durable isolated tests A success/B terminal cancel/C timeout with exact evidence and report | EUR 1.00 default within verified limits; no member debt/beverage revenue/automatic refund; UNKNOWN held, separate explicit real-test approval |
| D-24 | Backup/recovery GUI reuses EF-08 contracts; update GUI has restricted host execution boundary | All-writer hold, verified new-root restore/compatibility/reconciliation, preserve failed/post-backup state; no unrestricted socket/image-only incompatible rollback |
| D-25 | RL-07→RL-11 target sequence and real operator/device acceptance | Planned future packages, individually authorized; RL-06 safety CLI artifacts and prior evidence remain unchanged |

## Product architecture choices — OPEN, recommendations NOT approved

The options below must be resolved by the stated package before its relevant
implementation. D-18–25 approve outcomes, not these solutions. Record owner/security
review, threat model, chosen alternative, acceptance and migration/recovery impacts
in a future ADR. No agent may implement a recommendation simply to close an item.

### PO-ADR-01 — bootstrap administrator identity and credential recovery

- Options: installation-specific one-time claim/recovery material surfaced through
  a trusted Container Manager GUI channel; hardware/local-presence enrollment;
  external identity service. First-web-visitor/default PIN is not acceptable.
- Trade-offs: GUI claim delivery must work before service ownership, prevent remote
  takeover/concurrent claims and survive DB failure; external identity adds dependency
  and may block cash-only use without that service; hardware assumptions reduce portability.
- Recommendation: named local administrator, approved strong credential verifier,
  one-time installation-bound claim and separately protected recovery codes/material,
  delivered via a proven GUI-only trusted channel. Exact PIN policy/session/recovery
  enrollment and failed-DB verification remain open; never plaintext PIN fallback.
- Resolve: **RL-07**, owner/security review; recoverability implemented/rehearsed RL-09/11.

### PO-ADR-02 — durable encryption and key hierarchy

- Options: OS/NAS keystore; envelope encryption with per-installation master key
  protected separately from encrypted settings; external secret manager.
- Trade-offs: NAS keystore support/containers/portability uncertain; local master key
  alone cannot protect against host compromise; external manager adds availability/
  provisioning burden. Storing key beside ciphertext in an ordinary DB is inadequate.
- Recommendation: established authenticated encryption/envelope design with scoped
  server-only access, versioned key IDs and independent protected recovery wrapping;
  evaluate host-backed protection where available. Distinguish provider-secret keys,
  backup public recipient and recovery private keys. No new bespoke crypto.
- Resolve: **RL-07** security prerequisite, RL-08 provider/RL-09 backup integration.

### PO-ADR-03 — secrets restored to new NAS hardware

- Options: recovery-key-wrapped portable secret export; manual credential re-entry/
  provider rotation; hardware-bound key export through trusted keystore.
- Trade-offs: portable escrow aids disaster recovery but theft risk; re-entry can
  strand old provider reconciliation; hardware binding may make NAS loss unrecoverable.
- Recommendation: independent encrypted backups plus separately protected recovery
  material and explicit new-installation rebinding; retain old identities/key versions,
  start integrations off until reconciliation/reverification. Re-entry is a documented
  fallback, not a substitute for lost financial/provider identity recovery.
- Resolve: design **RL-07**, acceptance **RL-09**, actual loss journey **RL-11**.

### PO-ADR-04 — safe settings migration

- Options: settings embedded in versioned app DB; separate versioned settings/secret
  store; hybrid bootstrap metadata outside DB with operational values inside.
- Trade-offs: single DB simplifies atomic audit but cannot serve broken-DB recovery;
  multiple stores need crash-safe consistency, lock/backup boundaries and versions.
- Recommendation: minimal DB-independent bootstrap/recovery metadata, typed operational
  settings bound to app migration ledger and explicit encrypted secret references;
  select exact layout only after atomicity/recovery review. No financial history rewrite
  or silent defaulting of failed settings migrations.
- Resolve: **RL-07**, compatible backup format evolution **RL-09**.

### PO-ADR-05 — ENV versus GUI precedence during transition

- Options: ENV always wins; explicit one-time import then GUI authority; explicit
  locked infrastructure overrides with conflicts shown.
- Trade-offs: ENV wins frustrates routine GUI use; silent import/empty fallback can
  change merchant/key on restart; overrides need ownership/version tracking.
- Recommendation: previewed explicitly authorized one-time import for operational
  values, GUI source/revision thereafter; documented narrowly locked infrastructure
  overrides. Define blank/clear/missing behavior, import secrecy, crash rollback and
  restart drift rejection; preserve original configuration for unresolved operations.
- Resolve: **RL-07**, SumUp transition **RL-08**; not approved automatic import.

### PO-ADR-06 — payment integration access control and endpoint trust

- Options: extend existing local admin PIN with fresh scoped grants; named roles/
  stronger sessions; external identity provider. Endpoint policy: official fixed host
  only, reviewed allowlist, or separately approved nonproduction sandbox override.
- Trade-offs: small auth change preserves compatibility but browser-held PIN is not
  fresh proof; new roles add migration/recovery cost; external identity dependency.
  Arbitrary endpoint flexibility risks credential exfiltration/SSRF/redirect/DNS attacks.
- Recommendation: server-verified action/revision-bound fresh PIN grant and explicit
  least-privilege admin actions; no inherited member/agent financial administration.
  Official HTTPS default, narrowly reviewed advanced allowlist/no private targets or
  cross-origin credential forwarding. Resolve exact auth/CSRF/replay/expiry policy.
- Resolve: foundation **RL-07**, payment/endpoint **RL-08**; OQ-01 agent authority separate.

### PO-ADR-07 — active/UNKNOWN operations during configuration change

- Options: block all material changes until reconciliation; freeze per-operation
  config and allow new revision with retained access; emergency disable/revoke with
  intervention-only reconciliation path.
- Trade-offs: strict block can impede emergency rotation; concurrent revisions need
  durable identity/credential lifetime and terminal ownership; revoked keys may prevent
  API verification. Local timeout/cancel/expiry cannot clear a provider hold.
- Recommendation: block unsafe material changes, allow stopping new creation without
  erasing old operations; immutable operation config identity and explicit authorized
  emergency-revocation/reconciliation path. Serialize with checkout commits, keep
  old references and minimum restricted access as policy allows; no silent overwrite.
- Resolve: **RL-08** before dynamic settings/acceptance; backup recovery **RL-09**.

### PO-ADR-08 — acceptance transaction classification and policy

- Options: isolated test records plus separate reconciled funds/fees account;
  classified entries in a shared ledger with strict revenue exclusion; provider-only
  receipts (insufficient durable local audit).
- Trade-offs: isolation prevents debt/revenue pollution but still needs money/fee
  accounting/export/recovery; shared ledger risks accidental beverage totals. Provider
  final cancellation semantics/evidence and test freshness may be account/API-specific.
- Recommendation: isolated durable acceptance model with immutable request/config and
  append-only provider reconciliation, separate accounting of funds/fees. No automatic
  refund. Verify provider limits/identity/cancellation contracts and define mandatory
  tests, evidence validity/expiry, material-change reacceptance and activation policy;
  UNKNOWN can pass timeout safety but remains an activation blocker.
- Resolve: **RL-08**, owner/accounting/security review before schema/runtime changes.

### PO-ADR-09 — internal maintenance/recovery execution boundary

- Options: one service with mutually exclusive normal/maintenance supervisor modes;
  short-lived isolated recovery process under narrow control; separate recovery service
  only if required to prove isolation.
- Trade-offs: one service simplifies deployment but must reliably stop every writer
  and persist progress independently of DB; separate process/service adds permissions/
  authentication/mount coordination. SQLite lock alone cannot quiesce file/mail work.
- Recommendation: prefer one service with proven process/writer isolation and durable
  independent control journal; require explicit safety justification if inadequate.
  Reuse EF-08 verify/new-root restore, no web shell/arbitrary path/active DB overwrite.
- Resolve: boundary design **RL-07**, orchestration **RL-09**; update reuse **RL-10**.

### PO-ADR-10 — browser recovery when DB/application cannot start

- Options: DB-independent recovery surface in trusted image; GUI-started exact
  recovery-capable image/project on fresh volume; host-vendor recovery integration.
- Trade-offs: same image can share failure cause; separate image/project requires
  provenance and GUI-only credential/key/state selection; vendor plugin reduces
  portability. Main-DB PIN/session cannot be the sole recovery authority.
- Recommendation: minimal DB-independent protected surface plus independently
  retained exact recovery-capable image and Container Manager GUI restart/new-project
  path; authenticated uploads/key import, fixed roots and controlled state selection.
  Prove ordinary-admin steps before selecting implementation, not assumed SSH fallback.
- Resolve: bootstrap design **RL-07**, complete journey **RL-09**, hardware **RL-11**.

### PO-ADR-11 — publication/versioning/image provenance

- Options: promote exact tested image to authenticated digest with release receipt;
  reproducible separately verified rebuild; continued archive-only distribution.
- Trade-offs: promotion needs registry access/review/channel/support/retention policy;
  rebuild is not byte identity without proof; archive workflow burdens ordinary setup.
- Recommendation: owner-approved version/channel/support policy and exact tested-artifact
  promotion with digest/source/platform/schema/CI/provenance receipt, independently
  retained images. Runtime ENV labels alone are not authenticated image identity.
  Publication permission/reviewers remain separate; no release/registry action here.
- Resolve: install identity/distribution prerequisites **RL-07** (with OQ-05/07),
  authenticated update metadata **RL-10**, real acquisition **RL-11**.

### PO-ADR-12 — limited-privilege update orchestration

- Options: app produces guided approved plan, operator executes via Container Manager
  GUI; restricted external one-installation executor; narrowly scoped vendor API/plugin.
- Trade-offs: GUI handoff is safe/simple but not fully one-click; executor adds host
  trust/authentication/replay/progress recovery; vendor API availability uncertain.
  Unrestricted Docker socket/privileged application is excluded.
- Recommendation: GUI-led readiness/approval with Container Manager handoff initially;
  evaluate bounded authenticated executor only with independently reviewed authority
  (fixed installation/actions/exact digest/one-time grant/no commands or arbitrary mounts).
  No general host administration; readiness must not grant install permission.
- Resolve: **RL-10**, validated GUI-only maintenance acceptance **RL-11**.

### PO-ADR-13 — HTTPS/TLS for PWA and safe administration

- Options: DSM reverse proxy/trusted certificate; private CA with GUI trust enrollment;
  restricted VPN plus trusted HTTPS; bundled TLS termination with reviewed lifecycle.
- Trade-offs: trusted domain/certificate renewal needs infrastructure; private CA
  device trust can confuse operators; VPN alone does not make HTTP PWA secure;
  bundled TLS adds keys/ports/renewal complexity.
- Recommendation: private LAN/VPN + trusted HTTPS through host GUI, no public exposure
  requirement; clear browser readiness checks/device trust/renewal guidance. HTTP
  remote LAN is not installed-PWA/admin-secret acceptance. Define secure first-claim
  transport and minimal safe bootstrap exposure before credentials are entered.
- Resolve: design **RL-07**, verification **RL-11**; not authorization for NAS/TLS changes.

### PO-ADR-14 — independent/offsite backup and immutable retention

- Options: GUI-guided encrypted download to independent storage; narrow authenticated
  remote replica adapter; NAS/storage-vendor snapshots/object lock under separate authority.
- Trade-offs: manual download risks missed copies; adapters add credentials/quotas/
  transport; same-NAS snapshots do not cover NAS loss. Private permissions are not WORM.
- Recommendation: reuse EF-08b/c, explicit independent copy/full verification/key-image
  escrow and timed recovery; bounded GUI retention only for verified owned copies
  with independently restorable survivors. Protect immutable/offsite metadata under
  separate authority and owner-selected retention/RPO/RTO; no audit-history purge.
- Resolve: preferences/key preparedness **RL-07**, recovery/retention **RL-09**,
  actual geography/immutability/operator evidence **RL-11**; OQ-03 remains separate.

## Confirmed decisions

RL-06 (owner-authorized isolated test delivery, not production): DP-025 ready gate
`docs/rl-06-contract.md`. Distribute the tested exact-checkout local AMD64 image
through non-publishing Actions archive; no registry/stable/timer change. New test
Compose uses internal network, explicitly isolated state, non-root test-owner UID/
GID, strong test PIN and one-time synthetic v2 initialization; no automatic seeding
or update. Reuse EF-08b/c full recovery and exact-image isolated compatibility gates.
Same-schema compatibility needs evidence/approval, not age/name inference; failed
state and post-backup financial activity must be preserved. Actual NAS/HTTPS/devices/
offsite/operator acceptance stays pending. PR must remain OPEN/UNMERGED.

| ID | Decision / evidence | Consequence |
| --- | --- | --- |
| D-01 | Retain FastAPI/direct sqlite3/WAL/vanilla PWA and authoritative served legacy handlers (owner foundation scope; ARCHITECTURE.md EF-ADR-001) | No architectural transplant; parity tests precede one-seam migrations |
| D-02 | Preserve immediate round approval/charge as observed API contract (`legacy_main.create_round_request`; existing and HTTP tests) | Correct operating-agent docs; do not silently add approvals/change debt rules |
| D-03 | Independent branch was created from verified `fb08128`; owner subsequently merged PR #1 as `052c2bb` and authorized integration | Merge verified main into foundation before delivery, preserve history/work |
| D-04 | PR/main checks never publish; explicit approved main dispatch separates verified image publication | Keep stable/latest naming and deployment compatibility; no dispatch/deploy in this assignment |
| D-05 | Mandatory Ruff/syntax/unittest/browser/security/container gates, mechanical format debt isolated | No ignores to hide meaningful errors; local/CI/manual evidence labeled separately |
| D-06 | Owner approves PR #2 merge only after final pushed-HEAD checks, then main-CI/tree verification | Mark ready, use normal reviewed integration without bypass; no release/publication/deployment |
| D-07 | Next intended session is database backup, restore and data integrity | Prepare bounded EF-08 recovery handoff only; implement nothing from it during finalization |
| D-08 | Owner approved bounded EF-08a implementation on 2026-11-23 | Full SQLite plus unchanged CSV in atomic bundles; new-target-only restore; count retention opt-in (minimum two); no production/deployment/mail redesign |
| D-09 | EF-08b uses explicit all-writer maintenance quiescence, observed change checks and a distinct application bundle contract | No online/DB-lock-only consistency claim; preserve event CSV→PDF→SMTP→commit behavior; exact artifact relocation only, no side-effect redesign |
| D-10 | Application recovery core is filesystem/one-shot CLI only, atomic no-replace publication on Linux/Windows; no new retention | Scheduling/transport/encryption/independent copies remain operator-controlled; unsupported publication semantics fail closed; no production adoption |
| D-11 | EF-08c optional encrypted filesystem replicas use established external age and standard tar, unchanged EF-08b bundle inside; PR #5 correction makes producer public-key-only | v2 marker means encrypted transfer only; separate private-key full verification, explicit trusted independent/offsite receipts; combined verification opt-in, no immutable/geography proof |
| D-12 | Complete installation-loss rehearsal removes only owned synthetic source storage, preserves compatible image/key escrow independently and gates network-disabled startup on explicit synthetic reconciliation | Synthetic RPO/RTO reported separately from operational guarantees; Windows EF-08a rename issue remains a separate reliability follow-up |
| D-13 | RL-01 preflight is standalone, explicit isolated EF-08b bundle only, exact identities/schema/installation/config and trusted key/compatibility evidence; unknown non-success | No live-state/default discovery, migrations, deployment or automatic rollback; readiness approves rehearsal only. Existing startup/deployment defaults preserved. |
| D-14 | RL-01 characterizes existing partial DDL and repeatable purchase-cost backfills without rewriting migrations; digest/version evidence remains nullable until actually available | Synthetic fixtures are not authentic release evidence. Versioned migrations/pre-write gate and tested-image promotion require separate RL-02/release decisions. |

## Unresolved decisions (not implementation authorization)

**D-17 RL-05 owner decision (2026-11-24):** normal consumption reports use actual net
consumption after approved erroneous-booking corrections, original-period attribution
and separate immutable originals/correction audit. Negative admin identity/purpose
mandatory, explicit correction-only pay success; no unkeyed retry guarantee. Addendum:
round cancellation is coordinated, stable unit/deduction provenance and exact once-only
compensation; paid/closed/unknown/legacy ambiguity fail closed, no provider refund,
inventory return or reopened settled debt. Actual additive v2 authorized only synthetic
implementation; no extra historic fingerprint/production migration/merge approval.
OQ-06 remains open for other policies/adoption/historical gaps; FH-05 remains open.

**RL-04 D-16 (2026-11-24):** owner approves routine historical snapshot preservation
only, including zero/nonzero/unusual round snapshots; missing defaults initialize,
existing default zero master is retained. Admin edits and startup do not infer past
costs. Paid reports read present stored profit including zero; operational formulas
stay unchanged. FH-04 characterization only: signed correction-detail semantics are
not unambiguous. No historical repair/reconstruction/inferred-cost storage/additional
adoption/v2/production operations. This supersedes RL-03 NOT-approved wording below
only for this bounded authorization. **OQ-06 remains OPEN** for separate questions;
FH-04/05 and EF-08a Windows WinError 5 remain unresolved. See rl-04-contract and
correction-audit-contract for exact boundaries.

RL-03 integration (2026-11-24): owner completed independent PR #8 evidence review
and explicitly approved guarded merge of reviewed `0b43f379...`; merged
`9d09015b2d83d652d88b283ef9f5ab45050128bf`, exact reviewed tree preserved.
**OQ-06 remains OPEN.** This approval accepts the evidence package only, **not**
snapshot rewrite prevention, accounting/reporting policy, inferred-cost storage,
append-only corrections, historical repair, new migrations/schema allowlists or
production rollout. FH-01..FH-06 and severities remain open; preserve-original
recommendation below stays **PROPOSED/NOT APPROVED**. No next work package authorized.

RL-03 proposal (2026-11-23), **not approved**: [financial-history decision record](docs/financial-history-policy.md)
compares A exact originals, B separate provenance-labelled inference, C controlled
corrections. Recommend A preservation invariant plus separately authorized B;
defer C, prefer additive corrections if required. Existing legacy startup **and served
item-update API** overwrite historical zeros/cost/profit; versioned startup does not
protect the API. No accounting/migration/adoption implementation here. Source-only
inventory finds eight fresh schemas and an ALTER-fee variant, **no authenticated
historical DB/release image**; no support widened. OQ-06 remains owner-pending.

RL-02 D-15 (2026-11-23): implement smaller opt-in baseline contract rather than
mandatory historical migrations. Fresh explicit initialization and exact-current
metadata-only adoption → v1, DELETE journal mode, no repeated existing financial/
default normalization, transactional ledger, no automatic WAL recovery. Default
legacy remains unchanged. Rollout must be separately reviewed. OQ-06's ledger seam
is implemented, but authentic historical support, adoption breadth, legitimate-zero/
round-cost/prototype-history policy and production adoption remain **unresolved**.
No new accounting interpretation is authorized by implementation/test success.

- **OQ-01 — agent financial authority:** Should token-operating agents immediately
  charge rounds or require a separate consent/role? Current behavior is confirmed
  but can incur debt. Owner must decide; EF-05, not this foundation.
- **OQ-02 — uncertain SMTP side effects:** What retry/reconciliation policy is
  acceptable when files/mail precede DB closure? No exactly-once claim; avoid blind
  retries or duplicate invoices. EF-08 needs explicit acceptance.
- **OQ-03 — recovery scope:** What retention/export verification is required for
  all operational tables and separate event files? Synthetic rehearsal first;
  production recovery remains independently authorized.
- **OQ-04 — legacy module ownership:** Which one seam should migrate first after
  parity coverage? Extracted helpers are not automatically runtime equivalents.
- **OQ-05 — release protection:** Owner must configure required reviewers for
  `production-images` and select merge-required checks. No settings change or
  production release is authorized by this PR.
- **OQ-06 — financial preservation and adoption breadth:** RL-02 opt-in ledger/
  transaction gate is integrated. Remaining owner choice: original zero/nonzero/
  round snapshots, explicit unknown/inference provenance, corrections/report basis,
  authentic historical sources and exact supported adoption paths. RL-03 supplies
  evidence/options, not approval. Image downgrade on newer state is not safe rollback.
- **OQ-07 — product release identity:** Choose human version/channel/support policy,
  authenticated historical fixtures and exact tested-artifact promotion/provenance/
  digest receipt. Current mutable base/dependencies and separate publish rebuild
  do not prove reproducibility; no registry publication is authorized in RL-01.

Unresolved entries stay visible; they do not block adding the non-invasive
foundation or become inferred requirements just because they appear here.
