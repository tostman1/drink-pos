"""DP-023: isolated synthetic release evidence, never a live installation."""

import importlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

from app import application_recovery as recovery
from app.db import schema


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="drink-pos-release-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "source.db"

        @contextmanager
        def connect():
            with closing(sqlite3.connect(source)) as conn:
                conn.row_factory = sqlite3.Row
                yield conn

        original = schema.DB_PATH, schema.ENV_PIN_CODE, schema.ENV_PIN_FROM_ENV, schema.get_conn
        try:
            schema.configure_runtime(str(source), "847296", False, connect)
            with patch.object(schema, "ensure_messages_file"):
                schema.init_db()
        finally:
            schema.configure_runtime(*original)
        with closing(sqlite3.connect(source)) as conn:
            conn.executescript("""
                CREATE TABLE history(id INTEGER PRIMARY KEY, payment_id TEXT UNIQUE);
                INSERT INTO history VALUES(1,'synthetic-payment');
            """)
        messages = self.root / "messages.json"
        messages.write_text('{"synthetic":"ä"}', encoding="utf-8")
        self.bundle = recovery.create_backup(
            source,
            messages,
            self.root / "backup",
            deployment_id="installation-A",
            app_commit="a" * 40,
            image_ref="registry.invalid/drink-pos@sha256:" + "1" * 64,
            configuration={"DRINK_POS_ENV": "production", "SUMUP_CURRENCY": "EUR"},
            quiesced=True,
        )

    def module(self):
        try:
            return importlib.import_module("app.upgrade_preflight")
        except ModuleNotFoundError:
            self.fail("RL-01 preflight interface missing")

    def inputs(self):
        from app.release_identity import release_identity

        module = self.module()
        current = release_identity("a" * 40, "stable", "source")
        current["image_ref"] = "registry.invalid/drink-pos@sha256:" + "1" * 64
        candidate = release_identity("b" * 40, "candidate", "candidate")
        candidate["image_ref"] = "registry.invalid/drink-pos@sha256:" + "2" * 64
        schema = recovery.read_json(self.bundle / "manifest.json")["database"]["schema_sha256"]
        evidence = {
            "format": "drink-pos-upgrade-evidence",
            "format_version": 1,
            "deployment_id": "installation-A",
            "current_identity_sha256": recovery.digest_json(current),
            "candidate_identity_sha256": recovery.digest_json(candidate),
            "source_schema_sha256": schema,
            "target_schema_sha256": schema,
            "supported": True,
            "approved_by": "synthetic-reviewer",
            "permitted_changes": [],
            "candidate_configuration": recovery.read_json(self.bundle / "configuration.json"),
            "target_python": "3.12",
            "secrets_recovery_verified": True,
            "encryption_required": False,
        }
        return module, current, candidate, evidence

    def evaluate(self, **changes):
        module, current, candidate, evidence = self.inputs()
        options = dict(
            bundle=self.bundle,
            current=current,
            candidate=candidate,
            evidence=evidence,
            isolated_copy=True,
            mode="production",
            max_backup_age_seconds=3600,
        )
        options.update(changes)
        return module.evaluate(**options)

    def test_valid_evidence_only_approves_rehearsal_without_side_effects(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        # Preflight may read SQLite; it must never request a write-capable connection.
        real_connect = sqlite3.connect

        def read_only(database, *args, **kwargs):
            self.assertTrue(str(database).endswith(("?immutable=1", "?mode=ro")))
            return real_connect(database, *args, **kwargs)

        with (
            patch("sqlite3.connect", side_effect=read_only),
            patch("socket.socket.connect", side_effect=AssertionError),
            patch("subprocess.run", side_effect=AssertionError),
        ):
            result = self.evaluate()
        self.assertEqual(result["status"], "rehearsal-ready")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(
            before, {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        )
        self.assertFalse(result["deployment_authorized"])

    def test_missing_identity_backup_and_isolation_are_not_success(self):
        for options in (
            {"current": {}},
            {"candidate": {}},
            {"evidence": {}},
            {"bundle": self.root / "missing"},
            {"isolated_copy": False},
        ):
            with self.subTest(options=options):
                result = self.evaluate(**options)
                self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(self.evaluate(evidence={})["status"], "unknown")

    def test_mutable_wrong_images_unsupported_schema_and_installation_fail_closed(self):
        module, current, candidate, evidence = self.inputs()
        for field, value in (("image_ref", "registry.invalid/drink-pos:stable"), ("git_commit", "unknown")):
            changed = {**candidate, field: value}
            result = self.evaluate(candidate=changed)
            self.assertNotEqual(result["exit_code"], 0)
        for field, value in (
            ("deployment_id", "installation-B"),
            ("supported", False),
            ("source_schema_sha256", "0" * 64),
            ("target_schema_sha256", "0" * 64),
        ):
            changed = {**evidence, field: value}
            result = self.evaluate(evidence=changed)
            self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(self.evaluate(evidence={**evidence, "supported": False})["status"], "unsafe")
        current["image_ref"] = "registry.invalid/drink-pos@sha256:" + "9" * 64
        self.assertEqual(self.evaluate(current=current)["status"], "unsafe")

    def test_configuration_runtime_and_secret_recovery_require_intervention(self):
        _, _, _, evidence = self.inputs()
        for field, value in (
            ("candidate_configuration", {"DRINK_POS_ENV": "development"}),
            ("target_python", "3.11"),
            ("secrets_recovery_verified", False),
        ):
            result = self.evaluate(evidence={**evidence, field: value})
            self.assertEqual(result["status"], "intervention-required")

    def test_encryption_receipt_must_bind_full_verification_to_this_bundle(self):
        _, _, _, evidence = self.inputs()
        evidence["encryption_required"] = True
        self.assertEqual(self.evaluate(evidence=evidence)["status"], "unknown")
        manifest = recovery.verify_application_bundle(self.bundle)
        receipt = {
            "backup_id": manifest["backup_id"],
            "deployment_id": "installation-A",
            "app_commit": "a" * 40,
            "schema_sha256": manifest["database"]["schema_sha256"],
            "verification_level": "decrypted-application-verified",
            "verification_scope": "independent",
            "verifier_id": "synthetic",
            "verified_at_utc": manifest["created_at_utc"],
        }
        self.assertEqual(self.evaluate(evidence=evidence, key_receipt=receipt)["status"], "rehearsal-ready")
        for field, value in (
            ("backup_id", "other"),
            ("verification_level", "encrypted-transfer-complete"),
            ("verification_scope", "local"),
            ("verifier_id", None),
        ):
            self.assertNotEqual(self.evaluate(evidence=evidence, key_receipt={**receipt, field: value})["exit_code"], 0)

    def test_corrupt_snapshot_and_sidecars_rejected_before_sqlite_open(self):
        database = self.bundle / "state/database.db"
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(database) + suffix)
            sidecar.write_bytes(b"synthetic")
            with patch("sqlite3.connect", side_effect=AssertionError("must reject before open")):
                result = self.evaluate(evidence={})
            self.assertEqual(result["status"], "unsafe")
            sidecar.unlink()
        database.write_bytes(b"corrupt synthetic")
        self.assertEqual(self.evaluate(evidence={})["status"], "unsafe")

    def test_snapshot_wal_header_refused_even_without_sidecars(self):
        database = self.bundle / "state/database.db"
        data = bytearray(database.read_bytes())
        data[18:20] = b"\x02\x02"
        database.write_bytes(data)
        with patch("sqlite3.connect", side_effect=AssertionError):
            self.assertEqual(self.evaluate(evidence={})["status"], "unsafe")

    def test_stale_backup_and_unapproved_schema_need_operator(self):
        _, _, _, evidence = self.inputs()
        self.assertEqual(self.evaluate(max_backup_age_seconds=0)["status"], "unknown")
        self.assertEqual(self.evaluate(max_backup_age_seconds=0.000001)["status"], "intervention-required")
        evidence["approved_by"] = ""
        self.assertEqual(self.evaluate(evidence=evidence)["status"], "unknown")

    def test_local_identity_is_deterministic_no_registry_or_runtime_import(self):
        from app.release_identity import release_identity

        self.assertEqual(release_identity("b" * 40, "local", None), release_identity("b" * 40, "local", None))
        _, current, candidate, evidence = self.inputs()
        candidate["image_ref"] = None
        evidence["candidate_identity_sha256"] = recovery.digest_json(candidate)
        self.assertEqual(
            self.evaluate(candidate=candidate, evidence=evidence, mode="local")["status"], "rehearsal-ready"
        )
        self.assertEqual(self.evaluate(candidate=candidate, evidence=evidence)["status"], "unknown")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from app.release_identity import release_identity; import sys; release_identity('b'*40,'local',None); assert 'app.main' not in sys.modules and 'app.db.schema' not in sys.modules",
            ],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_json_exit_codes_and_sanitized_missing_input(self):
        module, current, candidate, evidence = self.inputs()
        paths = []
        for name, value in (("current", current), ("candidate", candidate), ("evidence", evidence)):
            path = self.root / (name + ".json")
            path.write_text(json.dumps(value), encoding="utf-8")
            paths.append(str(path))
        args = [
            sys.executable,
            "-B",
            "-m",
            "app.upgrade_preflight",
            "--bundle",
            str(self.bundle),
            "--current",
            paths[0],
            "--candidate",
            paths[1],
            "--evidence",
            paths[2],
            "--isolated-copy",
            "--mode",
            "production",
            "--max-backup-age-seconds",
            "3600",
        ]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "rehearsal-ready")
        Path(paths[1]).unlink()
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 4)
        self.assertEqual(json.loads(result.stdout)["status"], "unknown")
        self.assertNotIn(str(self.root), result.stdout + result.stderr)

    def test_required_application_tables_cannot_be_replaced_by_generic_sqlite(self):
        _, _, _, evidence = self.inputs()
        database = self.bundle / "state/database.db"
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("DROP TABLE self_payment_sessions")
            conn.commit()
        manifest = recovery.read_json(self.bundle / "manifest.json")
        manifest["database"] = recovery.database_metadata(database, immutable=True)
        manifest["files"]["state/database.db"] = recovery.file_metadata(database)
        (self.bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        marker = {
            "status": "verified",
            "backup_id": self.bundle.name,
            "manifest": recovery.file_metadata(self.bundle / "manifest.json"),
        }
        (self.bundle / "COMPLETED.json").write_text(json.dumps(marker), encoding="utf-8")
        evidence["source_schema_sha256"] = evidence["target_schema_sha256"] = manifest["database"]["schema_sha256"]
        self.assertEqual(self.evaluate(evidence=evidence)["status"], "unsafe")

    def test_future_unassigned_and_malformed_metadata_never_succeed(self):
        _, current, candidate, evidence = self.inputs()
        for changed in (
            {**candidate, "format_version": 99},
            {**candidate, "version": None},
            {**candidate, "schema_version": 1},
            {**candidate, "python": [{}]},
        ):
            self.assertEqual(self.evaluate(candidate=changed)["status"], "unknown")
        self.assertNotEqual(self.evaluate(evidence={**evidence, "candidate_identity_sha256": "0" * 64})["exit_code"], 0)

    def test_foreign_key_corruption_and_observed_change_are_rejected(self):
        from app import upgrade_preflight

        _, current, candidate, evidence = self.inputs()
        verify = upgrade_preflight.verify_application_bundle
        calls = []

        def changed(bundle):
            calls.append(1)
            if len(calls) == 2:
                (bundle / "state/messages.json").write_text('{"changed":true}', encoding="utf-8")
            return verify(bundle)

        with patch.object(upgrade_preflight, "verify_application_bundle", side_effect=changed):
            self.assertEqual(self.evaluate(evidence=evidence)["status"], "unsafe")
        database = self.bundle / "state/database.db"
        with closing(sqlite3.connect(database)) as conn:
            conn.execute(
                "INSERT INTO order_lines(person_id,item_id,quantity,unit_price_eur,item_name_snapshot,item_short_label_snapshot,consumed_date,created_at,updated_at) VALUES(999999,NULL,1,2.5,'synthetic','synthetic','then','then','then')"
            )
            conn.commit()
        self.assertEqual(self.evaluate(evidence=evidence)["status"], "unsafe")

    def test_interrupted_cli_returns_unknown_and_no_write_on_read_only_bundle(self):
        import io
        from contextlib import redirect_stdout
        from app import upgrade_preflight

        with (
            patch.object(upgrade_preflight, "read_json", side_effect=KeyboardInterrupt),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = upgrade_preflight.main(
                [
                    "--bundle",
                    str(self.bundle),
                    "--current",
                    "current.json",
                    "--candidate",
                    "candidate.json",
                    "--evidence",
                    "evidence.json",
                    "--mode",
                    "production",
                    "--max-backup-age-seconds",
                    "3600",
                ]
            )
        self.assertEqual(code, 130)
        self.assertEqual(json.loads(output.getvalue())["status"], "unknown")
        if sys.platform.startswith("linux"):
            files = [p for p in self.bundle.rglob("*") if p.is_file()]
            directories = [self.bundle, *[p for p in self.bundle.rglob("*") if p.is_dir()]]
            try:
                for p in files:
                    p.chmod(0o400)
                for p in directories:
                    p.chmod(0o500)
                self.assertEqual(self.evaluate()["exit_code"], 0)
            finally:
                for p in directories:
                    p.chmod(0o700)
                for p in files:
                    p.chmod(0o600)
