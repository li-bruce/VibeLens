"""Presentation must preserve definition identities and runtime authority."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from test_native_behavior_bindings import binding_fixture
import test_native_behavior_integration as integration
from bo_observer.behavior.presentation import project
from bo_observer.observation.behavior_context import BehaviorContext, design_context
from bo_observer.observation.session import GraphSession
from bo_observer.observation.recording_session import checkpoint


class BehaviorPresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract, self.discovery, self.model, _ = binding_fixture(self.root)

    def test_independent_models_keep_complete_states_without_extra_graph_nodes(self):
        before = deepcopy((self.contract, self.discovery, self.model))
        result = project(self.contract, self.discovery, self.model)
        self.assertEqual(result["models"], ["state-model:grant", "state-model:archive"])
        self.assertEqual(
            result["records"]["variable/grant-status"]["domain"]["values"], ["inactive", "active"]
        )
        self.assertIn("variable/grant-status", result["nodes"]["state:grant:active"])
        self.assertNotIn("variable/grant-status", result["nodes"]["state:archive:active"])
        self.assertNotIn("edges", result)
        self.assertEqual(before, (self.contract, self.discovery, self.model))

    def test_native_read_action_completion_and_property_remain_distinct(self):
        result = project(self.contract, self.discovery, self.model)
        self.assertIn("variable/grant-status", result["nodes"]["grant"])
        self.assertIn("action/grant-share", result["nodes"]["commit"])
        action = result["records"]["action/grant-share"]
        self.assertEqual(action["completion"]["kind"], "commit")
        self.assertEqual(action["transition"]["dest"], "active")
        self.assertEqual(action["properties"], ["archive-unchanged"])
        self.assertEqual(
            result["records"]["property/archive-unchanged"]["kind"], "transition_constraint"
        )
        self.assertNotIn("observed_at", json.dumps(result))

    def test_shared_property_is_locatable_at_both_actual_dependencies(self):
        result = project(self.contract, self.discovery, self.model)
        self.assertIn("property/archive-unchanged", result["nodes"]["state-model:archive"])
        self.assertIn("property/archive-unchanged", result["nodes"]["share"])

    def test_source_free_user_action_is_located_through_the_explicit_event_link(self):
        result = project(self.contract, self.discovery, {"nodes": []})
        self.assertIn("action/grant-share", result["nodes"].get("share", []))
        self.assertNotIn("action/grant-share", result["nodes"].get("view-profile", []))

    def test_unbound_source_free_definition_has_no_fake_source_or_success(self):
        self.contract["scope"]["unresolved"] = ["When queued access is rechecked"]
        result = project(self.contract, self.discovery, {"nodes": []})
        self.assertEqual(result["unresolved"], ["When queued access is rechecked"])
        self.assertEqual(result["records"]["action/grant-share"]["binding"], None)
        self.assertNotIn("status", result["records"]["action/grant-share"])

    def test_invalid_definition_fails_before_projection(self):
        self.contract["actions"][0]["writes"] = []
        with self.assertRaises(ValueError):
            project(self.contract, self.discovery, self.model)


class BehaviorContextTests(unittest.TestCase):
    def setUp(self):
        self.fixture = integration.NativeIntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_current_bundle_is_read_once_and_views_cannot_mutate_it(self):
        context = BehaviorContext(
            self.fixture.root,
            self.fixture.project,
            {"behavior": self.fixture.contract, "discovery": self.fixture.discovery},
        )
        self.assertEqual(context.changed_inputs(), [])
        view = context.view()
        view["models"].clear()
        self.assertEqual(len(context.view()["models"]), 2)

    def test_same_length_contract_edit_invalidates_live_session_even_without_envelope_change(self):
        session = GraphSession(self.fixture.root)
        try:
            self.assertIn("state-model:grant", session.view()["behavior_context"]["models"])
            path = self.fixture.root / "bo_stategraph/behavior.json"
            raw = path.read_bytes()
            self.assertIn(b"The selected grant is committed", raw)
            path.write_bytes(
                raw.replace(b"The selected grant is committed", b"The selected grant is completed")
            )
            result = session.binding()
            self.assertEqual(result["status"], "stale")
            self.assertIn("bo_stategraph/behavior.json", result["behavior_inputs_changed"])
            self.assertEqual(len(session.history.events), 0)
        finally:
            session.web.close()

    def test_draft_details_do_not_silently_borrow_another_revision(self):
        self.assertEqual(
            design_context(self.fixture.root, self.fixture.discovery)["schema"],
            "bo-behavior-details/v1",
        )
        changed = deepcopy(self.fixture.discovery)
        changed["state_models"][0]["label"] = "A new draft"
        result = design_context(self.fixture.root, changed)
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("records", result)

    def test_old_verification_remains_recorded_not_current_live_approval(self):
        root = self.fixture.root
        (root / ".stategraph/check").mkdir(parents=True)
        (root / ".stategraph/active.json").write_text(json.dumps({"change": ".stategraph/check"}))
        receipt = {
            "candidate_id": "old-build",
            "checked_at": "2026-11-19T00:00:00Z",
            "valid": False,
            "behavior_coverage": {
                "categories": {
                    "capture": {"status": "failed", "coverage": {"required": 3, "checked": 1}}
                }
            },
        }
        (root / ".stategraph/check/verification.json").write_text(json.dumps(receipt))
        context = BehaviorContext(
            root,
            self.fixture.project,
            {"behavior": self.fixture.contract, "discovery": self.fixture.discovery},
        )
        result = context.view()["last_verification"]
        self.assertEqual(result["freshness"], "recorded")
        self.assertFalse(result["valid"])
        self.assertEqual(result["candidate_id"], "old-build")
        (root / ".stategraph/active.json").write_text(json.dumps({"change": "../elsewhere"}))
        self.assertEqual(context.view()["last_verification"], {"freshness": "unavailable"})

    def test_recording_keeps_definition_context_without_copying_it_to_every_frame(self):
        session = GraphSession(self.fixture.root)
        try:
            view = session.view()
            full = checkpoint(view, context=True)
            self.assertEqual(full["behavior_context"], view["behavior_context"])
            self.assertNotIn("behavior_context", checkpoint(view))
            full["behavior_context"]["records"].clear()
            self.assertTrue(session.view()["behavior_context"]["records"])
        finally:
            session.web.close()


if __name__ == "__main__":
    unittest.main()
