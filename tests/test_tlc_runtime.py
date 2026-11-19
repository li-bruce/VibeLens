"""Actual optional TLC executions; independent expectations cover supported semantics."""

from copy import deepcopy
import os
from pathlib import Path
import tempfile
import threading
import unittest

import test_analysis_admission as admission_fixture
from test_behavior_contract import literal, variable, operation
from test_behavior_evidence import snapshot
from bo_observer.analysis.runner import run_profile
from bo_observer.analysis.tla.results import parse_output, value
from bo_observer.analysis.tla.toolchain import resolve
from bo_observer.analysis.artifacts import verify_attempt, collect
from test_analysis_collections import queue_fixture


def finite_fixture():
    fixture = admission_fixture.AdmissionTests()
    fixture.setUp()
    result = snapshot()
    result.update(
        behavior=fixture.contract,
        behavior_discovery=fixture.discovery,
        analysis_profiles=[fixture.profile],
    )
    return result


@unittest.skipUnless(
    os.environ.get("VIBELENS_TLC_JAR"), "Optional real TLC distribution not selected"
)
class TLCExecutions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snap = finite_fixture()
        self.contract = self.snap["behavior"]
        self.profile = self.snap["analysis_profiles"][0]

    def run_model(self, **kwargs):
        result = run_profile(self.root, self.snap, "small", **kwargs)
        evidence = os.environ.get("VIBELENS_TLC_EVIDENCE_DIR")
        if evidence:
            import shutil

            destination = Path(evidence) / self._testMethodName / result["id"]
            shutil.copytree(
                self.root / result["directory"],
                destination,
                ignore=shutil.ignore_patterns("states", "tmp"),
            )
        return result

    def invariant(self, expression):
        self.contract["properties"][0].update(
            kind="state_invariant", action_refs=[], expression=expression
        )

    def test_two_models_preserve_other_state(self):
        result = self.run_model()
        self.assertEqual(result["status"], "pass", result["results"])
        self.assertEqual(result["results"][0]["stats"]["queued"], 0)
        self.assertEqual(result["results"][0]["stats"]["distinct"], 17)

    def test_counterexample_retains_physical_values_and_action(self):
        self.invariant(operation("eq", variable(), literal("inactive", "status")))
        result = self.run_model()
        self.assertEqual(result["status"], "fail", result)
        trace = result["results"][0]["trace"]
        self.assertEqual(trace["states"][-1]["grant-status"], "active")
        self.assertEqual(trace["steps"][-1]["action"], "grant-share")
        self.assertNotIn("time", trace)

    def test_after_state_constraint_is_checked_after_canonical_update(self):
        self.contract["properties"][0]["expression"] = operation(
            "eq", variable(phase="after"), literal("inactive", "status")
        )
        result = self.run_model()
        self.assertEqual(result["status"], "fail", result)

    def test_deadlock_and_declared_termination_are_distinct(self):
        for action in self.contract["actions"]:
            action["enabled"] = literal(False)
        result = self.run_model()
        self.assertEqual(result["results"][0]["reason"], "deadlock", result)
        self.profile["termination"] = {
            "condition": literal(True),
            "source_refs": ["U1"],
        }
        self.assertEqual(self.run_model()["status"], "pass")

    def test_cancelled_process_retains_incomplete_result(self):
        cancel = threading.Event()
        cancel.set()
        result = self.run_model(cancel=cancel)
        self.assertEqual(result["status"], "incomplete", result)
        self.assertEqual(result["results"][0]["reason"], "cancelled")

    def test_missing_tool_does_not_create_success_or_change_model(self):
        original = deepcopy(self.snap)
        result = self.run_model(jar=self.root / "absent.jar")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(self.snap, original)

    def test_progress_with_and_without_fairness(self):
        prop = self.contract["properties"][0]
        prop.update(
            kind="progress_property",
            action_refs=[],
            trigger=literal(True),
            expression=operation("eq", variable(), literal("active", "status")),
            fairness="none",
            assumption_refs=[],
        )
        result = self.run_model()
        self.assertEqual(result["status"], "fail", result)
        self.assertIsNotNone(result["results"][0]["trace"]["loop_back"])
        self.contract["assumptions"] = [
            {
                "id": "schedule",
                "kind": "scheduling",
                "model_refs": ["state-model:grant"],
                "action_refs": ["grant-share"],
                "statement": "An enabled share is eventually scheduled",
                "status": "confirmed",
                "review_source_refs": ["U1"],
                "source_refs": ["U1"],
                "rationale": "Adopted scheduler behavior",
                "invalidated_by": ["Scheduler cancellation"],
            }
        ]
        prop.update(fairness="weak", assumption_refs=["schedule"])
        self.profile["assumption_refs"] = ["schedule"]
        result = self.run_model()
        self.assertEqual(result["status"], "pass", result)
        prop["fairness"] = "strong"
        self.assertEqual(self.run_model()["status"], "pass")
        self.contract["properties"].append(
            {
                **deepcopy(prop),
                "id": "no-fairness",
                "fairness": "none",
                "assumption_refs": [],
            }
        )
        self.profile["property_refs"].append("no-fairness")
        separate = self.run_model()
        self.assertEqual([r["status"] for r in separate["results"]], ["pass", "fail"])

    def test_fair_cycle_retains_back_to_state_and_closing_action(self):
        self.contract["properties"][0].update(
            kind="progress_property",
            action_refs=[],
            trigger=literal(True),
            expression=literal(False),
            fairness="weak",
            assumption_refs=["schedule"],
        )
        self.contract["assumptions"] = [
            {
                "id": "schedule",
                "kind": "scheduling",
                "model_refs": ["state-model:grant"],
                "action_refs": ["grant-share", "grant-revoke"],
                "statement": "Enabled changes are scheduled",
                "status": "confirmed",
                "review_source_refs": ["U1"],
                "source_refs": ["U1"],
                "rationale": "Adopted scheduler",
                "invalidated_by": ["Scheduler shutdown"],
            }
        ]
        self.profile["assumption_refs"] = ["schedule"]
        result = self.run_model()
        self.assertEqual(result["status"], "fail", result["results"])
        trace = result["results"][0]["trace"]
        self.assertIsNotNone(trace["loop_back"])
        self.assertIsNotNone(trace["steps"][-1]["action"])
        self.assertEqual(trace["states"][-1], trace["states"][trace["loop_back"]])

    def queue(self):
        queued, discovery = queue_fixture()
        for model in discovery["state_models"]:
            for transition in model["transitions"]:
                transition["conditions"] = []
        discovery["crosslinks"] = [
            link
            for link in discovery["crosslinks"]
            if link["relation"] != "transition_guarded_by"
        ]
        self.snap["behavior_discovery"] = discovery
        self.contract["domains"] = queued["domains"] + [
            {
                "id": "size",
                "type": "integer",
                "min": 0,
                "max": 2,
                "bound_origin": "application_limit",
                "source_refs": ["U1"],
            }
        ]
        self.contract["variables"] = queued["variables"]
        self.contract["initial"] = queued["initial"]
        for action in self.contract["actions"]:
            action["unchanged"].append("pending")
        enqueue = queued["actions"][-1]
        enqueue["enabled"] = operation(
            "lt", operation("length", variable("pending")), literal(2, "size")
        )
        dequeue = deepcopy(enqueue)
        dequeue.update(
            id="dequeue",
            parameters={},
            enabled=operation(
                "lt", literal(0, "size"), operation("length", variable("pending"))
            ),
            updates={"pending": operation("tail", variable("pending"))},
        )
        self.contract["actions"] += [enqueue, dequeue]
        return enqueue, dequeue

    def test_fifo_and_capacity_have_explicit_state_and_do_not_clip_next(self):
        enqueue, dequeue = self.queue()
        self.invariant(
            operation(
                "le", operation("length", variable("pending")), literal(2, "size")
            )
        )
        self.assertEqual(self.run_model()["status"], "pass")
        # Removing the physical capacity guard must expose the out-of-domain state.
        enqueue["enabled"] = literal(True)
        failed = self.run_model()
        self.assertEqual(
            failed["results"][0]["reason"], "application_domain_violation", failed
        )
        self.assertEqual(len(failed["results"][0]["trace"]["states"][-1]["pending"]), 3)
        self.profile["bounds"] = {"queue": {"max_items": 2, "origin": "analysis_bound"}}
        bounded = self.run_model()
        self.assertEqual(bounded["status"], "incomplete", bounded)
        self.assertEqual(bounded["results"][0]["reason"], "analysis_domain_exceeded")

    def test_set_resource_capacity_and_holder_identity(self):
        enqueue, dequeue = self.queue()
        domain = next(d for d in self.contract["domains"] if d["id"] == "queue")
        domain["type"] = "set"
        enqueue["updates"]["pending"] = operation(
            "set_add", variable("pending"), {"op": "param", "id": "payload"}
        )
        dequeue["parameters"] = {"payload": "flag"}
        dequeue["updates"]["pending"] = operation(
            "set_remove", variable("pending"), {"op": "param", "id": "payload"}
        )
        self.invariant(
            operation(
                "le", operation("length", variable("pending")), literal(2, "size")
            )
        )
        self.assertEqual(self.run_model()["status"], "pass")

    def test_empty_initial_range_is_not_an_exhaustive_pass(self):
        self.queue()
        self.contract["initial"]["args"][-1] = operation(
            "lt", operation("length", variable("pending")), literal(0, "size")
        )
        result = self.run_model()
        self.assertEqual(result["status"], "error", result)
        self.assertEqual(result["results"][0]["reason"], "empty_initial")

    def test_frozen_result_is_reparsed_and_changes_invalidate(self):
        import json

        result = self.run_model()
        folder = self.root / result["directory"]
        checked = verify_attempt(self.root, result["directory"], self.snap)
        self.assertEqual(checked["outcome"], "pass")
        self.contract["actions"][0]["enabled"] = literal(False)
        self.assertEqual(collect(self.root, self.snap)[0], [])
        self.contract["actions"][0]["enabled"] = literal(True)
        report = json.loads((folder / "report.json").read_text())
        report["results"][0]["reason"] = "made up"
        (folder / "report.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "modified"):
            verify_attempt(self.root, result["directory"], self.snap)

    def test_independent_handwritten_oracle_has_four_physical_states(self):
        import shutil
        from bo_observer.analysis.tla.process import execute

        directory = self.root / "handwritten"
        directory.mkdir()
        fixture = Path(__file__).parent / "fixtures/tlc-oracles"
        for name in ("Model.tla", "Model.cfg"):
            shutil.copyfile(fixture / name, directory / name)
        java, jar, _ = resolve()
        execution = execute(java, jar, directory, self.profile["budget"])
        result = parse_output(
            (directory / "stdout.log").read_text(encoding="utf-8"),
            execution["exit_code"],
            {},
        )
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["stats"]["distinct"], 4)
        # Check reachability of all four physical combinations using negated
        # invariants. These expectations are independent of generated action text.
        for grant in ("inactive", "active"):
            for archive in ("inactive", "active"):
                self.invariant(
                    operation(
                        "not",
                        operation(
                            "all",
                            operation("eq", variable(), literal(grant, "status")),
                            operation(
                                "eq",
                                variable("archive-status"),
                                literal(archive, "status"),
                            ),
                        ),
                    )
                )
                checked = self.run_model()
                self.assertEqual(checked["status"], "fail", checked)
                self.assertEqual(
                    checked["results"][0]["trace"]["states"][-1],
                    {"grant-status": grant, "archive-status": archive},
                )

    def test_native_reproduction_is_independent_of_a_design_result(self):
        self.invariant(operation("eq", variable(), literal("inactive", "status")))
        result = self.run_model()
        trace = result["results"][0]["trace"]

        def native_step(state, action, bug=False):
            state = deepcopy(state)
            owner, event = action.split("-", 1)
            if bug and owner == "grant":
                owner = "archive"
            state[owner + "-status"] = "active" if event == "share" else "inactive"
            return state

        correct = deepcopy(trace["states"][0])
        broken = deepcopy(correct)
        for step in trace["steps"]:
            correct = native_step(correct, step["action"])
            broken = native_step(broken, step["action"], True)
        self.assertEqual(correct, trace["states"][-1])
        self.assertNotEqual(broken, trace["states"][-1])
        # The original design passes its intended constraint despite faulty native
        # code: there is deliberately no implementation-equivalence claim.
        self.contract["properties"][0].update(
            kind="transition_constraint",
            action_refs=["grant-share"],
            expression=operation(
                "eq", variable("archive-status"), variable("archive-status", "after")
            ),
        )
        self.assertEqual(self.run_model()["status"], "pass")

    def test_wall_budget_stops_large_exploration_without_filtering(self):
        self.queue()
        self.contract["initial"] = literal(True)
        next(d for d in self.contract["domains"] if d["id"] == "queue")[
            "max_items"
        ] = 24
        self.profile["budget"]["wall_seconds"] = 1
        result = self.run_model()
        self.assertEqual(result["status"], "incomplete", result)
        self.assertIn(result["results"][0]["reason"], {"timeout", "profile_timeout"})

    def test_scalar_sequence_quantifiers_and_shared_policy(self):
        self.queue()
        policy = self.snap["behavior_discovery"]["policy"]
        policy["inputs"]["confirmed"] = "boolean"
        policy["nodes"].extend(
            [
                {
                    "id": "confirmed",
                    "op": "input",
                    "name": "confirmed",
                    "source_refs": ["U1"],
                },
                {
                    "id": "negated",
                    "op": "not",
                    "inputs": ["confirmed"],
                    "source_refs": ["U1"],
                },
                {
                    "id": "choice",
                    "op": "any",
                    "inputs": ["confirmed", "negated"],
                    "source_refs": ["U1"],
                },
                {
                    "id": "all-confirmed",
                    "op": "all",
                    "inputs": ["choice", "confirmed"],
                    "source_refs": ["U1"],
                },
            ]
        )
        policy["operations"].append(
            {"id": "confirmation", "root": "all-confirmed", "source_refs": ["U1"]}
        )
        self.contract["scope"]["model_refs"].append("policy-operation:confirmation")
        self.profile["model_refs"] = self.contract["scope"]["model_refs"][:]
        self.invariant(
            operation(
                "all",
                operation("ne", literal(True), literal(False)),
                operation(
                    "eq",
                    operation("add", literal(0, "size"), literal(1, "size")),
                    literal(1, "size"),
                ),
                operation(
                    "eq",
                    operation("sub", literal(2, "size"), literal(1, "size")),
                    literal(1, "size"),
                ),
                operation("member", literal(True), literal([True, False], "queue")),
                operation(
                    "eq",
                    operation(
                        "select",
                        literal([True, False], "queue"),
                        literal(0, "size"),
                        literal(False),
                    ),
                    literal(True),
                ),
                operation(
                    "eq",
                    operation(
                        "select",
                        literal([True], "queue"),
                        literal(2, "size"),
                        literal(False),
                    ),
                    literal(False),
                ),
                {
                    "op": "forall",
                    "bind": "x",
                    "domain": "status",
                    "body": operation(
                        "eq", {"op": "param", "id": "x"}, {"op": "param", "id": "x"}
                    ),
                },
                {
                    "op": "exists",
                    "bind": "x",
                    "domain": "status",
                    "body": operation(
                        "eq", {"op": "param", "id": "x"}, literal("active", "status")
                    ),
                },
                {
                    "op": "policy_ref",
                    "id": "policy-operation:confirmation",
                    "bindings": {"confirmed": literal(True)},
                },
            )
        )
        result = self.run_model()
        self.assertEqual(result["status"], "pass", result["results"])

    def test_fixed_identity_pool_can_be_a_typed_set(self):
        enqueue, dequeue = self.queue()
        owner = next(
            o for o in self.snap["behavior_discovery"]["objects"] if o["id"] == "grant"
        )
        owner["fields"]["pending"] = ["string"]
        next(
            f for f in self.snap["behavior_discovery"]["facts"] if f["id"] == "pending"
        )["type"] = ["string"]
        self.contract["domains"].append(
            {
                "id": "holder",
                "type": "identity",
                "object_ref": "object:grant",
                "identity_policy": "fixed_pool",
                "values": ["worker-a", "worker-b"],
                "source_refs": ["U1"],
            }
        )
        next(d for d in self.contract["domains"] if d["id"] == "queue").update(
            type="set", element_domain="holder"
        )
        enqueue["parameters"] = {"payload": "holder"}
        dequeue["parameters"] = {"payload": "holder"}
        enqueue["updates"]["pending"] = operation(
            "set_add", variable("pending"), {"op": "param", "id": "payload"}
        )
        dequeue["updates"]["pending"] = operation(
            "set_remove", variable("pending"), {"op": "param", "id": "payload"}
        )
        self.invariant(
            operation(
                "le", operation("length", variable("pending")), literal(2, "size")
            )
        )
        self.assertEqual(self.run_model()["status"], "pass")

    def test_external_assumption_cannot_be_used_as_automatic_fairness(self):
        self.contract["assumptions"] = [
            {
                "id": "external",
                "kind": "environment",
                "model_refs": self.profile["model_refs"],
                "action_refs": [],
                "statement": "External storage always finishes",
                "status": "confirmed",
                "review_source_refs": ["U1"],
                "source_refs": ["U1"],
                "rationale": "User expectation",
                "invalidated_by": ["Storage outage"],
            }
        ]
        self.profile["assumption_refs"] = ["external"]
        result = self.run_model()
        self.assertEqual(result["status"], "unsupported", result["results"])
        self.assertFalse((self.root / result["directory"] / "property-0").exists())

    def test_cancel_then_complete_preserves_attempt_and_uses_finished_proof(self):
        cancel = threading.Event()
        cancel.set()
        first = self.run_model(cancel=cancel)
        second = self.run_model()
        receipts, _, diagnostics = collect(self.root, self.snap)
        self.assertEqual([r["outcome"] for r in receipts], ["pass"], diagnostics)
        self.assertTrue((self.root / first["directory"] / "receipt.json").is_file())
        self.assertEqual(second["status"], "pass")

    def test_rehashing_an_edited_summary_cannot_change_raw_result(self):
        import json
        from bo_observer.concepts.common import digest
        from bo_observer.analysis.tla.toolchain import sha256

        result = self.run_model()
        folder = self.root / result["directory"]
        path = folder / "report.json"
        report = json.loads(path.read_text())
        report["results"][0]["reason"] = "invented"
        path.write_text(json.dumps(report))
        receipt = json.loads((folder / "receipt.json").read_text())
        receipt["artifacts"][path.relative_to(self.root).as_posix()] = sha256(path)
        receipt["fingerprint"] = digest(
            {k: v for k, v in receipt.items() if k != "fingerprint"}
        )
        (folder / "receipt.json").write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "actual tool output"):
            verify_attempt(self.root, result["directory"], self.snap)

    def test_missing_tool_receipt_stays_incomplete_until_real_execution(self):
        self.run_model(jar=self.root / "absent.jar")
        self.assertEqual(
            [r["outcome"] for r in collect(self.root, self.snap)[0]], ["incomplete"]
        )
        self.run_model()
        self.assertEqual(
            [r["outcome"] for r in collect(self.root, self.snap)[0]], ["pass"]
        )

    def test_required_profile_closes_only_formal_gate(self):
        from bo_observer.workflow.behavior_iteration import finalize
        from test_behavior_workflow import BehaviorWorkflowTests

        fixture = BehaviorWorkflowTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        current = fixture.current
        current.update(
            behavior=self.contract,
            behavior_discovery=self.snap["behavior_discovery"],
            analysis_profiles=[self.profile],
        )
        self.profile["required_for_acceptance"] = True
        self.snap = current
        report = deepcopy(fixture.report)
        finalize(current, report, root=self.root)
        self.assertIn("formal_analysis/small", report["behavior_coverage"]["blocking"])
        self.run_model()
        report = deepcopy(fixture.report)
        report.update(valid=False, errors=["Original independent check failed"])
        finalize(current, report, root=self.root)
        formal = report["behavior_coverage"]["categories"]["formal_analysis"][
            "profiles"
        ]["small"]
        self.assertEqual(formal["status"], "passed", formal)
        self.assertFalse(report["valid"])
        self.assertIn("Original independent check failed", report["errors"])

    def test_changed_checker_options_cannot_reuse_completed_output(self):
        import json
        from bo_observer.concepts.common import digest
        from bo_observer.analysis.tla.toolchain import sha256

        result = self.run_model()
        folder = self.root / result["directory"]
        path = folder / "property-0/execution.json"
        execution = json.loads(path.read_text())
        execution["arguments"].insert(-1, "-deadlock")
        path.write_text(json.dumps(execution))
        receipt = json.loads((folder / "receipt.json").read_text())
        receipt["artifacts"][path.relative_to(self.root).as_posix()] = sha256(path)
        receipt["fingerprint"] = digest(
            {k: v for k, v in receipt.items() if k != "fingerprint"}
        )
        (folder / "receipt.json").write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "fixed checker command"):
            verify_attempt(self.root, result["directory"], self.snap)


