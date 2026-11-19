"""Source-backed model work is scoped independently of authored questions.

These are synthetic protocol tests, not independent chat acceptance. Real trials
remain P7; this suite exercises the scheduling/preview services they will use.
"""

from copy import deepcopy
import unittest

from test_construction_contract import document, show_all
from bo_observer.concepts import assess, confirm, snapshot
from bo_observer.concepts.model import build
from bo_observer.workflow.requirements_dialogue import assess as dialogue


def inventory():
    value = document()
    value["construction"]["obligations"] = [
        {
            "id": "sharing",
            "kind": "model",
            "source_refs": ["U1"],
            "meaning": "Build the requested sharing capability",
            "target_ref": "business-network:sharing",
            "target_kind": "business_network",
        }
    ]
    value["networks"].append(
        {
            "id": "account",
            "title": "Account preferences",
            "actors": ["Owner"],
            "trigger": "Open preferences",
            "outcome": "Read preferences",
            "nodes": [
                {
                    "id": "preferences",
                    "kind": "action",
                    "label": "Read preferences",
                    "meaning": "Read independent account preferences",
                    "source_refs": ["U1"],
                }
            ],
            "edges": [],
        }
    )
    value["applicability"].append(
        {
            "operation": "preferences",
            "state": {"status": "none", "reason": "Read only"},
            "rules": {"status": "none", "reason": "Public preferences"},
            "source_refs": ["U1"],
        }
    )
    return value


def question(identity="D1", kind="business_intent", owner="human"):
    """Same meaning with two audience wordings; both remain one decision ID."""
    return {
        "id": identity,
        "topic": "scope",
        "status": "open",
        "blocking": True,
        "question": "Does revocation prevent a new read?",
        "why": "Clarify revocation timing",
        "source_refs": ["U1"],
        "affects": ["read"],
        "routing": {
            "kind": kind,
            "owner": owner,
            "stage": "before_implementation",
            "trigger": "The requested revoke behavior is ambiguous at read start",
            "authority": {
                "kind": "user" if owner == "human" else "engineering",
                "source_refs": ["U1"],
                "scope_refs": ["read"],
            },
            "obligation_refs": ["sharing"],
            "evidence_required": (
                ["conversation_answer"] if owner == "human" else ["source_reference"]
            ),
            "invalidated_by": ["meaning"] if owner == "human" else ["source", "build"],
            "wording": {
                "en": {
                    "business": "Can a recipient start reading after revocation?",
                    "technical": "Must the grant be rechecked at read-start?",
                },
                "zh-CN": {
                    "business": "撤销后，对方还能开始读取文件吗？",
                    "technical": "读取开始时是否必须重新检查授权？",
                },
            },
        },
    }


