"""DP-014 full-snapshot safety regressions; only disposable synthetic state."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from app import backup_database, restore_database, database_recovery


class SnapshotRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="drink-pos-recovery-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source #ä.db"
        self.destination = self.root / "backups"
        self.environment = patch.dict(
            os.environ,
            {
                "DRINK_POS_DB": str(self.source),
                "DRINK_POS_BACKUP_DIR": str(self.destination),
                "DRINK_POS_BACKUP_KEEP": "",
                "DRINK_POS_ENV": "development",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.conn = sqlite3.connect(self.source)
        self.addCleanup(self.conn.close)
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE people(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
            CREATE TABLE event_lines(id INTEGER PRIMARY KEY, person_id INTEGER REFERENCES people(id),
                                     quantity INTEGER CHECK(quantity >= 0), payload BLOB);
            CREATE INDEX event_person ON event_lines(person_id);
            CREATE TRIGGER keep_history BEFORE DELETE ON event_lines
              BEGIN SELECT RAISE(ABORT, 'immutable'); END;
            CREATE VIEW event_totals AS SELECT SUM(quantity) FROM event_lines;
            INSERT INTO people(name) VALUES ('Müller');
            INSERT INTO people(id,name) VALUES (100, 'deleted sequence');
            DELETE FROM people WHERE id=100;
            INSERT INTO event_lines VALUES(1,1,3,x'00ff');
            """
        )

    def backup(self):
        csv = backup_database.export_backup()
        self.assertEqual(csv.read_bytes()[:3], b"\xef\xbb\xbf")
        database = csv.parent / "database.db"
        self.assertTrue(database.is_file(), "full database snapshot must persist beside CSV")
        return database

    def test_wal_snapshot_preserves_schema_sequence_and_committed_state(self):
        self.conn.execute("INSERT INTO people(name) VALUES ('uncommitted')")
        database = self.backup()
        target = self.root / "recovered.db"
        restore_database.restore_backup(database, target)
        with closing(sqlite3.connect(target)) as recovered:
            self.assertEqual(recovered.execute("SELECT name FROM people").fetchall(), [("Müller",)])
            self.assertEqual(recovered.execute("SELECT seq FROM sqlite_sequence").fetchall(), [(100,)])
            self.assertEqual(recovered.execute("SELECT payload FROM event_lines").fetchone()[0], b"\x00\xff")
            self.assertEqual(recovered.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
            self.assertFalse(recovered.execute("PRAGMA foreign_key_check").fetchall())
            self.assertEqual(
                recovered.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall(),
                self.conn.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall(),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                recovered.execute("DELETE FROM event_lines")
            with self.assertRaises(sqlite3.IntegrityError):
                recovered.execute("INSERT INTO event_lines VALUES(2,1,-1,NULL)")

    def test_same_timestamp_never_overwrites_completed_bundle(self):
        with patch.object(backup_database, "backup_timestamp", return_value="same-time"):
            first, second = self.backup(), self.backup()
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_file())

    def test_corrupt_snapshot_rejected_without_target_or_temporary_files(self):
        database = self.backup()
        database.write_bytes(b"corrupt")
        target = self.root / "recovered.db"
        with self.assertRaises((ValueError, RuntimeError, sqlite3.DatabaseError)):
            restore_database.restore_backup(database, target)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob(".recovered.db*")))

    def test_manifest_required_and_tampering_rejected(self):
        database = self.backup()
        manifest = database.parent / "manifest.json"
        metadata = json.loads(manifest.read_text())
        self.assertEqual(metadata["tables"]["event_lines"], 1)
        manifest.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            restore_database.restore_backup(database, self.root / "recovered.db")

    def test_existing_target_and_sidecars_are_not_overwritten(self):
        database = self.backup()
        target = self.root / "recovered.db"
        target.write_bytes(b"owner work")
        with self.assertRaises(FileExistsError):
            restore_database.restore_backup(database, target)
        self.assertEqual(target.read_bytes(), b"owner work")
        target.unlink()
        sidecar = Path(str(target) + "-wal")
        sidecar.write_bytes(b"owner WAL")
        with self.assertRaises(FileExistsError):
            restore_database.restore_backup(database, target)
        self.assertEqual(sidecar.read_bytes(), b"owner WAL")

    def test_interrupted_snapshot_cleans_only_owned_staging(self):
        self.destination.mkdir()
        unrelated = self.destination / ".other-run.tmp"
        unrelated.write_bytes(b"owner work")
        with patch.object(backup_database, "create_snapshot", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                backup_database.export_backup()
        self.assertEqual(list(self.destination.iterdir()), [unrelated])

    def test_foreign_key_violation_refuses_publication(self):
        self.conn.execute("PRAGMA foreign_keys=OFF")
        self.conn.execute("INSERT INTO event_lines VALUES(2,999,1,NULL)")
        self.conn.commit()
        with self.assertRaises((ValueError, RuntimeError)):
            backup_database.export_backup()
        self.assertFalse(list(self.destination.glob("drink_pos_backup_*")))

    def test_retention_disabled_by_default_and_invalid_setting_fails_before_backup(self):
        for _ in range(3):
            self.backup()
        self.assertEqual(len(list(self.destination.glob("drink_pos_backup_*"))), 3)
        os.environ["DRINK_POS_BACKUP_KEEP"] = "1"
        with self.assertRaises(ValueError):
            backup_database.export_backup()
        self.assertEqual(len(list(self.destination.glob("drink_pos_backup_*"))), 3)

    def test_retention_keeps_two_verified_bundles_and_preserves_unknown_files(self):
        first = self.backup()
        invalid = self.backup()
        invalid.write_bytes(b"corrupt")
        foreign = self.destination / "legacy.csv"
        foreign.write_bytes(b"owner work")
        third = self.backup()
        os.environ["DRINK_POS_BACKUP_KEEP"] = "2"
        newest = self.backup()
        self.assertFalse(first.exists())
        for path in (invalid, foreign, third, newest):
            self.assertTrue(path.exists())

    def test_failed_csv_export_and_publication_clean_staging(self):
        for operation in ("export_csv",):
            with patch.object(backup_database, operation, side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    backup_database.export_backup()
            self.assertFalse(list(self.destination.iterdir()))
        with patch.object(Path, "rename", side_effect=OSError("rename failed")):
            with self.assertRaises(OSError):
                backup_database.export_backup()
        self.assertFalse(list(self.destination.iterdir()))

    def test_abrupt_process_exit_leaves_only_unpublished_staging_and_next_run_recovers(self):
        code = (
            "import os; from app import backup_database as b; "
            "b.export_csv = lambda *args: os._exit(37); b.export_backup()"
        )
        result = subprocess.run([sys.executable, "-c", code], env=os.environ.copy(), check=False)
        self.assertEqual(result.returncode, 37)
        self.assertFalse(list(self.destination.glob("drink_pos_backup_*")))
        abandoned = list(self.destination.glob(".drink-pos-backup-*"))
        self.assertEqual(len(abandoned), 1)
        with self.assertRaises((ValueError, FileNotFoundError)):
            restore_database.restore_backup(abandoned[0], self.root / "recovered.db")
        self.assertTrue(self.backup().is_file())
        self.assertTrue(abandoned[0].exists(), "another run's staging must not be cleaned")

    def test_tampered_csv_refuses_even_database_restore(self):
        database = self.backup()
        (database.parent / "export.csv").write_bytes(b"truncated")
        with self.assertRaises(ValueError):
            restore_database.restore_backup(database, self.root / "recovered.db")

    def test_completed_bundle_publication_failure_cleans_staging(self):
        rename = Path.rename

        def fail_publication(source, destination):
            if source.is_dir():
                raise OSError("publication failed")
            return rename(source, destination)

        with patch.object(Path, "rename", fail_publication):
            with self.assertRaises(OSError):
                backup_database.export_backup()
        self.assertFalse(list(self.destination.iterdir()))

    def test_stale_retention_lock_disables_cleanup(self):
        first = self.backup()
        lock = self.destination / ".drink-pos-retention.lock"
        lock.write_text("previous run")
        os.environ["DRINK_POS_BACKUP_KEEP"] = "2"
        for _ in range(3):
            self.backup()
        self.assertTrue(first.exists())
        self.assertEqual(lock.read_text(), "previous run")

    def test_retention_never_prunes_another_database_in_shared_destination(self):
        foreign_source = self.root / "another.db"
        with closing(sqlite3.connect(foreign_source)) as conn:
            conn.execute("CREATE TABLE foreign_data(id INTEGER)")
            conn.commit()
        with patch.dict(os.environ, {"DRINK_POS_DB": str(foreign_source)}):
            foreign_backup = backup_database.export_backup().parent
        os.environ["DRINK_POS_BACKUP_KEEP"] = "2"
        for _ in range(3):
            self.backup()
        self.assertTrue(foreign_backup.exists())

    def test_racing_target_is_not_clobbered_and_restore_temp_is_removed(self):
        database = self.backup()
        target = self.root / "recovered.db"
        original_link = os.link

        def race(source, destination):
            target.write_bytes(b"concurrent owner work")
            original_link(source, destination)

        with patch.object(database_recovery.os, "link", side_effect=race):
            with self.assertRaises(FileExistsError):
                restore_database.restore_backup(database, target)
        self.assertEqual(target.read_bytes(), b"concurrent owner work")
        self.assertFalse(list(self.root.glob(".recovered.db*")))

    def test_failed_restore_verification_never_publishes(self):
        database = self.backup()
        target = self.root / "recovered.db"
        with patch.object(restore_database, "verify_database", side_effect=ValueError("invalid recovered state")):
            with self.assertRaises(ValueError):
                restore_database.restore_backup(database, target)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob(".recovered.db*")))

    def test_corrupt_source_and_failed_migration_can_recover_prior_snapshot(self):
        database = self.backup()
        self.conn.executescript("ALTER TABLE people ADD COLUMN incomplete_migration TEXT;")
        self.conn.close()
        self.source.write_bytes(b"corrupted after failed migration")
        target = self.root / "recovered.db"
        restore_database.restore_backup(database, target)
        with closing(sqlite3.connect(target)) as recovered:
            self.assertNotIn("incomplete_migration", [row[1] for row in recovered.execute("PRAGMA table_info(people)")])
            self.assertEqual(recovered.execute("SELECT name FROM people").fetchall(), [("Müller",)])

    def test_legacy_csv_fk_violation_and_unknown_columns_fail_closed(self):
        import csv

        legacy = self.root / "legacy.csv"
        for payload in ({"id": 1, "parent": 999}, {"id": 1, "unknown": 5}):
            with legacy.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(["section", "table_name", "data_json"])
                writer.writerow(
                    [
                        "schema",
                        "parent",
                        json.dumps(
                            {"type": "table", "name": "parent", "sql": "CREATE TABLE parent(id INTEGER PRIMARY KEY)"}
                        ),
                    ]
                )
                writer.writerow(
                    [
                        "schema",
                        "child",
                        json.dumps(
                            {
                                "type": "table",
                                "name": "child",
                                "sql": "CREATE TABLE child(id INTEGER PRIMARY KEY,parent INTEGER REFERENCES parent(id))",
                            }
                        ),
                    ]
                )
                writer.writerow(["data", "child", json.dumps(payload)])
            target = self.root / "recovered.db"
            with self.assertRaises(ValueError):
                restore_database.restore_backup(legacy, target)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
