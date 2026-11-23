"""Read-only readiness check of an attested isolated EF-08b snapshot bundle.

Never approves deployment, opens live state, runs startup, decrypts, or invokes
container/network commands. Evidence authenticity and writer isolation are operator
boundaries. Run with python -B to suppress interpreter bytecode cache writes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from app.application_recovery import digest_json, read_json, regular_file, verify_application_bundle
    from app.release_identity import FORMAT
except ImportError:
    from application_recovery import digest_json, read_json, regular_file, verify_application_bundle
    from release_identity import FORMAT

EXITS = {"rehearsal-ready": 0, "intervention-required": 3, "unknown": 4, "unsafe": 2}
SHA = r"[0-9a-f]{64}"
IMAGE = r"[A-Za-z0-9./:_-]+@sha256:" + SHA
IDENTITY_KEYS = {
    "format",
    "format_version",
    "git_commit",
    "version",
    "channel",
    "image_ref",
    "migration_code_sha256",
    "python",
    "application_bundle_version",
    "schema_version",
}
STATE_TABLES = {
    "settings",
    "people",
    "items",
    "order_lines",
    "change_requests",
    "round_requests",
    "member_messages",
    "member_message_recipients",
    "transactions",
    "client_operations",
    "self_payment_sessions",
    "paid_round_units",
    "transaction_items",
    "round_events",
    "event_sessions",
    "event_lines",
}


def snapshot_guard(bundle: Path) -> None:
    # ALL checks precede SQLite opens. Do not set immutable=1 on active WAL state.
    database = bundle / "state/database.db"
    regular_file(database)
    for suffix in ("-wal", "-shm", "-journal"):
        if os.path.lexists(Path(str(database) + suffix)):
            raise ValueError("SQLite sidecars are not an offline snapshot")
    with database.open("rb") as source:
        header = source.read(100)
    if len(header) != 100 or header[:16] != b"SQLite format 3\0" or header[18:20] != b"\x01\x01":
        raise ValueError("Expected completed rollback-journal snapshot")


def evaluate(
    *,
    bundle: Path,
    current: dict,
    candidate: dict,
    evidence: dict,
    isolated_copy: bool,
    mode: str,
    max_backup_age_seconds: float,
    key_receipt: dict | None = None,
) -> dict:
    checks = []

    def issue(code, status):
        checks.append({"code": code, "status": status})

    def finish():
        statuses = {entry["status"] for entry in checks}
        status = next((s for s in ("unsafe", "unknown", "intervention-required") if s in statuses), "rehearsal-ready")
        return {
            "format": "drink-pos-preflight",
            "format_version": 1,
            "status": status,
            "exit_code": EXITS[status],
            "checks": checks,
            "deployment_authorized": False,
            "scope": "isolated-offline-bundle-only; operator-trusted-evidence",
        }

    if isolated_copy is not True:
        issue("isolation-not-attested", "unknown")
        return finish()
    if (
        mode not in {"local", "production"}
        or not isinstance(max_backup_age_seconds, (int, float))
        or not math.isfinite(max_backup_age_seconds)
        or max_backup_age_seconds <= 0
    ):
        issue("invalid-assessment-policy", "unknown")
        return finish()
    try:
        snapshot_guard(bundle)
        manifest = verify_application_bundle(bundle)
    except FileNotFoundError:
        issue("backup-unavailable", "unknown")
        return finish()
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        issue("backup-corrupt-incomplete-or-not-snapshot", "unsafe")
        return finish()
    except OSError:
        issue("backup-unreadable", "unknown")
        return finish()
    issue("full-bundle-integrity-inventory-verified", "rehearsal-ready")
    if not STATE_TABLES.issubset(manifest["database"]["tables"]):
        issue("required-application-state-tables-missing", "unsafe")
    for name, identity in (("current", current), ("candidate", candidate)):
        if not isinstance(identity, dict) or set(identity) != IDENTITY_KEYS:
            issue(name + "-identity-missing-or-unsupported", "unknown")
            continue
        if (
            identity["format"] != FORMAT
            or type(identity["format_version"]) is not int
            or identity["format_version"] != 1
            or identity["application_bundle_version"] != 1
            or identity["schema_version"] is not None
        ):
            issue(name + "-identity-format-unsupported", "unknown")
        for field, pattern in (
            ("git_commit", r"[0-9a-f]{40}"),
            ("migration_code_sha256", SHA),
            ("channel", r"[a-z][a-z0-9-]{0,39}"),
        ):
            if not isinstance(identity[field], str) or not re.fullmatch(pattern, identity[field]):
                issue(name + "-identity-invalid", "unknown")
        if (
            not isinstance(identity["python"], list)
            or not identity["python"]
            or any(not isinstance(v, str) or v not in {"3.12", "3.13"} for v in identity["python"])
        ):
            issue(name + "-runtime-unsupported", "unknown")
        if identity["version"] is None:
            if mode == "production":
                issue(name + "-version-unassigned", "unknown")
        elif not isinstance(identity["version"], str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,79}", identity["version"]
        ):
            issue(name + "-version-invalid", "unknown")
        image = identity["image_ref"]
        if not image:
            if mode == "production":
                issue(name + "-published-image-evidence-missing", "unknown")
        elif not isinstance(image, str) or not re.fullmatch(IMAGE, image):
            issue(name + "-image-not-digest-pinned", "unsafe")
    if any(c["status"] in {"unsafe", "unknown"} for c in checks):
        return finish()
    if manifest["app_commit"] != current["git_commit"] or manifest["image_ref"] != (current["image_ref"] or ""):
        issue("backup-current-release-mismatch", "unsafe")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(manifest["started_at_utc"])).total_seconds()
    if not 0 <= age <= max_backup_age_seconds:
        issue("backup-age-outside-policy", "intervention-required")
    if not manifest["messages_present"]:
        issue("runtime-messages-missing", "intervention-required")
    required = {
        "format",
        "format_version",
        "deployment_id",
        "current_identity_sha256",
        "candidate_identity_sha256",
        "source_schema_sha256",
        "target_schema_sha256",
        "supported",
        "approved_by",
        "permitted_changes",
        "candidate_configuration",
        "target_python",
        "secrets_recovery_verified",
        "encryption_required",
    }
    if (
        not isinstance(evidence, dict)
        or set(evidence) != required
        or evidence.get("format") != "drink-pos-upgrade-evidence"
        or type(evidence.get("format_version")) is not int
        or evidence.get("format_version") != 1
    ):
        issue("exact-compatibility-evidence-missing-or-unsupported", "unknown")
        return finish()
    if evidence["deployment_id"] != manifest["deployment_id"]:
        issue("installation-mismatch", "unsafe")
    if evidence["current_identity_sha256"] != digest_json(current) or evidence[
        "candidate_identity_sha256"
    ] != digest_json(candidate):
        issue("compatibility-release-identity-mismatch", "unsafe")
    if evidence["supported"] is False:
        issue("explicitly-unsupported-path", "unsafe")
    elif (
        evidence["supported"] is not True
        or not isinstance(evidence["approved_by"], str)
        or not evidence["approved_by"].strip()
    ):
        issue("compatibility-not-approved", "unknown")
    if evidence["source_schema_sha256"] != manifest["database"]["schema_sha256"]:
        issue("unsupported-source-schema", "unsafe")
    if evidence["target_schema_sha256"] != evidence["source_schema_sha256"]:
        issue("schema-transition-needs-versioned-migration-decision", "unknown")
    if not isinstance(evidence["permitted_changes"], list) or any(
        not isinstance(c, str) or not c for c in evidence["permitted_changes"]
    ):
        issue("permitted-state-changes-unspecified", "unknown")
    if evidence["candidate_configuration"] != read_json(bundle / "configuration.json"):
        issue("configuration-change-needs-review", "intervention-required")
    if evidence["target_python"] not in candidate["python"]:
        issue("runtime-baseline-conflict", "intervention-required")
    if evidence["secrets_recovery_verified"] is not True:
        issue("independent-secrets-recovery-unverified", "intervention-required")
    if type(evidence["encryption_required"]) is not bool:
        issue("encryption-policy-unknown", "unknown")
    elif evidence["encryption_required"]:
        expected = {
            "backup_id": manifest["backup_id"],
            "deployment_id": manifest["deployment_id"],
            "app_commit": manifest["app_commit"],
            "schema_sha256": manifest["database"]["schema_sha256"],
            "verification_level": "decrypted-application-verified",
        }
        if (
            not isinstance(key_receipt, dict)
            or any(key_receipt.get(k) != v for k, v in expected.items())
            or key_receipt.get("verification_scope") not in ("independent", "offsite")
            or not isinstance(key_receipt.get("verifier_id"), str)
            or not key_receipt["verifier_id"].strip()
        ):
            issue("independent-full-key-verification-evidence-missing", "unknown")
        else:
            try:
                timestamp = datetime.fromisoformat(key_receipt["verified_at_utc"])
                if timestamp.tzinfo is None or not datetime.fromisoformat(
                    manifest["created_at_utc"]
                ) <= timestamp <= datetime.now(timezone.utc):
                    raise ValueError
            except (ValueError, TypeError, KeyError):
                issue("key-verification-time-invalid", "unknown")
    # Defense in depth against observed change; trusted read-only parents are still
    # required, these checks are not a hostile-writer/TOCTOU security protocol.
    try:
        snapshot_guard(bundle)
        if verify_application_bundle(bundle) != manifest:
            issue("bundle-changed-during-inspection", "unsafe")
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        issue("bundle-changed-during-inspection", "unsafe")
    return finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "current", "candidate", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--key-receipt", type=Path)
    parser.add_argument("--isolated-copy", action="store_true")
    parser.add_argument("--mode", choices=("local", "production"), required=True)
    parser.add_argument("--max-backup-age-seconds", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(
            bundle=args.bundle,
            current=read_json(args.current),
            candidate=read_json(args.candidate),
            evidence=read_json(args.evidence),
            key_receipt=read_json(args.key_receipt) if args.key_receipt else None,
            isolated_copy=args.isolated_copy,
            mode=args.mode,
            max_backup_age_seconds=args.max_backup_age_seconds,
        )
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        result = {
            "status": "unknown",
            "exit_code": 4,
            "checks": [{"code": "input-unavailable-or-invalid", "status": "unknown"}],
            "deployment_authorized": False,
        }
    except KeyboardInterrupt:
        result = {
            "status": "unknown",
            "exit_code": 130,
            "checks": [{"code": "interrupted", "status": "unknown"}],
            "deployment_authorized": False,
        }
    print(json.dumps(result, sort_keys=True))
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
