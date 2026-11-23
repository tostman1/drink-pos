"""Portable, offline application-state recovery. No runtime/application imports.

The operator must quiesce ALL writers. Change detection is defense in depth,
not an online snapshot protocol. Storage/transport/scheduling remain external.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

try:
    from app.backup_database import create_snapshot
    from app.database_recovery import (
        create_private_directories,
        file_metadata,
        sync_directory,
        sync_file,
        verify_database,
    )
except ImportError:
    from backup_database import create_snapshot
    from database_recovery import create_private_directories, file_metadata, sync_directory, sync_file, verify_database


FORMAT = "drink_pos_application"
VERSION = 1
PREFIX = "drink_pos_application_"
CONFIG_KEYS = {"DRINK_POS_ENV", "TZ", "PAYMENT_PROVIDER", "SUMUP_CURRENCY", "SUMUP_TIMEOUT_SECONDS"}
CONSISTENCY = "operator-quiesced-all-writers; observed-source-change-detection"


class OperationBusy(RuntimeError):
    """A cooperating or interrupted operation owns the exclusive lock."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Unsafe portable payload path")
    parts = value.split("/")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    for part in parts:
        if part in {"", ".", ".."} or part.endswith((".", " ")) or any(ord(c) < 32 or c in '<>:"|?*' for c in part):
            raise ValueError("Unsafe portable payload path")
        if part.split(".")[0].upper() in reserved:
            raise ValueError("Nonportable reserved filename")
    return value


def reject_links(path: Path) -> None:
    # Includes ancestors and Windows junctions/reparse points. Trusted parents
    # remain a requirement: stdlib path checks are not hostile-race protection.
    for entry in (path, *path.parents):
        if os.path.lexists(entry):
            info = entry.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Symlinks/reparse points are not supported")


def regular_file(path: Path) -> None:
    reject_links(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Expected a regular file")


def scan_tree(root: Path) -> tuple[dict[str, Path], set[str]]:
    reject_links(root)
    files: dict[str, Path] = {}
    directories: set[str] = set()
    if not root.is_dir():
        raise ValueError("Expected a directory")
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            reject_links(path)
            relative = safe_path(path.relative_to(root).as_posix())
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                directories.add(relative)
            elif stat.S_ISREG(mode):
                files[relative] = path
            else:
                raise ValueError("Unexpected filesystem entry")
    all_paths = [*files, *directories]
    if len({name.casefold() for name in all_paths}) != len(all_paths):
        raise ValueError("Case-colliding paths are not portable")
    return files, directories


def write_json(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, ensure_ascii=False, sort_keys=True, indent=2)
        output.write("\n")


def read_json(path: Path) -> dict:
    regular_file(path)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Recovery metadata exceeds supported size")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON metadata key")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("Recovery metadata must be an object")
    return value


