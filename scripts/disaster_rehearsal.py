"""Complete synthetic installation-loss drill; never use production resources.

Creates/removes only UUID-named disposable containers/volumes and owned temporary
files. External age and Docker are required; no image publication or network access
from application/recovery containers. Measurements are synthetic, not guarantees.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import independent_recovery as independent  # noqa: E402
from app.application_recovery import database_metadata, utc_now, verify_application_bundle  # noqa: E402
from scripts.container_smoke import docker  # noqa: E402


def metrics(backup_started: str, failure_at: str, rto_seconds: float, *, target_rpo: float, target_rto: float) -> dict:
    point, failure = datetime.fromisoformat(backup_started), datetime.fromisoformat(failure_at)
    if point.utcoffset() != timezone.utc.utcoffset(None) or failure.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("Measurement timestamps must be UTC")
    age = (failure - point).total_seconds()
    if min(age, rto_seconds, target_rpo, target_rto) < 0:
        raise ValueError("Invalid measurement duration")
    return {
        "rpo_age_seconds": age,
        "rto_seconds": rto_seconds,
        "target_rpo_seconds": target_rpo,
        "target_rto_seconds": target_rto,
        "synthetic_targets_met": age <= target_rpo and rto_seconds <= target_rto,
        "rpo_definition": "loss-time minus backup-start; conservative snapshot-age upper bound",
        "rto_definition": "assumed-loss through independent recovery and validated isolated startup",
        "operational_performance": "unverified",
        "real_external_reconciliation_seconds": None,
        "real_key_image_retrieval_seconds": None,
    }


def run_drill(
    image: str, expected_commit: str, age: str, keygen: str, *, target_rpo: float = 3600, target_rto: float = 300
) -> dict:
    # Inspect local immutable image identity; all container runs --pull=never.
    info = json.loads(docker("image", "inspect", image))[0]
    image_id = info["Id"]
    environment = dict(value.split("=", 1) for value in info["Config"]["Env"])
    if environment.get("APP_BUILD_COMMIT") != expected_commit:
        raise ValueError("Verification image does not match expected application commit")
    identity = "drink-pos-dr-" + uuid.uuid4().hex[:16]
    original, source_volume, recovery_volume = identity + "-original", identity + "-source", identity + "-recovery"
    containers, volumes = set(), set()
    phase = "initialization"
    started, monotonic_started = utc_now(), time.monotonic()
    durations = {}
    with tempfile.TemporaryDirectory(prefix="drink-pos-disaster-") as name:
        root = Path(name)
        escrow, independent_store, scratch, journal, image_store = (
            root / n for n in ("escrow", "independent", "scratch", "journal", "images")
        )
        escrow.mkdir(mode=0o700)
        image_store.mkdir(mode=0o700)
        key = escrow / "synthetic-key.txt"
        with key.open("wb") as output:
            subprocess.run([keygen], stdout=output, stderr=subprocess.PIPE, check=True)
        if os.name == "posix":
            key.chmod(0o600)
        recipient = subprocess.run([keygen, "-y", str(key)], capture_output=True, text=True, check=True).stdout.strip()
        try:
            image_archive = image_store / "verified-image.tar"
            docker("image", "save", "--output", str(image_archive), image_id)
            image_hash = independent.file_metadata(image_archive)
            volumes.add(source_volume)
            docker("volume", "create", source_volume)
            containers.add(original)
            docker(
                "run",
                "--detach",
                "--name",
                original,
                "--pull=never",
                "--network",
                "none",
                "--mount",
                f"type=volume,source={source_volume},target=/app/data",
                "--env",
                "DRINK_POS_ENV=production",
                "--env",
                "DRINK_POS_PIN=847296",
                "--env",
                "DRINK_POS_DB=/app/data/custom.db",
                "--env",
                "DRINK_POS_MESSAGES=/app/data/messages.json",
                "--env",
                "PAYMENT_PROVIDER=",
                "--env",
                "SUMUP_API_KEY=",
                image_id,
            )
            # Wait via docker-exec loopback probe, no published ports.
            deadline = time.monotonic() + 60
            while True:
                try:
                    docker(
                        "exec",
                        original,
                        "python",
                        "-c",
                        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).read()",
                    )
                    break
                except subprocess.CalledProcessError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Synthetic source startup failed")
                    time.sleep(0.5)
            docker("cp", str(ROOT / "scripts/disaster_fixture.py"), original + ":/fixture.py")
            phase = "synthetic-population"
            docker("exec", original, "python", "/fixture.py", "seed")
            phase = "maintenance-backup"
            tick = time.monotonic()
            docker("stop", original)
            backup_output = docker(
                "run",
                "--rm",
                "--network",
                "none",
                "--pull=never",
                "--entrypoint",
                "python",
                "--mount",
                f"type=volume,source={source_volume},target=/app/data",
                image_id,
                "/app/application_recovery.py",
                "backup",
                "--database",
                "/app/data/custom.db",
                "--messages",
                "/app/data/messages.json",
                "--destination",
                "/app/data/backups",
                "--deployment-id",
                "disaster-synthetic",
                "--app-commit",
                expected_commit,
                "--quiesced",
            )
            created = json.loads(backup_output)
            backup_id = created["backup_id"]
            local_bundle = root / "local" / backup_id
            local_bundle.parent.mkdir(mode=0o700)
            docker("cp", original + ":/app/data/backups/" + backup_id, str(local_bundle))
            expected = verify_application_bundle(local_bundle)
            durations["maintenance_backup_seconds"] = time.monotonic() - tick
            # Preserve only deterministic evidence independently; not source bytes.
            expected_file = escrow / "expected.json"
            expected_file.write_text(json.dumps(expected), encoding="utf-8")
            reconciliation = {
                "scope": "synthetic-only",
                "uncertain_card": "held-no-retry",
                "post_snapshot": "held-no-replay",
                "browser_queue": "held-no-replay",
                "invoice_mail": "held-no-resend",
            }
            reconciliation_file = escrow / "reconciliation.json"
            reconciliation_file.write_text(json.dumps(reconciliation), encoding="utf-8")
            phase = "encrypted-independent-replication"
            tick = time.monotonic()
            replica = independent.replicate(
                local_bundle, independent_store, recipient=recipient, identity=key, scratch=scratch, age=age
            )
            verified = independent.verify_replica(replica, identity=key, scratch=scratch, age=age)
            independent.record_event(
                journal,
                "verification",
                "success",
                uuid.uuid4().hex,
                backup_id=backup_id,
                ciphertext_sha256=verified["ciphertext"]["sha256"],
            )
            durations["replication_verification_seconds"] = time.monotonic() - tick
            docker(
                "run",
                "--rm",
                "--network",
                "none",
                "--pull=never",
                "--entrypoint",
                "python",
                "--mount",
                f"type=volume,source={source_volume},target=/app/data",
                image_id,
                "-c",
                "import sqlite3; c=sqlite3.connect('/app/data/custom.db'); c.execute(\"INSERT INTO transactions(type,total,details,timestamp) VALUES('DR_POST_SNAPSHOT',0,'synthetic independently known loss','then')\"); c.commit(); c.close()",
            )
            phase = "source-loss"
            failure_at, loss_tick = utc_now(), time.monotonic()
            docker("rm", original)
            containers.remove(original)
            docker("volume", "rm", source_volume)
            volumes.remove(source_volume)
            shutil.rmtree(local_bundle.parent)  # exact owned disposable source-copy root
            if source_volume in docker("volume", "ls", "--format", "{{.Name}}").splitlines() or local_bundle.exists():
                raise AssertionError("Source storage remains accessible")
            phase = "independent-key-image-retrieval"
            tick = time.monotonic()
            independent.private_identity(key)
            assert independent.file_metadata(image_archive) == image_hash
            docker("image", "load", "--input", str(image_archive))
            assert json.loads(docker("image", "inspect", image_id))[0]["Id"] == image_id
            durations["synthetic_key_image_retrieval_seconds"] = time.monotonic() - tick
            phase = "independent-recovery"
            tick = time.monotonic()
            recovered_root = root / "fresh" / "recovered"
            recovered = independent.recover_replica(
                replica,
                recovered_root,
                identity=key,
                scratch=scratch,
                age=age,
                expected_commit=expected_commit,
                expected_schema=expected["database"]["schema_sha256"],
            )
            assert (
                database_metadata(
                    recovered / "state/database.db", immutable=True, original_references=expected["event_references"]
                )
                == expected["database"]
            )
            durations["decryption_recovery_validation_seconds"] = time.monotonic() - tick
            phase = "fresh-storage-reconstruction"
            volumes.add(recovery_volume)
            docker("volume", "create", recovery_volume)
            fresh = identity + "-fresh"
            containers.add(fresh)
            docker(
                "create",
                "--name",
                fresh,
                "--pull=never",
                "--network",
                "none",
                "--entrypoint",
                "python",
                "--mount",
                f"type=volume,source={recovery_volume},target=/reconstruction",
                "--env",
                "DRINK_POS_DB=/reconstruction/recovered/state/database.db",
                "--env",
                "DRINK_POS_MESSAGES=/reconstruction/recovered/state/messages.json",
                "--env",
                "DRINK_POS_ENV=production",
                "--env",
                "DRINK_POS_PIN=847296",
                "--env",
                "PAYMENT_PROVIDER=",
                "--env",
                "SUMUP_API_KEY=",
                "--env",
                "DRINK_POS_SMTP_HOST=",
                image_id,
                "/fixture.py",
                "startup",
                "/reconstruction/recovered",
                "/expected.json",
                "/reconciliation.json",
            )
            # EF-08b performs location relocation for container's final path in a
            # one-shot offline recovery container, fed ONLY independent bundle bytes.
            # Host restore above measured cross-host reconstruction; a fresh target
            # inside volume keeps references valid at startup.
            docker("cp", str(ROOT / "scripts/disaster_fixture.py"), fresh + ":/fixture.py")
            docker("cp", str(expected_file), fresh + ":/expected.json")
            docker("cp", str(reconciliation_file), fresh + ":/reconciliation.json")
            # Restore using the same compatible image, then startup in different
            # container. Container root bundle keeps basename required by format.
            tools = identity + "-tools"
            containers.add(tools)
            docker(
                "create",
                "--name",
                tools,
                "--network",
                "none",
                "--pull=never",
                "--entrypoint",
                "python",
                "--mount",
                f"type=volume,source={recovery_volume},target=/reconstruction",
                image_id,
                "/app/application_recovery.py",
                "restore",
                "/input/" + backup_id,
                "/reconstruction/recovered",
                "--expected-commit",
                expected_commit,
                "--expected-schema",
                expected["database"]["schema_sha256"],
            )
            with tempfile.TemporaryDirectory(dir=scratch) as temp:
                bundle, _ = independent.decrypt_verified(replica, key, Path(temp), age)
                docker("cp", str(bundle.parent) + "/.", tools + ":/input")
            docker("start", "--attach", tools)
            assert docker("inspect", "--format", "{{.State.ExitCode}}", tools) == "0"
            phase = "explicit-synthetic-reconciliation-startup"
            tick = time.monotonic()
            result = docker("start", "--attach", fresh)
            assert docker("inspect", "--format", "{{.State.ExitCode}}", fresh) == "0"
            assert json.loads(result.splitlines()[-1])["status"] == "isolated-synthetic-startup-verified"
            assert docker("inspect", "--format", "{{.HostConfig.NetworkMode}}", fresh) == "none"
            durations["synthetic_reconciliation_startup_seconds"] = time.monotonic() - tick
            measured = metrics(
                expected["started_at_utc"],
                failure_at,
                time.monotonic() - loss_tick,
                target_rpo=target_rpo,
                target_rto=target_rto,
            )
            if not measured["synthetic_targets_met"]:
                raise ValueError("Synthetic acceptance timing threshold exceeded")
            independent.record_event(
                journal,
                "rehearsal",
                "success",
                uuid.uuid4().hex,
                backup_id=backup_id,
                rpo_age_seconds=measured["rpo_age_seconds"],
                rto_seconds=measured["rto_seconds"],
            )
            status = independent.recovery_status(
                replica, journal, max_age_seconds=target_rpo, max_verify_age_seconds=target_rpo, max_used_percent=100
            )
            assert status["status"] == "ok", status
            return {
                "status": "synthetic-disaster-recovery-passed",
                "started_at_utc": started,
                "finished_at_utc": utc_now(),
                "assumed_failure_at_utc": failure_at,
                "backup_id": backup_id,
                "app_commit": expected_commit,
                "image_id": image_id,
                "independently_verified_at_utc": verified["independently_verified_at_utc"],
                "source_storage_removed": True,
                "recovered_startup_network": "none",
                "encryption": "external-age-X25519",
                "state": "all-table normalized fingerprint + every artifact checksum",
                "phase_durations": durations,
                "total_drill_seconds": time.monotonic() - monotonic_started,
                **measured,
                "immutability": "not-enforced",
                "geographic_hardware_independence": "not-demonstrated",
                "synthetic_post_snapshot_commits_not_recovered": 1,
                "synthetic_external_reconciliation": "held; no automatic replay/charge/mail",
            }
        except Exception:
            print(json.dumps({"status": "disaster-rehearsal-failed", "phase": phase}), file=sys.stderr)
            raise
        finally:
            for container in list(containers):
                docker("rm", "--force", container)
            for volume in list(volumes):
                docker("volume", "rm", volume)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--age", default="age")
    parser.add_argument("--age-keygen", default="age-keygen")
    parser.add_argument("--target-rpo-seconds", type=float, default=3600)
    parser.add_argument("--target-rto-seconds", type=float, default=300)
    args = parser.parse_args()
    result = run_drill(
        args.image,
        args.expected_commit,
        args.age,
        args.age_keygen,
        target_rpo=args.target_rpo_seconds,
        target_rto=args.target_rto_seconds,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
