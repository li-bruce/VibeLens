"""External observer integration remains small, independently checked and native."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.delivery import integration
from bo_observer.delivery.architecture_guard import collect
from bo_observer.workflow.implementation_coverage import inventory_errors


class IntegrationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def test_legacy_entrypoints_resolve_the_installed_provider(self):
        integration.install(self.root, "python")
        expected = integration.inspect(self.root)
        installed = integration.canonical_scripts().parent
        with patch.object(integration, "SCRIPTS", self.root / "observer_runtime"):
            with patch.dict(os.environ, {"VIBELENS_SKILL": str(installed)}):
                self.assertEqual(integration.inspect(self.root), expected)

    def test_legacy_copy_cannot_claim_to_be_its_own_canonical_provider(self):
        integration.install(self.root, "javascript")
        with patch.object(integration, "SCRIPTS", self.root / "observer_runtime"):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "installed Skill"):
                    integration.inspect(self.root)

    def test_python_executes_without_observer_installation(self):
        result = integration.install(self.root, "python")
        self.assertEqual(len(result["files"]), 6)
        self.assertFalse((self.root / "observer_runtime").exists())
        # The copied dependency set must execute a real waiting/resume sequence,
        # not merely import while the full observer happens to be on sys.path.
        machine = json.loads(
            (ROOT / "examples/multilanguage/bo_stategraph/project.json").read_text(encoding="utf-8")
        )["model"]["machine"]
        code = """
from bo_stategraph.bo_executor import BOExecutor
from bo_stategraph.bo_probe import BOProbe
import json
engine = BOExecutor(json.load(sys.stdin), {'available': lambda context, payload: context['slots'] > 0})
state, states = 'pending', []
for event, slots in [('start', 0), ('resume', 1), ('finish', 1)]:
    state = engine.step(state, event, {'slots': slots})['state']
    states.append(state)
print(json.dumps(states))
"""
        run = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import sys; sys.path.insert(0, sys.argv[1]); " + code,
                str(self.root),
            ],
            capture_output=True,
            text=True,
            input=json.dumps(machine),
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), ["waiting", "running", "done"])
        self.assertTrue(integration.inspect(self.root)["valid"])

    def test_javascript_adapter_loads_without_python_or_viewer(self):
        result = integration.install(self.root, "javascript")
        self.assertEqual(len(result["files"]), 2)
        adapter = (self.root / "bo_stategraph/bo_runtime.mjs").as_uri()
        machine = json.loads(
            (ROOT / "examples/multilanguage/bo_stategraph/project.json").read_text(encoding="utf-8")
        )["model"]["machine"]
        code = (
            f"import {{BOProbe, BOExecutor}} from {json.dumps(adapter)};"
            + """
import fs from 'node:fs';
const engine = new BOExecutor(JSON.parse(fs.readFileSync(0, 'utf8')), {available: context => context.slots > 0});
let state = 'pending';
const states = [['start', 0], ['resume', 1], ['finish', 1]].map(([event, slots]) => {
  state = engine.step(state, event, {slots}).state;
  return state;
});
if (!BOProbe) process.exit(1);
console.log(JSON.stringify(states));
"""
        )
        run = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                code,
            ],
            capture_output=True,
            text=True,
            input=json.dumps(machine),
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), ["waiting", "running", "done"])

    def test_editing_receipt_does_not_authorize_adapter_modification(self):
        integration.install(self.root, "python")
        name = "bo_stategraph/bo_probe.py"
        path = self.root / name
        path.write_bytes(path.read_bytes() + b"\n# unreviewed change\n")
        receipt = self.root / integration.RECEIPT
        value = json.loads(receipt.read_text())
        value["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
        receipt.write_text(json.dumps(value), encoding="utf-8")
        checked = integration.inspect(self.root)
        self.assertFalse(checked["valid"])
        self.assertTrue(inventory_errors({}, {"framework": checked}))

    def test_install_conflict_preserves_application_and_dependencies(self):
        target = self.root / "bo_stategraph"
        target.mkdir()
        (target / "project.json").write_text('{"mine":true}', encoding="utf-8")
        (target / "bo_probe.py").write_text("# local implementation", encoding="utf-8")
        before = {p.name: p.read_bytes() for p in target.iterdir()}
        with self.assertRaisesRegex(ValueError, "edits require review"):
            integration.install(self.root, "python")
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})

    def test_missing_dependency_and_invalid_source_map_fail(self):
        integration.install(self.root, "javascript")
        (self.root / "bo_stategraph/bo_runtime.mjs").unlink()
        self.assertFalse(integration.inspect(self.root)["valid"])
        integration.install(self.root, "javascript")
        receipt = self.root / integration.RECEIPT
        value = json.loads(receipt.read_text())
        value["sources"]["bo_stategraph/bo_runtime.mjs"] = "../../app.js"
        receipt.write_text(json.dumps(value), encoding="utf-8")
        self.assertFalse(integration.inspect(self.root)["valid"])

    def test_dependency_directories_are_never_descended(self):
        (self.root / "app.py").write_text("pass", encoding="utf-8")
        dependency = self.root / "node_modules" / "huge"
        dependency.mkdir(parents=True)
        (dependency / "ignore.py").write_text("pass", encoding="utf-8")
        import os

        original = os.scandir

        def guarded(path):
            if "node_modules" in Path(path).parts:
                raise AssertionError("dependency traversal")
            return original(path)

        with patch("os.scandir", guarded):
            self.assertEqual(collect(self.root, ["."]), ["app.py"])


if __name__ == "__main__":
    unittest.main()
