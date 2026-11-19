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

    def test_legacy_package_imports_without_the_skill_directory_on_sys_path(self):
        """Copied observers must resolve the same model helpers as CLI entrypoints."""
        from bo_upgrade import apply

        apply(self.root, runtime="observer_runtime", viewers=[])
        code = """
import sys
sys.path.insert(0, sys.argv[1])
from observer_runtime import recording_session
from observer_runtime.bo_observer.concepts import projection
from observer_runtime.bo_observer.explanations import context
from observer_runtime.bo_observer.web import semantic_names
from observer_runtime.bo_observer.observation import runtime_frames
from bo_stategraph.bo_models import machine_registry
assert semantic_names.machine_registry is machine_registry
assert recording_session.machine_registry is machine_registry
"""
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", code, str(self.root)],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_python_executes_without_observer_installation(self):
        result = integration.install(self.root, "python")
        self.assertEqual(len(result["files"]), 7)
        self.assertFalse(
            any(
                p.suffix in {".wasm", ".html", ".css"} or p.name.endswith(".vendor.js")
                for p in self.root.rglob("*")
            )
        )
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

    def test_registry_dependency_upgrade_preserves_local_configuration(self):
        """The new native module can be added to a known six-file receipt."""
        integration.install(self.root, "python")
        receipt = self.root / integration.RECEIPT
        prior = json.loads(receipt.read_text())
        name = "bo_stategraph/bo_models.py"
        prior["files"].pop(name)
        prior["sources"].pop(name)
        receipt.write_text(json.dumps(prior), encoding="utf-8")
        (self.root / name).unlink()
        settings = self.root / "bo_stategraph/config"
        settings.mkdir()
        personal = settings / "layout.json"
        personal.write_text('{"position":[3,4]}', encoding="utf-8")
        self.assertEqual(integration.plan(self.root, "python")["changes"], [name])
        integration.install(self.root, "python")
        self.assertTrue(integration.inspect(self.root)["valid"])
        self.assertEqual(personal.read_text(), '{"position":[3,4]}')

    def test_javascript_adapter_loads_without_python_or_viewer(self):
        result = integration.install(self.root, "javascript")
        self.assertEqual(
            set(result["files"]),
            {
                "bo_stategraph/bo_runtime.mjs",
                "bo_stategraph/bo_capture.mjs",
                "bo_stategraph/bo_http.mjs",
            },
        )
        adapter = (self.root / "bo_stategraph/bo_runtime.mjs").as_uri()
        http_adapter = (self.root / "bo_stategraph/bo_http.mjs").as_uri()
        machine = json.loads(
            (ROOT / "examples/multilanguage/bo_stategraph/project.json").read_text(encoding="utf-8")
        )["model"]["machine"]
        code = (
            f"import {{BOProbe, BOExecutor}} from {json.dumps(adapter)};"
            + f"import {{bo_observeHttp}} from {json.dumps(http_adapter)};"
            + """
import fs from 'node:fs';
const engine = new BOExecutor(JSON.parse(fs.readFileSync(0, 'utf8')), {available: context => context.slots > 0});
let state = 'pending';
const states = [['start', 0], ['resume', 1], ['finish', 1]].map(([event, slots]) => {
  state = engine.step(state, event, {slots}).state;
  return state;
});
if (!BOProbe || typeof bo_observeHttp !== 'function') process.exit(1);
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

    def legacy_javascript_receipt(self):
        """Retain the previous two-member ownership contract in an isolated project."""
        integration.install(self.root, "javascript")
        receipt = self.root / integration.RECEIPT
        prior = json.loads(receipt.read_text(encoding="utf-8"))
        name = "bo_stategraph/bo_http.mjs"
        prior["files"].pop(name)
        prior["sources"].pop(name)
        (self.root / name).unlink()
        receipt.write_text(json.dumps(prior), encoding="utf-8")
        return receipt.read_bytes()

    def test_known_http_dependency_upgrade_preserves_receipt_and_personal_files(self):
        before = self.legacy_javascript_receipt()
        personal = self.root / "bo_stategraph/config/layout.json"
        personal.parent.mkdir()
        personal.write_text('{"position":[3,4]}', encoding="utf-8")
        project = self.root / "bo_stategraph/project.json"
        project.write_text('{"project":"unchanged"}', encoding="utf-8")
        planned = integration.plan(self.root, "javascript")
        self.assertEqual(planned["changes"], ["bo_stategraph/bo_http.mjs"])
        self.assertFalse(integration.inspect(self.root)["valid"])
        self.assertEqual((self.root / integration.RECEIPT).read_bytes(), before)
        result = integration.install(self.root, "javascript")
        self.assertEqual((self.root / result["migration"]["receipt_backup"]).read_bytes(), before)
        self.assertTrue(integration.inspect(self.root)["valid"])
        self.assertEqual(personal.read_text(), '{"position":[3,4]}')
        self.assertEqual(project.read_text(), '{"project":"unchanged"}')
        self.assertEqual(integration.plan(self.root, "javascript")["changes"], [])

    def test_http_upgrade_refuses_unknown_old_members_and_source_maps(self):
        before = self.legacy_javascript_receipt()
        receipt = self.root / integration.RECEIPT
        for kind in ("missing", "extra", "source", "protocol"):
            with self.subTest(kind=kind):
                value = json.loads(before)
                if kind == "missing":
                    value["files"].pop("bo_stategraph/bo_capture.mjs")
                    value["sources"].pop("bo_stategraph/bo_capture.mjs")
                elif kind == "extra":
                    value["files"]["app.mjs"] = "0" * 64
                    value["sources"]["app.mjs"] = "other.mjs"
                elif kind == "source":
                    value["sources"]["bo_stategraph/bo_runtime.mjs"] = "other.mjs"
                else:
                    value["protocols"]["event"] = "unsupported"
                raw = json.dumps(value).encode()
                receipt.write_bytes(raw)
                with self.assertRaises(ValueError):
                    integration.install(self.root, "javascript")
                self.assertEqual(receipt.read_bytes(), raw)
                self.assertFalse((self.root / "bo_stategraph/bo_http.mjs").exists())

    def test_released_pre_registry_protocol_inventory_upgrades(self):
        """The released pre-registry receipt lacks only snapshot_registry.

        Commit 03c3488a shipped this protocol map with six Python or two Node
        modules. Rejecting it would regress the previously supported upgrade.
        """
        for language, addition in (
            ("python", "bo_stategraph/bo_models.py"),
            ("javascript", "bo_stategraph/bo_http.mjs"),
        ):
            with self.subTest(language=language):
                root = self.root / language
                integration.install(root, language)
                receipt = root / integration.RECEIPT
                prior = json.loads(receipt.read_text(encoding="utf-8"))
                prior["files"].pop(addition)
                prior["sources"].pop(addition)
                prior["protocols"].pop("snapshot_registry")
                (root / addition).unlink()
                receipt.write_text(json.dumps(prior), encoding="utf-8")
                before = receipt.read_bytes()
                result = integration.install(root, language)
                self.assertEqual(
                    (root / result["migration"]["receipt_backup"]).read_bytes(), before
                )
                self.assertTrue(integration.inspect(root)["valid"])
                self.assertEqual(
                    json.loads(receipt.read_text())["protocols"], integration.PROTOCOLS
                )

    def test_http_upgrade_refuses_local_edits_and_unowned_new_target(self):
        before = self.legacy_javascript_receipt()
        for name in ("bo_runtime.mjs", "bo_http.mjs"):
            with self.subTest(name=name):
                target = self.root / "bo_stategraph" / name
                old = target.read_bytes() if target.exists() else None
                target.write_bytes(b"// project-owned change\n")
                with self.assertRaisesRegex(ValueError, "edits require review"):
                    integration.install(self.root, "javascript")
                self.assertEqual(target.read_bytes(), b"// project-owned change\n")
                self.assertEqual((self.root / integration.RECEIPT).read_bytes(), before)
                if old is None:
                    target.unlink()
                else:
                    target.write_bytes(old)

    def test_http_upgrade_copy_failure_restores_all_old_bytes(self):
        self.legacy_javascript_receipt()
        receipt = self.root / integration.RECEIPT
        runtime = self.root / "bo_stategraph/bo_runtime.mjs"
        runtime.write_bytes(runtime.read_bytes() + b"\n// previous managed revision\n")
        prior = json.loads(receipt.read_text(encoding="utf-8"))
        prior["files"]["bo_stategraph/bo_runtime.mjs"] = hashlib.sha256(
            runtime.read_bytes()
        ).hexdigest()
        receipt.write_text(json.dumps(prior), encoding="utf-8")
        before, old_runtime = receipt.read_bytes(), runtime.read_bytes()
        from bo_upgrade import replace_copy

        def broken_copy(source, target):
            if target.name == "bo_http.mjs":
                raise OSError("simulated write failure")
            return replace_copy(source, target)

        with patch("bo_upgrade.replace_copy", side_effect=broken_copy):
            with self.assertRaisesRegex(OSError, "simulated write failure"):
                integration.install(self.root, "javascript")
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(runtime.read_bytes(), old_runtime)
        self.assertFalse((self.root / "bo_stategraph/bo_http.mjs").exists())

    def test_http_upgrade_refuses_changed_archive_without_writing_dependencies(self):
        before = self.legacy_javascript_receipt()
        planned = integration.plan(self.root, "javascript")
        backup = self.root / planned["migration"]["receipt_backup"]
        backup.parent.mkdir(parents=True)
        backup.write_bytes(b"unrelated archive")
        with self.assertRaisesRegex(ValueError, "archive differs"):
            integration.install(self.root, "javascript")
        self.assertEqual(backup.read_bytes(), b"unrelated archive")
        self.assertEqual((self.root / integration.RECEIPT).read_bytes(), before)
        self.assertFalse((self.root / "bo_stategraph/bo_http.mjs").exists())

    def test_http_upgrade_receipt_failure_restores_old_inventory(self):
        before = self.legacy_javascript_receipt()
        planned = integration.plan(self.root, "javascript")
        with patch.object(integration, "write", side_effect=OSError("receipt unavailable")):
            with self.assertRaisesRegex(OSError, "receipt unavailable"):
                integration.install(self.root, "javascript")
        self.assertEqual((self.root / integration.RECEIPT).read_bytes(), before)
        self.assertEqual((self.root / planned["migration"]["receipt_backup"]).read_bytes(), before)
        self.assertFalse((self.root / "bo_stategraph/bo_http.mjs").exists())

    def test_malformed_existing_receipt_cannot_be_treated_as_a_fresh_install(self):
        receipt = self.root / integration.RECEIPT
        receipt.parent.mkdir(parents=True)
        for value in (
            {},
            [],
            None,
            {"schema": "vibelens-integration/v1", "language": "javascript"},
        ):
            with self.subTest(value=value):
                raw = json.dumps(value).encode()
                receipt.write_bytes(raw)
                with self.assertRaises(ValueError):
                    integration.install(self.root, "javascript")
                self.assertEqual(receipt.read_bytes(), raw)
                self.assertFalse((self.root / "bo_stategraph/bo_http.mjs").exists())

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
