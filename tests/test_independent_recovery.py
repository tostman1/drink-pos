"""DP-022 real external age integration, disposable keys/state only."""

import importlib
import errno
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import tarfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


class IndependentRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="drink-pos-independent-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original"
        self.source.mkdir()
        self.scratch = self.root / "private-scratch"
        self.destination = self.root / "independent"
        self.escrow = self.root / "escrow"
        self.escrow.mkdir(mode=0o700)
        self.age = os.environ.get("DRINK_POS_TEST_AGE") or shutil.which("age")
        self.keygen = os.environ.get("DRINK_POS_TEST_AGE_KEYGEN") or shutil.which("age-keygen")
        if not self.age or not self.keygen:
            self.fail("External age/age-keygen required: install pinned tools; never silently skip encryption checks")
        self.key = self.escrow / "identity.txt"
        with self.key.open("wb") as output:
            subprocess.run([self.keygen], stdout=output, stderr=subprocess.PIPE, check=True)
        if os.name == "posix":
            self.key.chmod(0o600)
        self.recipient = subprocess.run(
            [self.keygen, "-y", str(self.key)], capture_output=True, text=True, check=True
        ).stdout.strip()
        self.database = self.source / "custom.db"
        with closing(sqlite3.connect(self.database)) as conn:
            conn.executescript("""
                CREATE TABLE transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, details TEXT, amount REAL);
                INSERT INTO transactions VALUES(1,'synthetic audit',2.5);
                CREATE TRIGGER immutable BEFORE DELETE ON transactions BEGIN SELECT RAISE(ABORT,'immutable'); END;
                CREATE TABLE event_sessions(id INTEGER PRIMARY KEY, csv_path TEXT, pdf_path TEXT, status TEXT, invoice_created INTEGER);
            """)
            events = self.source / "events"
            events.mkdir()
            (events / "bill.csv").write_bytes(b"\xef\xbb\xbfsynthetic-invoice")
            (events / "bill.pdf").write_bytes(b"%PDF-synthetic")
            conn.execute(
                "INSERT INTO event_sessions VALUES(1,?,?,'CLOSED',1)",
                (str(events / "bill.csv"), str(events / "bill.pdf")),
            )
            conn.commit()
        self.messages = self.source / "messages.json"
        self.messages.write_text('{"synthetic":"Independent recovery"}', encoding="utf-8")
        from app.application_recovery import create_backup

        self.bundle = create_backup(
            self.database,
            self.messages,
            self.source / "backups",
            deployment_id="independent-test",
            app_commit="a" * 40,
            quiesced=True,
        )
        from app.application_recovery import verify_application_bundle

        self.manifest = verify_application_bundle(self.bundle)

    def module(self):
        try:
            return importlib.import_module("app.independent_recovery")
        except ModuleNotFoundError:
            self.fail("EF-08c independent replica interface missing")

    def replicate(self):
        return self.module().replicate(
            self.bundle,
            self.destination,
            recipient=self.recipient,
            identity=self.key,
            scratch=self.scratch,
            age=self.age,
        )

    def recover(self, replica, target=None, identity=None):
        return self.module().recover_replica(
            replica,
            target or self.root / "reconstructed",
            identity=identity or self.key,
            scratch=self.scratch,
            age=self.age,
            expected_commit="a" * 40,
            expected_schema=self.manifest["database"]["schema_sha256"],
        )

    def test_encrypted_independent_recovery_after_complete_source_loss(self):
        replica = self.replicate()
        ciphertext = (replica / "payload.tar.age").read_bytes()
        self.assertNotIn(b"synthetic audit", ciphertext)
        self.assertNotIn(self.key.read_bytes().strip(), ciphertext)
        self.assertEqual({p.name for p in replica.iterdir()}, {"payload.tar.age", "replica.json", "COMPLETED.json"})
        summary = self.module().verify_replica(replica, identity=self.key, scratch=self.scratch, age=self.age)
        self.assertEqual(summary["backup_id"], self.bundle.name)
        shutil.rmtree(self.source)  # owned disposable source ONLY
        self.assertFalse(self.source.exists())
        recovered = self.recover(replica)
        from app.application_recovery import database_metadata

        self.assertEqual(
            database_metadata(
                recovered / "state/database.db", immutable=True, original_references=self.manifest["event_references"]
            ),
            self.manifest["database"],
        )
        self.assertEqual((recovered / "state/events/bill.pdf").read_bytes(), b"%PDF-synthetic")
        self.assertFalse(self.source.exists())

    def test_missing_and_wrong_identity_fail_without_recovery(self):
        replica = self.replicate()
        wrong = self.escrow / "wrong.txt"
        with wrong.open("wb") as output:
            subprocess.run([self.keygen], stdout=output, stderr=subprocess.PIPE, check=True)
        if os.name == "posix":
            wrong.chmod(0o600)
        for key in (self.escrow / "missing.txt", wrong):
            with self.assertRaises((ValueError, OSError)):
                self.recover(replica, identity=key)
            self.assertFalse((self.root / "reconstructed").exists())

    def test_missing_corrupt_or_incomplete_copy_fails_closed(self):
        module = self.module()
        with self.assertRaises((OSError, ValueError)):
            self.recover(self.destination / "absent")
        replica = self.replicate()
        (replica / "payload.tar.age").write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            self.recover(replica)
        self.assertFalse((self.root / "reconstructed").exists())
        (replica / "COMPLETED.json").unlink()
        with self.assertRaises((ValueError, OSError)):
            module.inspect_replica(replica)

    def test_interrupt_replication_and_recovery_clean_owned_staging(self):
        module = self.module()
        with patch.object(module, "encrypt_archive", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.replicate()
        self.assertFalse(list(self.destination.glob("*.replica")))
        replica = self.replicate()
        with patch.object(module, "restore_application", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.recover(replica)
        self.assertFalse((self.root / "reconstructed").exists())
        self.assertFalse(list(self.scratch.iterdir()))

    def test_existing_state_collision_or_source_destination_rejected(self):
        replica = self.replicate()
        with self.assertRaises((OSError, ValueError)):
            self.replicate()
        with self.assertRaises(FileExistsError):
            self.recover(replica, self.source)
        self.assertTrue(self.database.is_file())
        with self.assertRaises(ValueError):
            self.module().replicate(
                self.bundle,
                self.bundle / "nested",
                recipient=self.recipient,
                identity=self.key,
                scratch=self.scratch,
                age=self.age,
            )

    def test_invalid_source_manifest_or_missing_required_artifacts_rejected(self):
        for name in ("state/events/bill.pdf", "state/messages.json", "manifest.json"):
            content = (self.bundle / name).read_bytes()
            (self.bundle / name).unlink()
            with self.assertRaises((ValueError, OSError, KeyError)):
                self.replicate()
            (self.bundle / name).write_bytes(content)

    def test_incompatible_commit_schema_fail_without_target(self):
        replica = self.replicate()
        for commit, schema in (("b" * 40, self.manifest["database"]["schema_sha256"]), ("a" * 40, "0" * 64)):
            with self.assertRaises(ValueError):
                self.module().recover_replica(
                    replica,
                    self.root / "reconstructed",
                    identity=self.key,
                    scratch=self.scratch,
                    age=self.age,
                    expected_commit=commit,
                    expected_schema=schema,
                )
        self.assertFalse((self.root / "reconstructed").exists())

    def test_storage_failures_never_publish(self):
        module = self.module()
        for error in (
            PermissionError("synthetic permission"),
            OSError(errno.ENOSPC, "synthetic capacity"),
            OSError(errno.ENODEV, "synthetic unavailable"),
        ):
            with patch.object(module, "encrypt_archive", side_effect=error):
                with self.assertRaises(OSError):
                    self.replicate()
            self.assertFalse(list(self.destination.glob("*.replica")))
            self.assertFalse(list(self.scratch.iterdir()))

    def test_unsafe_duplicate_or_link_archive_entries_fail(self):
        module = self.module()
        for names, link in (
            (["../escape"], False),
            ([self.bundle.name, self.bundle.name], False),
            ([self.bundle.name + "/link"], True),
        ):
            archive = self.root / "unsafe.tar"
            with tarfile.open(archive, "w") as output:
                for name in names:
                    member = tarfile.TarInfo(name)
                    member.type = tarfile.SYMTYPE if link else tarfile.DIRTYPE
                    member.linkname = "outside" if link else ""
                    output.addfile(member)
            with self.assertRaises(ValueError):
                module.unpack_archive(archive, self.root / "extracted", self.bundle.name)
            self.assertFalse((self.root / "extracted").exists())

    def test_status_separates_replication_verification_age_failures_capacity(self):
        module = self.module()
        replica = self.replicate()
        journal = self.root / "journal"
        result = module.recovery_status(replica, journal, max_age_seconds=3600, max_verify_age_seconds=3600)
        self.assertIn("independent-verification-missing-or-stale", result["issues"])
        verified = module.verify_replica(replica, identity=self.key, scratch=self.scratch, age=self.age)
        module.record_event(
            journal, "verification", "success", "verification-test", ciphertext_sha256=verified["ciphertext"]["sha256"]
        )
        self.assertEqual(
            module.recovery_status(replica, journal, max_age_seconds=3600, max_verify_age_seconds=3600)["status"], "ok"
        )
        module.record_event(journal, "replication", "started", "interrupted")
        module.record_event(journal, "recovery", "failed", "failed-test", error_code=2)
        self.destination.joinpath(".drink-pos-replica.lock").write_text("synthetic stale")
        with patch.object(shutil, "disk_usage", return_value=shutil._ntuple_diskusage(100, 99, 1)):
            result = module.recovery_status(
                replica, journal, max_age_seconds=0.000001, max_verify_age_seconds=0.000001, max_used_percent=90
            )
        for issue in (
            "backup-stale-or-future",
            "independent-verification-missing-or-stale",
            "recorded-operation-failures",
            "interrupted-or-running-operation",
            "lock-or-incomplete-staging",
            "storage-capacity-threshold",
        ):
            self.assertIn(issue, result["issues"])
        self.assertEqual(result["immutability"], "not-enforced")
        self.assertEqual(result["offsite"], "not-assessed")
        self.assertNotIn("synthetic audit", json.dumps(result))

    def test_cli_nonzero_sanitized_failure_journal(self):
        import sys

        journal = self.root / "journal"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.independent_recovery",
                "--age",
                self.age,
                "--journal",
                str(journal),
                "verify",
                str(self.destination / "missing"),
                "--identity",
                str(self.key),
                "--scratch",
                str(self.scratch),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stderr)["status"], "failed")
        events = [json.loads((p / "event.json").read_text()) for p in journal.glob("*.event")]
        self.assertEqual({e["status"] for e in events}, {"started", "failed"})
        self.assertNotIn(self.key.read_text().strip(), result.stderr)
        self.assertNotIn("synthetic audit", result.stderr)

    def test_abrupt_replication_leaves_only_unpublished_staging(self):
        import sys

        code = (
            "import os; from pathlib import Path; from app import independent_recovery as r; "
            "r.encrypt_archive=lambda *a: os._exit(37); "
            f"r.replicate(Path({str(self.bundle)!r}),Path({str(self.destination)!r}),recipient={self.recipient!r},identity=Path({str(self.key)!r}),scratch=Path({str(self.scratch)!r}),age={self.age!r})"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertFalse(list(self.destination.glob("*.replica")))
        self.assertTrue((self.destination / ".drink-pos-replica.lock").exists())
        abandoned = list(self.destination.glob(".drink-pos-replica-*"))
        self.assertEqual(len(abandoned), 1)
        with self.assertRaises(self.module().OperationBusy):
            self.replicate()
        self.assertTrue(abandoned[0].exists())

    def test_cli_journal_cannot_mutate_source_or_key_escrow(self):
        import sys

        before = {p.relative_to(self.bundle).as_posix() for p in self.bundle.rglob("*")}
        for journal in (self.bundle / "journal", self.escrow / "journal"):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "app.independent_recovery",
                    "--age",
                    self.age,
                    "--journal",
                    str(journal),
                    "verify",
                    str(self.bundle),
                    "--identity",
                    str(self.key),
                    "--scratch",
                    str(self.scratch),
                ],
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(journal.exists())
        self.assertEqual(before, {p.relative_to(self.bundle).as_posix() for p in self.bundle.rglob("*")})

    @unittest.skipUnless(os.name == "posix", "POSIX ACL modes require Linux; Windows effective ACLs separate")
    def test_private_ciphertext_and_key_modes(self):
        replica = self.replicate()
        self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)
        for path in (replica, *replica.iterdir()):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)


