"""Actual SQLite snapshots preserve reflection without blocking file publication."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.data import catalog


class AtomicSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "business.sqlite"
        self.store = {
            "id": "app",
            "engine": "sqlalchemy",
            "url_env": "BO_ATOMIC_SQLITE",
            "sqlite_file_mode": "atomic_replace",
        }
        environment = patch.dict(os.environ, {"BO_ATOMIC_SQLITE": "sqlite:///business.sqlite"})
        environment.start()
        self.addCleanup(environment.stop)
        self.publish("before")

    def publish(self, table):
        """Mimic an immutable complete-image publisher, without SQLite on the target."""
        staged = self.root / "published.tmp"
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.execute(
                f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)'
            )
            connection.execute(
                f'INSERT INTO "{table}" VALUES (1, ?)', ("private-row-not-exported",)
            )
            connection.commit()
            staged.write_bytes(connection.serialize())
        os.replace(staged, self.path)

    def collect(self):
        return catalog.collect(self.store, root=self.root)

    def test_replacement_during_reflection_is_safe_and_next_poll_sees_new_schema(self):
        original = catalog._inspect
        replaced = []

        def inspect(*args, **kwargs):
            if not replaced:
                self.publish("after")
                replaced.append(True)
            return original(*args, **kwargs)

        with patch.object(catalog, "_inspect", inspect):
            before = self.collect()
        after = self.collect()
        self.assertEqual([r["name"] for r in before["resources"]], ["before"])
        self.assertEqual([r["name"] for r in after["resources"]], ["after"])
        self.assertEqual(before["origin"], "database")
        self.assertEqual(before["coverage"], "complete")
        self.assertEqual(
            {c["kind"] for c in before["resources"][0]["constraints"]}, {"primary_key", "unique"}
        )
        self.assertNotIn("private-row-not-exported", json.dumps(before))
        self.assertNotIn(str(self.path), json.dumps(before))

    def test_file_read_handle_allows_atomic_publication(self):
        from bo_observer.data.sqlite_snapshot import open_published_image

        original = self.path.read_bytes()
        with open_published_image(self.path) as stream:
            self.publish("after")
            self.assertEqual(stream.read(), original)
        self.assertNotEqual(self.path.read_bytes(), original)

    @unittest.skipUnless(os.name == "nt", "Windows private alias cleanup")
    def test_alias_is_removed_on_success_and_failure_without_copying_data(self):
        from bo_observer.data import sqlite_snapshot

        link = os.link
        aliases = []

        def create_link(source, target):
            link(source, target)
            self.assertTrue(os.path.samefile(source, target))
            aliases.append(Path(target))

        with patch.object(sqlite_snapshot.os, "link", create_link):
            self.collect()
            with self.assertRaisesRegex(RuntimeError, "stop"):
                with sqlite_snapshot.open_published_image(self.path):
                    raise RuntimeError("stop")
        self.assertEqual(len(aliases), 2)
        self.assertTrue(all(not path.exists() and not path.parent.exists() for path in aliases))
        self.assertTrue(self.path.exists())

    @unittest.skipUnless(os.name == "nt", "Windows requires same-volume alias")
    def test_link_failure_does_not_open_the_original_file(self):
        from bo_observer.data import sqlite_snapshot

        with patch.object(sqlite_snapshot.os, "link", side_effect=OSError("cross volume")):
            with patch.object(
                sqlite_snapshot,
                "_open_windows_link",
                side_effect=AssertionError("must not fall back"),
            ):
                with self.assertRaisesRegex(catalog.CatalogError, "same-volume"):
                    self.collect()

    def test_snapshot_engine_is_memory_only_and_query_only(self):
        import sqlalchemy

        create = sqlalchemy.create_engine
        seen = []

        def engine(url, **kwargs):
            self.assertEqual(str(url), "sqlite+pysqlite:///:memory:")
            result = create(url, **kwargs)
            with result.connect() as connection:
                self.assertEqual(connection.exec_driver_sql("PRAGMA query_only").scalar(), 1)
                self.assertEqual(connection.exec_driver_sql("PRAGMA database_list").one()[2], "")
                with self.assertRaises(sqlalchemy.exc.OperationalError):
                    connection.exec_driver_sql("CREATE TABLE unexpected (id INTEGER)")
            seen.append(True)
            return result

        original = self.path.read_bytes()
        with patch.object(sqlalchemy, "create_engine", engine):
            self.collect()
        self.assertTrue(seen)
        self.assertEqual(original, self.path.read_bytes())

    def test_wal_and_journal_are_rejected_without_touching_source(self):
        for suffix in ("-wal", "-journal"):
            with self.subTest(suffix=suffix):
                artifact = Path(str(self.path) + suffix)
                artifact.write_bytes(b"active")
                try:
                    with self.assertRaisesRegex(catalog.CatalogError, "standalone"):
                        self.collect()
                finally:
                    artifact.unlink()
        value = bytearray(self.path.read_bytes())
        value[18:20] = b"\x02\x02"
        self.path.write_bytes(value)
        with self.assertRaisesRegex(catalog.CatalogError, "standalone"):
            self.collect()

    def test_snapshot_size_is_bounded_and_does_not_fall_back_to_live_connection(self):
        from bo_observer.data import sqlite_snapshot

        with patch.object(sqlite_snapshot, "MAX_SNAPSHOT_BYTES", 100):
            with self.assertRaisesRegex(catalog.CatalogError, "size limit"):
                self.collect()

    def test_invalid_mode_and_wrong_backend_are_rejected(self):
        for mode in ("typo", None, 1):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(catalog.CatalogError, "sqlite_file_mode"):
                    catalog.collect({**self.store, "sqlite_file_mode": mode}, root=self.root)
        with patch.dict(os.environ, {"BO_ATOMIC_SQLITE": "postgresql://localhost/test"}):
            with self.assertRaisesRegex(catalog.CatalogError, "SQLite"):
                self.collect()
        with self.assertRaisesRegex(catalog.CatalogError, "sqlite_file_mode"):
            catalog.collect({**self.store, "engine": "redis"}, root=self.root)

    def test_snapshot_rejects_driver_options_that_it_cannot_preserve(self):
        with patch.dict(os.environ, {"BO_ATOMIC_SQLITE": "sqlite:///business.sqlite?mode=ro"}):
            with self.assertRaisesRegex(catalog.CatalogError, "options"):
                self.collect()

    def test_config_accepts_explicit_modes_and_rejects_unknown_values(self):
        schema_path = (
            ROOT / "skills/vibelens/scripts/bo_observer/schemas/database-config.schema.json"
        )
        import jsonschema

        store_schema = json.loads(schema_path.read_text())["properties"]["stores"]["items"][
            "properties"
        ]
        for mode in ("transactional", "atomic_replace"):
            jsonschema.validate(mode, store_schema["sqlite_file_mode"])
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate("guess", store_schema["sqlite_file_mode"])

    def test_config_rejects_mode_on_a_non_sqlite_collector(self):
        import jsonschema

        schema_path = (
            ROOT / "skills/vibelens/scripts/bo_observer/schemas/database-config.schema.json"
        )
        store_schema = json.loads(schema_path.read_text())["properties"]["stores"]["items"]
        store = {
            **self.store,
            "label": "Application",
            "model_layer": "sql.js",
            "source_files": ["store.mjs"],
            "selection": {"source": "user", "answer": "SQLite", "locator": "dialogue:2"},
        }
        jsonschema.validate(store, store_schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({**store, "engine": "mongodb"}, store_schema)

    def test_transactional_wal_remains_supported_by_the_default_collector(self):
        store = {key: value for key, value in self.store.items() if key != "sqlite_file_mode"}
        with closing(sqlite3.connect(self.path)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("CREATE TABLE wal_table(id INTEGER PRIMARY KEY)")
            writer.commit()
            result = catalog.collect(store, root=self.root)
            self.assertEqual({r["name"] for r in result["resources"]}, {"before", "wal_table"})
            with self.assertRaisesRegex(catalog.CatalogError, "standalone"):
                self.collect()

    @unittest.skipUnless(os.name == "nt", "Windows file sharing reproducer")
    def test_ordinary_live_sqlite_handle_reproduces_replace_conflict(self):
        with closing(
            sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)
        ) as connection:
            connection.execute("SELECT name FROM sqlite_master").fetchall()
            with self.assertRaises(PermissionError):
                self.publish("after")
        self.publish("after")


if __name__ == "__main__":
    unittest.main()
