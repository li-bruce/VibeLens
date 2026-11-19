"""The same bindings inspect real Node async calls and committed file values."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_native_behavior_runtime import fixture, BUILD, ROOT
from bo_observer.behavior.native_runtime import assess_runtime
from bo_observer.sources import scan


class NativeNodeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract, self.discovery, self.model, _, _ = fixture(self.root)
        files = ROOT / "tests/fixtures/behavior-contracts"
        (self.root / "application.mjs").write_bytes((files / "native_application.mjs").read_bytes())
        (self.root / "bo_native_case.mjs").write_bytes((files / "bo_native_case.mjs").read_bytes())

        def rebind(value):
            if isinstance(value, dict):
                if value.get("path") == "application.py" and "symbol" in value:
                    value["path"] = "application.mjs"
                for item in value.values():
                    rebind(item)
            elif isinstance(value, list):
                for item in value:
                    rebind(item)
        rebind(self.model)
        self.index = scan(self.root, ["application.mjs"])
        config = {"root": str(self.root), "build": BUILD,
                  "project": {"project_id": self.contract["project_id"], "model": self.model},
                  "adapter": (ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs").as_uri()}
        (self.root / "case.json").write_text(json.dumps(config), encoding="utf-8")
        result = subprocess.run(["node", str(self.root / "bo_native_case.mjs"), str(self.root / "case.json")],
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.payload = json.loads(result.stdout)

    def result(self):
        return assess_runtime(self.contract, self.discovery, self.model, self.payload,
                              index=self.index, case_ids={"share", "error"})

    def test_native_async_parameters_error_commit_and_all_model_values(self):
        result = self.result()
        self.assertTrue(result["valid"], result.get("errors"))
        self.assertEqual(len(result["boundaries"]), 2)

    def test_modes_preserve_real_native_store_and_report_missing_capture(self):
        expected = {run["case"]: run["native_state"] for run in self.payload["runs"] if run["mode"] == "on"}
        for run in self.payload["runs"]:
            self.assertEqual(run["native_state"], expected[run["case"]])
            if run["mode"] in {"off", "fault"}:
                self.assertEqual(run["events"], [])
            if run["mode"] == "fault":
                self.assertGreater(run["health"]["errors"], 0)
        limited = next(run for run in self.payload["runs"] if run["mode"] == "limited" and run["case"] == "share")
        self.assertGreater(limited["health"]["dropped"], 0)
        limited["mode"] = "on"
        self.payload["runs"] = [limited, next(run for run in self.payload["runs"] if run["mode"] == "on" and run["case"] == "error")]
        self.assertFalse(self.result()["valid"])

    def test_changed_build_and_missing_commit_do_not_pass(self):
        original = deepcopy(self.payload)
        run = next(run for run in self.payload["runs"] if run["case"] == "share" and run["mode"] == "on")
        next(e for e in run["events"] if e["node"] == "commit")["build_id"] = "old"
        self.assertFalse(self.result()["valid"])
        self.payload = original
        run = self.payload["runs"][0]
        run["events"] = [e for e in run["events"] if e["node"] != "commit"]
        self.assertFalse(self.result()["valid"])


if __name__ == "__main__":
    unittest.main()