class ToolParsingTests(unittest.TestCase):
    def test_child_environment_excludes_credentials_and_java_options(self):
        from unittest.mock import patch
        from bo_observer.analysis.tla.toolchain import isolated_environment

        with patch.dict(
            os.environ,
            {
                "JAVA_TOOL_OPTIONS": "-javaagent:unexpected.jar",
                "TOKEN": "private",
                "PATH": "elsewhere",
            },
        ):
            result = isolated_environment(Path("temporary"))
        self.assertFalse({"JAVA_TOOL_OPTIONS", "TOKEN", "PATH"} & result.keys())

    def test_untrusted_jar_fails_before_starting_java(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "tool.jar"
            jar.write_bytes(b"changed")
            with patch("subprocess.run") as run, self.assertRaisesRegex(
                ValueError, "checksum"
            ):
                resolve(java=Path(__file__), jar=jar)
            run.assert_not_called()

    def test_typed_nested_carriers_reject_unconsumed_text(self):
        self.assertEqual(
            value('<< TRUE, {"s61", "s62"}, -2 >>'), [True, ["a", "b"], -2]
        )
        for text in ("<< TRUE", "1 eval()", '"arbitrary"', "[a |-> 1]"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                value(text)

    def test_exit_zero_without_completion_cannot_pass(self):
        result = parse_output(
            "@!@!@STARTMSG 2193:0 @!@!@\nSuccess\n@!@!@ENDMSG 2193 @!@!@", 0, {}
        )
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