def digest_json(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def database_metadata(path: Path, *, immutable: bool = False, original_references: list | None = None) -> dict:
    regular_file(path)
    uri = path.absolute().as_uri() + ("?immutable=1" if immutable else "?mode=ro")
    conn = sqlite3.connect(uri, uri=True, timeout=15)
    try:
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN")
        schema = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        logical = hashlib.sha256()
        logical.update(json.dumps(schema, ensure_ascii=False).encode())
        counts = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            quoted = '"' + name.replace('"', '""') + '"'
            # Sort encoded rows rather than depend on rowid (WITHOUT ROWID supported).
            rows = []
            cursor = conn.execute(f"SELECT * FROM {quoted}")
            columns = [entry[0] for entry in cursor.description]
            for row in cursor:
                if name == "event_sessions" and original_references:
                    row = list(row)
                    for ref in original_references:
                        if row[columns.index("id")] == ref["event_id"]:
                            row[columns.index(ref["column"])] = ref["source_path"]
                encoded = [{"bytes": v.hex()} if isinstance(v, bytes) else v for v in row]
                rows.append(json.dumps(encoded, ensure_ascii=False, separators=(",", ":")))
            counts[name] = len(rows)
            logical.update(json.dumps([name, sorted(rows)], ensure_ascii=False).encode())
        metadata = {
            "schema_sha256": digest_json(schema),
            "logical_sha256": logical.hexdigest(),
            "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
            "application_id": conn.execute("PRAGMA application_id").fetchone()[0],
            "tables": counts,
        }
        return metadata
    finally:
        conn.close()


@contextmanager
def operation_lock(path: Path):
    reject_links(path)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise OperationBusy("Operation lock exists; confirm no running operation before manual removal") from exc
    try:
        with os.fdopen(descriptor, "w") as output:
            json.dump({"operation_id": uuid.uuid4().hex, "started_at_utc": utc_now()}, output)
        yield
    finally:
        path.unlink()


def source_payload(source_db: Path, messages: Path) -> dict[str, Path]:
    payload = {}
    events = source_db.absolute().parent / "events"
    reject_links(events)
    if events.exists():
        files, _ = scan_tree(events)
        payload.update({f"state/events/{name}": path for name, path in files.items()})
    reject_links(messages)
    if messages.exists():
        regular_file(messages)
        payload["state/messages.json"] = messages
    return payload


def event_references(database: Path, events_root: Path | None = None) -> list[dict]:
    conn = sqlite3.connect(database.absolute().as_uri() + "?immutable=1", uri=True)
    try:
        conn.execute("PRAGMA trusted_schema=OFF")
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='event_sessions'").fetchone():
            raise ValueError("Application snapshot lacks event_sessions")
        result = []
        for event_id, csv, pdf, status, invoice in conn.execute(
            "SELECT id,csv_path,pdf_path,status,invoice_created FROM event_sessions ORDER BY id"
        ):
            if status == "CLOSED" and not csv or invoice and not pdf:
                raise ValueError("Event is missing a required artifact reference")
            for column, value in (("csv_path", csv), ("pdf_path", pdf)):
                if value:
                    if events_root is None:
                        # For a bundle, mapping is derived from captured references,
                        # not by interpreting source host paths on the restore host.
                        result.append({"event_id": event_id, "column": column, "source_path": value})
                    else:
                        path = Path(value).absolute()
                        try:
                            name = safe_path(path.relative_to(events_root.absolute()).as_posix())
                        except ValueError as exc:
                            raise ValueError("Event artifact is outside the supported events root") from exc
                        result.append(
                            {
                                "event_id": event_id,
                                "column": column,
                                "source_path": value,
                                "payload": f"state/events/{name}",
                            }
                        )
        return result
    finally:
        conn.close()


def copy_payload(payload: dict[str, Path], destination: Path) -> None:
    for name, source in sorted(payload.items()):
        safe_path(name)
        regular_file(source)
        target = destination / name
        create_private_directories(target.parent)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output, length=1024 * 1024)


def sync_tree(root: Path) -> None:
    files, directories = scan_tree(root)
    for path in files.values():
        sync_file(path)
    for name in sorted(directories, key=lambda s: s.count("/"), reverse=True):
        sync_directory(root / name)
    sync_directory(root)


def validate_identity(deployment_id: str, app_commit: str, image_ref: str) -> None:
    if any(not isinstance(value, str) for value in (deployment_id, app_commit, image_ref)):
        raise ValueError("Invalid application identity metadata")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", deployment_id):
        raise ValueError("Deployment ID must be a portable operator-selected identifier")
    if not re.fullmatch(r"[0-9a-f]{40}", app_commit):
        raise ValueError("An exact 40-character application commit is required")
    if image_ref and not re.fullmatch(r"[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}", image_ref):
        raise ValueError("Optional image reference must be pinned by SHA-256 digest")


def publish_directory(staging: Path, target: Path) -> None:
    """Atomic no-replace directory publication, or fail closed.

    Windows rename does not replace any existing destination. Linux renameat2
    RENAME_NOREPLACE provides the same guarantee, including racing empty dirs.
    No check-then-rename fallback on other platforms/filesystems.
    """
    if os.name == "nt":
        # Windows indexers/AV can transiently hold rename-incompatible handles.
        # Retry only this no-replace filesystem operation, bounded to 1.5 seconds;
        # no snapshot/payment/mail operation is repeated. Persistent denial fails.
        for attempt in range(6):
            try:
                staging.rename(target)
                break
            except OSError as exc:
                if os.path.lexists(target):
                    raise FileExistsError("Publication target exists") from exc
                if getattr(exc, "winerror", None) not in {5, 32} or attempt == 5:
                    raise
                print(json.dumps({"event": "publication-retry", "attempt": attempt + 1}), file=sys.stderr)
                time.sleep(0.1 * (attempt + 1))
    elif sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise OSError("Atomic no-replace directory rename is unavailable")
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(staging), -100, os.fsencode(target), 1) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
    else:
        raise OSError("Atomic no-replace directory publication requires Linux or Windows")


