# Decisions and open questions

## Confirmed decisions

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

## Unresolved decisions (not implementation authorization)

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

Unresolved entries stay visible; they do not block adding the non-invasive
foundation or become inferred requirements just because they appear here.
