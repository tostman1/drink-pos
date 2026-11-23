"""Filesystem and SQLite verification primitives shared by recovery CLIs."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path


def read_connection(path: Path) -> sqlite3.Connection:
    # as_uri escapes spaces, #, ?, Unicode and Windows drive letters.
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)


def verify_database(path: Path) -> dict[str, int]:
    conn = read_connection(path)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchall()
        if integrity != [("ok",)]:
            raise ValueError(f"Database failed integrity_check: {integrity}")
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ValueError(f"Database failed foreign_key_check: {violations}")
        tables = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + name.replace('"', '""') + '"'
            tables[name] = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
        if not tables:
            raise ValueError("Database contains no tables")
        return tables
    finally:
        conn.close()


def file_metadata(path: Path) -> dict[str, str | int]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def sync_file(path: Path) -> None:
    with path.open("r+b") as handle:
        os.fsync(handle.fileno())


def sync_directory(path: Path) -> None:
    # Linux/Synology: persist the rename/directory entry, not just file contents.
    # Windows does not expose directory fsync through os.open.
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def check_new_target(path: Path) -> None:
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"), Path(str(path) + "-journal")):
        if os.path.lexists(candidate):
            raise FileExistsError(f"Target database or sidecar already exists: {candidate}")


def create_private_directories(path: Path) -> None:
    # Path.mkdir(parents=True, mode=...) does NOT apply mode to ancestors.
    # Create each missing component privately; never chmod existing directories.
    try:
        path.mkdir(mode=0o700)
    except FileNotFoundError:
        create_private_directories(path.parent)
        create_private_directories(path)
    except FileExistsError:
        if not path.is_dir():
            raise


def publish_new_file(temporary: Path, target: Path) -> None:
    check_new_target(target)
    if os.name == "posix":
        os.chmod(temporary, 0o600)
    sync_file(temporary)
    # Hard-link creation is atomic and fails if *any* target exists (including a
    # dangling symlink). Unlike replace/rename this cannot clobber a racing writer.
    # Fail closed on filesystems without hard-link support; never fall back to copy.
    os.link(temporary, target)
    temporary.unlink()
    sync_directory(target.parent)


def verify_bundle(directory: Path) -> dict:
    if directory.is_symlink() or (directory / "manifest.json").is_symlink():
        raise ValueError("Backup bundle/manifest must not be symlinks")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1 or manifest.get("app") != "drink_pos":
        raise ValueError("Unsupported backup manifest")
    artifacts = manifest.get("artifacts", {})
    if set(artifacts) != {"database.db", "export.csv"}:
        raise ValueError("Backup manifest must contain database.db and export.csv")
    for name, expected in artifacts.items():
        path = directory / name
        if path.is_symlink() or file_metadata(path) != expected:
            raise ValueError(f"Backup checksum/size mismatch: {name}")
    if verify_database(directory / "database.db") != manifest.get("tables"):
        raise ValueError("Backup table counts do not match manifest")
    return manifest
