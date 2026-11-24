"""Actual RL-06 Compose/image rehearsal in disposable CI-only test state.

Retains financial evidence and failure state. Never runs production Compose,
pulls, imports existing installations or accesses real provider/mail/NAS.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from container_smoke import request, wait_ready

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "25a78ba6606e74760969cce7c993d60d3a139f2e"


def rehearsal(image: str, commit: str, target: Path, baseline_image: str, unsupported_image: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or os.path.lexists(target):
        raise ValueError("Exact source and nonexistent disposable target required")
    target.mkdir(mode=0o700, parents=True)
    candidate_tag = "drink-pos-test:" + commit
    baseline_tag = "drink-pos-test:" + BASELINE
    for source, tag in ((image, candidate_tag), (baseline_image, baseline_tag)):
        subprocess.run(["docker", "tag", source, tag], check=True)
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("DRINK_POS_", "SUMUP_", "SMTP_", "PAYMENT_PROVIDER"))
    }
    env.update(
        DRINK_POS_TEST_IMAGE=candidate_tag,
        DRINK_POS_TEST_HOST_ROOT=str(target.absolute()),
        DRINK_POS_TEST_ID="drink-pos-test-ci",
        DRINK_POS_TEST_PIN="7391850264",
        DRINK_POS_TEST_TZ="Europe/Zurich",
        DRINK_POS_TEST_SUBNET="172.30.89.0/28",
        DRINK_POS_TEST_CONTAINER_IP="172.30.89.2",
        DRINK_POS_TEST_UID=str(os.getuid()),
        DRINK_POS_TEST_GID=str(os.getgid()),
    )
    prefix = [
        "docker",
        "compose",
        "--env-file",
        str(ROOT / ".env.test.example"),
        "-p",
        "drink-pos-test",
        "-f",
        str(ROOT / "compose.synology.test.yaml"),
    ]
    baseline_override = target / "baseline-override.yaml"
    baseline_override.write_text(
        "services:\n  drink-pos-test:\n    command: [uvicorn, 'main:app', --host, 0.0.0.0, --port, '8000']\n",
        encoding="utf-8",
    )
    current_commit = commit

    def compose(*args, ok=True):
        result = subprocess.run([*prefix, *args], env=env, capture_output=True, text=True)
        if ok and result.returncode:
            raise RuntimeError("Disposable Compose operation failed: " + result.stderr)
        return result

    def tool(*args, ok=True, fresh=False, readonly=False):
        # Read-only inspection mounts do not accidentally authorize state mutation.
        if readonly:
            command = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--pull",
                "never",
                "--read-only",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--mount",
                f"type=bind,source={target.absolute()},target=/test,readonly",
                "--entrypoint",
                "python",
                image,
                "-B",
                "/app/synology_test.py",
                *args,
            ]
            result = subprocess.run(command, env=env, capture_output=True, text=True)
        else:
            extra = ["-e", "DRINK_POS_ALLOW_FRESH=1"] if fresh else []
            result = compose(
                "run",
                "--rm",
                "--no-deps",
                *extra,
                "drink-pos-test",
                "python",
                "-B",
                "/app/synology_test.py",
                *args,
                ok=False,
            )
        if ok and result.returncode:
            raise RuntimeError("Disposable test utility failed: " + result.stderr)
        return result

    pin = env["DRINK_POS_TEST_PIN"]
    base = "http://" + env["DRINK_POS_TEST_CONTAINER_IP"] + ":8000"

    def api(path, payload=None):
        return json.loads(request(base, path, payload))

    def health():
        result = wait_ready(base)
        assert result["status"] == "ok"
        assert api("/api/config")["build"]["commit"] == current_commit

    def start():
        compose("up", "-d", "--no-build", "--pull", "never")
        health()

    compose("config", "--quiet")
    # Uninitialized deliverable must exit, not silently seed on startup.
    assert tool("inspect", ok=False).returncode != 0
    assert not (target / "data").exists()
    tool("initialize", "--synthetic-only", fresh=True)
    assert tool("initialize", "--synthetic-only", fresh=True, ok=False).returncode != 0
    tool("inspect")
    try:
        start()
        inspected = json.loads(
            subprocess.run(["docker", "inspect", "drink-pos-test"], capture_output=True, text=True, check=True).stdout
        )[0]
        assert inspected["HostConfig"]["ReadonlyRootfs"]
        assert inspected["HostConfig"]["CapDrop"] == ["ALL"]
        assert inspected["HostConfig"]["RestartPolicy"]["Name"] == "no"
        assert all(
            m["Source"] == str(target.absolute()) and m["Destination"] == "/test"
            for m in inspected["Mounts"]
            if m["Type"] == "bind"
        )
        network = next(iter(inspected["NetworkSettings"]["Networks"]))
        details = json.loads(
            subprocess.run(["docker", "network", "inspect", network], capture_output=True, text=True, check=True).stdout
        )[0]
        assert details["Internal"]
        # Actual outbound network prohibition, not merely empty credentials.
        outbound = subprocess.run(
            [
                "docker",
                "exec",
                "drink-pos-test",
                "python",
                "-B",
                "-c",
                "import socket; socket.create_connection(('1.1.1.1',443),timeout=2)",
            ],
            capture_output=True,
            text=True,
        )
        assert outbound.returncode != 0
        timezone = subprocess.run(
            [
                "docker",
                "exec",
                "drink-pos-test",
                "python",
                "-B",
                "-c",
                "import os,time; assert os.environ['TZ']=='Europe/Zurich'; time.tzset(); assert time.tzname==('CET','CEST')",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert timezone.returncode == 0
        config = api("/api/config")
        item = config["user_items"][0]
        payer, consumer = [
            api("/api/admin/people/create", {"pin": pin, "first_name": "CI", "last_name": name})["id"]
            for name in ("Roundpayer", "Consumer")
        ]
        for person in (payer, consumer):
            api("/api/add-drink", {"person_id": person, "item_id": item["id"], "client_operation_id": f"rl06-{person}"})
        api("/api/round-request", {"person_id": payer, "quantity": 1})
        query = "import sqlite3,json; c=sqlite3.connect('/test/data/database.db'); print(json.dumps(c.execute('SELECT id FROM round_units ORDER BY id DESC LIMIT 1').fetchone())); c.close()"
        unit = json.loads(
            subprocess.run(
                ["docker", "exec", "drink-pos-test", "python", "-B", "-c", query],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )[0]
        api("/api/deduct-round", {"pin": pin, "round_unit_id": unit})
        cancellation = {
            "pin": pin,
            "round_unit_ids": [unit],
            "correction_operation_id": "rl06-cancel",
            "correction_reason": "Synthetic installation rehearsal",
        }
        cancelled = api("/api/admin/rounds/cancel", cancellation)
        stats = api("/api/admin/statistics", {"pin": pin, "scope": "all"})
        assert stats["kpis"]["quantity"] == 2
        assert stats["rounds"]["deducted_vk_eur"] == 0
        assert api("/api/admin/rounds/cancel", cancellation) == cancelled
        paid = api("/api/pay", {"pin": pin, "person_id": payer, "payment_operation_id": "rl06-cash"})
        assert paid["status"] == "paid"
        api("/api/admin/event/start", {"pin": pin, "name": "RL06 synthetic invoice"})
        api("/api/event/add-drink", {"item_id": item["id"]})
        api("/api/admin/event/end", {"pin": pin, "create_invoice": True})
        balance = api(f"/api/kassa/person/{consumer}")
        compose("restart")
        health()
        assert api(f"/api/kassa/person/{consumer}")["revision"] == balance["revision"]
        compose("stop")
        # Verified immutable main baseline has the same v2 financial contract but
        # predates the test-only wrapper. Run that exact app with unchanged strict
        # permissions in the SAME isolated deliverable Compose, command-only
        # override; no fresh/adoption and no schema transformation.
        env["DRINK_POS_TEST_IMAGE"] = baseline_tag
        prefix.extend(["-f", str(baseline_override)])
        current_commit = BASELINE
        start()
        assert api("/api/admin/rounds/cancel", cancellation) == cancelled
        assert api(f"/api/kassa/person/{consumer}")["revision"] == balance["revision"]
        compose("stop")
        backed_result = compose(
            "run",
            "--rm",
            "--no-deps",
            "drink-pos-test",
            "python",
            "-B",
            "/app/application_recovery.py",
            "backup",
            "--database",
            "/test/data/database.db",
            "--messages",
            "/test/data/messages.json",
            "--destination",
            "/test/backups",
            "--deployment-id",
            "drink-pos-test-ci",
            "--app-commit",
            BASELINE,
            "--quiesced",
        )
        backed = json.loads(backed_result.stdout)
        backed["bundle"] = backed["path"]
        current_identity = json.loads(
            compose(
                "run",
                "--rm",
                "--no-deps",
                "drink-pos-test",
                "python",
                "-B",
                "/app/release_identity.py",
                "--commit",
                BASELINE,
                "--channel",
                "synology-test",
            ).stdout
        )
        # Restore with exact original image before candidate preflight, preserving
        # all state as well as the original baseline image and identity.
        bundle = Path(backed["bundle"].replace("/test", str(target.absolute()), 1))
        manifest = json.loads((bundle / "manifest.json").read_text())
        compose(
            "run",
            "--rm",
            "--no-deps",
            "drink-pos-test",
            "python",
            "-B",
            "/app/application_recovery.py",
            "restore",
            "/test/backups/" + backed["backup_id"],
            "/test/recovery/pre-update",
            "--expected-commit",
            BASELINE,
            "--expected-schema",
            manifest["database"]["schema_sha256"],
        )
        shutil.copyfile(
            target / "data/TEST-INSTALLATION.json", target / "recovery/pre-update/state/TEST-INSTALLATION.json"
        )
        del prefix[-2:]
        env["DRINK_POS_TEST_IMAGE"] = candidate_tag
        current_commit = commit
        independent_bundle = "/test/evidence/" + backed["backup_id"]
        shutil.copytree(bundle, target / "evidence" / backed["backup_id"])
        old_schema = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--pull",
                "never",
                "--read-only",
                "--mount",
                f"type=bind,source={bundle.absolute()},target=/snapshot,readonly",
                "--entrypoint",
                "python",
                unsupported_image,
                "-B",
                "/app/db/migrations.py",
                "/snapshot/state/database.db",
            ],
            capture_output=True,
            text=True,
        )
        assert old_schema.returncode != 0
        assert json.loads(old_schema.stdout)["state"] == "future-version"
        preserved = {
            p.relative_to(target / "data"): p.read_bytes() for p in (target / "data").rglob("*") if p.is_file()
        }
        env["DRINK_POS_TEST_IMAGE"] = unsupported_image
        failed_start = compose(
            "run", "--rm", "--no-deps", "drink-pos-test", "python", "-B", "-c", "import main; main.startup()", ok=False
        )
        assert failed_start.returncode != 0
        assert preserved == {
            p.relative_to(target / "data"): p.read_bytes() for p in (target / "data").rglob("*") if p.is_file()
        }
        env["DRINK_POS_TEST_IMAGE"] = candidate_tag
        tool("verify", independent_bundle, readonly=True)
        identity = json.loads(tool("identity", readonly=True).stdout)
        # Exact-baseline -> candidate same-schema/no-financial-change decision is
        # synthetic evidence only, not compatibility for arbitrary older images.
        import hashlib

        def digest_json(value):
            return hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest()

        evidence = {
            "format": "drink-pos-upgrade-evidence",
            "format_version": 1,
            "deployment_id": "drink-pos-test-ci",
            "current_identity_sha256": digest_json(current_identity),
            "candidate_identity_sha256": digest_json(identity),
            "source_schema_sha256": manifest["database"]["schema_sha256"],
            "target_schema_sha256": manifest["database"]["schema_sha256"],
            "supported": True,
            "approved_by": "ci-exact-baseline-candidate-rehearsal-only",
            "permitted_changes": [],
            "candidate_configuration": json.loads((bundle / "configuration.json").read_text()),
            "target_python": "3.12",
            "secrets_recovery_verified": True,
            "encryption_required": False,
        }
        for name, value in (("identity", identity), ("current", current_identity), ("compatibility", evidence)):
            (target / f"evidence/{name}.json").write_text(json.dumps(value), encoding="utf-8")
        ready = tool(
            "preflight",
            "--bundle",
            independent_bundle,
            "--current",
            "/test/evidence/current.json",
            "--candidate",
            "/test/evidence/identity.json",
            "--evidence",
            "/test/evidence/compatibility.json",
            "--isolated-copy",
            readonly=True,
        )
        assert not json.loads(ready.stdout)["deployment_authorized"]
        (target / "evidence/PREFLIGHT.json").write_text(ready.stdout, encoding="utf-8")
        # No operator approval inferred from green preflight. In this explicitly
        # synthetic exercise only, approve candidate start after isolated restore.
        env["DRINK_POS_TEST_STATE"] = "recovery/pre-update/state"
        start()
        assert api("/api/admin/rounds/cancel", cancellation) == cancelled
        assert api(f"/api/kassa/person/{consumer}")["revision"] == balance["revision"]
        compose("stop")
        env["DRINK_POS_TEST_STATE"] = "data"
        compose("up", "-d", "--no-build", "--pull", "never", "--force-recreate")
        health()
        assert api("/api/admin/rounds/cancel", cancellation) == cancelled
        assert api(f"/api/kassa/person/{consumer}")["revision"] == balance["revision"]
        # Compare every table/schema/ledger/receipt and DB-referenced artifact,
        # not just balances. No permitted financial/startup transformation.
        full_check = (
            "from pathlib import Path; from application_recovery import database_metadata,read_json; "
            f"m=read_json(Path('{independent_bundle}/manifest.json')); "
            "assert database_metadata(Path('/test/data/database.db'),original_references=m['event_references'])==m['database']"
        )
        compose("exec", "drink-pos-test", "python", "-B", "-c", full_check)
        api("/api/add-drink", {"person_id": consumer, "item_id": item["id"], "client_operation_id": "rl06-post-backup"})
        compose("stop")
        # Start only explicitly approved independent recovery after preserving
        # post-backup original state; verify full old financial replay outcome.
        env["DRINK_POS_TEST_STATE"] = "recovery/pre-update/state"
        env["DRINK_POS_TEST_IMAGE"] = baseline_tag
        prefix.extend(["-f", str(baseline_override)])
        current_commit = BASELINE
        start()
        assert api("/api/admin/rounds/cancel", cancellation) == cancelled
        assert api(f"/api/kassa/person/{consumer}")["revision"] == balance["revision"]
        assert api("/api/admin/statistics", {"pin": pin, "scope": "all"})["kpis"]["quantity"] == 2
        compose("stop")
        del prefix[-2:]
        env["DRINK_POS_TEST_IMAGE"] = candidate_tag
        current_commit = commit
        env["DRINK_POS_TEST_STATE"] = "data"
        start()
        assert api(f"/api/kassa/person/{consumer}")["total"] == balance["total"] + item["price"]
        compose("stop")
        result = {
            "status": "actual-test-compose-verified",
            "source_sha": commit,
            "fresh_v2": True,
            "no_reseed": True,
            "persistent_restart": True,
            "outbound_blocked": True,
            "independent_full_recovery": True,
            "round_replay_preserved": True,
            "post_backup_activity_preserved": True,
            "update_scope": "exact-main-baseline-to-candidate-same-v2-schema",
            "baseline_sha": BASELINE,
            "unsupported_v1_image_downgrade_blocked": True,
            "failed_candidate_state_preserved": True,
            "full_state_candidate_comparison": True,
            "nas_device_acceptance": "pending",
            "backup_id": backed["backup_id"],
            "approval": "explicit-synthetic-ci-only-not-operator-deployment",
            "candidate_image_config_id": subprocess.run(
                ["docker", "image", "inspect", "--format", "{{.Id}}", image], capture_output=True, text=True, check=True
            ).stdout.strip(),
            "baseline_image_config_id": subprocess.run(
                ["docker", "image", "inspect", "--format", "{{.Id}}", baseline_image],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            "schema_sha256": manifest["database"]["schema_sha256"],
        }
        (target / "evidence/RESULT.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    except Exception:
        logs = compose("logs", "--no-color", ok=False)
        (target / "evidence/FAILED-container.log").write_text(
            (logs.stdout + logs.stderr).replace(pin, "[REDACTED]"), encoding="utf-8"
        )
        raise
    finally:
        # Only this owned test project; retain host evidence and failed state.
        compose("down", ok=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--baseline-image", required=True)
    parser.add_argument("--unsupported-image", required=True)
    args = parser.parse_args()
    print(json.dumps(rehearsal(args.image, args.commit, args.target, args.baseline_image, args.unsupported_image)))


if __name__ == "__main__":
    main()
