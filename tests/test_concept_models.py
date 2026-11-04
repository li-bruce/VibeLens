"""Concept-first contracts: meaning, provenance, native bindings and view metadata.

The synthetic conversation fixture is deliberately unconfirmed on disk. Tests
record simulated assent explicitly, then mutate one semantic or physical fact at
a time. A green graph alone cannot satisfy these checks.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/vibelens"
sys.path.insert(0, str(SKILL / "scripts"))

from bo_observer import concepts  # noqa: E402
from bo_observer.policy.projection import project  # noqa: E402


def draft():
    """Read the distributable design example without mutating the shared asset."""
    return json.loads(
        (SKILL / "assets/discovery.concepts.example.json").read_text(encoding="utf-8")
    )


def approve(document, scope=None, source="U1", identity="C1"):
    document["confirmations"].append(concepts.confirm(document, scope or ["*"], [source], identity))
    return document


def codes(report):
    return {item["code"] for item in report["errors"]}


def activity_draft():
    """Use the native run-scoped capacity and ALL-join semantics before coding."""
    document = draft()
    state = document["state_models"][0]
    state["guards"]["checks_complete"] = {
        "meaning": "All declared checks completed",
        "source_refs": ["U1"],
    }
    state["transitions"][0]["conditions"].append("checks_complete")
    state["execution"] = {
        "schema": "activity-graph/v1",
        "within": "inactive",
        "parent": "share",
        "activity_states": [
            "pending",
            "waiting",
            "running",
            "succeeded",
            "rejected",
            "failed",
            "cancelled",
        ],
        "activities": [
            {"id": "scan", "requires": {"workers": 1}},
            {"id": "index", "requires": {"workers": 1}},
        ],
        "resources": [
            {"id": "workers", "scope": "run", "capacity_field": "workers", "min": 1, "max": 2}
        ],
        "join": {
            "id": "checks",
            "policy": "all",
            "requires": ["scan", "index"],
            "success_event": "share",
            "success_states": ["active"],
            "guard": "checks_complete",
        },
    }
    return document


def bound_fixture():
    """Return a small native declaration with real policy projection identities.

    Source validation and event execution are tested by the integration suite.
    This fixture exercises exact semantic and physical mapping contracts without
    interpreting source labels as proof that a function executed.
    """
    document = approve(draft())

    def source(name):
        return {"path": "sharing.py", "symbol": name}

    state = document["state_models"][0]
    machine = {
        "engine": "bo.fsm",
        "version": "1",
        "state_type": "enum",
        "states": deepcopy(state["states"]),
        "values": deepcopy(state["states"]),
        "initial": state["initial"],
        "events": deepcopy(state["events"]),
        "context": {},
        "guards": {"may_manage": {"source": source("same_identity")}},
        "transitions": [
            {
                key: deepcopy(value)
                for key, value in item.items()
                if key in {"source", "dest", "trigger", "conditions", "unless"}
            }
            for item in state["transitions"]
        ],
    }
    policy = deepcopy(document["policy"])
    policy["stage"] = "bound"
    policy["predicates"][0]["source"] = source("same_identity")
    for operation in policy["operations"]:
        operation["business_nodes"] = (
            ["native:read"] if operation["id"] == "read" else ["native:share", "native:revoke"]
        )
        operation["cases"] = ["roundtrip"]
    nodes = [
        {
            "id": "native:" + name,
            "kind": "action",
            "source": source(name),
            "capture": {"in": {}, "out": {}},
        }
        for name in ["share", "read", "revoke"]
    ]
    nodes += [
        {"id": "native:state:" + name, "kind": "state", "value": name, "capture": {}}
        for name in state["states"]
    ]
    nodes.append(
        {
            "id": "native:context",
            "kind": "data",
            "source": source("load_context"),
            "capture": {
                "in": {},
                "out": {
                    "id": "string",
                    "owner_id": "string",
                    "recipient_id": "string",
                    "active": "boolean",
                },
            },
        }
    )
    model = project({"nodes": nodes, "edges": [], "machine": machine, "policy": policy})
    for name in ["actor", "owner", "recipient", "active"]:
        model["edges"].append(
            {"id": "fact:" + name, "from": "native:context", "to": "policy:" + name, "type": "data"}
        )
    crosslinks = {
        "share-requests-event": {
            "relation": "action_requests_event",
            "from": ["native:share"],
            "to": ["native:share"],
            "native_event": "share",
            "edges": [],
        },
        "revoke-requests-event": {
            "relation": "action_requests_event",
            "from": ["native:revoke"],
            "to": ["native:revoke"],
            "native_event": "revoke",
            "edges": [],
        },
        "share-guard": ["policy:operation:manage:native:share"],
        "revoke-guard": ["policy:operation:manage:native:revoke"],
        "read-actor-id": ["fact:actor"],
        "read-owner-id": ["fact:owner"],
        "read-recipient-id": ["fact:recipient"],
        "read-active-grant": ["fact:active"],
    }
    binding = {
        "schema": "bo-concept-bindings/v1",
        "semantic_revision": concepts.assess(document)["semantic_revision"],
        "primary_state_model": "grant",
        "objects": {"grant": deepcopy(state["subject"])},
        "business": {name: ["native:" + name] for name in ["share", "read", "revoke"]},
        "facts": {
            fact["id"]: [
                {
                    "node": "native:context",
                    "direction": "out",
                    "field": fact["field"],
                    "basis_checks": [{"case": "roundtrip", "path": ["reads", fact["id"]]}],
                }
            ]
            for fact in document["facts"]
        },
        "expectations": {"grant-roundtrip": ["roundtrip"]},
        "crosslinks": crosslinks,
        "events": {
            "event:grant:" + name: {"node": "native:" + name, "event": name}
            for name in ["share", "revoke"]
        },
    }
    model["concepts"] = binding
    acceptance = {"checks": [{"case": "roundtrip", "path": ["state"], "equals": "inactive"}]}
    for fact in document["facts"]:
        acceptance["checks"].append(
            {
                "case": "roundtrip",
                "path": ["reads", fact["id"]],
                "equals": {
                    "node": "native:context",
                    "direction": "out",
                    "field": fact["field"],
                    "read_basis": deepcopy(fact["read_basis"]),
                },
            }
        )
    for index, check in enumerate(acceptance["checks"]):
        check.update(id="observation-" + str(index), requirement="sharing")
    return document, model, acceptance


class ConceptDesignTests(unittest.TestCase):
    def test_activity_capacity_waiting_and_join_are_in_the_state_projection(self):
        document = activity_draft()
        report = concepts.assess(document)
        self.assertTrue(report["valid"], report)
        nodes = {node["id"]: node for node in report["graph"]["nodes"]}
        for ident in [
            "activity:grant:scan",
            "activity:grant:index",
            "resource:grant:workers",
            "join:grant:checks",
        ]:
            self.assertEqual(nodes[ident]["layer"], "state")
            self.assertNotIn("source", nodes[ident])
        allocations = [edge for edge in report["graph"]["edges"] if edge["type"] == "resource"]
        self.assertEqual(len(allocations), 2)
        self.assertTrue(all(edge["units"] == 1 for edge in allocations))

    def test_activity_design_rejects_invalid_capacity_scope_members_and_completion(self):
        mutations = [
            lambda execution: execution.update(schema="unknown/v1"),
            lambda execution: execution.update(within="missing"),
            lambda execution: execution["resources"][0].update(min=0),
            lambda execution: execution["resources"][0].update(max=True),
            lambda execution: execution["resources"][0].update(scope="global"),
            lambda execution: execution["activities"][0].update(requires={"workers": 2}),
            lambda execution: execution["activities"][0].update(requires={"missing": 1}),
            lambda execution: execution["join"].update(requires=["scan"]),
            lambda execution: execution["join"].update(guard="unknown"),
            lambda execution: execution["join"].update(success_event="missing"),
            lambda execution: execution["join"].update(success_states=["missing"]),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                document = activity_draft()
                mutation(document["state_models"][0]["execution"])
                self.assertFalse(concepts.assess(document)["valid"])
        document = activity_draft()
        document["state_models"][0]["transitions"][0]["conditions"].remove("checks_complete")
        self.assertFalse(concepts.assess(document)["valid"])

    def test_unconfirmed_source_free_design_has_three_connected_peer_views(self):
        result = concepts.assess(draft())
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["ready"])
        graph = result["graph"]
        self.assertEqual({node["layer"] for node in graph["nodes"]}, {"business", "state", "rules"})
        connected = {edge[key] for edge in graph["edges"] for key in ["from", "to"]}
        self.assertTrue(all(node["id"] in connected for node in graph["nodes"]))
        self.assertFalse(any("source" in node for node in graph["nodes"]))
        self.assertEqual(sum(node["id"] == "policy:actor" for node in graph["nodes"]), 1)

    def test_real_confirmation_is_required_and_inference_is_rejected(self):
        document = draft()
        document["sources"][0]["kind"] = "assistant"
        with self.assertRaisesRegex(ValueError, "actual recorded user"):
            approve(document)
        self.assertTrue(concepts.assess(approve(draft()))["ready"])

    def test_labels_and_source_locations_do_not_change_meaning(self):
        before = approve(draft())
        after = deepcopy(before)
        after["networks"][0]["nodes"][0]["label"] = "Share with colleague"
        after["policy"]["predicates"][0]["source"] = {"path": "new.py", "symbol": "is_same"}
        self.assertFalse(concepts.diff(before, after)["semantic_change"])
        self.assertTrue(concepts.assess(after, previous=before)["ready"])

    def test_business_meaning_rule_operator_and_read_basis_invalidate_confirmation(self):
        for change in [
            lambda doc: doc["networks"][0]["nodes"][0].update(meaning="Share with every employee"),
            lambda doc: doc["policy"]["nodes"][-1].update(op="any"),
            lambda doc: doc["facts"][-1]["read_basis"].update(timing="cached_at_login"),
        ]:
            with self.subTest(change=change):
                before = approve(draft())
                after = deepcopy(before)
                change(after)
                result = concepts.assess(after, previous=before)
                self.assertTrue(result["valid"], result)
                self.assertFalse(result["ready"])
                self.assertTrue(result["changes"]["semantic_change"])

    def test_previous_user_source_cannot_approve_a_different_snapshot(self):
        before = approve(draft())
        after = deepcopy(before)
        after["policy"]["nodes"][-1]["op"] = "any"
        approve(after, identity="C2")
        self.assertIn(
            "changed_meaning_needs_new_user_source", codes(concepts.assess(after, previous=before))
        )
        self.assertIn("changed_meaning_needs_new_user_source", codes(concepts.assess(after)))

    def test_boolean_and_integer_outcomes_have_distinct_confirmed_meaning(self):
        before = draft()
        before["expectations"][0]["then"][0]["equals"] = False
        approve(before)
        after = deepcopy(before)
        after["expectations"][0]["then"][0]["equals"] = 0
        result = concepts.assess(after, previous=before)
        self.assertTrue(result["changes"]["semantic_change"])
        self.assertFalse(result["ready"])

    def test_metadata_names_inside_domain_values_are_not_erased(self):
        for field in [
            "label",
            "summary",
            "description",
            "source_refs",
            "documentation",
            "presentation",
        ]:
            with self.subTest(field=field):
                before = draft()
                before["networks"][0]["nodes"][0]["meaning"] = {field: {"nested": False}}
                before["expectations"][0]["then"][0]["equals"] = {field: {"nested": False}}
                approve(before)
                after = deepcopy(before)
                after["networks"][0]["nodes"][0]["meaning"][field]["nested"] = 0
                after["expectations"][0]["then"][0]["equals"][field]["nested"] = 0
                result = concepts.assess(after, previous=before)
                changed = {item["id"] for item in result["changes"]["changed"]}
                self.assertIn("share", changed)
                self.assertIn("expectation:grant-roundtrip", changed)
                self.assertFalse(result["ready"])

    def test_predicate_parameter_names_named_label_remain_semantic(self):
        document = draft()
        document["policy"]["predicates"][0]["parameters"] = {
            "label": "string",
            "description": "string",
        }
        for item in document["policy"]["nodes"]:
            if item["op"] == "predicate":
                arguments = item["arguments"]
                item["arguments"] = {"label": arguments["left"], "description": arguments["right"]}
        record = concepts.snapshot(document)["records"]["policy-predicate:same_identity"]
        self.assertEqual(record["parameters"], {"label": "string", "description": "string"})
        self.assertEqual(
            concepts.policy_semantics(document["policy"])["predicates"][0]["parameters"],
            record["parameters"],
        )

    def test_activity_metadata_does_not_remove_resource_names_or_change_approval(self):
        before = activity_draft()
        execution = before["state_models"][0]["execution"]
        execution["resources"][0].update(id="label", min=2)
        for activity in execution["activities"]:
            activity["requires"] = {"label": 1}
        approve(before)
        after = deepcopy(before)
        after["state_models"][0]["execution"]["activities"][0]["label"] = "Scan the selected file"
        self.assertFalse(concepts.diff(before, after)["semantic_change"])
        self.assertTrue(concepts.assess(after, previous=before)["ready"])
        after["state_models"][0]["execution"]["activities"][0]["requires"]["label"] = 2
        self.assertFalse(concepts.assess(after, previous=before)["ready"])

    def test_default_relation_labels_are_readable_without_changing_types(self):
        graph = concepts.assemble(draft())
        edge = next(item for item in graph["edges"] if item["id"] == "read-actor-id")
        self.assertEqual(edge["type"], "decision_reads_fact")
        self.assertEqual(edge["label"], "Reads")

    def test_shared_dependency_review_survives_narrowing_active_scope(self):
        before = approve(draft())
        after = deepcopy(before)
        after["scope"] = ["share"]
        after["policy"]["predicates"][0]["parameters"]["left"] = "string"
        after["facts"][0]["read_basis"]["timing"] = "cached_at_login"
        result = concepts.assess(after, previous=before)
        self.assertFalse(result["ready"])
        self.assertIn("read", result["coverage_scope"])
        self.assertIn("read", result["confirmation"]["shared_dependents_requiring_review"])

    def test_immutable_history_cannot_be_rewritten(self):
        before = approve(draft())
        after = deepcopy(before)
        after["confirmations"][0]["scope"] = ["share"]
        self.assertIn(
            "immutable_confirmation_changed", codes(concepts.assess(after, previous=before))
        )
        after = deepcopy(before)
        after["sources"][0]["text"] = "Edited after approval"
        self.assertIn("confirmation_source_changed", codes(concepts.assess(after, previous=before)))

    def test_state_read_has_no_fake_event_and_state_change_requires_one(self):
        document = draft()
        reading = next(item for item in document["applicability"] if item["operation"] == "read")
        self.assertEqual(reading["state"]["mode"], "read")
        reading["state"]["mode"] = "change"
        self.assertFalse(concepts.assess(document)["valid"])
        document = draft()
        document["applicability"][0]["state"]["mode"] = "read"
        self.assertFalse(concepts.assess(document)["valid"])

    def test_invalid_state_transition_and_rule_cycle_fail_before_source_exists(self):
        document = draft()
        document["state_models"][0]["transitions"][0]["dest"] = "missing"
        self.assertFalse(concepts.assess(document)["valid"])
        document = draft()
        document["policy"]["nodes"][-1]["inputs"] = ["may_read", "active"]
        self.assertFalse(concepts.assess(document)["valid"])

    def test_ambiguous_alias_never_selects_an_arbitrary_object(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            concepts.resolve(draft(), "grant")
        self.assertEqual(concepts.resolve(draft(), "object:grant"), "object:grant")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            concepts.snapshot(draft(), [])

    def test_legacy_migration_requires_new_explicit_confirmation(self):
        legacy = {"schema": "business-discovery/v1", "confirmations": []}
        self.assertFalse(concepts.assess(legacy)["ready"])
        result = concepts.assess(draft(), previous=legacy)
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["ready"])
        self.assertIn(
            "legacy_migration_requires_fresh_confirmation",
            {item["code"] for item in result["warnings"]},
        )
        self.assertTrue(result["changes"]["semantic_change"])
        self.assertEqual(concepts.diff(legacy, draft())["migration"], "legacy-v1")

    def test_scoped_action_does_not_approve_unrelated_future_actions(self):
        document = draft()
        future = {
            "id": "future",
            "kind": "action",
            "label": "Future draft",
            "meaning": "An unrelated future action",
            "source_refs": ["U1"],
        }
        document["networks"][0]["nodes"].append(future)
        document["applicability"].append(
            {
                "operation": "future",
                "state": {"status": "none", "reason": "No stored state"},
                "rules": {"status": "none", "reason": "No permission decision"},
                "source_refs": ["U1"],
            }
        )
        document["scope"] = ["share"]
        approve(document, ["share"])
        result = concepts.assess(document)
        self.assertTrue(result["ready"], result)
        self.assertNotIn("future", result["coverage_scope"])
        self.assertFalse(concepts.assess(document, scope=["future"])["ready"])

    def test_removing_confirmed_work_cannot_hide_under_a_narrower_scope(self):
        document = draft()
        document["networks"][0]["nodes"].append(
            {
                "id": "extra",
                "kind": "action",
                "label": "Extra",
                "meaning": "Previously agreed independent work",
                "source_refs": ["U1"],
            }
        )
        document["applicability"].append(
            {
                "operation": "extra",
                "state": {"status": "none", "reason": "No state"},
                "rules": {"status": "none", "reason": "No rule"},
                "source_refs": ["U1"],
            }
        )
        before = approve(document)
        after = deepcopy(before)
        after["networks"][0]["nodes"].pop()
        after["applicability"].pop()
        after["scope"] = ["share"]
        result = concepts.assess(after, previous=before)
        self.assertIn("retired:extra", result["blocked"])
        after["sources"].append(
            {
                "id": "U2",
                "kind": "user",
                "text": "Synthetic user: remove the extra action; I confirm the updated complete graph.",
                "locator": "Synthetic removal acknowledgment",
            }
        )
        approve(after, ["*"], "U2", "C2")
        self.assertTrue(concepts.assess(after, previous=before)["ready"])


class ConceptBindingTests(unittest.TestCase):
    def check(self, document, model, acceptance):
        return concepts.check_binding(document, model, acceptance=acceptance)

    def test_confirmed_design_binds_native_machine_policy_and_independent_cases(self):
        document, model, acceptance = bound_fixture()
        result = self.check(document, model, acceptance)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["bound_state_models"], ["grant"])

    def test_activity_design_binds_original_native_resources_and_join(self):
        _, model, acceptance = bound_fixture()
        document = approve(activity_draft())
        designed = document["state_models"][0]
        machine = model["machine"]
        machine["engine"] = "python.explicit"
        machine["transitions"][0]["conditions"].append("checks_complete")
        machine["guards"]["checks_complete"] = {
            "source": {"path": "sharing.py", "symbol": "checks_complete"}
        }
        machine["execution"] = deepcopy(designed["execution"])
        machine["execution"]["parent"] = "native:share"
        for item in machine["execution"]["activities"]:
            item["source"] = {"path": "sharing.py", "symbol": item["id"]}
            model["nodes"].append(
                {
                    "id": item["id"],
                    "kind": "function",
                    "source": deepcopy(item["source"]),
                    "parent": "native:share",
                    "execution_role": "activity",
                }
            )
            model["edges"].append(
                {
                    "id": "allocate:" + item["id"],
                    "from": "workers",
                    "to": item["id"],
                    "type": "resource",
                    "units": 1,
                }
            )
            model["edges"].append(
                {"id": "complete:" + item["id"], "from": item["id"], "to": "checks", "type": "join"}
            )
        model["nodes"] += [
            {
                "id": "workers",
                "kind": "resource",
                "parent": "native:share",
                "execution_role": "resource",
            },
            {"id": "checks", "kind": "join", "parent": "native:share", "execution_role": "join"},
            {
                "id": "native:complete",
                "kind": "decision",
                "source": {"path": "sharing.py", "symbol": "checks_complete"},
                "capture": {"out": {"value": "boolean"}},
            },
        ]
        model["concepts"]["guards"] = {
            "guard:grant:checks_complete": {
                "node": "native:complete",
                "decision": None,
                "field": "value",
            }
        }
        model["concepts"]["semantic_revision"] = concepts.assess(document)["semantic_revision"]
        report = self.check(document, model, acceptance)
        self.assertTrue(report["valid"], report)
        projection = concepts.bind_projection(document, model, acceptance=acceptance)
        self.assertTrue(
            any(
                edge["from"] == "resource:grant:workers" and edge["to"] == "workers"
                for edge in projection["edges"]
            )
        )
        machine["execution"]["resources"][0]["max"] = 3
        self.assertIn(
            "state_semantics_changed_during_binding", codes(self.check(document, model, acceptance))
        )

    def test_native_transition_priority_and_condition_are_not_erased(self):
        document, model, acceptance = bound_fixture()
        model["machine"]["transitions"][0]["conditions"] = []
        self.assertIn(
            "state_semantics_changed_during_binding", codes(self.check(document, model, acceptance))
        )
        document, model, acceptance = bound_fixture()
        model["machine"]["transitions"].reverse()
        self.assertIn(
            "state_semantics_changed_during_binding", codes(self.check(document, model, acceptance))
        )

    def test_payload_and_context_names_are_preserved_during_native_binding(self):
        for location, field in [("context", "description"), ("payload", "label")]:
            with self.subTest(location=location):
                document, model, acceptance = bound_fixture()
                designed = document["state_models"][0]
                design_fields = (
                    designed["context"]
                    if location == "context"
                    else designed["events"]["share"]["payload"]
                )
                native_fields = (
                    model["machine"]["context"]
                    if location == "context"
                    else model["machine"]["events"]["share"]["payload"]
                )
                specification = {"type": "object", "properties": {"summary": {"type": "boolean"}}}
                design_fields[field] = deepcopy(specification)
                native_fields[field] = deepcopy(specification)
                document["confirmations"] = []
                approve(document)
                model["concepts"]["semantic_revision"] = concepts.assess(document)[
                    "semantic_revision"
                ]
                self.assertTrue(self.check(document, model, acceptance)["valid"])
                native_fields[field]["properties"]["summary"]["type"] = "integer"
                self.assertIn(
                    "state_semantics_changed_during_binding",
                    codes(self.check(document, model, acceptance)),
                )

    def test_literal_expected_metadata_keys_are_checked_with_json_types(self):
        document, model, acceptance = bound_fixture()
        assertion = {"path": ["payload"], "equals": {"label": {"description": False}}}
        document["expectations"][0]["then"] = [deepcopy(assertion)]
        acceptance["checks"][0].update(deepcopy(assertion))
        document["confirmations"] = []
        approve(document)
        model["concepts"]["semantic_revision"] = concepts.assess(document)["semantic_revision"]
        self.assertTrue(self.check(document, model, acceptance)["valid"])
        acceptance["checks"][0]["equals"]["label"]["description"] = 0
        self.assertIn(
            "independent_expected_assertion_differs", codes(self.check(document, model, acceptance))
        )

    def test_same_rule_ids_with_different_operator_do_not_pass(self):
        document, model, acceptance = bound_fixture()
        model["policy"]["nodes"][-1]["op"] = "any"
        self.assertIn(
            "rule_semantics_changed_during_binding", codes(self.check(document, model, acceptance))
        )

    def test_guard_name_alone_is_not_a_native_function_binding(self):
        document, model, acceptance = bound_fixture()
        model["machine"]["guards"]["may_manage"]["source"]["symbol"] = "always_true"
        self.assertIn("unbound_native_guard", codes(self.check(document, model, acceptance)))

    def test_crosslink_requires_matching_endpoint_and_relation_not_an_existing_edge_id(self):
        document, model, acceptance = bound_fixture()
        model["concepts"]["crosslinks"]["share-guard"] = ["policy:operation:manage:native:revoke"]
        self.assertIn(
            "crosslink_native_edge_meaning_differs", codes(self.check(document, model, acceptance))
        )
        document, model, acceptance = bound_fixture()
        edge = next(item for item in model["edges"] if item["id"] == "fact:actor")
        edge["type"] = "flow"
        self.assertIn(
            "crosslink_native_edge_meaning_differs", codes(self.check(document, model, acceptance))
        )

    def test_case_name_without_exact_independent_assertion_fails(self):
        document, model, acceptance = bound_fixture()
        self.assertIn("missing_independent_acceptance", codes(self.check(document, model, None)))
        acceptance["checks"][0]["equals"] = "active"
        self.assertIn(
            "independent_expected_assertion_differs", codes(self.check(document, model, acceptance))
        )

    def test_fact_capture_type_is_checked_against_the_declared_object_field(self):
        document, model, acceptance = bound_fixture()
        next(item for item in model["nodes"] if item["id"] == "native:context")["capture"]["out"][
            "active"
        ] = "string"
        self.assertIn("fact_capture_type_differs", codes(self.check(document, model, acceptance)))

    def test_fact_read_basis_requires_independent_capture_specific_observation(self):
        document, model, acceptance = bound_fixture()
        acceptance["checks"][1]["equals"]["read_basis"]["timing"] = "cached_at_login"
        self.assertIn(
            "fact_read_basis_assertion_differs", codes(self.check(document, model, acceptance))
        )
        document, model, acceptance = bound_fixture()
        acceptance["checks"][1]["equals"]["node"] = "unrelated:reader"
        self.assertIn(
            "fact_read_basis_assertion_differs", codes(self.check(document, model, acceptance))
        )

    def test_business_binding_cannot_point_to_a_state_or_sourceless_label(self):
        document, model, acceptance = bound_fixture()
        model["concepts"]["business"]["read"] = ["native:state:active"]
        self.assertIn(
            "business_binding_lacks_native_operation",
            codes(self.check(document, model, acceptance)),
        )
        document, model, acceptance = bound_fixture()
        next(item for item in model["nodes"] if item["id"] == "native:read").pop("source")
        self.assertIn(
            "business_binding_lacks_native_operation",
            codes(self.check(document, model, acceptance)),
        )

    def test_business_condition_requires_an_explicit_structural_binding(self):
        document, model, acceptance = bound_fixture()
        document["networks"][0]["nodes"].append(
            {
                "id": "business-condition",
                "kind": "condition",
                "label": "Can read",
                "meaning": "Recipient has access",
                "source_refs": ["U1"],
            }
        )
        document["confirmations"] = []
        approve(document)
        model["concepts"]["semantic_revision"] = concepts.assess(document)["semantic_revision"]
        self.assertIn("unbound_business_concept", codes(self.check(document, model, acceptance)))
        model["concepts"]["business"]["business-condition"] = ["policy:may_read"]
        self.assertTrue(self.check(document, model, acceptance)["valid"])

    def test_projection_does_not_mutate_executor_or_manufacture_observations(self):
        document, model, acceptance = bound_fixture()
        original = deepcopy(model)
        view = concepts.bind_projection(document, model, acceptance=acceptance)
        self.assertEqual(model, original)
        self.assertFalse(view["execution_authority"])
        self.assertNotIn("events", view)
        maps = [edge for edge in view["edges"] if edge.get("origin") == "concept-binding"]
        self.assertTrue(maps)
        self.assertTrue(all(edge["observed"] is False for edge in maps))
        self.assertIn("state:grant:active", {node["id"] for node in view["nodes"]})

    def test_scoped_increment_can_bind_without_implementing_unselected_rule(self):
        document, model, acceptance = bound_fixture()
        document["confirmations"] = []
        document["scope"] = ["share"]
        approve(document, ["share"])
        excluded = {"recipient", "active", "is_recipient", "may_read"}
        model["policy"]["operations"] = [
            item for item in model["policy"]["operations"] if item["id"] == "manage"
        ]
        model["policy"]["nodes"] = [
            item for item in model["policy"]["nodes"] if item["id"] not in excluded
        ]
        model = project(model)
        model["concepts"]["semantic_revision"] = concepts.assess(document)["semantic_revision"]
        result = self.check(document, model, acceptance)
        self.assertTrue(result["valid"], result)
        self.assertNotIn("read", result["scope"])

        from bo_observer.workflow.requirements_dialogue import assess as assess_dialogue

        reviewed = assess_dialogue(document, model=model, acceptance=acceptance)
        self.assertTrue(reviewed["ready"], reviewed["errors"])

    def test_malformed_native_anchor_is_a_validation_error(self):
        document, model, acceptance = bound_fixture()
        model["concepts"]["events"]["event:grant:share"]["node"] = ["native:share"]
        self.assertIn("invalid_concept_bindings", codes(self.check(document, model, acceptance)))


if __name__ == "__main__":
    unittest.main()
