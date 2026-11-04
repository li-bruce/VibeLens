"""Exercise the public design/confirmation workflow without generated business code.

The fixture's conversation is explicitly synthetic. These tests check evidence
handling and integration, rather than treating a simulated answer as real assent.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import io
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

from bo_observer.concepts import assess, confirm, snapshot
from bo_observer.observation.concept_context import ConceptContext
from bo_observer.observation.recording_session import checkpoint
from bo_observer.web.bo_design import BODesign
from bo_observer.workflow.concept_cli import main
from bo_observer.workflow.concept_review import concept_recall
from bo_observer.workflow.concept_review import compact_report
from bo_observer.workflow.requirements_dialogue import assess as assess_dialogue
from test_concept_models import bound_fixture


def draft():
    """Load the shipped, unconfirmed design example as a new conversation."""
    return json.loads(
        (ROOT / "skills/vibelens/assets/discovery.concepts.example.json").read_text(
            encoding="utf-8"
        )
    )


class ConceptWorkflowTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)
        self.path = self.root / "discovery.json"
        self.doc = draft()
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.path.write_text(json.dumps(self.doc), encoding="utf-8")

    def command(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main([*arguments, "--root", str(self.root)])
        return status, json.loads(output.getvalue())

    def test_draft_validation_and_confirmation_are_distinct(self):
        self.assertTrue(assess_dialogue(self.doc)["valid"])
        self.assertFalse(assess_dialogue(self.doc)["ready"])
        self.assertEqual(self.command("validate")[0], 0)
        self.assertEqual(self.command("check")[0], 1)
        original = self.path.read_bytes()
        self.assertEqual(self.command("snapshot", "--scope", "share")[0], 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_compact_cli_retains_verdict_and_can_save_complete_artifact(self):
        full = assess_dialogue(self.doc)
        compact = compact_report(full)
        self.assertEqual(compact["errors"], full["errors"])
        self.assertEqual(compact["blocked"], full["blocked"])
        self.assertNotIn("graph", compact["concepts"])
        self.assertIn("graph", full["concepts"])
        status, shown = self.command("validate", "--out", "review/full.json")
        self.assertEqual(status, 0)
        self.assertNotIn("graph", shown)
        saved = json.loads((self.root / "review/full.json").read_text())
        self.assertTrue(saved["graph"]["nodes"])
        self.assertTrue(self.command("validate", "--full-report")[1]["graph"]["nodes"])

    def test_three_no_code_views_share_ids_but_have_distinct_content(self):
        design = BODesign(self.root)
        full = design.view()
        self.assertEqual(full["stage"], "design")
        self.assertEqual(full["events"], [])
        self.assertIsNone(full["machine"]["current"])
        self.assertEqual(full["model"]["machine"]["values"], [])
        complete = {node["id"] for node in full["model"]["nodes"]}
        seen = {}
        for view in ("business", "state", "rules"):
            preview = design.preview("http://127.0.0.1:8830/graph", view=view, max_nodes=50)
            seen[view] = {
                node["id"] for node in preview["focus"]["nodes"] if node["id"] in complete
            }
            self.assertTrue(seen[view])
            self.assertIn("```mermaid", preview["markdown"])
        self.assertIn("share", seen["business"])
        self.assertIn("state:grant:active", seen["state"])
        self.assertIn("policy:may_read", seen["rules"])
        self.assertNotEqual(seen["business"], seen["rules"])
        self.assertFalse(assess(json.loads(self.path.read_text()))["ready"])
        small = design.preview("http://127.0.0.1:8830/graph", view="rules")
        shown = {node["id"] for node in small["focus"]["nodes"]}
        self.assertTrue({"policy-operation:manage", "policy-operation:read"} <= shown)

    def test_edge_focus_and_preview_retain_both_endpoints(self):
        design = BODesign(self.root)
        edge = next(e for e in design.view()["model"]["edges"] if e["id"] == "share-requests-event")
        focused = design.focus([edge["id"]])
        self.assertEqual(set(focused["nodes"]), {edge["from"], edge["to"]})
        preview = design.preview("http://127.0.0.1:8830/graph", [edge["id"]], max_nodes=50)
        ids = {node["id"] for node in preview["focus"]["nodes"]}
        self.assertTrue({edge["from"], edge["to"]} <= ids)

    def test_preview_export_protects_both_contract_paths_before_any_write(self):
        design = BODesign(self.root)
        preview = design.preview("http://127.0.0.1:8830/graph")
        before = self.path.read_bytes()
        for name in ("discovery.json", "discovery.md"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "contract input"):
                design.export_preview(preview, name)
            self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.root / "discovery.md").exists())
        design.export_preview(preview, "review/business.md")
        self.assertIn("```mermaid", (self.root / "review/business.md").read_text(encoding="utf-8"))
        self.assertEqual(
            json.loads((self.root / "review/business.json").read_text(encoding="utf-8")),
            preview,
        )

    def test_cli_confirm_is_idempotent_and_does_not_create_sources(self):
        status, result = self.command("confirm", "--scope", "*", "--sources", "U1", "--id", "C1")
        self.assertEqual(status, 0, result)
        saved = self.path.read_bytes()
        self.assertEqual(self.command("check")[0], 0)
        self.assertEqual(
            self.command("confirm", "--scope", "*", "--sources", "U1", "--id", "C1")[0],
            0,
        )
        self.assertEqual(saved, self.path.read_bytes())
        self.assertEqual(json.loads(saved)["sources"], self.doc["sources"])

    def test_unanswered_question_blocks_matching_confirmation_without_writes(self):
        self.doc["decisions"] = [
            {
                "id": "Q1",
                "topic": "authority",
                "blocking": True,
                "status": "open",
                "source_refs": ["U1"],
                "affects": ["share"],
                "question": "May a recipient share this file again?",
                "why": "This would change the stated owner-only permission.",
            }
        ]
        self.save()
        before = self.path.read_bytes()
        status, result = self.command(
            "confirm", "--scope", "share", "--sources", "U1", "--id", "C1"
        )
        self.assertEqual(status, 1)
        self.assertIn("Unanswered questions", result["error"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_confirm_output_cannot_overwrite_contract_or_partially_confirm(self):
        before = self.path.read_bytes()
        status, result = self.command(
            "confirm",
            "--scope",
            "*",
            "--sources",
            "U1",
            "--id",
            "C1",
            "--out",
            "discovery.json",
        )
        self.assertEqual(status, 1)
        self.assertIn("contract input", result["error"])
        self.assertEqual(self.path.read_bytes(), before)

    def add_future_question(self):
        """Keep an unrelated draft beside a confirmed, independently scoped feature."""
        document = self.doc
        document["networks"][0]["nodes"].append(
            {
                "id": "future",
                "kind": "action",
                "label": "Future feature",
                "meaning": "An independent later feature",
                "source_refs": ["U1"],
            }
        )
        document["applicability"].append(
            {
                "operation": "future",
                "state": {"status": "none", "reason": "No stored state"},
                "rules": {"status": "none", "reason": "No permission decision"},
                "source_refs": ["U1"],
            }
        )
        document["scope"] = ["share"]
        document["confirmations"].append(confirm(document, ["share"], ["U1"], "C1"))
        question = {
            "id": "future-question",
            "topic": "authority",
            "blocking": True,
            "status": "open",
            "source_refs": ["U1"],
            "affects": ["future"],
            "question": "Who can use the later feature?",
            "why": "Its actors are undecided.",
        }
        document["decisions"] = [question]
        return question

    def test_future_questions_do_not_block_a_confirmed_increment(self):
        question = self.add_future_question()
        document = self.doc
        result = assess_dialogue(document)
        self.assertTrue(result["ready"], result)
        self.assertEqual(result["questions"], [])
        # A settled future question also needs no source/acceptance links yet.
        question.update(
            status="resolved",
            resolution={
                "kind": "user_answer",
                "source_refs": ["U1"],
                "text": "The owner.",
            },
        )
        result = assess_dialogue(document, intent={"requirements": []})
        self.assertTrue(result["ready"], result)
        # Record legality is always global, even for a future feature.
        question["resolution"]["source_refs"] = ["missing-answer"]
        self.assertFalse(assess_dialogue(document)["valid"])

    def test_active_question_keeps_its_dependency_and_link_obligations(self):
        question = self.add_future_question()
        active = {
            **question,
            "id": "active-question",
            "affects": ["share"],
            "depends_on": [question["id"]],
        }
        self.doc["decisions"].append(active)
        result = assess_dialogue(self.doc)
        self.assertIn(question["id"], result["blocked"])
        self.assertIn(active["id"], result["blocked"])
        self.assertEqual([item["id"] for item in result["questions"]], [question["id"]])
        for item in self.doc["decisions"]:
            item.update(
                status="resolved",
                resolution={
                    "kind": "user_answer",
                    "source_refs": ["U1"],
                    "text": "The owner.",
                },
            )
        result = assess_dialogue(self.doc, intent={"requirements": []})
        missing = {
            item["item"] for item in result["errors"] if item["code"] == "missing_decision_link"
        }
        self.assertEqual(missing, {"active-question.requirements", "future-question.requirements"})

    def test_outputs_protect_configured_inputs_not_only_explicit_cli_arguments(self):
        config = {"model": "state/model.json", "code_files": ["app.py"]}
        (self.root / "sync.json").write_text(json.dumps(config))
        for name in (
            "sync.json",
            "state/model.json",
            "app.py",
            ".stategraph/active.json",
        ):
            with self.subTest(name=name):
                status, result = self.command("snapshot", "--scope", "share", "--out", name)
                self.assertEqual(status, 1, result)
        self.assertEqual(json.loads((self.root / "sync.json").read_text()), config)
        self.assertFalse((self.root / "state").exists())

    def test_outputs_preserve_unregistered_source_and_existing_project_files(self):
        for name, content in (
            ("new.py", "value = 1\n"),
            ("config.json", '{"port": 8000}'),
            ("README.md", "# My application\n"),
        ):
            path = self.root / name
            path.write_text(content)
            before = self.path.read_bytes()
            status, result = self.command(
                "confirm",
                "--scope",
                "share",
                "--sources",
                "U1",
                "--id",
                "C1",
                "--out",
                name,
            )
            self.assertEqual(status, 1, result)
            self.assertEqual(path.read_text(), content)
            self.assertEqual(self.path.read_bytes(), before)
        design = BODesign(self.root)
        preview = design.preview("http://localhost:8830/graph")
        with self.assertRaisesRegex(ValueError, "Existing output"):
            design.export_preview(preview, "README.md")
        self.assertFalse((self.root / "README.json").exists())
        # The normal review path is repeatable for both report formats.
        for _ in range(2):
            self.assertEqual(
                self.command("snapshot", "--scope", "share", "--out", "review/scope.json")[0],
                0,
            )
            design.export_preview(preview, "review/scope.md")

    def test_changed_meaning_invalidates_readiness_and_is_in_recall(self):
        self.doc["confirmations"] = [confirm(self.doc, ["*"], ["U1"], "C1")]
        previous = deepcopy(self.doc)
        self.doc["networks"][0]["nodes"][0]["meaning"] = "Allow any recipient to create grants"
        report = assess_dialogue(self.doc, previous=previous)
        self.assertFalse(report["ready"])
        recalled = concept_recall(self.doc, previous)
        self.assertFalse(recalled["ready"])
        self.assertTrue(recalled["changes"]["semantic_change"])
        self.assertEqual(previous["confirmations"], self.doc["confirmations"])

    def test_label_only_update_keeps_confirmed_semantics(self):
        self.doc["confirmations"] = [confirm(self.doc, ["*"], ["U1"], "C1")]
        previous = deepcopy(self.doc)
        self.doc["networks"][0]["nodes"][0]["label"] = "Share with a colleague"
        self.assertEqual(snapshot(previous), snapshot(self.doc))
        report = assess_dialogue(self.doc, previous=previous)
        self.assertTrue(report["ready"], report)

    def test_recording_pins_concepts_and_never_adds_runtime_events(self):
        view = BODesign(self.root).view()
        view["concept_structure"] = {
            "revision": "recorded",
            "nodes": [{"id": "share"}],
            "edges": [],
        }
        saved = checkpoint(view, context=True)
        view["concept_structure"]["revision"] = "edited"
        view["concept_structure"]["nodes"].clear()
        self.assertEqual(saved["concept_structure"]["revision"], "recorded")
        self.assertEqual(saved["concept_structure"]["nodes"], [{"id": "share"}])
        self.assertEqual(saved["events"], [])
        self.assertNotIn("concept_structure", checkpoint(view))

    def test_legacy_record_is_explicitly_unconfirmed_under_new_contract(self):
        old = json.loads((ROOT / "skills/vibelens/assets/discovery.example.json").read_text())
        recalled = concept_recall(old)
        self.assertFalse(recalled["ready"])
        self.assertEqual(recalled["status"], "legacy")

    def test_legacy_rule_binding_compares_meaning_not_only_operation_ids(self):
        document, model, _ = bound_fixture()
        document["schema"] = "business-discovery/v1"
        # The public legacy gate still has to reject a changed composition even
        # though its operation identities, inputs and source bindings all exist.
        model["policy"]["nodes"][-1]["op"] = "any"
        result = assess_dialogue(document, model=model)
        self.assertFalse(result["ready"])
        self.assertIn("policy_semantics_changed", {item["code"] for item in result["errors"]})

    def bound_context(self):
        """Write only the independent inputs consumed by the session context."""
        document, model, acceptance = bound_fixture()
        self.path.write_text(json.dumps(document), encoding="utf-8")
        (self.root / "acceptance.json").write_text(json.dumps(acceptance), encoding="utf-8")
        return ConceptContext(self.root, model)

    def test_bound_context_is_detached_and_detects_semantic_input_drift(self):
        context = self.bound_context()
        self.assertEqual(context.changed_inputs(), [])
        view = context.view()
        self.assertTrue(view["nodes"])
        self.assertFalse(view["execution_authority"])
        view["nodes"].clear()
        self.assertTrue(context.view()["nodes"])
        # Keep the byte length unchanged; timestamps/size must not substitute for
        # current source content when deciding whether an event is still current.
        before = self.path.stat()
        self.path.write_bytes(self.path.read_bytes().replace(b"before_effect", b"after__effect"))
        os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertIn("discovery.json", context.changed_inputs())

    def test_bound_context_tracks_configured_paths_not_unrelated_settings(self):
        context = self.bound_context()
        config_path = self.root / "sync.json"
        config_path.write_text(json.dumps({"test_commands": [["python", "tests.py"]]}))
        self.assertEqual(context.changed_inputs(), [])
        config_path.write_text(json.dumps({"discovery": "new-discovery.json"}))
        self.assertEqual(context.changed_inputs(), ["sync.json"])
        config_path.write_text("invalid")
        self.assertIn("sync.json", context.changed_inputs())

    def test_missing_contract_input_is_stale_and_missing_at_start_is_rejected(self):
        context = self.bound_context()
        (self.root / "acceptance.json").unlink()
        self.assertIn("acceptance.json", context.changed_inputs())
        _, model, _ = bound_fixture()
        with self.assertRaisesRegex(ValueError, "contract input"):
            ConceptContext(self.root, model)

    def test_unreadable_existing_configuration_is_not_treated_as_missing(self):
        context = self.bound_context()
        (self.root / "sync.json").write_text("{}", encoding="utf-8")
        read = context.sources.read
        with patch.object(
            context.sources,
            "read",
            side_effect=lambda name: None if name == "sync.json" else read(name),
        ):
            self.assertIn("sync.json", context.changed_inputs())

    def test_contract_parent_replacement_cannot_escape_with_identical_bytes(self):
        document, model, acceptance = bound_fixture()
        directory = self.root / "contracts"
        directory.mkdir()
        source = directory / "discovery.json"
        source.write_text(json.dumps(document), encoding="utf-8")
        (self.root / "acceptance.json").write_text(json.dumps(acceptance), encoding="utf-8")
        (self.root / "sync.json").write_text(
            json.dumps({"discovery": "contracts/discovery.json"}), encoding="utf-8"
        )
        context = ConceptContext(self.root, model)
        self.assertEqual(context.changed_inputs(), [])
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as external:
            (Path(external) / "discovery.json").write_bytes(source.read_bytes())
            source.unlink()
            directory.rmdir()  # This synthetic directory contained only source.
            if os.name == "nt":
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(directory), external],
                    check=True,
                    capture_output=True,
                )
            else:
                directory.symlink_to(external, target_is_directory=True)
            try:
                self.assertIn("contracts/discovery.json", context.changed_inputs())
            finally:
                if os.name == "nt":
                    directory.rmdir()
                else:
                    directory.unlink()

    def test_legacy_session_needs_no_new_contract_file(self):
        self.path.unlink()
        context = ConceptContext(self.root, {})
        self.assertIsNone(context.view())
        self.assertEqual(context.changed_inputs(), [])


if __name__ == "__main__":
    unittest.main()
