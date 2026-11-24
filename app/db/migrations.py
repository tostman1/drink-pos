"""Opt-in, SQLite-native baseline contract. No application/configuration imports.

Existing state must be quiesced, clean rollback-journal SQLite. Active WAL/hot
journals are intervention, never inspected with immutable reads or auto-repaired.
Only fresh initialization and exact-current metadata adoption are implemented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

VERSION = 2
APPLICATION_ID = 0x44504F53
# Exact sqlite_master fingerprint of synthetic current baseline at 65d7a869.
# No custom triggers/indexes/prototype tables, no historical-release claim.
BASELINE_SCHEMA = "090ea55aa19289c833f2010950722d4eb443c1b567068cbdc04217e1a25256a2"
MIGRATION_ID = "0001-establish-current-baseline"
LEDGER_SQL = """CREATE TABLE schema_migrations (
    target_version INTEGER PRIMARY KEY,
    migration_id TEXT NOT NULL UNIQUE,
    source_version INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    source_schema_sha256 TEXT NOT NULL,
    target_schema_sha256 TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('initialize', 'adopt')),
    completed_at TEXT NOT NULL
)"""
CHECKSUM = hashlib.sha256((MIGRATION_ID + "\n" + BASELINE_SCHEMA + "\n" + LEDGER_SQL).encode()).hexdigest()
CURRENT_SCHEMA = "a05a42f5e2ffc9c5c994684ed06b7572bb5d9c968166cba329e4475d0a232913"
TRANSITION_ID = "0002-transaction-integrity"
try:
    from app.db.transaction_schema import SQL as TRANSACTION_SQL, initialize as initialize_transaction_schema
except ImportError:
    from db.transaction_schema import SQL as TRANSACTION_SQL, initialize as initialize_transaction_schema
TRANSITION_CHECKSUM = hashlib.sha256(
    (TRANSITION_ID + "\n" + BASELINE_SCHEMA + "\n" + CURRENT_SCHEMA + "\n" + "\n".join(TRANSACTION_SQL)).encode()
).hexdigest()


class MigrationRejected(RuntimeError):
    """Unsupported/unknown state or missing explicit permission; no migration."""


class MigrationBusy(MigrationRejected):
    """Cooperating migration lock or existing SQLite writer; no waiting/retry."""


def schema_hash(rows) -> str:
    return hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def path_guard(database: Path) -> str | None:
    for path in (database, *database.parents):
        if os.path.lexists(path):
            stat = path.lstat()
            if path.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
                return "unsafe-path"
    for suffix in ("-wal", "-shm", "-journal"):
        if os.path.lexists(Path(str(database) + suffix)):
            return "recovery-required"
    if not os.path.lexists(database):
        return "fresh-permission-required"
    if not database.is_file():
        return "unsafe-path"
    with database.open("rb") as source:
        header = source.read(100)
    if len(header) < 100 or header[:16] != b"SQLite format 3\0":
        return "corrupt-or-incomplete"
    if header[18:20] != b"\x01\x01":
        return "recovery-required"
    return None


def inspect_connection(conn: sqlite3.Connection) -> dict:
    """Inspect one consistent SQLite transaction; no DDL or normalization."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    app_id = conn.execute("PRAGMA application_id").fetchone()[0]
    if version > VERSION:
        return {"state": "future-version", "version": version}
    if (
        conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]
        or conn.execute("PRAGMA foreign_key_check").fetchall()
    ):
        return {"state": "integrity-failure", "version": version}
    rows = [tuple(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
    application_rows = [r for r in rows if r[2] != "schema_migrations"]
    fingerprint = schema_hash(application_rows)
    ledger_rows = [r for r in rows if r[2] == "schema_migrations"]
    result = {
        "state": "unknown-schema",
        "version": version,
        "application_schema_sha256": fingerprint,
        "ledger_present": bool(ledger_rows),
    }
    if fingerprint not in {BASELINE_SCHEMA, CURRENT_SCHEMA}:
        return result
    if not ledger_rows:
        result["state"] = "recognized-unversioned" if version == 0 and app_id == 0 else "missing-ledger"
        return result
    if (
        ledger_rows
        != [
            ("index", "sqlite_autoindex_schema_migrations_1", "schema_migrations", None),
            ("table", "schema_migrations", "schema_migrations", LEDGER_SQL),
        ]
        or version not in {1, VERSION}
        or app_id != APPLICATION_ID
    ):
        result["state"] = "inconsistent-ledger"
        return result
    records = conn.execute(
        "SELECT target_version,migration_id,source_version,checksum,source_schema_sha256,target_schema_sha256,kind,completed_at FROM schema_migrations ORDER BY target_version"
    ).fetchall()
    if not records:
        result["state"] = "inconsistent-ledger"
        return result
    direct_v2 = version == 2 and len(records) == 1
    if not direct_v2 and len(records) != version:
        result["state"] = "inconsistent-ledger"
        return result
    target, identity, source, checksum, source_hash, target_hash, kind, completed = records[0]
    try:
        timestamp = datetime.fromisoformat(completed)
        valid_time = timestamp.tzinfo is not None and timestamp <= datetime.now(timezone.utc)
    except (ValueError, TypeError):
        valid_time = False
    expected_first = (
        (2, TRANSITION_ID, 0, TRANSITION_CHECKSUM, CURRENT_SCHEMA)
        if direct_v2
        else (1, MIGRATION_ID, 0, CHECKSUM, BASELINE_SCHEMA)
    )
    if (
        (target, identity, source, checksum, target_hash) != expected_first
        or kind not in {"initialize", "adopt"}
        or source_hash != ((CURRENT_SCHEMA if direct_v2 else BASELINE_SCHEMA) if kind == "adopt" else "")
        or not valid_time
    ):
        result["state"] = "inconsistent-ledger"
        return result
    if version == 1:
        if fingerprint != BASELINE_SCHEMA:
            result["state"] = "inconsistent-ledger"
            return result
        result["state"] = "versioned-upgrade-required"
    elif not direct_v2:
        second = records[1]
        try:
            second_time = datetime.fromisoformat(second[7])
            valid_second = second_time.tzinfo is not None and timestamp <= second_time <= datetime.now(timezone.utc)
        except (ValueError, TypeError):
            valid_second = False
        if (
            fingerprint != CURRENT_SCHEMA
            or tuple(second[:7])
            != (2, TRANSITION_ID, 1, TRANSITION_CHECKSUM, BASELINE_SCHEMA, CURRENT_SCHEMA, "initialize")
            or not valid_second
        ):
            result["state"] = "inconsistent-ledger"
            return result
        result["state"] = "versioned-current"
    else:
        result["state"] = "versioned-current" if fingerprint == CURRENT_SCHEMA else "inconsistent-ledger"
    result["migration_id"] = TRANSITION_ID if version == 2 else identity
    result["checksum"] = TRANSITION_CHECKSUM if version == 2 else checksum
    return result


def inspect(database: Path) -> dict:
    database = Path(database).absolute()
    try:
        state = path_guard(database)
        if state:
            return {"state": state, "version": None}
        before = database.stat()
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=0)) as conn:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.execute("BEGIN")
            result = inspect_connection(conn)
        after = database.stat()
        if path_guard(database) or (before.st_size, before.st_mtime_ns, before.st_ino, before.st_dev) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ino,
            after.st_dev,
        ):
            return {"state": "changed-during-inspection", "version": None}
        return result
    except sqlite3.Error:
        return {"state": "unreadable-or-busy", "version": None}
    except OSError:
        return {"state": "unreadable-path", "version": None}