def create_backup(
    source_db: Path,
    messages: Path,
    destination: Path,
    *,
    deployment_id: str,
    app_commit: str,
    quiesced: bool = False,
    image_ref: str = "",
    configuration: dict | None = None,
    allow_missing_messages: bool = False,
) -> Path:
    if not quiesced:
        raise ValueError("Stop/drain ALL application and filesystem writers; explicitly confirm quiescence")
    configuration = {} if configuration is None else configuration
    validate_identity(deployment_id, app_commit, image_ref)
    if (
        not isinstance(configuration, dict)
        or set(configuration) - CONFIG_KEYS
        or any(not isinstance(v, str) for v in configuration.values())
    ):
        raise ValueError("Configuration must contain only allowlisted non-secret string values")
    regular_file(source_db)
    reject_links(messages)
    if not messages.exists() and not allow_missing_messages:
        raise ValueError("Runtime message file missing; explicitly acknowledge bundled-default-only recovery")
    if messages.exists():
        read_json(messages)
    reject_links(destination)
    events_root = source_db.absolute().parent / "events"
    if destination.absolute().is_relative_to(events_root) or destination.absolute() == source_db.absolute().parent:
        raise ValueError("Backup destination must be separate from captured state")
    create_private_directories(destination)
    with operation_lock(destination / ".drink-pos-application.lock"):
        started = utc_now()
        backup_id = PREFIX + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix=".drink-pos-application-", dir=destination) as temporary:
            staging = Path(temporary)
            create_private_directories(staging / "state/events")
            before_db = database_metadata(source_db)
            before_files = source_payload(source_db, messages)
            before = {name: file_metadata(path) for name, path in before_files.items()}
            snapshot = create_snapshot(source_db, staging / "state")
            database = staging / "state/database.db"
            snapshot.rename(database)
            if database_metadata(database, immutable=True) != before_db:
                raise ValueError("Source database changed during snapshot")
            references = event_references(database, events_root)
            if any(ref["payload"] not in before for ref in references):
                raise ValueError("Missing DB-referenced event artifact")
            copy_payload(before_files, staging)
            write_json(staging / "configuration.json", configuration)
            after_files = source_payload(source_db, messages)
            after = {name: file_metadata(path) for name, path in after_files.items()}
            if before != after or database_metadata(source_db) != before_db:
                raise ValueError("Source changed; backup requires a writer-free maintenance boundary")
            files, directories = scan_tree(staging)
            manifest = {
                "format": FORMAT,
                "format_version": VERSION,
                "app": "drink_pos",
                "backup_id": backup_id,
                "started_at_utc": started,
                "created_at_utc": utc_now(),
                "consistency": CONSISTENCY,
                "deployment_id": deployment_id,
                "app_commit": app_commit,
                "image_ref": image_ref,
                "sqlite_version": sqlite3.sqlite_version,
                "database": before_db,
                "messages_present": "state/messages.json" in before,
                "event_references": references,
                "directories": sorted(directories),
                "files": {name: file_metadata(path) for name, path in files.items()},
            }
            if any(manifest["files"].get(name) != metadata for name, metadata in before.items()):
                raise ValueError("Copied artifacts differ from source inventory")
            write_json(staging / "manifest.json", manifest)
            write_json(
                staging / "COMPLETED.json",
                {"status": "verified", "backup_id": backup_id, "manifest": file_metadata(staging / "manifest.json")},
            )
            verify_application_bundle(staging, _staging=True)
            sync_tree(staging)
            completed = destination / backup_id
            if os.path.lexists(completed):
                raise FileExistsError("Backup publication target exists")
            publish_directory(staging, completed)
            sync_directory(destination)
        return completed


