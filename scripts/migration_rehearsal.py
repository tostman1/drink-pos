"""RL-02 synthetic-only actual-image migration/repeat/recovery evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sqlite3
import sys
from contextlib import closing
from pathlib import Path


def worker(target: Path, commit: str) -> dict:
    if sys.flags.optimize or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Exact commit and enabled assertions required")
    for p in (target, *target.parents):
        if os.path.lexists(p) and (p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Synthetic root must not use links/reparse points")
    target.mkdir(mode=0o700)
    for key in list(os.environ):
        if key.startswith(("DRINK_POS_", "SUMUP_", "SMTP_", "PAYMENT_PROVIDER")):
            del os.environ[key]
    os.environ.update(
        DRINK_POS_DB=str(target / "source.db"),
        DRINK_POS_MESSAGES=str(target / "messages.json"),
        DRINK_POS_PIN="847296",
        DRINK_POS_ENV="production",
    )
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "app"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import main
    from application_recovery import create_backup, verify_application_bundle, restore_application, database_metadata
    from db.migrations import inspect
    from disaster_fixture import seed

    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("Network forbidden")

    socket.socket.connect = forbidden
    # Fresh served startup and repeated initialization in the installed image.
    os.environ.update(DRINK_POS_MIGRATION_MODE="versioned", DRINK_POS_ALLOW_FRESH="1")
    original_path = main.DB_PATH
    main.DB_PATH = str(target / "fresh.db")
    main.startup()
    fresh_before = database_metadata(Path(main.DB_PATH))
    main.startup()
    assert database_metadata(Path(main.DB_PATH)) == fresh_before
    assert inspect(Path(main.DB_PATH))["state"] == "versioned-current"
    main.DB_PATH = original_path
    os.environ["DRINK_POS_MIGRATION_MODE"] = "legacy"
    os.environ.pop("DRINK_POS_ALLOW_FRESH")
    main.startup()
    seed()
    database = Path(main.DB_PATH)
    with closing(sqlite3.connect(database)) as conn:
        # Fixture-only audit trigger/index are outside exact adoption support.
        conn.execute("DROP TRIGGER dr_keep_audit")
        conn.execute("DROP INDEX dr_payment_identity")
        conn.execute("UPDATE order_lines SET unit_purchase_price_eur=0")
        conn.execute("UPDATE transaction_items SET unit_purchase_price_eur=0,purchase_total_eur=0,profit_eur=total_eur")
        conn.commit()
        conn.execute("PRAGMA journal_mode=DELETE")
    before = database_metadata(database)
    before_api = main.list_people(), main.config(), main.event_active()
    bundle = create_backup(
        database,
        target / "messages.json",
        target / "backups",
        deployment_id="rl02-synthetic",
        app_commit=commit,
        quiesced=True,
    )
    manifest = verify_application_bundle(bundle)
    os.environ.update(DRINK_POS_MIGRATION_MODE="versioned", DRINK_POS_ADOPT_LEGACY="1")
    main.startup()
    assert inspect(database)["state"] == "versioned-current"
    with closing(sqlite3.connect(database)) as conn, closing(sqlite3.connect(bundle / "state/database.db")) as original:
        for table in before["tables"]:
            assert (
                conn.execute(f'SELECT * FROM "{table}"').fetchall()
                == original.execute(f'SELECT * FROM "{table}"').fetchall()
            ), table
    assert (main.list_people(), main.config(), main.event_active()) == before_api
    after = database_metadata(database)
    main.startup()
    assert after == database_metadata(database)
    recovered = restore_application(
        bundle,
        target / "independent-recovery",
        expected_commit=commit,
        expected_schema=manifest["database"]["schema_sha256"],
    )
    assert (
        database_metadata(
            recovered / "state/database.db", immutable=True, original_references=manifest["event_references"]
        )
        == manifest["database"]
    )
    assert not attempts
    result = dict(
        status="synthetic-versioned-migration-verified",
        commit=commit,
        schema_version=1,
        original_tables_preserved=len(before["tables"]),
        history_rewritten=False,
        repeat_startup_verified=True,
        recovery_verified=True,
        network_attempts=0,
        production_authorized=False,
        historical_release_evidence="none; exact synthetic current fixture only",
    )
    (target / "RESULT.json").write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.synthetic_only:
        parser.error("Synthetic-only opt-in required")
    print(json.dumps(worker(args.target.absolute(), args.commit), sort_keys=True))


if __name__ == "__main__":
    main()
