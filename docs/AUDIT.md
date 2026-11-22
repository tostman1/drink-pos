# Technical audit — evidence, not a rewrite mandate

Audit of previous main `fb08128`, transfer `250a4e6`, and owner-merged main
`052c2bb`. Takeover/diff details in HANDOFF.md; requirements in ../REQUIREMENTS.md.
Observed results are dated in PROGRESS.md; no invented coverage percentages.

| Finding | Evidence | Risk / treatment |
| --- | --- | --- |
| Compatibility shell, partial extraction | main alias, application reload/copy lifecycle, registry mounts legacy APIRoutes | Authoritative runtime remains legacy; HTTP regression protects real seam |
| Extracted orders/payments/rounds differ | orders filters event_open debt, payments simplified, rounds creates PENDING | Do not mount/replace based on module naming; characterize per migration |
| Agent round-request immediately approves/charges | served create_round_request and agent delegation; test_round_and_cashup_flow | Confirmed contract, potential financial authorization risk; document/test, no silent change (OQ-01) |
| Financial debt differs from current tally | positive order_lines vs event_open, cashup/payment handlers | Guard historical debt through cashup, archived items and snapshot settlement |
| DB/audit invariants exist | explicit transaction/commit, FK/WAL/timeout, audit details, transfer correction tests | Add served HTTP rollback/stale/event tests; never use production DB |
| Core operational features already exist | exports, messages, sync polling, OpenAPI, backup/restore, named events/invoices | Historical "missing feature" claims are stale; do not implement duplicates |
| Config/import/schema globals persist | legacy reload, duplicate config, schema.configure_runtime | Tests isolate/restores globals; one-seam follow-up, not mass DI refactor |
| Startup lifecycle/TestClient deprecations | observed warnings under current dependency resolution | Retain visible warnings; dependency/lifecycle follow-up with parity |
| Static modules are scaffolding | no static/js references in current HTML | Syntax-check and preserve; no claim of completed frontend migration |
| Limited auth boundary | local-network PIN and token, rate limit in memory | Not public-product security; confirmed agent charge risk separately reviewed |
| Non-atomic artifacts/mail/DB | CSV→PDF→SMTP→close, existing failure tests | Keep ordering, uncertain-delivery risk; no blind retry/exactly-once promises |
| All-branch image publication in old CI | original container.yml push:true/packages:write/login | Split read-only checks from explicit approved publication; keep tags, no deployment |
| Device/external proof absent | backend mocks, original unfinished tablet/cache/SMTP items | Manual MV-01..06 remain pending despite owner merge or green CI |

## Verification limits

Previous main **87 tests**, handoff **96 tests**, initial foundation **100 tests**.
Those measured counts are not line/branch coverage percentages. HTTP tests add
assembled ASGI startup/routing/serialization coverage; browser smoke uses disposable
Chromium, not target iPad/mobile or installed-PWA upgrade proof. Container evidence
must come from actual GitHub execution; no local runtime is installed. Dependency
audit is an advisory-database check, not penetration testing or full supply-chain
assurance. Hardware/real mail/account/database operations remain out of scope.
