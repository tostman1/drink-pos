from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

try:
    from app.database_recovery import (
        check_new_target,
        publish_new_file,
        read_connection,
        verify_bundle,
        verify_database,
    )
except ImportError:
    from database_recovery import (
        check_new_target,
        publish_new_file,
        read_connection,
        verify_bundle,
        verify_database,
    )


SCHEMA_ORDER = {
    "table": 0,
    "view": 2,
    "index": 3,
    "trigger": 4,
}


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def decode_json_value(value: Any) -> Any:
    if isinstance(value, dict) and set(value.keys()) == {"__bytes_hex__"}:
        return bytes.fromhex(str(value["__bytes_hex__"]))
    return value


def backup_rows(backup_path: Path) -> list[dict[str, str]]:
    with backup_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        required = {"section", "table_name", "data_json"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Backup CSV is missing required columns: {', '.join(sorted(missing))}")
        return list(reader)


def payload_from_row(row: dict[str, str]) -> dict[str, Any]:
    raw = row.get("data_json") or "{}"
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Backup row payload is not a JSON object")
    return payload


def schema_entries(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for row in rows:
        if row.get("section") != "schema":
            continue
        payload = payload_from_row(row)
        name = str(payload.get("name") or "")
        sql = payload.get("sql")
        if not name or name.startswith("sqlite_") or not sql:
            continue
        entries.append(payload)
    return sorted(
        entries, key=lambda item: (SCHEMA_ORDER.get(str(item.get("type") or ""), 9), str(item.get("name") or ""))
    )


def data_entries(rows: list[dict[str, str]]) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    for row in rows:
        if row.get("section") != "data":
            continue
        table_name = str(row.get("table_name") or "")
        if not table_name or table_name.startswith("sqlite_"):
            continue
        entries.append((table_name, payload_from_row(row)))
    return entries


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()}


def insert_payload(conn: sqlite3.Connection, table_name: str, payload: dict[str, Any]) -> None:
    if not table_exists(conn, table_name):
        raise ValueError(f"CSV references missing table: {table_name}")
    available_columns = column_names(conn, table_name)
    if set(payload) - available_columns:
        raise ValueError(f"CSV references unknown columns in {table_name}")
    columns = [key for key in payload.keys() if key in available_columns]
    if not columns:
        return
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(quote_identifier(column) for column in columns)
    values = [decode_json_value(payload[column]) for column in columns]
    conn.execute(
        f"INSERT INTO {quote_identifier(table_name)} ({column_sql}) VALUES ({placeholders})",
        values,
    )


def refresh_sqlite_sequences(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "sqlite_sequence"):
        return
    tables = [
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    ]
    for table_name in tables:
        columns = column_names(conn, table_name)
        if "id" not in columns:
            continue
        max_id = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {quote_identifier(table_name)}").fetchone()[0]
        conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))
        conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table_name, int(max_id or 0)))


def restore_csv(backup_path: Path, temp_db: Path) -> None:
    rows = backup_rows(backup_path)
    if not rows:
        raise ValueError(f"Backup CSV is empty: {backup_path}")
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        entries = schema_entries(rows)
        table_entries = [entry for entry in entries if str(entry.get("type") or "") == "table"]
        post_data_entries = [entry for entry in entries if str(entry.get("type") or "") != "table"]

        for entry in table_entries:
            conn.execute(str(entry["sql"]))
        for table_name, payload in data_entries(rows):
            insert_payload(conn, table_name, payload)
        refresh_sqlite_sequences(conn)
        for entry in post_data_entries:
            conn.execute(str(entry["sql"]))

        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")
    finally:
        conn.close()


def restore_backup(backup_path: Path, target_db: Path) -> Path:
    check_new_target(target_db)
    if backup_path.is_dir():
        backup_path = backup_path / "database.db"
    # A CSV in a new bundle also requires its manifest; standalone legacy CSV
    # remains supported but cannot provide all-table completeness/checksums.
    manifest = None
    if backup_path.name == "database.db" or (backup_path.parent / "manifest.json").exists():
        manifest = verify_bundle(backup_path.parent)
    elif backup_path.suffix.lower() != ".csv":
        raise ValueError("SQLite recovery requires database.db in a verified backup bundle")

    target_db.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{target_db.name}.restore-", dir=target_db.parent) as temporary:
        temp_db = Path(temporary) / "database.db"
        if backup_path.suffix.lower() == ".csv":
            restore_csv(backup_path, temp_db)
        else:
            source = read_connection(backup_path)
            try:
                recovered = sqlite3.connect(temp_db)
                try:
                    source.backup(recovered)
                    recovered.execute("PRAGMA journal_mode=DELETE")
                finally:
                    recovered.close()
            finally:
                source.close()
        tables = verify_database(temp_db)
        if backup_path.suffix.lower() != ".csv" and manifest and tables != manifest["tables"]:
            raise ValueError("Recovered table counts do not match backup manifest")
        publish_new_file(temp_db, target_db)
    return target_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify and restore a Drink POS backup into a new SQLite target.")
    parser.add_argument("backup", type=Path, help="Completed backup directory/database.db, or legacy CSV (partial)")
    parser.add_argument("target_db", type=Path, help="Path for the new SQLite database to create")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    restored = restore_backup(args.backup, args.target_db)
    print(f"Restored database: {restored}")


if __name__ == "__main__":
    main()
