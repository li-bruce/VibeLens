"""Technical entrypoints retain coverage without inventing business operations."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]

from code_structure import enrich, scan
from implementation_coverage import static_errors, runtime_errors, protected_errors
from semantic_probe import Pins
from test_implementation_coverage import fixture


class TechnicalFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model, _ = fixture(self.root)
        source = self.root / "app.py"
        source.write_text(
            source.read_text(encoding="utf-8")
            + "\n@api.post('/health')\ndef readiness():\n"
            + '    """Return native service readiness for deployment checks."""\n'
            + "    return {'ready': True}\n",
            encoding="utf-8",
        )
        self.index = scan(self.root, ["app.py"])
        self.node = {
            "id": "service-readiness",
            "kind": "function",
            "layer": "program",
            "label": "readiness",
            "source": {"path": "app.py", "symbol": "readiness"},
            "capture": {"in": {}, "out": {"ready": "boolean"}},
        }
        self.model["nodes"].append(self.node)
        self.feature = {
            "id": "service-readiness",
            "label": "Service readiness endpoint",
            "category": "technical",
            "implementation_node": self.node["id"],
            "classification_reason": "Deployment health checks read the server's readiness.",
            "nodes": [self.node["id"]],
            "sources": ["app.py::readiness"],
            "parameters": [],
            "cases": [{"case": "health", "node": self.node["id"], "phase": "return"}],
        }
        self.model["implementation"]["features"].append(self.feature)

    def errors(self, model=None):
        model = model or self.model
        return static_errors(model["implementation"], model, self.index)

    def test_technical_entrypoint_is_visible_without_a_business_role(self):
        result = enrich(self.model, self.index)
        self.assertEqual(self.errors(result), [])
        node = next(n for n in result["nodes"] if n["id"] == self.node["id"])
        self.assertEqual(node["source"], self.node["source"])
        self.assertNotIn("business", node.get("semantic_roles", []))
        self.assertEqual(node["layer"], "program")

    def test_classification_is_explicit_and_does_not_excuse_missing_cases(self):
        for field, value in (
            ("category", "utility"),
            ("classification_reason", ""),
            ("classification_reason", []),
            ("implementation_node", "missing"),
        ):
            with self.subTest(field=field):
                model = deepcopy(self.model)
                model["implementation"]["features"][-1][field] = value
                self.assertTrue(self.errors(model))
        self.feature["cases"] = []
        self.assertIn({"feature_missing_runtime_cases": self.feature["id"]}, self.errors())

    def test_technical_classification_cannot_relabel_a_business_projection(self):
        for extra in (
            {"business_node": "upload"},
            {"implementation_node": "upload", "nodes": ["upload", self.node["id"]]},
        ):
            with self.subTest(extra=extra):
                model = deepcopy(self.model)
                model["implementation"]["features"][-1].update(extra)
                self.assertTrue(self.errors(model))
        self.model["concepts"] = {"business": {"check-ready": [self.node["id"]]}}
        self.assertTrue(self.errors())

    def test_business_default_still_requires_its_business_projection(self):
        self.feature.pop("category")
        self.assertIn({"feature_missing_business_projection": self.feature["id"]}, self.errors())

    def test_deleting_technical_observations_still_fails_the_iteration_guard(self):
        before = deepcopy(self.model["implementation"])
        self.feature["cases"] = []
        self.assertTrue(protected_errors(before, self.model["implementation"]))

    def test_a_technical_endpoint_still_requires_actual_runtime_values(self):
        # Execute the actual native function, then observe its returned value.
        namespace = {}
        exec(
            compile((self.root / "app.py").read_text(encoding="utf-8"), "app.py", "exec"), namespace
        )
        actual = namespace["readiness"]()
        events = []
        pins = Pins(self.model, "build", sink=lambda line: events.append(json.loads(line)))
        pins.attempt("health").record(
            self.node["id"], "return", {"param_version": 1}, lambda: {"outputs": actual}
        )
        pins.close()
        plan = {"schema": "bo-implementation/v1", "features": [self.feature]}
        payload = {
            "build_id": "build",
            "runs": [{"case": "health", "mode": "on", "events": events}],
        }
        self.assertEqual(runtime_errors(plan, self.model, payload)["errors"], [])
        payload["runs"][0]["events"] = []
        self.assertTrue(runtime_errors(plan, self.model, payload)["errors"])


if __name__ == "__main__":
    unittest.main()
