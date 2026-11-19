"""Draft targets and reviewed meaning never masquerade as executable models."""

from copy import deepcopy
from contextlib import contextmanager
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from test_concept_models import draft
from bo_observer.concepts import assess, confirm, snapshot
from bo_observer.concepts.common import digest
from bo_observer.concepts.construction import present, promote
from bo_observer.concepts.model import build
from bo_observer.definition_errors import ContractError
from bo_observer.workflow.concept_cli import main


def document():
    value = draft()
    value["schema"] = "business-discovery/v3"
    value["construction"] = {"targets": [], "obligations": [], "presentations": []}
    return value


def target():
    return {"id": "target:sharing", "kind": "business_network",
            "meaning": "Sharing capability described by the owner", "source_refs": ["U1"],
            "scope_refs": [], "unresolved": ["Build the requested network"]}


def show_all(value, identity="P1"):
    scope = snapshot(value, ["*"])["scope"]
    value["construction"]["presentations"].append(
        present(value, ["*"], scope, [], ["U1"], identity))


class ConstructionTests(unittest.TestCase):
    @contextmanager
    def rejects(self, code):
        with self.assertRaises(ContractError) as caught:
            yield
        self.assertEqual(caught.exception.diagnostic.code, code)

    def test_targets_remain_outside_graph_and_block_even_without_questions(self):
        value = document()
        value["construction"]["targets"].append(target())
        report = assess(value)
        self.assertTrue(report["valid"], report)
        self.assertFalse(report["ready"])
        self.assertIn("target:sharing", report["blocked"])
        self.assertNotIn("target:sharing", report["index"])

    def test_empty_source_backed_draft_can_retain_missing_models(self):
        value = document()
        for name in ("networks", "objects", "state_models", "facts", "crosslinks",
                     "applicability", "expectations", "decisions", "confirmations"):
            value[name] = []
        value.pop("policy", None)
        value["construction"]["targets"].append(target())
        report = assess(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["graph"]["nodes"])

    def test_declared_missing_relation_cannot_be_closed_by_empty_question_list(self):
        value = document()
        value["construction"]["obligations"].append({
            "id": "download-after-share", "kind": "relation",
            "source_refs": ["U1"], "meaning": "A share enables the recipient's read",
            "from_ref": "share", "to_ref": "read", "relation": "flow"})
        value["networks"][0]["edges"] = [
            edge for edge in value["networks"][0]["edges"] if edge["id"] != "share-read"]
        report = assess(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertIn("download-after-share", report["blocked"])

    def test_relation_obligation_uses_typed_link_not_containment(self):
        value = document()
        value["construction"]["obligations"].append({
            "id": "link", "kind": "relation", "source_refs": ["U1"], "meaning": "Read follows share",
            "from_ref": "share", "to_ref": "read", "relation": "flow"})
        self.assertFalse(build(value)["construction"]["gaps"])
        value["construction"]["obligations"][0]["relation"] = "calls"
        self.assertEqual(build(value)["construction"]["gaps"][0]["kind"], "missing_relation")

    def test_promote_is_atomic_and_keeps_identity(self):
        value = document()
        value["construction"]["targets"].append(target())
        before = deepcopy(value)
        result = promote(value, "target:sharing", value, "business-network:sharing", digest(value))
        self.assertEqual(value, before)
        self.assertEqual(result["construction"]["targets"][0]["promoted_to"], "business-network:sharing")
        self.assertFalse(build(result)["construction"]["gaps"])

    def test_invalid_native_candidate_never_promotes(self):
        value = document()
        value["construction"]["targets"].append(target())
        candidate = deepcopy(value)
        candidate["state_models"][0]["initial"] = "absent"
        with self.assertRaises(ValueError):
            promote(value, "target:sharing", candidate, "business-network:sharing", digest(value))
        self.assertNotIn("promoted_to", value["construction"]["targets"][0])

    def test_stale_promotion_is_rejected(self):
        value = document()
        value["construction"]["targets"].append(target())
        with self.rejects("stale_construction_revision"):
            promote(value, "target:sharing", value, "business-network:sharing", "old")

    def test_targets_require_known_sources(self):
        value = document()
        value["construction"]["targets"].append({**target(), "source_refs": ["invented"]})
        self.assertFalse(assess(value)["valid"])

    def test_full_presentation_allows_scoped_confirmation(self):
        value = document()
        value["construction"]["obligations"].append({
            "id": "sharing", "kind": "model", "source_refs": ["U1"],
            "meaning": "Sharing capability", "target_ref": "business-network:sharing",
            "target_kind": "business_network"})
        show_all(value)
        value["confirmations"].append(confirm(value, ["*"], ["U1"], "C1", presentation_ref="P1"))
        report = assess(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["ready"], report["blocked"])

    def test_omitted_boundary_cannot_be_confirmed(self):
        value = document()
        value["construction"]["presentations"].append(
            present(value, ["*"], ["share"], [], ["U1"], "P1"))
        with self.rejects("unreviewed_boundary"):
            confirm(value, ["*"], ["U1"], "C1", presentation_ref="P1")

    def test_stale_presentation_cannot_confirm_new_meaning(self):
        value = document()
        show_all(value)
        value["networks"][0]["nodes"][0]["meaning"] = "Share with everyone"
        with self.rejects("stale_presentation"):
            confirm(value, ["*"], ["U1"], "C1", presentation_ref="P1")

    def test_missing_presentation_is_not_implicit_assent(self):
        with self.rejects("missing_presentation"):
            confirm(document(), ["*"], ["U1"], "C1")

    def test_historical_presentations_cannot_be_rewritten(self):
        value = document()
        show_all(value)
        previous = deepcopy(value)
        value["construction"]["presentations"].clear()
        self.assertIn("immutable_presentation_changed",
                      {item["code"] for item in assess(value, previous)["errors"]})

    def test_v2_confirmations_stay_readable_without_new_guarantees(self):
        value = draft()
        value["confirmations"].append(confirm(value, ["*"], ["U1"], "C1"))
        self.assertTrue(assess(value)["ready"])
        value["schema"] = "business-discovery/v3"
        value["construction"] = {"targets": [], "obligations": [], "presentations": []}
        report = assess(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["ready"])
        self.assertIn("construction:review", report["blocked"])

    def test_existing_cli_records_presentation_then_confirms_exact_scope(self):
        value = document()
        value["construction"]["obligations"].append({
            "id": "sharing", "kind": "model", "source_refs": ["U1"],
            "meaning": "Sharing", "target_ref": "business-network:sharing",
            "target_kind": "business_network"})
        from test_concept_models import ROOT
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            path = Path(folder) / "discovery.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["present", "--root", folder, "--scope", "*", "--id", "P1",
                               "--sources", "U1", "--visible", *snapshot(value)["scope"]])
            self.assertEqual(status, 0, output.getvalue())
            with redirect_stdout(output):
                status = main(["confirm", "--root", folder, "--scope", "*", "--id", "C1",
                               "--sources", "U1", "--presentation", "P1"])
            self.assertEqual(status, 0, output.getvalue())
            self.assertTrue(assess(json.loads(path.read_text()))["ready"])

    def test_question_can_target_a_model_that_does_not_exist_yet(self):
        from bo_observer.workflow.requirements_dialogue import assess as dialogue
        value = document()
        value["construction"]["targets"].append(target())
        value["decisions"].append({
            "id": "D_TARGET", "topic": "scope",
            "question": "Does sharing form an independent capability?",
            "why": "The requested capability has not been modeled yet.",
            "affects": ["target:sharing"], "blocking": True,
            "status": "open", "source_refs": ["U1"]})
        result = dialogue(value)
        self.assertTrue(result["valid"], result)
        self.assertIn("D_TARGET", [q["id"] for q in result["questions"]])
        self.assertFalse(result["ready"])


if __name__ == "__main__":
    unittest.main()