class QuestionRoutingTests(unittest.TestCase):
    def test_review_locale_overrides_wording_without_changing_intent_or_preference(self):
        from bo_observer.workflow.construction_review import workbook

        value = self.doc()
        value["participation"] = {
            "language": "en",
            "explanation_depth": "mixed",
            "source_refs": ["U1"],
        }
        before = deepcopy(value)
        report = dialogue(value)
        review = workbook(value, report, locale="zh-CN")
        item = review["questions"][0]
        self.assertEqual(item["id"], "D1")
        self.assertEqual(item["language"], "zh-CN")
        wording = question()["routing"]["wording"]["zh-CN"]
        self.assertEqual(item["question"], wording["business"])
        self.assertEqual(item["technical_detail"], wording["technical"])
        self.assertEqual(value, before)
        self.assertEqual(report["questions"][0]["language"], "en")
        self.assertEqual(snapshot(value), snapshot(before))

    def test_legacy_records_cannot_use_unvalidated_routing_to_skip_questions(self):
        value = inventory()
        value["schema"] = "business-discovery/v2"
        value.pop("construction")
        value["decisions"] = [question()]
        value["decisions"][0]["routing"]["stage"] = "before_analysis"
        report = dialogue(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertIn("D1", report["blocked"])
        self.assertIn("D1", [q["id"] for q in report["questions"]])

    def doc(self):
        value = inventory()
        value["decisions"] = [question()]
        return value

    def test_preference_changes_wording_not_identity_or_semantics(self):
        value = self.doc()
        original = snapshot(value)
        for depth, key in [
            ("outcome", "business"),
            ("technical", "technical"),
            ("mixed", "business"),
        ]:
            value["participation"] = {
                "knowledge_domains": ["product", "development"],
                "explanation_depth": depth,
                "language": "zh-CN",
                "source_refs": ["U1"],
            }
            report = dialogue(value)
            self.assertTrue(report["valid"], report["errors"])
            item = report["questions"][0]
            self.assertEqual(item["id"], "D1")
            self.assertEqual(item["question"], question()["routing"]["wording"]["zh-CN"][key])
            self.assertEqual(snapshot(value), original)
            if depth == "mixed":
                self.assertIn("technical_detail", item)

    def test_skipped_preference_is_not_a_blocker(self):
        report = dialogue(self.doc())
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(len(report["questions"]), 1)

    def test_role_does_not_grant_agent_business_authority(self):
        value = self.doc()
        value["participation"] = {"knowledge_domains": ["architecture"], "source_refs": ["U1"]}
        value["decisions"][0]["routing"]["owner"] = "agent"
        self.assertIn("business_intent_authority", {e["code"] for e in dialogue(value)["errors"]})

    def test_three_human_questions_and_agent_work_are_separate(self):
        value = self.doc()
        value["decisions"] = [question("D" + str(i)) for i in range(5)]
        value["decisions"].append(question("F", "implementation_fact", "agent"))
        checker = question("V", "verification_gap", "checker")
        checker["routing"]["checker"] = "source-check"
        checker["routing"]["evidence_required"] = ["checker_receipt"]
        value["decisions"].append(checker)
        report = dialogue(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual([q["id"] for q in report["questions"]], ["D0", "D1", "D2"])
        self.assertEqual(report["routing"]["remaining_human"], ["D3", "D4"])
        self.assertEqual([q["id"] for q in report["routing"]["agent_work"]], ["F"])
        self.assertEqual([q["id"] for q in report["routing"]["checker_work"]], ["V"])

    def test_silence_then_partial_answer_supports_resume(self):
        value = self.doc()
        value["sources"].append(
            {
                "id": "Q1",
                "kind": "assistant",
                "text": "Can a read start after revoke?",
                "locator": "synthetic round 1",
            }
        )
        value["decisions"][0]["asked_in"] = ["Q1"]
        self.assertEqual(dialogue(value)["questions"], [])
        old = deepcopy(value)
        value["decisions"][0].update(
            status="partial",
            answers=[
                {
                    "id": "A1",
                    "text": "Existing transfers can continue; unsure about a new one.",
                    "source_refs": ["U1"],
                    "affects": ["read"],
                    "reply_to": "Q1",
                    "kind": "partial",
                }
            ],
        )
        report = dialogue(value, previous=old)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["ready"])
        self.assertEqual([q["id"] for q in report["questions"]], ["D1"])
        restarted = dialogue(deepcopy(value))
        self.assertEqual(restarted["questions"], report["questions"])

    def test_partial_answer_cannot_be_erased(self):
        old = self.doc()
        old["decisions"][0].update(
            status="partial",
            answers=[
                {
                    "id": "A1",
                    "text": "Need clarification",
                    "source_refs": ["U1"],
                    "affects": ["read"],
                    "kind": "partial",
                }
            ],
        )
        value = deepcopy(old)
        value["decisions"][0]["answers"] = []
        self.assertIn(
            "answer_history_changed", {e["code"] for e in dialogue(value, previous=old)["errors"]}
        )

    def test_conditional_work_retains_answer_and_does_not_block_inactive_branch(self):
        value = self.doc()
        first = value["decisions"][0]
        first.update(
            options=[
                {"id": "yes", "label": "Yes", "effect": "Allow reads"},
                {"id": "no", "label": "No", "effect": "Reject new reads"},
            ],
            status="resolved",
            resolution={
                "kind": "user_answer",
                "text": "Reject new reads",
                "source_refs": ["U1"],
                "choice": "no",
            },
        )
        follow = question("D2")
        follow["depends_on"] = ["D1"]
        follow["routing"]["when"] = [{"decision": "D1", "choice": "yes"}]
        value["decisions"].append(follow)
        report = dialogue(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["routing"]["inactive"], ["D2"])
        self.assertNotIn("D2", report["blocked"])
        self.assertNotIn("decision:D2", report["blocked"])
        self.assertEqual(len(value["decisions"]), 2)

    def test_unknown_condition_is_invalid(self):
        value = self.doc()
        value["decisions"][0]["routing"]["when"] = [{"decision": "missing", "choice": "yes"}]
        self.assertFalse(dialogue(value)["valid"])

    def test_agent_answer_does_not_confirm_intent(self):
        value = self.doc()
        value["sources"].append(
            {
                "id": "A",
                "kind": "assistant",
                "text": "I prefer rejection",
                "locator": "synthetic recommendation",
            }
        )
        value["decisions"][0].update(
            status="resolved",
            resolution={"kind": "user_answer", "text": "Reject", "source_refs": ["A"]},
        )
        self.assertFalse(dialogue(value)["valid"])

    def test_implementation_fact_requires_typed_evidence_not_human_guess(self):
        value = self.doc()
        d = question("F", "implementation_fact", "agent")
        value["decisions"] = [d]
        d.update(
            status="resolved",
            resolution={"kind": "user_answer", "text": "It probably checks", "source_refs": ["U1"]},
        )
        self.assertIn(
            "implementation_fact_needs_evidence", {e["code"] for e in dialogue(value)["errors"]}
        )
        value["sources"].append(
            {
                "id": "SCAN",
                "kind": "inference",
                "text": "Read guard found in source",
                "locator": "source.py:12",
            }
        )
        d["resolution"] = {
            "kind": "source_observation",
            "text": "Read guard found",
            "source_refs": ["SCAN"],
            "evidence": [
                {
                    "kind": "source_reference",
                    "path": "source.py",
                    "sha256": "a" * 64,
                    "scope_refs": ["read"],
                }
            ],
        }
        report = dialogue(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["routing"]["evidence_validation"], "not_checked")
        d["resolution"]["evidence"][0]["path"] = "../source.py"
        self.assertFalse(dialogue(value)["valid"])

    def test_route_changes_need_history_but_wording_does_not(self):
        old = self.doc()
        value = deepcopy(old)
        value["decisions"][0]["routing"]["wording"]["en"][
            "business"
        ] = "May the recipient read after access is removed?"
        self.assertTrue(dialogue(value, previous=old)["valid"])
        value["decisions"][0]["routing"]["stage"] = "before_acceptance"
        self.assertIn(
            "routing_changed_without_history",
            {e["code"] for e in dialogue(value, previous=old)["errors"]},
        )

    def test_unknown_routing_field_and_inferred_preference_rejected(self):
        value = self.doc()
        value["decisions"][0]["routing"]["force_approve"] = True
        self.assertFalse(dialogue(value)["valid"])

    def test_removing_obligation_requires_explicit_scope_change_history(self):
        old = self.doc()
        value = deepcopy(old)
        value["construction"]["obligations"] = []
        value["decisions"] = []
        value["changes"] = [
            {
                "id": "drop-question",
                "decision": "D1",
                "previous": old["decisions"][0],
                "source_refs": ["U1"],
                "reason": "Synthetic scope revision",
            }
        ]
        self.assertIn(
            "modeling_obligation_changed",
            {e["code"] for e in dialogue(value, previous=old)["errors"]},
        )
        value["changes"].append(
            {
                "id": "drop-model",
                "obligation": "sharing",
                "previous": old["construction"]["obligations"][0],
                "source_refs": ["U1"],
                "reason": "The user removed this modeled capability from the increment",
            }
        )
        self.assertTrue(dialogue(value, previous=old)["valid"])

    def test_unplaced_target_cannot_borrow_unrelated_authority(self):
        from test_construction_contract import target

        value = self.doc()
        value["construction"]["targets"] = [target()]
        value["decisions"][0]["affects"] = ["target:sharing"]
        value["decisions"][0]["routing"]["authority"]["scope_refs"] = ["object:actor"]
        self.assertIn("authority_scope_mismatch", {e["code"] for e in dialogue(value)["errors"]})

    def test_partial_answer_does_not_approve_the_model(self):
        value = self.doc()
        value["decisions"][0].update(
            status="contradicted",
            answers=[
                {
                    "id": "A1",
                    "kind": "contradiction",
                    "source_refs": ["U1"],
                    "affects": ["read"],
                    "text": "That is not what I meant by revoke",
                }
            ],
        )
        show_all(value)
        report = dialogue(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["ready"])
        self.assertEqual(value["confirmations"], [])

    def test_future_implementation_and_optional_analysis_work_stays_recorded(self):
        value = self.doc()
        source = question("F", "implementation_fact", "agent")
        source["routing"]["stage"] = "during_coding"
        analysis = question("A", "analysis_assumption", "human")
        analysis["routing"]["stage"] = "before_analysis"
        value["decisions"] += [source, analysis]
        initial = dialogue(value, stage="before_implementation")
        self.assertTrue(initial["valid"], initial["errors"])
        self.assertEqual(initial["routing"]["deferred_decisions"], ["A", "F"])
        self.assertNotIn("decision:F", initial["blocked"])
        delivery = dialogue(value)
        self.assertEqual(delivery["routing"]["deferred_decisions"], ["A"])
        self.assertNotIn("decision:A", delivery["blocked"])
        optional = dialogue(value, stage="before_analysis")
        self.assertIn("A", [q["id"] for q in optional["questions"]])

    def test_business_meaning_cannot_be_postponed_to_optional_analysis(self):
        value = self.doc()
        value["decisions"][0]["routing"]["stage"] = "before_analysis"
        self.assertFalse(dialogue(value)["valid"])

    def test_conditional_free_text_needs_structured_choice_before_branching(self):
        from bo_observer.concepts.decision_contract import condition_state

        first = question()
        first.update(
            status="resolved",
            resolution={"text": "Maybe", "kind": "user_answer", "source_refs": ["U1"]},
        )
        child = question("D2")
        child["routing"]["when"] = [{"decision": "D1", "choice": "yes"}]
        self.assertEqual(condition_state(child, {"D1": first, "D2": child}), "waiting")
        value = self.doc()
        value["sources"].append(
            {
                "id": "A",
                "kind": "assistant",
                "text": "Assume architect",
                "locator": "synthetic inference",
            }
        )
        value["participation"] = {"knowledge_domains": ["architecture"], "source_refs": ["A"]}
        self.assertFalse(dialogue(value)["valid"])


class GuidedConstructionScopeTests(unittest.TestCase):
    def test_later_target_does_not_block_confirmed_independent_increment(self):
        value = inventory()
        value["construction"]["targets"].append(
            {
                "id": "target:preferences-state",
                "kind": "state_model",
                "meaning": "A later account lifecycle",
                "source_refs": ["U1"],
                "scope_refs": ["business-network:account"],
                "unresolved": ["Identify state owner"],
            }
        )
        show_all(value)
        value["confirmations"].append(
            confirm(value, ["business-network:sharing"], ["U1"], "C1", presentation_ref="P1")
        )
        report = assess(value, scope=["business-network:sharing"])
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["ready"], report["blocked"])
        self.assertEqual(
            [x["id"] for x in report["construction"]["deferred_gaps"]], ["target:preferences-state"]
        )
        self.assertFalse(assess(value, scope=["*"])["ready"])

    def test_later_question_uses_same_target_scope(self):
        value = inventory()
        value["scope"] = ["business-network:sharing"]
        value["construction"]["targets"].append(
            {
                "id": "target:preferences-state",
                "kind": "state_model",
                "meaning": "A later account lifecycle",
                "source_refs": ["U1"],
                "scope_refs": ["business-network:account"],
                "unresolved": ["Identify state owner"],
            }
        )
        value["decisions"] = [
            {
                "id": "D-later",
                "topic": "scope",
                "status": "open",
                "blocking": True,
                "question": "Which account owns the preferences?",
                "why": "Clarify the requested owner",
                "source_refs": ["U1"],
                "affects": ["target:preferences-state"],
            }
        ]
        report = dialogue(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["questions"], [])
        self.assertNotIn("decision:D-later", report["blocked"])

    def test_target_scope_cycles_are_rejected(self):
        value = document()
        for name, other in [("a", "b"), ("b", "a")]:
            value["construction"]["targets"].append(
                {
                    "id": "target:" + name,
                    "kind": "state_model",
                    "meaning": "Pending owner",
                    "source_refs": ["U1"],
                    "scope_refs": ["target:" + other],
                    "unresolved": ["Owner"],
                }
            )
        report = assess(value)
        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"][0]["code"], "construction_scope_cycle")


