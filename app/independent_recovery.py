"""Optional external-age filesystem replication; EF-08b bundles stay unchanged.

No application startup, crypto implementation, provider API or automatic retention.
Trusted private storage/scratch and independent key escrow are operator boundaries.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from app.application_recovery import (
        OperationBusy,
        create_private_directories,
        file_metadata,
        operation_lock,
        publish_directory,
        read_json,
        regular_file,
        reject_links,
        restore_application,
        safe_path,
        scan_tree,
        sync_tree,
        sync_directory,
        utc_now,
        verify_application_bundle,
        write_json,
    )
except ImportError:
    from application_recovery import (
        OperationBusy,
        create_private_directories,
        file_metadata,
        operation_lock,
        publish_directory,
        read_json,
        regular_file,
        reject_links,
        restore_application,
        safe_path,
        scan_tree,
        sync_tree,
        sync_directory,
        utc_now,
        verify_application_bundle,
        write_json,
    )

FORMAT = "drink_pos_age_replica"
MAX_BYTES = 20 * 1024**3
MAX_ENTRIES = 100_000


def private_identity(identity: Path) -> None:
    regular_file(identity)
    if os.name == "posix" and identity.stat().st_mode & 0o077:
        raise ValueError("Identity must not be group/world accessible")


def distinct_roots(*roots: Path) -> None:
    for root in roots:
        reject_links(root)
    paths = [Path(os.path.abspath(p)) for p in roots]
    for index, path in enumerate(paths):
        if any(path.is_relative_to(other) or other.is_relative_to(path) for other in paths[index + 1 :]):
            raise ValueError("Source, replica, scratch, key and recovery roots must not overlap")


def age_command(age: str, arguments: list[str], output: Path) -> None:
    # age emits plaintext only into private owned staging. Do not relay stderr:
    # external tool errors may contain paths or identity material. No prompts.
    create_private_directories(output.parent)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        try:
            result = subprocess.run(
                [age, *arguments],
                stdin=subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.PIPE,
                timeout=1200,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("External encryption tool timed out") from exc
    if result.returncode:
        raise ValueError("External encryption/decryption failed")


def encrypt_archive(archive: Path, output: Path, recipient: str, age: str) -> None:
    # Restrict this example to ordinary native age X25519 recipients (no plugins).
    if not recipient.startswith("age1") or len(recipient) != 62 or not recipient.isalnum():
        raise ValueError("Expected a native age recipient")
    age_command(age, ["--encrypt", "--recipient", recipient, str(archive)], output)


def make_archive(bundle: Path, archive: Path) -> None:
    files, directories = scan_tree(bundle)
    if len(files) + len(directories) > MAX_ENTRIES or sum(p.stat().st_size for p in files.values()) > MAX_BYTES:
        raise ValueError("Bundle exceeds replica resource limits")
    descriptor = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with (
        os.fdopen(descriptor, "wb") as output,
        tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as tar,
    ):
        for name in [bundle.name, *(bundle.name + "/" + d for d in sorted(directories))]:
            info = tarfile.TarInfo(name)
            info.type, info.mode = tarfile.DIRTYPE, 0o700
            tar.addfile(info)
        for name, path in sorted(files.items()):
            regular_file(path)
            info = tarfile.TarInfo(bundle.name + "/" + name)
            info.size, info.mode = path.stat().st_size, 0o600
            with path.open("rb") as source:
                tar.addfile(info, source)


def unpack_archive(archive: Path, destination: Path, backup_id: str) -> Path:
    # Never extractall or interpret archive permissions/links/sparse files. Validate
    # all entries before writes, enforce bounds, copy only regular bytes privately.
    with tarfile.open(archive, "r:") as tar:
        members = []
        seen = set()
        total = 0
        for member in tar:
            name = safe_path(member.name)
            if name != backup_id and not name.startswith(backup_id + "/"):
                raise ValueError("Archive root mismatch")
            if name.casefold() in seen or not (member.isdir() or member.isfile()) or member.issparse():
                raise ValueError("Unsafe/duplicate archive entry")
            seen.add(name.casefold())
            total += member.size
            if member.size < 0 or total > MAX_BYTES or len(seen) > MAX_ENTRIES:
                raise ValueError("Archive exceeds resource limits")
            members.append(member)
        for member in members:
            target = destination / member.name
            if member.isdir():
                create_private_directories(target)
            else:
                create_private_directories(target.parent)
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as output, tar.extractfile(member) as source:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                if target.stat().st_size != member.size:
                    raise ValueError("Truncated archive entry")
    return destination / backup_id


def replica_metadata(manifest: dict, ciphertext: Path) -> dict:
    return {
        "format": FORMAT,
        "format_version": 1,
        "backup_id": manifest["backup_id"],
        "deployment_id": manifest["deployment_id"],
        "app_commit": manifest["app_commit"],
        "schema_sha256": manifest["database"]["schema_sha256"],
        "backup_started_at_utc": manifest["started_at_utc"],
        "backup_created_at_utc": manifest["created_at_utc"],
        "replicated_at_utc": utc_now(),
        "ciphertext": file_metadata(ciphertext),
        "encryption": "age-X25519",
        "protection": "private-filesystem; not-immutable; geographic-independence-not-assessed",
    }


def inspect_replica(replica: Path, *, staging: bool = False) -> dict:
    files, directories = scan_tree(replica)
    if set(files) != {"replica.json", "payload.tar.age", "COMPLETED.json"} or directories:
        raise ValueError("Incomplete or unexpected replica inventory")
    metadata = read_json(replica / "replica.json")
    required = {
        "format",
        "format_version",
        "backup_id",
        "deployment_id",
        "app_commit",
        "schema_sha256",
        "backup_started_at_utc",
        "backup_created_at_utc",
        "replicated_at_utc",
        "ciphertext",
        "encryption",
        "protection",
    }
    if (
        set(metadata) != required
        or metadata["format"] != FORMAT
        or type(metadata["format_version"]) is not int
        or metadata["format_version"] != 1
    ):
        raise ValueError("Unsupported replica envelope")
    safe_path(metadata["backup_id"])
    if not metadata["backup_id"].startswith("drink_pos_application_"):
        raise ValueError("Unsupported inner bundle identity")
    if not staging and replica.name != metadata["backup_id"] + ".replica":
        raise ValueError("Replica is not published")
    if metadata["encryption"] != "age-X25519" or file_metadata(replica / "payload.tar.age") != metadata["ciphertext"]:
        raise ValueError("Replica ciphertext mismatch")
    if metadata["ciphertext"]["size_bytes"] > MAX_BYTES + 128 * 1024**2:
        raise ValueError("Replica exceeds resource limits")
    for key in ("backup_started_at_utc", "backup_created_at_utc", "replicated_at_utc"):
        if datetime.fromisoformat(metadata[key]).utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("Replica timestamps must be UTC")
    if read_json(replica / "COMPLETED.json") != {
        "status": "verified-replica",
        "metadata": file_metadata(replica / "replica.json"),
    }:
        raise ValueError("Replica completion marker mismatch")
    return metadata


def decrypt_verified(
    replica: Path, identity: Path, temporary: Path, age: str, *, staging: bool = False
) -> tuple[Path, dict]:
    private_identity(identity)
    metadata = inspect_replica(replica, staging=staging)
    archive = temporary / "decrypted.tar"
    age_command(age, ["--decrypt", "--identity", str(identity), str(replica / "payload.tar.age")], archive)
    bundle = unpack_archive(archive, temporary / "unpacked", metadata["backup_id"])
    manifest = verify_application_bundle(bundle)
    expected = {
        "backup_id": manifest["backup_id"],
        "deployment_id": manifest["deployment_id"],
        "app_commit": manifest["app_commit"],
        "schema_sha256": manifest["database"]["schema_sha256"],
        "backup_started_at_utc": manifest["started_at_utc"],
        "backup_created_at_utc": manifest["created_at_utc"],
    }
    if any(metadata[key] != value for key, value in expected.items()):
        raise ValueError("Envelope does not match decrypted bundle")
    return bundle, metadata


def replicate(
    bundle: Path, destination: Path, *, recipient: str, identity: Path, scratch: Path, age: str = "age"
) -> Path:
    distinct_roots(bundle, destination, scratch, identity.parent)
    private_identity(identity)
    manifest = verify_application_bundle(bundle)
    completed = destination / (manifest["backup_id"] + ".replica")
    if os.path.lexists(completed):
        raise FileExistsError("Replica already exists")
    create_private_directories(destination)
    create_private_directories(scratch)
    with operation_lock(destination / ".drink-pos-replica.lock"):
        with (
            tempfile.TemporaryDirectory(prefix=".drink-pos-replica-", dir=destination) as stage_name,
            tempfile.TemporaryDirectory(prefix=".drink-pos-crypto-", dir=scratch) as work_name,
        ):
            staging, work = Path(stage_name), Path(work_name)
            archive = work / "bundle.tar"
            make_archive(bundle, archive)
            encrypt_archive(archive, staging / "payload.tar.age", recipient, age)
            metadata = replica_metadata(manifest, staging / "payload.tar.age")
            write_json(staging / "replica.json", metadata)
            write_json(
                staging / "COMPLETED.json",
                {"status": "verified-replica", "metadata": file_metadata(staging / "replica.json")},
            )
            # Verify from destination bytes, not source. Detect wrong recipients too.
            decrypt_verified(staging, identity, work / "verification", age, staging=True)
            sync_tree(staging)
            publish_directory(staging, completed)
            sync_directory(destination)
    return completed


def verify_replica(replica: Path, *, identity: Path, scratch: Path, age: str = "age") -> dict:
    distinct_roots(replica, scratch, identity.parent)
    create_private_directories(scratch)
    with tempfile.TemporaryDirectory(prefix=".drink-pos-verify-", dir=scratch) as name:
        _, metadata = decrypt_verified(replica, identity, Path(name), age)
        return {**metadata, "independently_verified_at_utc": utc_now(), "verification": "decrypted-full-bundle"}


def recover_replica(
    replica: Path,
    target: Path,
    *,
    identity: Path,
    scratch: Path,
    expected_commit: str,
    expected_schema: str,
    age: str = "age",
) -> Path:
    distinct_roots(replica, target, scratch, identity.parent)
    reject_links(target)
    if os.path.lexists(target):
        raise FileExistsError("Recovery target exists")
    create_private_directories(scratch)
    with tempfile.TemporaryDirectory(prefix=".drink-pos-decrypt-", dir=scratch) as name:
        bundle, _ = decrypt_verified(replica, identity, Path(name), age)
        return restore_application(bundle, target, expected_commit=expected_commit, expected_schema=expected_schema)


def record_event(journal: Path, action: str, status: str, operation_id: str, **fields) -> Path:
    # Explicitly bounded fields, never tool output/exception strings/content.
    allowed = {
        "backup_id",
        "ciphertext_sha256",
        "created_at_utc",
        "verified_at_utc",
        "duration_seconds",
        "rpo_age_seconds",
        "rto_seconds",
        "error_code",
    }
    if (
        action not in {"replication", "verification", "recovery", "rehearsal"}
        or status not in {"started", "success", "failed"}
        or set(fields) - allowed
    ):
        raise ValueError("Unsupported journal event")
    if not isinstance(operation_id, str) or len(operation_id) > 80 or not operation_id.replace("-", "").isalnum():
        raise ValueError("Invalid journal operation identity")
    reject_links(journal)
    create_private_directories(journal)
    event = {
        "format": "drink_pos_recovery_event",
        "format_version": 1,
        "operation_id": operation_id,
        "action": action,
        "status": status,
        "at_utc": utc_now(),
        **fields,
    }
    with tempfile.TemporaryDirectory(prefix=".drink-pos-event-", dir=journal) as name:
        staging = Path(name)
        write_json(staging / "event.json", event)
        sync_tree(staging)
        completed = journal / (uuid.uuid4().hex + ".event")
        publish_directory(staging, completed)
    return completed


def recovery_status(
    replica: Path, journal: Path, *, max_age_seconds: float, max_verify_age_seconds: float, max_used_percent: float = 95
) -> dict:
    if min(max_age_seconds, max_verify_age_seconds) <= 0 or not 0 < max_used_percent <= 100:
        raise ValueError("Invalid monitoring threshold")
    issues = []
    metadata = None
    try:
        metadata = inspect_replica(replica)
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        issues.append("replica-missing-or-invalid")
    events = []
    reject_links(journal)
    if journal.is_dir():
        for path in journal.glob("*.event"):
            try:
                entry = read_json(path / "event.json")
                if (
                    entry.get("format") != "drink_pos_recovery_event"
                    or entry.get("format_version") != 1
                    or entry.get("action") not in {"replication", "verification", "recovery", "rehearsal"}
                    or entry.get("status") not in {"started", "success", "failed"}
                    or not isinstance(entry.get("operation_id"), str)
                ):
                    raise ValueError("Unsupported event")
                if datetime.fromisoformat(entry["at_utc"]).utcoffset() != timezone.utc.utcoffset(None):
                    raise ValueError("Invalid event timestamp")
                events.append(entry)
            except (OSError, ValueError, TypeError, KeyError):
                issues.append("invalid-journal-event")
    now = datetime.now(timezone.utc)
    age = None
    if metadata:
        age = (now - datetime.fromisoformat(metadata["backup_started_at_utc"])).total_seconds()
        if not 0 <= age <= max_age_seconds:
            issues.append("backup-stale-or-future")
    verified = [
        e
        for e in events
        if e.get("action") in {"verification", "replication"}
        and e.get("status") == "success"
        and metadata
        and e.get("ciphertext_sha256") == metadata["ciphertext"]["sha256"]
    ]
    latest = max(verified, key=lambda e: e["at_utc"], default=None)
    verify_age = None if latest is None else (now - datetime.fromisoformat(latest["at_utc"])).total_seconds()
    if verify_age is None or not 0 <= verify_age <= max_verify_age_seconds:
        issues.append("independent-verification-missing-or-stale")
    started = {e["operation_id"] for e in events if e.get("status") == "started"}
    finished = {e["operation_id"] for e in events if e.get("status") in {"success", "failed"}}
    if started - finished:
        issues.append("interrupted-or-running-operation")
    failed = sum(e.get("status") == "failed" for e in events)
    if failed:
        issues.append("recorded-operation-failures")
    roots = [replica.parent, journal]
    incomplete = 0
    for root in roots:
        reject_links(root)
        if root.is_dir():
            incomplete += sum(
                p.name.startswith((".drink-pos-replica-", ".drink-pos-event-")) or p.name.endswith(".lock")
                for p in root.iterdir()
            )
    if incomplete:
        issues.append("lock-or-incomplete-staging")
    capacity = None
    try:
        usage = shutil.disk_usage(replica.parent)
        capacity = 100 * usage.used / usage.total
        if capacity >= max_used_percent:
            issues.append("storage-capacity-threshold")
    except OSError:
        issues.append("storage-capacity-unavailable")
    rehearsals = [e for e in events if e.get("action") == "rehearsal" and e.get("status") == "success"]
    last_rehearsal = max(rehearsals, key=lambda e: e["at_utc"], default=None)
    return {
        "status": "attention" if issues else "ok",
        "issues": sorted(set(issues)),
        "backup_id": metadata["backup_id"] if metadata else None,
        "last_backup_created_at_utc": metadata["backup_created_at_utc"] if metadata else None,
        "last_replication_at_utc": metadata["replicated_at_utc"] if metadata else None,
        "last_independent_verification_at_utc": latest["at_utc"] if latest else None,
        "backup_age_seconds": age,
        "verification_age_seconds": verify_age,
        "last_rehearsal_at_utc": last_rehearsal["at_utc"] if last_rehearsal else None,
        "recorded_failed_attempts": failed,
        "incomplete_or_lock_entries": incomplete,
        "storage_used_percent": capacity,
        "current_check": "ciphertext-checksum; historical-decryption-receipt",
        "immutability": "not-enforced",
        "offsite": "not-assessed",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--age", default="age", help="Trusted external age executable")
    parser.add_argument("--journal", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    replication = sub.add_parser("replicate")
    replication.add_argument("bundle", type=Path)
    replication.add_argument("destination", type=Path)
    replication.add_argument("--recipient", required=True)
    for command in (replication, sub.add_parser("verify"), sub.add_parser("recover")):
        if command is not replication:
            command.add_argument("replica", type=Path)
        command.add_argument("--identity", type=Path, required=True)
        command.add_argument("--scratch", type=Path, required=True)
        if command.prog.endswith("recover"):
            command.add_argument("target", type=Path)
            command.add_argument("--expected-commit", required=True)
            command.add_argument("--expected-schema", required=True)
    status = sub.add_parser("status")
    status.add_argument("replica", type=Path)
    status.add_argument("--max-age-seconds", type=float, required=True)
    status.add_argument("--max-verify-age-seconds", type=float, required=True)
    status.add_argument("--max-used-percent", type=float, default=95)
    args = parser.parse_args(argv)
    operation_id, started = uuid.uuid4().hex, time.monotonic()
    action = {"replicate": "replication", "verify": "verification", "recover": "recovery"}.get(args.command)
    error = 0
    journal_safe = False
    try:
        # Validate separation BEFORE journal writes, including identity escrow.
        roots = [args.journal]
        if args.command == "replicate":
            roots.extend((args.bundle, args.destination, args.scratch, args.identity.parent))
        elif args.command in {"verify", "recover"}:
            roots.extend((args.replica, args.scratch, args.identity.parent))
            if args.command == "recover":
                roots.append(args.target)
        else:
            roots.append(args.replica)
        distinct_roots(*roots)
        journal_safe = True
        if action:
            record_event(args.journal, action, "started", operation_id)
        if args.command == "replicate":
            result_path = replicate(
                args.bundle,
                args.destination,
                recipient=args.recipient,
                identity=args.identity,
                scratch=args.scratch,
                age=args.age,
            )
            metadata = inspect_replica(result_path)
            result = {"status": "verified-replica", "backup_id": metadata["backup_id"]}
        elif args.command == "verify":
            metadata = verify_replica(args.replica, identity=args.identity, scratch=args.scratch, age=args.age)
            result = {"status": "decrypted-verified", "backup_id": metadata["backup_id"]}
        elif args.command == "recover":
            recover_replica(
                args.replica,
                args.target,
                identity=args.identity,
                scratch=args.scratch,
                age=args.age,
                expected_commit=args.expected_commit,
                expected_schema=args.expected_schema,
            )
            metadata = inspect_replica(args.replica)
            result = {"status": "recovered-not-started", "backup_id": metadata["backup_id"]}
        else:
            result = recovery_status(
                args.replica,
                args.journal,
                max_age_seconds=args.max_age_seconds,
                max_verify_age_seconds=args.max_verify_age_seconds,
                max_used_percent=args.max_used_percent,
            )
        if action:
            record_event(
                args.journal,
                action,
                "success",
                operation_id,
                backup_id=metadata["backup_id"],
                ciphertext_sha256=metadata["ciphertext"]["sha256"],
                duration_seconds=time.monotonic() - started,
            )
        print(json.dumps(result, sort_keys=True))
        return 4 if result["status"] == "attention" else 0
    except OperationBusy:
        error = 3
    except (ValueError, TypeError, KeyError, sqlite3.Error, tarfile.TarError):
        error = 2
    except OSError as exc:
        error = 5 if exc.errno == errno.ENOSPC else 1
    except KeyboardInterrupt:
        error = 130
    if action and journal_safe:
        try:
            record_event(args.journal, action, "failed", operation_id, error_code=error)
        except (OSError, ValueError):
            pass  # Explicit stderr outcome still emitted when journal unavailable.
    print(json.dumps({"status": "failed", "command": args.command, "error_code": error}), file=sys.stderr)
    return error


if __name__ == "__main__":
    sys.exit(main())
