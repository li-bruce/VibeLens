"""Bindings use the pinned project bundle and the original iteration gates."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from test_native_behavior_runtime import fixture, ROOT
sys.path.insert(0, str(ROOT / "tools"))
from test_multilanguage import project_fixture
from bo_observer.project_artifacts import byte_hash, load_bundle, load_project
from bo_observer.protocol import validate_project
from bo_observer.workflow.sync_config import snapshot


class NativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract, self.discovery, native, _, _ = fixture(self.root)
        self.project = project_fixture(self.root)
        self.project["protocol"] = "bo-project/v2"
        self.project["project_id"] = self.project["model"]["project_id"] = self.contract["project_id"]
        for node in native["nodes"]:
            node.update(label=node["id"], summary="Native test boundary")
        self.project["model"]["nodes"].extend(native["nodes"])
        self.project["model"]["source_files"].append("application.py")
        self.project["model"]["behavior_bindings"] = native["behavior_bindings"]
        self.project["contracts"] = {"analysis_profiles": []}
        for role, name, value in (("discovery", "discovery.json", self.discovery),
                                  ("behavior", "bo_stategraph/behavior.json", self.contract)):
            raw = (json.dumps(value) + "\n").encode("utf-8")
            (self.root / name).write_bytes(raw)
            self.project["contracts"][role] = {"path": name, "schema": value["schema"], "sha256": byte_hash(raw)}
        self.write()

    def write(self):
        (self.root / "bo_stategraph/project.json").write_text(json.dumps(self.project), encoding="utf-8")

    def test_bundle_reuses_exact_discovery_and_behavior_without_claiming_native_semantics(self):
        project, documents = load_bundle(self.root)
        self.assertEqual(documents["behavior"], self.contract)
        self.assertEqual(documents["discovery"], self.discovery)
        self.assertEqual(project, load_project(self.root))

    def test_bindings_cannot_float_outside_a_pinned_definition(self):
        self.project["contracts"]["behavior"] = None
        with self.assertRaisesRegex(ValueError, "pinned"):
            validate_project(self.project)

    def test_unknown_binding_field_and_stale_meaning_are_rejected_by_project_reader(self):
        original = deepcopy(self.project)
        self.project["model"]["behavior_bindings"]["weak_validation"] = True
        self.write()
        with self.assertRaises(ValueError):
            load_project(self.root)
        self.project = original
        self.project["model"]["behavior_bindings"]["definition_sha256"] = "0" * 64
        self.write()
        with self.assertRaisesRegex(ValueError, "stale_behavior_binding"):
            load_project(self.root)

    def test_snapshot_watches_the_pinned_artifacts_even_if_watch_files_omits_them(self):
        cfg = {"config_path": "sync.json", "model": "bo_stategraph/project.json", "manifest": "manifest.json",
               "code_files": ["worker.py", "application.py"], "watch_files": ["sync.json"],
               "acceptance": "acceptance.json", "discovery": "discovery.json"}
        (self.root / "sync.json").write_text(json.dumps(cfg), encoding="utf-8")
        (self.root / "acceptance.json").write_text('{"checks":[]}', encoding="utf-8")
        snap = snapshot(self.root, cfg)
        self.assertEqual(snap["behavior"], self.contract)
        self.assertEqual(snap["behavior_discovery"], self.discovery)
        self.assertIn("bo_stategraph/behavior.json", snap["files"])
        self.assertEqual(snap["files"]["bo_stategraph/behavior.json"], self.project["contracts"]["behavior"]["sha256"])


if __name__ == "__main__":
    unittest.main()