def permitted(result: dict, *, allow_fresh: bool, adopt_legacy: bool) -> None:
    state = result["state"]
    if (
        state in {"versioned-current", "versioned-upgrade-required"}
        or state == "fresh-permission-required"
        and allow_fresh
        or state == "recognized-unversioned"
        and adopt_legacy
    ):
        return
    raise MigrationRejected("Drink POS migration gate: " + state + "; preserve state and obtain operator review")


def migrate(
    database: Path, *, allow_fresh: bool = False, adopt_legacy: bool = False, initialize=None, fault=None
) -> dict:
    """Explicit authorized execution seam; existing adoption changes metadata only.

    Fault callback is test-only Python dependency injection, never an env/CLI flag.
    SQLite changes and completion commit together; file/lock creation does not.
    """
    database = Path(database).absolute()
    if os.path.lexists(Path(str(database) + ".migration-lock")):
        raise MigrationBusy("Drink POS migration lock owned or stale; operator review required")
    initial = inspect(database)
    permitted(initial, allow_fresh=allow_fresh, adopt_legacy=adopt_legacy)
    if initial["state"] == "versioned-current":
        return initial
    fresh = initial["state"] == "fresh-permission-required"
    if fresh and initialize is None:
        raise MigrationRejected("Fresh initialization requires the authoritative initializer")
    checkpoint = fault or (lambda point, conn: None)
    checkpoint("before-write", None)
    # Filesystem starts only after positive compatibility/permission decision.
    database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = Path(str(database) + ".migration-lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise MigrationBusy("Drink POS migration lock owned or stale; operator review required") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(str(os.getpid()))
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck path/header before write-capable SQLite open. Never create an
        # existing installation that disappeared or replace a racing fresh target.
        current = inspect(database)
        permitted(current, allow_fresh=allow_fresh, adopt_legacy=adopt_legacy)
        if current != initial:
            raise MigrationRejected("Installation changed after compatibility decision")
        if fresh:
            fd = os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        with closing(
            sqlite3.connect(database.as_uri() + "?mode=rw", uri=True, timeout=0, isolation_level=None)
        ) as conn:
            try:
                conn.execute("PRAGMA foreign_keys=ON")
                try:
                    conn.execute("BEGIN IMMEDIATE")
                except sqlite3.OperationalError as exc:
                    if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                        raise MigrationBusy("Concurrent SQLite writer; no migration retry") from exc
                    raise
                if fresh:
                    if conn.execute("SELECT name FROM sqlite_master").fetchall():
                        raise MigrationRejected("Fresh target no longer empty")
                    # Row names are required only by existing initialization helpers.
                    conn.row_factory = sqlite3.Row
                    initialize(conn)
                    conn.row_factory = None
                    expected = inspect_connection(conn)
                    if expected["state"] != "recognized-unversioned":
                        raise MigrationRejected("Fresh initialization schema differs from verified baseline")
                elif inspect_connection(conn) != initial:
                    raise MigrationRejected("Source prerequisites changed before transaction")
                upgrading = initial["state"] == "versioned-upgrade-required"
                if not upgrading:
                    conn.execute(LEDGER_SQL)
                checkpoint("after-schema", conn)
                old_baseline = initial.get("application_schema_sha256") == BASELINE_SCHEMA and not fresh
                if not upgrading and old_baseline:
                    conn.execute(
                        "INSERT INTO schema_migrations VALUES(?,?,?,?,?,?,?,?)",
                        (
                            1,
                            MIGRATION_ID,
                            0,
                            CHECKSUM,
                            BASELINE_SCHEMA,
                            BASELINE_SCHEMA,
                            "adopt",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                initialize_transaction_schema(conn)
                checkpoint("after-transaction-schema", conn)
                transitioning = upgrading or old_baseline
                conn.execute(
                    "INSERT INTO schema_migrations VALUES(?,?,?,?,?,?,?,?)",
                    (
                        2,
                        TRANSITION_ID,
                        1 if transitioning else 0,
                        TRANSITION_CHECKSUM,
                        BASELINE_SCHEMA if transitioning else ("" if fresh else CURRENT_SCHEMA),
                        CURRENT_SCHEMA,
                        "initialize" if transitioning or fresh else "adopt",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
                conn.execute(f"PRAGMA user_version={VERSION}")
                checkpoint("after-ledger", conn)
                result = inspect_connection(conn)
                if result["state"] != "versioned-current":
                    raise MigrationRejected("Post-migration schema/ledger/integrity verification failed")
                checkpoint("before-commit", conn)
                conn.execute("COMMIT")
                return result
            except BaseException:
                if conn.in_transaction:
                    conn.rollback()
                raise
    finally:
        lock.unlink()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only migration contract inspection; never authorizes deployment")
    parser.add_argument("database", type=Path)
    args = parser.parse_args(argv)
    result = inspect(args.database)
    result["deployment_authorized"] = False
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] in {"recognized-unversioned", "versioned-current"} else 2


if __name__ == "__main__":
    sys.exit(main())
