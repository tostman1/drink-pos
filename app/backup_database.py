from __future__ import annotations

import csv
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


IMPORTANT_TABLES = [
    "settings",
    "people",
    "items",
    "order_lines",
    "change_requests",
    "round_requests",
    "transactions",
    "transaction_items",
    "round_events",
]


def default_db_path_for_env(env: str) -> str:
    normalized = (env or "development").strip().lower()
    if normalized in {"production", "prod"}:
        return "/app/data/drink_pos.db"
    return "/app/data/drink_pos_dev.db"


def resolve_db_path() -> Path:
    env = os.getenv("DRINK_POS_ENV", "development")
    return Path(os.getenv("DRINK_POS_DB") or default_db_path_for_env(env))


def resolve_backup_dir(source_db: Path) -> Path:
    configured = os.getenv("DRINK_POS_BACKUP_DIR")
    if configured:
        return Path(configured)
    return source_db.parent / "backups"


def backup_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    return value


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: json_safe(row[key]) for key in row.keys()}


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [row["name"] for row in conn.execute(f'PRAGMA table_info("{table_name}")')]


def order_clause(columns: list[str]) -> str:
    if "id" in columns:
        return ' ORDER BY "id"'
    if "key" in columns:
        return ' ORDER BY "key"'
    if "timestamp" in columns:
        return ' ORDER BY "timestamp"'
    return ""


def write_csv_row(
    writer: csv.writer,
    created_at: str,
    source_db: Path,
    section: str,
    table_name: str,
    row_id: str,
    payload: dict[str, Any],
) -> None:
    writer.writerow(
        [
            created_at,
            str(source_db),
            section,
            table_name,
            row_id,
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        ]
    )


def create_snapshot(source_db: Path, backup_dir: Path) -> Path:
    fd, snapshot_name = tempfile.mkstemp(
        prefix="_drink_pos_snapshot_",
        suffix=".db",
        dir=str(backup_dir),
    )
    os.close(fd)
    snapshot_path = Path(snapshot_name)

    source_conn = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True, timeout=30)
    try:
        snapshot_conn = sqlite3.connect(snapshot_path)
        try:
            source_conn.backup(snapshot_conn)
        finally:
            snapshot_conn.close()
    finally:
        source_conn.close()

    return snapshot_path


def export_backup() -> Path:
    source_db = resolve_db_path()
    if not source_db.exists():
        raise FileNotFoundError(f"Database not found: {source_db}")

    backup_dir = resolve_backup_dir(source_db)
    backup_dir.mkdir(parents=True, exist_ok=True)

    created_at = backup_timestamp()
    output_path = backup_dir / f"drink_pos_backup_{created_at}.csv"
    snapshot_path = create_snapshot(source_db, backup_dir)
    exported_rows = 0

    try:
        conn = sqlite3.connect(snapshot_path)
        conn.row_factory = sqlite3.Row
        try:
            with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(
                    [
                        "backup_created_at",
                        "source_db",
                        "section",
                        "table_name",
                        "row_id",
                        "data_json",
                    ]
                )

                metadata = {
                    "app": "drink_pos",
                    "backup_created_at": created_at,
                    "drink_pos_env": os.getenv("DRINK_POS_ENV", "development"),
                    "source_db": str(source_db),
                    "source_db_size_bytes": source_db.stat().st_size,
                    "format": "semicolon CSV; each row payload is JSON",
                }
                write_csv_row(writer, created_at, source_db, "metadata", "__backup__", "1", metadata)

                schema_rows = conn.execute(
                    """
                    SELECT type, name, tbl_name, sql
                    FROM sqlite_master
                    WHERE type IN ('table', 'index', 'trigger', 'view')
                    ORDER BY type, name
                    """
                ).fetchall()
                for index, schema_row in enumerate(schema_rows, start=1):
                    write_csv_row(
                        writer,
                        created_at,
                        source_db,
                        "schema",
                        "__sqlite_master__",
                        str(index),
                        row_to_dict(schema_row),
                    )

                for table_name in IMPORTANT_TABLES:
                    if not table_exists(conn, table_name):
                        write_csv_row(
                            writer,
                            created_at,
                            source_db,
                            "summary",
                            table_name,
                            "missing",
                            {"exists": False, "row_count": 0},
                        )
                        continue

                    columns = table_columns(conn, table_name)
                    count = conn.execute(f'SELECT COUNT(*) AS count FROM "{table_name}"').fetchone()["count"]
                    write_csv_row(
                        writer,
                        created_at,
                        source_db,
                        "summary",
                        table_name,
                        "count",
                        {"exists": True, "row_count": count, "columns": columns},
                    )

                    rows = conn.execute(f'SELECT * FROM "{table_name}"{order_clause(columns)}').fetchall()
                    for position, row in enumerate(rows, start=1):
                        keys = row.keys()
                        row_id = str(row["id"]) if "id" in keys else str(position)
                        write_csv_row(
                            writer,
                            created_at,
                            source_db,
                            "data",
                            table_name,
                            row_id,
                            row_to_dict(row),
                        )
                        exported_rows += 1
        finally:
            conn.close()
    finally:
        snapshot_path.unlink(missing_ok=True)

    print(f"Backup written: {output_path} ({exported_rows} data rows)")
    return output_path


if __name__ == "__main__":
    export_backup()
