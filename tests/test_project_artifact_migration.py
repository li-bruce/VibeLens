"""Exact-version migration, interruption recovery and Python/Node reader parity."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_concept_models import draft, ROOT
sys.path.insert(0, str(ROOT / "tools"))
from test_multilanguage import project_fixture
from bo_observer.delivery import artifact_migration as migration
from bo_observer.project_artifacts import load_project, parse

JS = ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_project.mjs"


class ProjectArtifactTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.discovery = draft()
        self.discovery["project_id"] = self.project["project_id"]
        (self.root / "discovery.json").write_bytes(migration.encode(self.discovery))
        self.project_path = self.root / "bo_stategraph/project.json"
        self.before = self.project_path.read_bytes()
        self.discovery_before = (self.root / "discovery.json").read_bytes()
        personal = self.root / "bo_stategraph/config/views/personal.json"
        personal.parent.mkdir(parents=True)
        personal.write_text('{"positions":{"advance":[1,2]},"hidden":["done"]}')
        self.personal = personal

    def node(self):
        code = "import {bo_readProject} from " + json.dumps(JS.as_uri()) + ";"
        code += "try {console.log(JSON.stringify(await bo_readProject(process.argv[1])))}"
        code += "catch(e) {console.log(JSON.stringify({error:e.message}));process.exitCode=1}"
        result = subprocess.run(["node", "--input-type=module", "-e", code, str(self.root)],
                                capture_output=True, text=True, timeout=20)
        return result.returncode, json.loads(result.stdout)

    def test_plan_is_read_only_and_leaves_personal_files_outside_changes(self):
        proposal = migration.plan(self.root)
        self.assertEqual(self.project_path.read_bytes(), self.before)
        self.assertEqual({item["path"] for item in proposal["changes"]},
                         {"discovery.json", "bo_stategraph/project.json"})
        self.assertTrue(all("views" not in item["path"] for item in proposal["changes"]))

    def test_migrate_keeps_models_ids_history_and_views(self):
        view = self.personal.read_bytes()
        original = deepcopy(self.project)
        proposal = migration.plan(self.root)
        self.assertEqual(migration.apply(self.root, proposal)["status"], "committed")
        current = load_project(self.root)
        self.assertEqual(current["model"], original["model"])
        self.assertEqual(self.personal.read_bytes(), view)
        discovery = parse((self.root / "discovery.json").read_bytes())
        self.assertEqual(discovery["confirmations"], self.discovery["confirmations"])
        self.assertEqual(discovery["state_models"], self.discovery["state_models"])
        self.assertEqual(discovery["construction"]["presentations"], [])
        self.assertEqual(migration.check(self.root)["runtime_evidence"], "not_checked")
        code, node = self.node()
        self.assertEqual(code, 0, node)
        self.assertEqual(node["project"], current)
        self.assertEqual(node["documents"]["discovery"], discovery)

    def test_stale_plan_changes_no_files(self):
        proposal = migration.plan(self.root)
        (self.root / "discovery.json").write_bytes(self.discovery_before + b" ")
        with self.assertRaisesRegex(ValueError, "Re-plan"):
            migration.apply(self.root, proposal)
        self.assertEqual(self.project_path.read_bytes(), self.before)

    def test_forged_plan_cannot_overwrite_personal_files(self):
        proposal = migration.plan(self.root)
        proposal["changes"][0]["path"] = "bo_stategraph/config/views/personal.json"
        with self.assertRaises(ValueError):
            migration.apply(self.root, proposal)
        self.assertEqual(self.project_path.read_bytes(), self.before)

    def test_process_interruption_blocks_reads_then_restores_exact_bytes(self):
        proposal = migration.plan(self.root)
        real = migration.replace_bytes
        def interrupt(path, raw):
            real(path, raw)
            if path == self.root / "discovery.json":
                raise KeyboardInterrupt("simulated process interruption")
        with patch.object(migration, "replace_bytes", interrupt), self.assertRaises(KeyboardInterrupt):
            migration.apply(self.root, proposal)
        with self.assertRaisesRegex(ValueError, "Recover"):
            load_project(self.root)
        self.assertEqual(self.node()[1]["error"], "migration_pending")
        self.assertEqual(migration.recover(self.root)["status"], "rolled_back")
        self.assertEqual(self.project_path.read_bytes(), self.before)
        self.assertEqual((self.root / "discovery.json").read_bytes(), self.discovery_before)

    def test_recovery_preserves_external_edit_and_pending_marker(self):
        proposal = migration.plan(self.root)
        real = migration.replace_bytes
        def interrupt(path, raw):
            real(path, raw)
            if path == self.root / "discovery.json":
                raise KeyboardInterrupt()
        with patch.object(migration, "replace_bytes", interrupt), self.assertRaises(KeyboardInterrupt):
            migration.apply(self.root, proposal)
        changed = b'{"manual":"edit"}'
        (self.root / "discovery.json").write_bytes(changed)
        with self.assertRaisesRegex(ValueError, "Preserve the external"):
            migration.recover(self.root)
        self.assertEqual((self.root / "discovery.json").read_bytes(), changed)
        self.assertTrue((self.root / ".stategraph/migrations/active.json").exists())

    def test_mixed_revision_is_rejected_by_both_readers(self):
        migration.apply(self.root, migration.plan(self.root))
        (self.root / "discovery.json").write_bytes(self.discovery_before)
        with self.assertRaises(ValueError):
            load_project(self.root)
        code, result = self.node()
        self.assertEqual(code, 1)
        self.assertEqual(result["error"], "artifact_revision_mismatch")

    def test_wrong_reference_version_and_path_are_rejected(self):
        migration.apply(self.root, migration.plan(self.root))
        original = parse(self.project_path.read_bytes())
        for mutation in ({"schema": "business-discovery/v99"}, {"path": "../outside.json"}):
            current = deepcopy(original)
            current["contracts"]["discovery"].update(mutation)
            self.project_path.write_bytes(migration.encode(current))
            with self.assertRaises(ValueError):
                load_project(self.root)
            self.assertEqual(self.node()[0], 1)

    def test_repeated_plan_keeps_v2_references_unchanged(self):
        migration.apply(self.root, migration.plan(self.root))
        proposal = migration.plan(self.root)
        self.assertEqual(proposal["changes"], [])
        self.assertEqual(migration.apply(self.root, proposal)["status"], "unchanged")

    def test_legacy_project_without_discovery_does_not_invent_models(self):
        (self.root / "discovery.json").unlink()
        migration.apply(self.root, migration.plan(self.root))
        self.assertEqual(load_project(self.root)["contracts"],
                         {"discovery": None, "behavior": None, "analysis_profiles": []})

    def test_regular_io_error_rolls_back_before_propagating(self):
        real = migration.replace_bytes
        failed = False
        def once(path, raw):
            nonlocal failed
            if path == self.project_path and not failed:
                failed = True
                raise OSError("simulated disk error")
            real(path, raw)
        with patch.object(migration, "replace_bytes", once), self.assertRaises(OSError):
            migration.apply(self.root, migration.plan(self.root))
        self.assertEqual(self.project_path.read_bytes(), self.before)
        self.assertEqual((self.root / "discovery.json").read_bytes(), self.discovery_before)

    def test_interruption_before_journal_releases_only_unchanged_inputs(self):
        with patch.object(migration, "replace_bytes", side_effect=KeyboardInterrupt()), self.assertRaises(KeyboardInterrupt):
            migration.apply(self.root, migration.plan(self.root))
        self.assertEqual(migration.recover(self.root)["status"], "rolled_back")
        self.assertEqual(self.project_path.read_bytes(), self.before)

    def test_duplicate_keys_are_rejected_in_python_and_node(self):
        raw = self.before.decode("utf-8").replace('"protocol":', '"protocol":"ignored","protocol":', 1)
        self.project_path.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            load_project(self.root)
        self.assertEqual(self.node()[1]["error"], "duplicate_json_key")

    def test_reference_refresh_is_explicit_and_stale_writes_are_rejected(self):
        migration.apply(self.root, migration.plan(self.root))
        discovery = parse((self.root / "discovery.json").read_bytes())
        discovery["title"] = "Team sharing"
        (self.root / "discovery.json").write_bytes(migration.encode(discovery))
        with self.assertRaises(ValueError):
            load_project(self.root)
        proposal = migration.plan(self.root, refresh=True)
        self.assertEqual([c["path"] for c in proposal["changes"]], ["bo_stategraph/project.json"])
        migration.apply(self.root, proposal)
        self.assertEqual(load_project(self.root)["model"], self.project["model"])
        self.assertFalse(migration.plan(self.root, refresh=True)["changes"])

    def test_v1_discovery_remains_legacy_without_manufactured_identity_or_confirmation(self):
        raw = (ROOT / "skills/vibelens/assets/discovery.example.json").read_bytes()
        value = parse(raw)
        value.pop("project_id", None)
        raw = migration.encode(value)
        (self.root / "discovery.json").write_bytes(raw)
        migration.apply(self.root, migration.plan(self.root))
        self.assertEqual((self.root / "discovery.json").read_bytes(), raw)
        self.assertEqual(load_project(self.root)["contracts"]["discovery"]["schema"], "business-discovery/v1")
        self.assertEqual(self.node()[0], 0)

    def test_edit_during_plan_cannot_be_pinned_to_old_model_content(self):
        real = migration.validate_documents
        def concurrent_edit(project, documents):
            result = real(project, documents)
            changed = deepcopy(self.project)
            changed["model"]["revision"] = "concurrent-edit"
            self.project_path.write_bytes(migration.encode(changed))
            return result
        with patch.object(migration, "validate_documents", concurrent_edit):
            with self.assertRaisesRegex(ValueError, "Input changed"):
                migration.plan(self.root)
        self.assertEqual(parse(self.project_path.read_bytes())["model"]["revision"], "concurrent-edit")


if __name__ == "__main__":
    unittest.main()