class DisasterMeasurementTests(unittest.TestCase):
    def test_deterministic_rpo_rto_definitions_and_thresholds(self):
        from scripts.disaster_rehearsal import metrics

        result = metrics("2026-01-01T00:00:00+00:00", "2026-01-01T00:02:00+00:00", 45, target_rpo=180, target_rto=60)
        self.assertEqual(result["rpo_age_seconds"], 120)
        self.assertEqual(result["rto_seconds"], 45)
        self.assertTrue(result["synthetic_targets_met"])
        self.assertIsNone(result["real_external_reconciliation_seconds"])
        self.assertFalse(
            metrics("2026-01-01T00:00:00+00:00", "2026-01-01T00:02:00+00:00", 45, target_rpo=60, target_rto=30)[
                "synthetic_targets_met"
            ]
        )

    def test_image_fixture_seed_and_explicit_reconciliation_startup(self):
        import sys
        from scripts.standard_checks import test_environment
        from app.application_recovery import create_backup, verify_application_bundle, restore_application

        with tempfile.TemporaryDirectory(prefix="drink-pos-dr-fixture-") as temporary:
            root = Path(temporary)
            environment = test_environment(root)
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "app")
            script = Path(__file__).resolve().parents[1] / "scripts/disaster_fixture.py"
            code = "import main; main.startup(); import runpy,sys; sys.argv=[sys.argv[1],'seed']; runpy.run_path(sys.argv[0],run_name='__main__')"
            seeded = subprocess.run(
                [sys.executable, "-c", code, str(script)], env=environment, capture_output=True, text=True
            )
            self.assertEqual(seeded.returncode, 0, seeded.stderr)
            bundle = create_backup(
                root / "checks.db",
                root / "messages.json",
                root / "backups",
                deployment_id="fixture-test",
                app_commit="a" * 40,
                quiesced=True,
            )
            manifest = verify_application_bundle(bundle)
            target = restore_application(
                bundle,
                root / "recovered",
                expected_commit="a" * 40,
                expected_schema=manifest["database"]["schema_sha256"],
            )
            evidence = root / "expected.json"
            evidence.write_text(json.dumps(manifest), encoding="utf-8")
            reconciliation = root / "reconciliation.json"
            reconciliation.write_text(
                json.dumps(
                    {
                        "scope": "synthetic-only",
                        "uncertain_card": "held-no-retry",
                        "post_snapshot": "held-no-replay",
                        "browser_queue": "held-no-replay",
                        "invoice_mail": "held-no-resend",
                    }
                )
            )
            environment.update(
                DRINK_POS_DB=str(target / "state/database.db"), DRINK_POS_MESSAGES=str(target / "state/messages.json")
            )
            started = subprocess.run(
                [sys.executable, str(script), "startup", str(target), str(evidence), str(reconciliation)],
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertEqual(json.loads(started.stdout.splitlines()[-1])["network_attempts"], 0)
            reconciliation.write_text("{}")
            blocked = subprocess.run(
                [sys.executable, str(script), "startup", str(target), str(evidence), str(reconciliation)],
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(blocked.returncode, 0)
