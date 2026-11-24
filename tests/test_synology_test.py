"""RL-06 / DP-001,008,009,016,024 test-only deployment boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


class SynologyTestTests(unittest.TestCase):
    def environment(self, root):
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("DRINK_POS_", "SUMUP_", "SMTP_", "APP_BUILD_", "PAYMENT_PROVIDER"))
        }
        env.update(
            DRINK_POS_TEST_ID="drink-pos-test-regression",
            DRINK_POS_TEST_ROOT=str(root),
            DRINK_POS_ENV="production",
            DRINK_POS_PIN="7391850264",
            TZ="Europe/Zurich",
            DRINK_POS_DB=str(root / "data/database.db"),
            DRINK_POS_MESSAGES=str(root / "data/messages.json"),
            DRINK_POS_BACKUP_DIR=str(root / "backups"),
            DRINK_POS_MIGRATION_MODE="versioned",
            DRINK_POS_ALLOW_FRESH="0",
            DRINK_POS_ADOPT_LEGACY="0",
            APP_BUILD_COMMIT=COMMIT,
            DRINK_POS_IMAGE_REF="drink-pos-test:" + COMMIT,
        )
        return env

    def command(self, env, *args):
        return subprocess.run(
            [sys.executable, "-B", "-m", "app.synology_test", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_compose_is_local_only_one_service_and_internal_network(self):
        config = yaml.safe_load((ROOT / "compose.synology.test.yaml").read_text())
        self.assertEqual(list(config["services"]), ["drink-pos-test"])
        service = config["services"]["drink-pos-test"]
        self.assertEqual(service["pull_policy"], "never")
        self.assertEqual(service["platform"], "linux/amd64")
        self.assertEqual(service["cap_drop"], ["ALL"])
        self.assertTrue(service["read_only"])
        self.assertTrue(config["networks"]["test-only"]["internal"])
        self.assertNotIn("ports", service)
        self.assertIn("ipv4_address", service["networks"]["test-only"])
        self.assertNotIn("build", service)
        self.assertNotIn("env_file", service)
        self.assertTrue(all(v["target"] != "/app" for v in service["volumes"]))

    def test_missing_marker_serve_rejects_without_creating_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.command(self.environment(root), "serve")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "data").exists())

    def test_initialization_rejects_mutable_or_mismatched_image_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for image in ("drink-pos:stable", "drink-pos-test:" + "b" * 40, ""):
                env = self.environment(root)
                env.update(DRINK_POS_ALLOW_FRESH="1", DRINK_POS_IMAGE_REF=image)
                self.assertNotEqual(self.command(env, "initialize", "--synthetic-only").returncode, 0)
                self.assertFalse((root / "data").exists())

    def test_explicit_empty_initialization_v2_read_only_inspect_and_repeat_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.environment(root)
            denied = self.command(env, "initialize")
            self.assertNotEqual(denied.returncode, 0)
            self.assertFalse((root / "data").exists())
            env["DRINK_POS_ALLOW_FRESH"] = "1"
            result = self.command(env, "initialize", "--synthetic-only")
            self.assertEqual(result.returncode, 0, result.stderr)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            repeat = self.command(env, "initialize", "--synthetic-only")
            self.assertNotEqual(repeat.returncode, 0)
            env["DRINK_POS_ALLOW_FRESH"] = "0"
            inspected = self.command(env, "inspect")
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            self.assertEqual(json.loads(inspected.stdout)["migration"]["version"], 2)
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})

    def test_initialization_blocks_weak_pin_credentials_adoption_and_nonempty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, value in (
                ("DRINK_POS_PIN", "1234567890"),
                ("SUMUP_API_KEY", "secret-do-not-log"),
                ("DRINK_POS_AGENT_TOKEN", "secret-do-not-log"),
                ("DRINK_POS_ADOPT_LEGACY", "1"),
                ("TZ", ""),
                ("DRINK_POS_TEST_ID", "drink-pos"),
            ):
                with self.subTest(key=key):
                    env = self.environment(root)
                    env.update({key: value, "DRINK_POS_ALLOW_FRESH": "1"})
                    result = self.command(env, "initialize", "--synthetic-only")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("secret-do-not-log", result.stdout + result.stderr)
                    self.assertFalse((root / "data").exists())
            (root / "data").mkdir()
            (root / "data/keep.txt").write_text("do not discard")
            env = self.environment(root)
            env["DRINK_POS_ALLOW_FRESH"] = "1"
            self.assertNotEqual(self.command(env, "initialize", "--synthetic-only").returncode, 0)
            self.assertEqual((root / "data/keep.txt").read_text(), "do not discard")

    def test_full_backup_independent_verify_restore_and_identity_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.environment(root)
            env["DRINK_POS_ALLOW_FRESH"] = "1"
            self.assertEqual(self.command(env, "initialize", "--synthetic-only").returncode, 0)
            env["DRINK_POS_ALLOW_FRESH"] = "0"
            self.assertNotEqual(self.command(env, "backup").returncode, 0)
            backed = self.command(env, "backup", "--quiesced")
            self.assertEqual(backed.returncode, 0, backed.stderr)
            bundle = Path(json.loads(backed.stdout)["bundle"])
            self.assertEqual(self.command(env, "verify", str(bundle)).returncode, 0)
            import shutil

            renamed = root / "evidence/renamed"
            shutil.copytree(bundle, renamed)
            self.assertNotEqual(self.command(env, "verify", str(renamed)).returncode, 0)
            independent = root / "evidence" / bundle.name
            shutil.copytree(bundle, independent)
            self.assertEqual(self.command(env, "verify", str(independent)).returncode, 0)
            self.assertNotEqual(self.command(env, "restore", str(bundle), "independent").returncode, 0)
            wrong = dict(env, APP_BUILD_COMMIT="b" * 40)
            self.assertNotEqual(
                self.command(wrong, "restore", str(bundle), "wrong", "--approve-full-recovery").returncode, 0
            )
            self.assertFalse((root / "recovery/wrong").exists())
            restored = self.command(env, "restore", str(bundle), "independent", "--approve-full-recovery")
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertNotEqual(
                self.command(env, "restore", str(bundle), "independent", "--approve-full-recovery").returncode, 0
            )
            recovered = dict(
                env,
                DRINK_POS_TEST_STATE="recovery/independent/state",
                DRINK_POS_DB=str(root / "recovery/independent/state/database.db"),
                DRINK_POS_MESSAGES=str(root / "recovery/independent/state/messages.json"),
            )
            self.assertEqual(self.command(recovered, "inspect").returncode, 0)

    def test_future_or_unversioned_database_and_marker_mismatch_block_inspect(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.environment(root)
            env["DRINK_POS_ALLOW_FRESH"] = "1"
            self.assertEqual(self.command(env, "initialize", "--synthetic-only").returncode, 0)
            env["DRINK_POS_ALLOW_FRESH"] = "0"
            marker = root / "data/TEST-INSTALLATION.json"
            original = marker.read_bytes()
            data = json.loads(original)
            data["deployment_id"] = "drink-pos-test-another"
            marker.write_text(json.dumps(data))
            self.assertNotEqual(self.command(env, "inspect").returncode, 0)
            marker.write_bytes(original)
            for version in (0, 3):
                with closing(sqlite3.connect(root / "data/database.db")) as connection:
                    connection.execute(f"PRAGMA user_version={version}")
                before = (root / "data/database.db").read_bytes()
                self.assertNotEqual(self.command(env, "inspect").returncode, 0)
                self.assertEqual(before, (root / "data/database.db").read_bytes())

    def test_preflight_requires_isolated_exact_image_and_no_state_changes(self):
        from app.application_recovery import digest_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.environment(root)
            env["DRINK_POS_ALLOW_FRESH"] = "1"
            self.assertEqual(self.command(env, "initialize", "--synthetic-only").returncode, 0)
            env["DRINK_POS_ALLOW_FRESH"] = "0"
            backed = self.command(env, "backup", "--quiesced")
            self.assertEqual(backed.returncode, 0, backed.stderr)
            bundle = Path(json.loads(backed.stdout)["bundle"])
            manifest = json.loads((bundle / "manifest.json").read_text())
            identity = json.loads(self.command(env, "identity").stdout)
            evidence = {
                "format": "drink-pos-upgrade-evidence",
                "format_version": 1,
                "deployment_id": env["DRINK_POS_TEST_ID"],
                "current_identity_sha256": digest_json(identity),
                "candidate_identity_sha256": digest_json(identity),
                "source_schema_sha256": manifest["database"]["schema_sha256"],
                "target_schema_sha256": manifest["database"]["schema_sha256"],
                "supported": True,
                "approved_by": "synthetic-regression-only",
                "permitted_changes": [],
                "candidate_configuration": json.loads((bundle / "configuration.json").read_text()),
                "target_python": "3.12",
                "secrets_recovery_verified": True,
                "encryption_required": False,
            }
            identity_path = root / "evidence/identity.json"
            evidence_path = root / "evidence/compatibility.json"
            identity_path.write_text(json.dumps(identity))
            evidence_path.write_text(json.dumps(evidence))
            args = (
                "preflight",
                "--bundle",
                str(bundle),
                "--current",
                str(identity_path),
                "--candidate",
                str(identity_path),
                "--evidence",
                str(evidence_path),
            )
            self.assertNotEqual(self.command(env, *args).returncode, 0)
            ready = self.command(env, *args, "--isolated-copy")
            self.assertEqual(ready.returncode, 0, ready.stderr + ready.stdout)
            self.assertFalse(json.loads(ready.stdout)["deployment_authorized"])
            evidence["permitted_changes"] = ["unapproved financial rewrite"]
            evidence_path.write_text(json.dumps(evidence))
            self.assertNotEqual(self.command(env, *args, "--isolated-copy").returncode, 0)
            evidence["permitted_changes"] = []
            evidence["supported"] = False
            evidence_path.write_text(json.dumps(evidence))
            self.assertNotEqual(self.command(env, *args, "--isolated-copy").returncode, 0)

    def test_archive_identity_checksum_platform_tag_and_config_tampering(self):
        import hashlib
        import io
        import tarfile
        from scripts.export_test_image import verify_archive

        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "image.tar"
            config = json.dumps(
                {"os": "linux", "architecture": "amd64", "config": {"Env": ["APP_BUILD_COMMIT=" + COMMIT]}}
            ).encode()
            config_hash = hashlib.sha256(config).hexdigest()
            tag = "drink-pos-test:" + COMMIT
            manifest = json.dumps([{"Config": config_hash + ".json", "RepoTags": [tag], "Layers": []}]).encode()
            with tarfile.open(archive, "w") as bundle:
                for name, content in (("manifest.json", manifest), (config_hash + ".json", config)):
                    entry = tarfile.TarInfo(name)
                    entry.size = len(content)
                    bundle.addfile(entry, io.BytesIO(content))
            receipt = {
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "source_sha": COMMIT,
                "image_config_id": "sha256:" + config_hash,
                "image_tag": tag,
            }
            verify_archive(archive, receipt)
            for key, value in (
                ("archive_sha256", "0" * 64),
                ("image_config_id", "sha256:" + "0" * 64),
                ("source_sha", "b" * 40),
                ("image_tag", "drink-pos:stable"),
            ):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_archive(archive, {**receipt, key: value})


if __name__ == "__main__":
    unittest.main()