def verify_application_bundle(directory: Path, *, _staging: bool = False) -> dict:
    files, directories = scan_tree(directory)
    manifest = read_json(directory / "manifest.json")
    required = {
        "format",
        "format_version",
        "app",
        "backup_id",
        "started_at_utc",
        "created_at_utc",
        "consistency",
        "deployment_id",
        "app_commit",
        "image_ref",
        "sqlite_version",
        "database",
        "messages_present",
        "event_references",
        "directories",
        "files",
    }
    if not isinstance(manifest["database"], dict) or not isinstance(manifest["backup_id"], str):
        raise ValueError("Invalid database/backup identity metadata")
    if (
        set(manifest) != required
        or manifest["format"] != FORMAT
        or type(manifest["format_version"]) is not int
        or manifest["format_version"] != VERSION
        or manifest["app"] != "drink_pos"
    ):
        raise ValueError("Malformed or unsupported application bundle")
    validate_identity(manifest["deployment_id"], manifest["app_commit"], manifest["image_ref"])
    if (
        not re.fullmatch(PREFIX + r"[0-9]{8}T[0-9]{6}Z_[0-9a-f]{32}", manifest["backup_id"])
        or not _staging
        and directory.name != manifest["backup_id"]
    ):
        raise ValueError("Bundle is not a completed application backup directory")
    times = {}
    for key in ("started_at_utc", "created_at_utc"):
        times[key] = datetime.fromisoformat(manifest[key])
        if times[key].utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("Backup timestamps must be UTC")
    if times["started_at_utc"] > times["created_at_utc"] or manifest["consistency"] != CONSISTENCY:
        raise ValueError("Invalid backup consistency/timestamps")
    inventory = manifest["files"]
    if not isinstance(inventory, dict) or not {"state/database.db", "configuration.json"}.issubset(inventory):
        raise ValueError("Required state payload is missing")
    for name, metadata in inventory.items():
        safe_path(name)
        if (
            not isinstance(metadata, dict)
            or set(metadata) != {"size_bytes", "sha256"}
            or type(metadata["size_bytes"]) is not int
            or metadata["size_bytes"] < 0
            or not isinstance(metadata["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])
        ):
            raise ValueError("Malformed file checksum/size metadata")
        if name not in {"state/database.db", "state/messages.json", "configuration.json"} and not name.startswith(
            "state/events/"
        ):
            raise ValueError("Unsupported payload location")
    if type(manifest["messages_present"]) is not bool or manifest["messages_present"] != (
        "state/messages.json" in inventory
    ):
        raise ValueError("Message inventory mismatch")
    if (
        set(files) != set(inventory) | {"manifest.json", "COMPLETED.json"}
        or not isinstance(manifest["directories"], list)
        or sorted(directories) != manifest["directories"]
    ):
        raise ValueError("Extra or missing bundle entries")
    expected_dirs = {"state", "state/events"}
    for name in inventory:
        expected_dirs.update(str(p) for p in PurePosixPath(name).parents if str(p) != ".")
    if directories != expected_dirs:
        raise ValueError("Unsupported/empty directories in bundle")
    marker = read_json(directory / "COMPLETED.json")
    if marker != {
        "status": "verified",
        "backup_id": manifest["backup_id"],
        "manifest": file_metadata(directory / "manifest.json"),
    }:
        raise ValueError("Completion marker/manifest mismatch")
    for name, expected in inventory.items():
        if file_metadata(files[name]) != expected:
            raise ValueError("Payload checksum/size mismatch")
    database = directory / "state/database.db"
    if (
        verify_database(database) != manifest["database"].get("tables")
        or database_metadata(database, immutable=True) != manifest["database"]
    ):
        raise ValueError("SQLite schema/logical state mismatch")
    configuration = read_json(directory / "configuration.json")
    if manifest["messages_present"]:
        read_json(directory / "state/messages.json")
    if set(configuration) - CONFIG_KEYS or any(not isinstance(v, str) for v in configuration.values()):
        raise ValueError("Unsupported portable configuration")
    refs = manifest["event_references"]
    if not isinstance(refs, list) or any(
        not isinstance(ref, dict) or set(ref) != {"event_id", "column", "source_path", "payload"} for ref in refs
    ):
        raise ValueError("Invalid event artifact mapping")
    for ref in refs:
        if (
            ref["column"] not in {"csv_path", "pdf_path"}
            or type(ref["event_id"]) is not int
            or not isinstance(ref["source_path"], str)
        ):
            raise ValueError("Invalid event artifact reference types")
        safe_path(ref["payload"])
        if (
            not ref["source_path"]
            .replace("\\", "/")
            .endswith("/events/" + ref["payload"].removeprefix("state/events/"))
        ):
            raise ValueError("Artifact mapping does not match captured source-relative relationship")
    captured = [{key: ref[key] for key in ("event_id", "column", "source_path")} for ref in refs]
    if captured != event_references(database) or any(
        ref["payload"] not in inventory or not ref["payload"].startswith("state/events/") for ref in refs
    ):
        raise ValueError("Missing or invalid required event artifact")
    return manifest


def restore_application(bundle: Path, target: Path, *, expected_commit: str, expected_schema: str) -> Path:
    reject_links(target)
    if target.absolute().is_relative_to(bundle.absolute()):
        raise ValueError("Recovery destination must be outside its immutable source bundle")
    if os.path.lexists(target):
        raise FileExistsError("Recovery root already exists; select an isolated nonexistent destination")
    manifest = verify_application_bundle(bundle)
    if expected_commit != manifest["app_commit"] or expected_schema != manifest["database"]["schema_sha256"]:
        raise ValueError("Incompatible application commit/schema; no automatic migrations")
    create_private_directories(target.parent)
    lock_name = (
        ".drink-pos-restore-"
        + hashlib.sha256(target.absolute().as_posix().casefold().encode()).hexdigest()[:24]
        + ".lock"
    )
    with operation_lock(target.parent / lock_name):
        if os.path.lexists(target):
            raise FileExistsError("Recovery root already exists")
        with tempfile.TemporaryDirectory(prefix=".drink-pos-recovery-", dir=target.parent) as temporary:
            staging = Path(temporary)
            for name in manifest["directories"]:
                create_private_directories(staging / name)
            copy_payload({name: bundle / name for name in manifest["files"]}, staging)
            for name, expected in manifest["files"].items():
                if file_metadata(staging / name) != expected:
                    raise ValueError("Restored payload checksum/size mismatch")
            database = staging / "state/database.db"
            if database_metadata(database, immutable=True) != manifest["database"]:
                raise ValueError("Restored database differs")
            conn = sqlite3.connect(database)
            try:
                conn.execute("PRAGMA trusted_schema=OFF")
                conn.execute("PRAGMA foreign_keys=ON")
                if conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name='event_sessions'"
                ).fetchone():
                    raise ValueError("Event relocation does not support event_sessions triggers")
                for ref in manifest["event_references"]:
                    # Only these mutable location columns change; audit remains untouched.
                    conn.execute(
                        f"UPDATE event_sessions SET {ref['column']}=? WHERE id=?",
                        (str(target.absolute() / ref["payload"]), ref["event_id"]),
                    )
                conn.commit()
            finally:
                conn.close()
            if verify_database(database) != manifest["database"]["tables"]:
                raise ValueError("Restored database integrity/relationships failed")
            restored_meta = database_metadata(database, immutable=True)
            if restored_meta["schema_sha256"] != expected_schema:
                raise ValueError("Restore changed schema")
            if (
                database_metadata(database, immutable=True, original_references=manifest["event_references"])
                != manifest["database"]
            ):
                raise ValueError("Restore changed state beyond permitted artifact relocation")
            # Verify every non-DB file again after relocation, and record DB checksum.
            files, dirs = scan_tree(staging)
            for name in manifest["files"]:
                if name != "state/database.db" and file_metadata(files[name]) != manifest["files"][name]:
                    raise ValueError("Restored artifacts changed")
            write_json(
                staging / "RECOVERED.json",
                {
                    "backup_id": manifest["backup_id"],
                    "recovered_at_utc": utc_now(),
                    "app_commit": expected_commit,
                    "database": restored_meta,
                    "relocated_event_references": len(manifest["event_references"]),
                    "files": {name: file_metadata(path) for name, path in files.items()},
                    "directories": sorted(dirs),
                    "warning": "Not started; reconcile external payments/mail and restore independent secrets before approved adoption",
                },
            )
            sync_tree(staging)
            reject_links(target)
            if os.path.lexists(target):
                raise FileExistsError("Recovery root created concurrently")
            publish_directory(staging, target)
            sync_directory(target.parent)
    return target


def backup_status(destination: Path, deployment_id: str, max_age_seconds: int) -> dict:
    if max_age_seconds <= 0:
        raise ValueError("Maximum backup age must be positive")
    reject_links(destination)
    valid = []
    invalid = 0
    if destination.exists():
        for path in destination.glob(PREFIX + "*"):
            try:
                manifest = verify_application_bundle(path)
                if manifest["deployment_id"] == deployment_id:
                    valid.append(manifest)
            except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
                invalid += 1
    latest = max(valid, key=lambda m: m["created_at_utc"], default=None)
    age = (
        None
        if latest is None
        else (datetime.now(timezone.utc) - datetime.fromisoformat(latest["created_at_utc"])).total_seconds()
    )
    lock_present = os.path.lexists(destination / ".drink-pos-application.lock")
    return {
        "status": "ok"
        if age is not None and 0 <= age <= max_age_seconds and not invalid and not lock_present
        else "attention",
        "deployment_id": deployment_id,
        "latest_backup_id": latest["backup_id"] if latest else None,
        "age_seconds": age,
        "invalid_candidates": invalid,
        "operation_lock_present": lock_present,
        "replication": "not-assessed; run verification at independent destination",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup")
    create.add_argument("--database", type=Path, required=True)
    create.add_argument("--messages", type=Path, required=True)
    create.add_argument("--destination", type=Path, required=True)
    create.add_argument("--deployment-id", required=True)
    create.add_argument("--app-commit", required=True)
    create.add_argument("--image-ref", default="")
    create.add_argument("--configuration", type=Path)
    create.add_argument(
        "--allow-missing-messages",
        action="store_true",
        help="Acknowledge absent runtime catalog; restore uses exact image defaults",
    )
    create.add_argument(
        "--quiesced", action="store_true", help="Attest all app processes/editors/importers stopped and work drained"
    )
    verify = commands.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    restore = commands.add_parser("restore")
    restore.add_argument("bundle", type=Path)
    restore.add_argument("target", type=Path)
    restore.add_argument("--expected-commit", required=True)
    restore.add_argument("--expected-schema", required=True)
    status = commands.add_parser("status")
    status.add_argument("--destination", type=Path, required=True)
    status.add_argument("--deployment-id", required=True)
    status.add_argument("--max-age-seconds", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            path = create_backup(
                args.database,
                args.messages,
                args.destination,
                deployment_id=args.deployment_id,
                app_commit=args.app_commit,
                image_ref=args.image_ref,
                quiesced=args.quiesced,
                configuration=read_json(args.configuration) if args.configuration else None,
                allow_missing_messages=args.allow_missing_messages,
            )
            result = {"status": "verified", "backup_id": path.name, "path": str(path)}
        elif args.command == "verify":
            manifest = verify_application_bundle(args.bundle)
            result = {
                "status": "verified",
                "backup_id": manifest["backup_id"],
                "app_commit": manifest["app_commit"],
                "schema_sha256": manifest["database"]["schema_sha256"],
                "created_at_utc": manifest["created_at_utc"],
            }
        elif args.command == "restore":
            path = restore_application(
                args.bundle, args.target, expected_commit=args.expected_commit, expected_schema=args.expected_schema
            )
            result = {"status": "recovered-not-started", "path": str(path)}
        else:
            result = backup_status(args.destination, args.deployment_id, args.max_age_seconds)
        print(json.dumps(result, sort_keys=True))
        return 4 if result["status"] == "attention" else 0
    except OperationBusy:
        print(json.dumps({"status": "busy-or-interrupted", "command": args.command}), file=sys.stderr)
        return 3
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        # No exception strings: malformed/source content can contain sensitive data.
        print(json.dumps({"status": "invalid-or-incompatible", "command": args.command}), file=sys.stderr)
        return 2
    except OSError:
        print(json.dumps({"status": "io-failure", "command": args.command}), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(json.dumps({"status": "interrupted", "command": args.command}), file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
