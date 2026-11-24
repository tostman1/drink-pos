"""Explicit isolated-test operations. No production defaults or automatic updates.

Run with python -B. Trusted dedicated test mount/parents and stopped writers are
operator boundaries, not established by a marker. No exception content is logged.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

try:
    from app.application_recovery import (
        create_backup,
        read_json,
        reject_links,
        restore_application,
        verify_application_bundle,
        write_json,
    )
    from app.db.migrations import CURRENT_SCHEMA, inspect
    from app.release_identity import release_identity
    from app.upgrade_preflight import evaluate
except ImportError:
    from application_recovery import (
        create_backup,
        read_json,
        reject_links,
        restore_application,
        verify_application_bundle,
        write_json,
    )
    from db.migrations import CURRENT_SCHEMA, inspect
    from release_identity import release_identity
    from upgrade_preflight import evaluate

MARKER = "TEST-INSTALLATION.json"


def configuration(*, fresh: bool = False) -> tuple[Path, Path, str]:
    env = os.environ
    identity = env.get("DRINK_POS_TEST_ID", "")
    root = Path(env.get("DRINK_POS_TEST_ROOT", ""))
    state_name = env.get("DRINK_POS_TEST_STATE", "data")
    if (
        not root.is_absolute()
        or not root.is_dir()
        or not re.fullmatch(r"drink-pos-test-[a-z0-9-]{1,40}", identity)
        or not re.fullmatch(r"(?:data|recovery/[a-zA-Z0-9_-]+/state)", state_name)
    ):
        raise ValueError("Explicit test identity and isolated existing root required")
    reject_links(root)
    state = root / state_name
    reject_links(state)
    pin = env.get("DRINK_POS_PIN", "")
    if (
        not re.fullmatch(r"[0-9]{10,20}", pin)
        or len(set(pin)) < 6
        or any(sequence in pin for sequence in ("123456", "654321", "012345", "987654"))
    ):
        raise ValueError("Strong random test-only PIN required")
    # Bounded supported IANA identifiers, also validated against libc in image CI.
    # Windows development hosts need not have a system zoneinfo installation.
    if env.get("TZ") not in {"Europe/Zurich", "Europe/Berlin", "Europe/Vienna", "UTC"}:
        raise ValueError("Explicit supported timezone required")
    expected = {
        "DRINK_POS_ENV": "production",
        "DRINK_POS_DB": str(state / "database.db"),
        "DRINK_POS_MESSAGES": str(state / "messages.json"),
        "DRINK_POS_BACKUP_DIR": str(root / "backups"),
        "DRINK_POS_MIGRATION_MODE": "versioned",
        "DRINK_POS_ADOPT_LEGACY": "0",
        "DRINK_POS_ALLOW_FRESH": "1" if fresh else "0",
    }
    if any(env.get(key) != value for key, value in expected.items()):
        raise ValueError("Test paths/migration permissions must be explicit")
    for key, value in env.items():
        if value and (
            key.startswith(("SUMUP_", "SMTP_", "DRINK_POS_SMTP_"))
            or key in {"PAYMENT_PROVIDER", "DRINK_POS_AGENT_TOKEN"}
        ):
            raise ValueError("Provider/mail/agent configuration forbidden")
    if env.get("DRINK_POS_ALLOW_TEST_CARD_PAYMENTS", "0") != "0":
        raise ValueError("Card simulation is not enabled in acceptance installation")
    release_identity(env.get("APP_BUILD_COMMIT", ""), "synology-test", None)
    if env.get("DRINK_POS_IMAGE_REF") != "drink-pos-test:" + env["APP_BUILD_COMMIT"]:
        raise ValueError("Exact source-bound imported test image tag required")
    return root, state, identity


def marker(identity: str) -> dict:
    return {
        "format": "drink-pos-test-installation",
        "version": 1,
        "deployment_id": identity,
        "initialized_commit": os.environ["APP_BUILD_COMMIT"],
        "synthetic_only": True,
    }


def inspect_installation() -> dict:
    _, state, identity = configuration()
    value = read_json(state / MARKER)
    if (
        set(value) != set(marker(identity))
        or value.get("format") != "drink-pos-test-installation"
        or value.get("version") != 1
        or value.get("deployment_id") != identity
        or value.get("synthetic_only") is not True
        or not re.fullmatch(r"[0-9a-f]{40}", value.get("initialized_commit", ""))
    ):
        raise ValueError("Test installation marker mismatch")
    result = inspect(state / "database.db")
    if result["state"] != "versioned-current" or result["application_schema_sha256"] != CURRENT_SCHEMA:
        raise ValueError("Only exact current v2 installation supported; no downgrade/adoption")
    read_json(state / "messages.json")
    return {
        "status": "verified-test-installation",
        "deployment_id": identity,
        "migration": result,
        "release": release_identity(os.environ["APP_BUILD_COMMIT"], "synology-test", None),
        "deployment_authorized": False,
    }


def initialize(*, synthetic_only: bool = False) -> dict:
    root, state, identity = configuration(fresh=True)
    if not synthetic_only or state != root / "data" or (state.exists() and any(state.iterdir())):
        raise ValueError("Synthetic opt-in and empty initial data target required; no reseeding")
    for name in ("backups", "recovery", "evidence"):
        reject_links(root / name)
        if (root / name).exists() and any((root / name).iterdir()):
            raise ValueError("Initial test directories must be empty")
    # Existing authoritative initializer provides synthetic Demo Person/default items.
    # No application startup, HTTP, provider/mail or financial records are created.
    try:
        from app.db.schema import init_db
    except ImportError:
        from db.schema import init_db
    init_db()
    if inspect(state / "database.db")["state"] != "versioned-current":
        raise ValueError("Fresh v2 verification failed; preserve failed target")
    read_json(state / "messages.json")  # Optional runtime fallback is insufficient here.
    for name in ("backups", "recovery", "evidence"):
        (root / name).mkdir(mode=0o700, exist_ok=True)
    write_json(state / MARKER, marker(identity))
    return {"status": "initialized-synthetic-v2", "deployment_id": identity, "fresh_permission": "remove-before-serve"}


def backup(*, quiesced: bool) -> dict:
    inspected = inspect_installation()
    root, state, identity = configuration()
    path = create_backup(
        state / "database.db",
        state / "messages.json",
        root / "backups",
        deployment_id=identity,
        app_commit=inspected["release"]["git_commit"],
        quiesced=quiesced,
        configuration={"DRINK_POS_ENV": "production", "TZ": os.environ["TZ"], "PAYMENT_PROVIDER": ""},
    )
    return {"status": "verified", "bundle": str(path), "backup_id": path.name}


def restore(bundle: Path, name: str, *, approved: bool) -> dict:
    root, _, identity = configuration()
    if not approved or not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", name):
        raise ValueError("Explicit full-state recovery approval and new target required")
    manifest = verify_application_bundle(bundle)
    if manifest["deployment_id"] != identity:
        raise ValueError("Different installation backup rejected")
    if inspect(bundle / "state/database.db")["state"] != "versioned-current":
        raise ValueError("Full test recovery requires exact v2 state")
    target = root / "recovery" / name
    restore_application(
        bundle,
        target,
        expected_commit=os.environ["APP_BUILD_COMMIT"],
        expected_schema=manifest["database"]["schema_sha256"],
    )
    # EF-08b does not include deployment marker or secrets. Explicit test wrapper
    # establishes a new test marker only after verified full recovery.
    write_json(target / "state" / MARKER, marker(identity))
    return {
        "status": "recovered-not-started",
        "state": "recovery/" + name + "/state",
        "backup_id": manifest["backup_id"],
        "reconciliation_required": True,
    }


def preflight(
    bundle: Path,
    current: dict,
    candidate: dict,
    evidence: dict,
    *,
    isolated_copy: bool,
    key_receipt: dict | None = None,
) -> dict:
    """Read-only isolated bundle evaluation, never installation authorization."""
    running = release_identity(os.environ.get("APP_BUILD_COMMIT", ""), "synology-test", None)
    if candidate != running or evidence.get("permitted_changes") != []:
        raise ValueError("Exact executing candidate image and no-change compatibility evidence required")
    migration = inspect(bundle / "state/database.db")
    if migration["state"] != "versioned-current" or migration["application_schema_sha256"] != CURRENT_SCHEMA:
        raise ValueError("Only verified v2 same-schema update; other paths require separate migration decision")
    return evaluate(
        bundle=bundle,
        current=current,
        candidate=candidate,
        evidence=evidence,
        isolated_copy=isolated_copy,
        mode="local",
        max_backup_age_seconds=86400,
        key_receipt=key_receipt,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect")
    commands.add_parser("identity")
    commands.add_parser("serve")
    commands.add_parser("initialize").add_argument("--synthetic-only", action="store_true")
    commands.add_parser("backup").add_argument("--quiesced", action="store_true")
    commands.add_parser("verify").add_argument("bundle", type=Path)
    recovery = commands.add_parser("restore")
    recovery.add_argument("bundle", type=Path)
    recovery.add_argument("name")
    recovery.add_argument("--approve-full-recovery", action="store_true")
    check = commands.add_parser("preflight")
    for name in ("bundle", "current", "candidate", "evidence"):
        check.add_argument("--" + name, type=Path, required=True)
    check.add_argument("--isolated-copy", action="store_true")
    check.add_argument("--key-receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "identity":
            result = release_identity(os.environ.get("APP_BUILD_COMMIT", ""), "synology-test", None)
        elif args.command == "initialize":
            result = initialize(synthetic_only=args.synthetic_only)
        elif args.command in {"inspect", "serve"}:
            result = inspect_installation()
            if args.command == "serve":
                import uvicorn

                uvicorn.run("main:app", host="0.0.0.0", port=8000)
        elif args.command == "backup":
            result = backup(quiesced=args.quiesced)
        elif args.command == "restore":
            result = restore(args.bundle, args.name, approved=args.approve_full_recovery)
        elif args.command == "preflight":
            result = preflight(
                args.bundle,
                read_json(args.current),
                read_json(args.candidate),
                read_json(args.evidence),
                isolated_copy=args.isolated_copy,
                key_receipt=read_json(args.key_receipt) if args.key_receipt else None,
            )
        else:
            manifest = verify_application_bundle(args.bundle)
            result = {
                "status": "verified",
                "backup_id": manifest["backup_id"],
                "app_commit": manifest["app_commit"],
                "schema_sha256": manifest["database"]["schema_sha256"],
            }
        print(json.dumps(result, sort_keys=True))
        return result.get("exit_code", 0)
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, RuntimeError):
        print(json.dumps({"status": "blocked-preserve-state", "command": args.command}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