class ConstructionReviewTests(unittest.TestCase):
    def test_inventory_and_single_model_preview_share_canonical_ids(self):
        from bo_observer.workflow.construction_review import workbook

        value = inventory()
        report = dialogue(value)
        for model in ("business-network:sharing", "state-model:grant", "policy-operation:read"):
            result = workbook(value, report, model_ref=model, max_nodes=3, locale="zh-CN")
            self.assertEqual(result["preview"]["model_ref"], model)
            self.assertEqual(len(result["preview"]["focus"]["nodes"]), 3)
            self.assertTrue(result["preview"]["omitted_refs"])
            original_ids = {n["id"] for n in build(value)["graph"]["nodes"]}
            self.assertTrue(set(result["preview"]["visible_refs"]) <= set(snapshot(value)["scope"]))
            self.assertTrue({n["id"] for n in result["preview"]["focus"]["nodes"]} <= original_ids)
            self.assertFalse(result["preview"]["presentation_recorded"])
            self.assertEqual(value["confirmations"], [])
            self.assertEqual({m["binding"] for m in result["models"]}, {"not_checked"})
        roots = {m["model_ref"] for m in result["models"]}
        self.assertIn("business-network:account", roots)
        self.assertEqual(len([r for r in roots if r.startswith("policy-operation:")]), 2)

    def test_empty_question_list_cannot_clear_omitted_relation(self):
        from bo_observer.workflow.construction_review import workbook

        value = inventory()
        value["construction"]["obligations"].append(
            {
                "id": "branch",
                "kind": "relation",
                "meaning": "The requested route to preferences",
                "source_refs": ["U1"],
                "from_ref": "share",
                "to_ref": "preferences",
                "relation": "flow",
            }
        )
        result = workbook(value, dialogue(value))
        self.assertEqual(result["questions"], [])
        self.assertIn("branch", [g["id"] for g in result["gaps"]])
        self.assertFalse(
            any(
                e["from"] == "share" and e["to"] == "preferences"
                for e in result["preview"]["focus"]["edges"]
            )
        )

    def test_source_free_target_has_no_fake_runtime_node(self):
        from bo_observer.workflow.construction_review import workbook, markdown
        from test_construction_contract import target

        value = document()
        for name in (
            "networks",
            "objects",
            "facts",
            "state_models",
            "crosslinks",
            "applicability",
            "expectations",
        ):
            value[name] = []
        value.pop("policy", None)
        value["construction"]["targets"] = [target()]
        result = workbook(value, dialogue(value))
        self.assertEqual(result["models"], [])
        self.assertIsNone(result["preview"])
        self.assertIn("Still to model:", markdown(result))

    def test_review_cli_writes_portable_report_without_confirming(self):
        from bo_observer.workflow.concept_cli import main
        from contextlib import redirect_stdout
        from pathlib import Path
        import tempfile
        import json
        import io

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "discovery.json"
            value = inventory()
            path.write_text(json.dumps(value), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as output:
                result = main(
                    [
                        "review",
                        "--root",
                        folder,
                        "--review-model",
                        "state-model:grant",
                        "--locale",
                        "zh-CN",
                        "--url",
                        "http://127.0.0.1:8797/graph",
                        "--out",
                        "review/model.json",
                    ]
                )
            self.assertEqual(result, 0, output.getvalue())
            stored = json.loads((Path(folder) / "review/model.json").read_text(encoding="utf-8"))
            self.assertIn("flowchart LR", stored["markdown"])
            self.assertIn("http://127.0.0.1:8797/graph", stored["markdown"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), value)
            self.assertNotIn("focus", json.loads(output.getvalue())["preview"])


if __name__ == "__main__":
    unittest.main()
