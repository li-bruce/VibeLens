"""Watcher reuse preserves fresh collection, strict changes and independent checks."""

from copy import deepcopy
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
import test_database_watch as fixture
from bo_observer import protocol
from bo_observer.data import catalog
from bo_observer.data.projection_validation import ProjectionValidation
from bo_observer.data.sync import synchronize


class DatabaseWatchValidationTests(unittest.TestCase):
    setUp = fixture.DatabaseWatchTests.setUp
    close_server = fixture.DatabaseWatchTests.close_server
    write_config = fixture.DatabaseWatchTests.write_config

    def test_repeated_tick_reuses_validation_but_collects_each_time(self):
        with (
            patch.object(protocol, "validate_project", wraps=protocol.validate_project) as validate,
            patch.object(catalog, "collect", wraps=catalog.collect) as collect,
        ):
            first = self.watcher.tick()
            second = self.watcher.tick()
        self.assertTrue(first["valid"], first)
        self.assertTrue(second["valid"], second)
        self.assertFalse(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(validate.call_count, 1)
        self.assertEqual(collect.call_count, 2)

    def test_same_size_same_time_invalid_project_is_rejected_on_every_tick(self):
        self.assertTrue(self.watcher.tick()["valid"])
        path = self.root / "bo_stategraph/project.json"
        original, stamp = path.read_bytes(), path.stat()
        mode = self.server.bo_session.project["selection"]["mode"].encode()
        changed = original.replace(b'"' + mode + b'"', b'"' + b"x" * len(mode) + b'"', 1)
        self.assertNotEqual(original, changed)
        self.assertEqual(len(original), len(changed))
        path.write_bytes(changed)
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        previous = self.server.bo_session
        with patch.object(
            protocol, "validate_project", wraps=protocol.validate_project
        ) as validate:
            first = self.watcher.tick()
            second = self.watcher.tick()
        self.assertFalse(first["valid"])
        self.assertFalse(second["valid"])
        self.assertEqual(validate.call_count, 2)
        self.assertIs(self.server.bo_session, previous)
        path.write_bytes(original)
        self.assertTrue(self.watcher.tick()["valid"])

    def test_schema_change_is_collected_and_replaces_the_observed_build(self):
        self.assertTrue(self.watcher.tick()["valid"])
        before = self.server.bo_session
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("ALTER TABLE images ADD COLUMN reviewed BOOLEAN")
        report = self.watcher.tick()
        self.assertTrue(report["valid"], report)
        self.assertTrue(report["changed"])
        self.assertIsNot(self.server.bo_session, before)
        self.assertNotEqual(
            before.manifest["build_id"], self.server.bo_session.manifest["build_id"]
        )

    def test_independent_and_forced_checks_do_not_reuse_watch_validation(self):
        self.assertTrue(self.watcher.tick()["valid"])
        with patch.object(
            protocol, "validate_project", wraps=protocol.validate_project
        ) as validate:
            for options in ({"update": False}, {"force": True}):
                result = synchronize(
                    self.root, validation_cache=self.watcher.validation_cache, **options
                )
                self.assertTrue(result["valid"], result)
        self.assertEqual(validate.call_count, 2)

    def test_cached_json_cannot_admit_python_coercions(self):
        memo = ProjectionValidation()
        original = self.server.bo_session.project
        memo.check(original)
        invalid = deepcopy(original)
        invalid["model"]["source_files"] = tuple(invalid["model"]["source_files"])
        with self.assertRaisesRegex(ValueError, "non-JSON"):
            memo.check(invalid)
        with self.assertRaisesRegex(ValueError, "keys"):
            memo.check({1: "value"})
        memo.check(original)


if __name__ == "__main__":
    unittest.main()
