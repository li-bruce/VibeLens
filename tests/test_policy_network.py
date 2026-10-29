"""Behavioral regressions for shared rules, source identity and recorded paths."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.policy.definition import validate, fingerprint
from bo_observer.policy.runtime import evaluate
from bo_observer.policy.projection import project, projection_errors
from bo_observer.policy.evidence import binding_errors, evaluation_errors, runtime_errors
from bo_observer.policy.sync import synchronize
from bo_observer.policy.recording import record_evaluation
from bo_observer.graph.code_structure import scan
from bo_contracts import validate_graph
from bo_observer.web.bo_design import BODesign
from bo_observer.workflow.requirements_dialogue import assess as assess_dialogue
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.protocol import validate_event
from bo_upgrade import apply as upgrade_runtime
from bo_observer.workflow.bo_sync import source_inventory
import hashlib

EXAMPLE = ROOT / "examples/policy-network"
TEMP = ROOT / ".validation/policy-network"
TEMP.mkdir(parents=True, exist_ok=True)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load(EXAMPLE / "build_example.py", "policy_builder")
predicates = load(EXAMPLE / "predicates.py", "policy_predicates")


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = builder.definition()
        self.callbacks = {
            "same_identity": predicates.same_identity,
            "flag_enabled": predicates.flag_enabled,
        }
        self.inputs = {
            "actor": "Lin",
            "owner": "Lin",
            "parent_owner": "Mei",
            "recipient": "Ning",
            "logged_in": True,
            "grant_active": True,
            "role_allowed": True,
            "changes_owner": False,
        }

    def run_policy(self, operation="download", **options):
        return evaluate(
            self.policy,
            operation,
            options.pop("inputs", self.inputs),
            self.callbacks,
            source_root=EXAMPLE,
            fact_revision=options.pop("fact_revision", "snapshot-1"),
            **options,
        )

    def graph(self):
        return project(
            {
                "schema_version": 3,
                "revision": "1",
                "intent": "intent.json",
                "source_files": ["predicates.py"],
                "scope": {"unknowns": []},
                "overview": [{"node": "download"}],
                "nodes": [
                    {
                        "id": item["id"],
                        "kind": "data",
                        "label": item["id"],
                        "summary": "Business entry",
                    }
                    for item in self.policy["operations"]
                ],
                "edges": [],
                "policy": self.policy,
            }
        )

    def test_shared_definition_and_distinct_bindings(self):
        index = validate(self.policy)
        self.assertEqual(
            index["operations"]["share"]["root"], index["operations"]["revoke"]["root"]
        )
        self.assertEqual(
            index["nodes"]["is_owner"]["predicate"], index["nodes"]["is_parent_owner"]["predicate"]
        )
        first = self.run_policy("share")
        second = self.run_policy("transfer")
        self.assertTrue(first["value"])
        self.assertFalse(second["value"])
        self.assertNotEqual(first["check_id"], second["check_id"])
        self.assertEqual(len({s["node"] for s in first["trace"]}), len(first["trace"]))

    def test_download_fresh_grant_revocation_and_alternative_owner_path(self):
        inputs = {**self.inputs, "actor": "Ning"}
        self.assertTrue(self.run_policy(inputs=inputs)["value"])
        inputs["grant_active"] = False
        denied = self.run_policy(inputs=inputs, fact_revision="snapshot-2")
        self.assertFalse(denied["value"])
        self.assertEqual(evaluation_errors(self.policy, denied), [])
        self.assertTrue(self.run_policy(inputs={**inputs, "actor": "Lin"})["value"])

    def test_owner_change_cannot_bypass_parent_rule_via_role_edit(self):
        inputs = {**self.inputs, "changes_owner": True, "role_allowed": True}
        self.assertFalse(self.run_policy("edit", inputs=inputs)["value"])
        self.assertTrue(self.run_policy("edit", inputs={**inputs, "actor": "Mei"})["value"])
        self.assertTrue(self.run_policy("edit", inputs={**inputs, "changes_owner": False})["value"])

    def test_short_circuit_is_actual_and_missing_context_stays_unknown(self):
        result = self.run_policy()
        self.assertNotIn("active_grant", [s["node"] for s in result["trace"]])
        self.assertEqual(evaluation_errors(self.policy, result), [])
        inputs = {**self.inputs, "actor": "Ning"}
        del inputs["grant_active"]
        unknown = self.run_policy(inputs=inputs)
        self.assertIsNone(unknown["value"])
        self.assertEqual(unknown["decision"], "unknown")
        self.assertEqual(evaluation_errors(self.policy, unknown), [])

    def test_observation_fault_does_not_change_business_decision(self):
        def broken_sink(step):
            raise OSError("offline")

        result = self.run_policy(on_step=broken_sink)
        self.assertTrue(result["value"])
        self.assertTrue(result["diagnostics"])
        self.assertEqual(evaluation_errors(self.policy, result), [])

    def test_standalone_cli_rejects_evidence_from_changed_source(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            source = root / "predicates.py"
            source.write_bytes((EXAMPLE / "predicates.py").read_bytes())
            (root / "model.json").write_text(json.dumps(self.graph()), encoding="utf-8")
            (root / "proof.json").write_text(json.dumps(self.run_policy()), encoding="utf-8")
            command = [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(ROOT / "skills/vibelens/scripts/bo_policy.py"),
                "check",
                "--root",
                str(root),
                "--model",
                "model.json",
                "--evaluation",
                "proof.json",
            ]
            first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            source.write_text(
                source.read_text().replace("return value", "return not value"), encoding="utf-8"
            )
            second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(second.returncode, 0)
            self.assertTrue(any("stale" in error for error in json.loads(second.stdout)["errors"]))

    def test_concurrent_requests_do_not_share_values(self):
        def one(i):
            return self.run_policy(
                inputs={**self.inputs, "actor": "Ning", "grant_active": bool(i % 2)},
                fact_revision=str(i),
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            reports = list(pool.map(one, range(32)))
        self.assertEqual([r["value"] for r in reports], [bool(i % 2) for i in range(32)])
        self.assertEqual(len({r["check_id"] for r in reports}), 32)

    def test_invalid_definitions_fail_before_execution(self):
        mutations = []
        missing = deepcopy(self.policy)
        missing["nodes"][-1]["inputs"] = ["absent"]
        mutations.append(missing)
        cycle = deepcopy(self.policy)
        cycle["nodes"][-1]["inputs"] = [cycle["nodes"][-1]["id"]]
        mutations.append(cycle)
        op = deepcopy(self.policy)
        op["nodes"][-1]["op"] = "evaluate_python"
        mutations.append(op)
        arity = deepcopy(self.policy)
        arity["nodes"][-1]["inputs"] = []
        mutations.append(arity)
        duplicate = deepcopy(self.policy)
        duplicate["nodes"].append(deepcopy(duplicate["nodes"][0]))
        mutations.append(duplicate)
        wrong_type = deepcopy(self.policy)
        wrong_type["inputs"]["owner"] = "number"
        mutations.append(wrong_type)
        unknown_arg = deepcopy(self.policy)
        unknown_arg["nodes"][8]["arguments"] = {"other": "actor"}
        mutations.append(unknown_arg)
        no_case = deepcopy(self.policy)
        no_case["operations"][0]["cases"] = []
        mutations.append(no_case)
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)), self.assertRaises(ValueError):
                validate(mutation)

    def test_exact_projection_and_source_free_exemption_cannot_be_forged(self):
        model = self.graph()
        validate_graph(model)
        self.assertEqual(project(model), model)
        self.assertEqual(projection_errors(model), [])
        policy_ids = [n["id"] for n in model["nodes"] if n.get("policy_node")]
        self.assertEqual(len(policy_ids), len(set(policy_ids)))
        changed = deepcopy(model)
        changed["edges"].pop()
        with self.assertRaises(ValueError):
            validate_graph(changed)
        changed = deepcopy(model)
        next(n for n in changed["nodes"] if n.get("policy_node") == "signed_in")["label"] = "wrong"
        with self.assertRaises(ValueError):
            validate_graph(changed)
        changed = deepcopy(model)
        changed.pop("policy")
        with self.assertRaises(ValueError):
            validate_graph(changed)

    def test_recorded_proof_rejects_missing_wrong_stale_and_mixed_evidence(self):
        result = self.run_policy(inputs={**self.inputs, "actor": "Ning"})
        self.assertEqual(evaluation_errors(self.policy, result), [])
        for field, value in (("policy_hash", "old"), ("value", False), ("check_id", "")):
            wrong = deepcopy(result)
            wrong[field] = value
            self.assertTrue(evaluation_errors(self.policy, wrong))
        missing = deepcopy(result)
        missing["trace"].pop(0)
        self.assertTrue(evaluation_errors(self.policy, missing))
        wrong = deepcopy(result)
        next(s for s in wrong["trace"] if s["node"] == "is_recipient")["arguments"][
            "right"
        ] = "someone-else"
        self.assertTrue(evaluation_errors(self.policy, wrong))
        index = scan(EXAMPLE, ["predicates.py"])
        self.assertEqual(binding_errors(self.policy, index), [])
        index["symbols"].clear()
        self.assertTrue(binding_errors(self.policy, index))

    def test_required_cases_cannot_be_removed_from_runtime_evidence(self):
        payload = {
            "runs": [
                {
                    "case": op["cases"][0],
                    "mode": "on",
                    "policy_evaluations": [self.run_policy(op["id"])],
                }
                for op in self.policy["operations"]
            ]
        }
        for run in payload["runs"]:
            events = run["events"] = []

            class Probe:
                def record(self, node, phase, builder, **context):
                    ident = "event-" + str(len(events))
                    events.append(
                        {"id": ident, "node": node, "phase": phase, **builder(), **context}
                    )
                    return ident

            record_evaluation(
                self.policy,
                run["policy_evaluations"][0],
                Probe(),
                entity="file-1",
                attempt="attempt-1",
            )
        self.assertEqual(runtime_errors(self.policy, payload), [])
        broken = deepcopy(payload)
        broken["runs"][0]["events"].pop()
        self.assertTrue(runtime_errors(self.policy, broken))
        payload["runs"].pop()
        self.assertTrue(runtime_errors(self.policy, payload))

    def test_three_updates_refresh_projection_and_preserve_shared_identities(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            path = root / "project.json"
            model = self.graph()
            for version in range(3):
                model["policy"]["revision"] = str(version)
                next(n for n in model["policy"]["nodes"] if n["id"] == "is_owner")["label"] = (
                    "Owner " + str(version)
                )
                path.write_text(json.dumps(model), encoding="utf-8")
                self.assertFalse(
                    synchronize(root, model_path="project.json", update=False)["valid"]
                )
                self.assertTrue(synchronize(root, model_path="project.json")["valid"])
                current = json.loads(path.read_text())
                self.assertEqual(projection_errors(current), [])
                self.assertEqual(
                    {n["id"] for n in current["nodes"]}, {n["id"] for n in model["nodes"]}
                )
                model = current

    def test_design_web_contains_shared_rules_before_source_exists(self):
        doc = json.loads((ROOT / "skills/vibelens/assets/discovery.example.json").read_text())
        source_id = doc["sources"][0]["id"]
        raw = doc["networks"][0]["nodes"][0]
        anchor = (raw.get("model_nodes") or [raw["id"]])[0]
        draft = deepcopy(self.policy)
        draft["stage"] = "draft"
        for pred in draft["predicates"]:
            pred.pop("source")
            pred["source_refs"] = [source_id]
        for item in [*draft["nodes"], *draft["operations"]]:
            item["source_refs"] = [source_id]
        for operation in draft["operations"]:
            operation["business_nodes"] = [anchor]
            operation["cases"] = []
        doc["policy"] = draft
        self.assertTrue(assess_dialogue(doc)["valid"])
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            (root / "discovery.json").write_text(json.dumps(doc), encoding="utf-8")
            view = BODesign(root).view()
            self.assertEqual(view["stage"], "design")
            self.assertEqual(view["events"], [])
            self.assertIn("policy:download_allowed", {n["id"] for n in view["model"]["nodes"]})
            self.assertGreater(
                sum(e["from"] == "policy:owned_session" for e in view["model"]["edges"]), 1
            )
        with self.assertRaises(ValueError):
            validate(draft)

    def test_loaded_callback_must_match_updated_source(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            path = root / "predicates.py"
            path.write_text((EXAMPLE / "predicates.py").read_text(), encoding="utf-8")
            module = load(path, "fresh_policy_predicates")
            callbacks = {"same_identity": module.same_identity, "flag_enabled": module.flag_enabled}
            evaluate(
                self.policy, "share", self.inputs, callbacks, source_root=root, fact_revision="1"
            )
            path.write_text(
                path.read_text().replace("return left == right", "return left != right"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "loaded policy function differs"):
                evaluate(
                    self.policy,
                    "share",
                    self.inputs,
                    callbacks,
                    source_root=root,
                    fact_revision="2",
                )

    def test_repeated_arguments_keep_one_dependency_and_one_fact(self):
        node = next(n for n in self.policy["nodes"] if n["id"] == "is_owner")
        node["arguments"]["right"] = "actor"
        # Keep the former owner input reachable through the parent comparison.
        next(n for n in self.policy["nodes"] if n["id"] == "is_parent_owner")["arguments"][
            "right"
        ] = "owner"
        self.policy["nodes"] = [n for n in self.policy["nodes"] if n["id"] != "parent_owner"]
        result = self.run_policy("share")
        self.assertEqual(evaluation_errors(self.policy, result), [])
        self.assertEqual(
            next(s for s in result["trace"] if s["node"] == "is_owner")["used"], ["actor"]
        )

    def test_predicate_errors_are_unknown_with_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            path = root / "predicates.py"
            text = (
                (EXAMPLE / "predicates.py")
                .read_text()
                .replace("return value", "raise OSError('reader offline')")
            )
            path.write_text(text, encoding="utf-8")
            module = load(path, "broken_policy_reader")
            callbacks = {"same_identity": module.same_identity, "flag_enabled": module.flag_enabled}
            result = evaluate(
                self.policy,
                "share",
                self.inputs,
                callbacks,
                source_root=root,
                fact_revision="offline",
            )
            self.assertIsNone(result["value"])
            self.assertEqual(result["decision"], "unknown")
            self.assertTrue(any(s["status"] == "error" for s in result["trace"]))
            self.assertEqual(evaluation_errors(self.policy, result), [])

    def test_native_probe_produces_valid_graph_events_and_causal_links(self):
        model = self.graph()
        project_doc = {"project_id": "policy-test", "model": model}
        events = []
        probe = BOProbe(project_doc, "build-1", sink=lambda event, kind: events.append(event))
        try:
            result = self.run_policy(inputs={**self.inputs, "actor": "Ning"})
            record_evaluation(
                self.policy,
                result,
                probe,
                entity="file-1",
                attempt="attempt-1",
                basis={"param_version": 1},
            )
            self.assertTrue(probe.flush())
            self.assertEqual(probe.bo_errors, 0)
            self.assertEqual(len(events), len(result["trace"]))
            for event in events:
                validate_event(event, project_doc, "build-1")
            # Every operation needs its own original proof and graph events.
            payload = {
                "runs": [
                    {"case": op["cases"][0], "mode": "on", "events": [], "policy_evaluations": []}
                    for op in self.policy["operations"]
                ]
            }
            for run in payload["runs"]:
                operation = next(
                    op["id"] for op in self.policy["operations"] if op["cases"][0] == run["case"]
                )
                proof = self.run_policy(operation)
                collector = BOProbe(
                    project_doc,
                    "build-1",
                    sink=lambda event, kind, run=run: run["events"].append(event),
                )
                record_evaluation(
                    self.policy,
                    proof,
                    collector,
                    entity="file-1",
                    attempt="attempt-1",
                    basis={"param_version": 1},
                )
                self.assertTrue(collector.flush())
                collector.close()
                run["policy_evaluations"] = [proof]
            self.assertEqual(runtime_errors(self.policy, payload), [])
        finally:
            probe.close()

    def test_upgraded_core_executes_rules_without_observer_imports(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            upgrade_runtime(root, runtime="observer_runtime", policy_core=True)
            (root / "policy.json").write_text(json.dumps(self.policy), encoding="utf-8")
            command = (
                "import sys,json; from pathlib import Path; "
                f"sys.path.insert(0,{str(root)!r}); sys.path.insert(0,{str(EXAMPLE)!r}); "
                "from bo_stategraph.policy.runtime import evaluate; import predicates; "
                "p=json.loads(Path('policy.json').read_text()); "
                f"r=evaluate(p,'share',{self.inputs!r},{{'same_identity':predicates.same_identity,'flag_enabled':predicates.flag_enabled}},source_root={str(EXAMPLE)!r},fact_revision='1'); "
                "assert r['value'] is True; assert not any(k.startswith('bo_observer') for k in sys.modules); "
                "print('core-policy-ok')"
            )
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-X", "utf8", "-c", command],
                cwd=root,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("core-policy-ok", result.stdout)

    def test_semantic_rule_addition_and_source_move_refresh_three_rounds(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            (root / "predicates.py").write_text(
                (EXAMPLE / "predicates.py").read_text(), encoding="utf-8"
            )
            native = load(root / "predicates.py", "iterative_native")
            policy = deepcopy(self.policy)
            previous_ids = set()
            previous_proof = None
            for version in range(3):
                policy["revision"] = "iteration-" + str(version)
                if version == 1:
                    policy["inputs"]["file_ready"] = "boolean"
                    policy["nodes"] += [
                        {
                            "id": "file_ready",
                            "op": "input",
                            "name": "file_ready",
                            "source_refs": ["U1"],
                        },
                        {
                            "id": "file_is_ready",
                            "op": "predicate",
                            "predicate": "flag_enabled",
                            "arguments": {"value": "file_ready"},
                            "source_refs": ["U1"],
                        },
                    ]
                    next(n for n in policy["nodes"] if n["id"] == "download_allowed")[
                        "inputs"
                    ].append("file_is_ready")
                if version == 2:
                    (root / "rules").mkdir()
                    (root / "rules/identity.py").write_text(
                        "def same_identity(left: str, right: str) -> bool:\n    return left == right\n",
                        encoding="utf-8",
                    )
                    policy["predicates"][0]["source"] = {
                        "path": "rules/identity.py",
                        "symbol": "same_identity",
                    }
                model = self.graph()
                model["policy"] = policy
                path = root / "project.json"
                path.write_text(json.dumps(model), encoding="utf-8")
                current_check = synchronize(root, model_path="project.json", update=False)
                self.assertEqual(current_check["valid"], version == 0)
                self.assertTrue(synchronize(root, model_path="project.json")["valid"])
                model = json.loads(path.read_text())
                validate_graph(model)
                ids = {n["id"] for n in model["nodes"]}
                self.assertTrue(previous_ids <= ids)
                previous_ids = ids
                paths = sorted({p["source"]["path"] for p in policy["predicates"]})
                self.assertEqual(binding_errors(policy, scan(root, paths)), [])
                callbacks = {
                    "flag_enabled": native.flag_enabled,
                    "same_identity": native.same_identity,
                }
                if version == 2:
                    callbacks["same_identity"] = load(
                        root / "rules/identity.py", "moved_identity"
                    ).same_identity
                inputs = {
                    **self.inputs,
                    "actor": "Ning",
                    **({"file_ready": True} if version else {}),
                }
                proof = evaluate(
                    policy,
                    "download",
                    inputs,
                    callbacks,
                    source_root=root,
                    fact_revision=str(version),
                )
                self.assertTrue(proof["value"])
                self.assertEqual(evaluation_errors(policy, proof), [])
                if previous_proof:
                    self.assertTrue(evaluation_errors(policy, previous_proof))
                previous_proof = proof

    def test_unconditional_rule_does_not_require_a_fake_function(self):
        policy = {
            "schema": "bo-policy/v1",
            "stage": "bound",
            "revision": "public-1",
            "inputs": {},
            "predicates": [],
            "nodes": [
                {
                    "id": "public",
                    "op": "constant",
                    "type": "boolean",
                    "value": True,
                    "source_refs": ["U1"],
                }
            ],
            "operations": [
                {
                    "id": "read",
                    "root": "public",
                    "business_nodes": ["read"],
                    "cases": ["public-read"],
                    "source_refs": ["U1"],
                }
            ],
        }
        result = evaluate(policy, "read", {}, {}, source_root=EXAMPLE, fact_revision="public")
        self.assertTrue(result["value"])
        self.assertEqual(evaluation_errors(policy, result), [])

    def test_malformed_json_evidence_is_rejected_without_repair(self):
        for evidence in (None, [], {}, {"trace": None}, {"trace": [None]}):
            self.assertTrue(evaluation_errors(self.policy, evidence))
        result = self.run_policy()
        for key, value in (("operation", []), ("bindings", []), ("trace", [None])):
            mutated = deepcopy(result)
            mutated[key] = value
            self.assertTrue(evaluation_errors(self.policy, mutated))
        for payload in (None, {}, {"runs": None}, {"runs": [None]}):
            self.assertTrue(runtime_errors(self.policy, payload))
        mutated = deepcopy(self.policy)
        mutated["nodes"][8]["op"] = []
        with self.assertRaises(ValueError):
            validate(mutated)

    def test_optional_core_is_not_copied_to_unrelated_projects_and_tampering_is_seen(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            upgrade_runtime(root, runtime="observer_runtime")
            self.assertFalse((root / "bo_stategraph/policy/runtime.py").is_file())
            upgrade_runtime(root, runtime="observer_runtime", policy_core=True)
            relative = "bo_stategraph/policy/runtime.py"
            cfg = {"source_scope": {"roots": ["bo_stategraph"]}}
            inventory = source_inventory(root, cfg)
            self.assertIn(relative, inventory["excluded"])
            self.assertNotIn(relative, inventory["files"])
            path = root / relative
            path.write_text(
                path.read_text() + "\ndef application_feature():\n    return 1\n", encoding="utf-8"
            )
            # A forged local fingerprint alone cannot make application code an SDK.
            manifest = root / "bo_stategraph/runtime-version.json"
            data = json.loads(manifest.read_text())
            data["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(data), encoding="utf-8")
            inventory = source_inventory(root, cfg)
            self.assertIn(relative, inventory["files"])

    def test_static_function_can_locate_all_bound_evaluation_owners(self):
        module_url = (ROOT / "skills/vibelens/assets/stategraph-viewer/graph-links.js").as_uri()
        script = (
            "import fs from 'node:fs'; import assert from 'node:assert/strict'; "
            f"const {{runtimeOwners}}=await import({json.dumps(module_url)}); "
            "const graph=JSON.parse(fs.readFileSync(0,'utf8')); "
            "assert.deepEqual(runtimeOwners(graph,'policy:function:same_identity'),"
            "['policy:is_owner','policy:is_parent_owner','policy:is_recipient']);"
        )
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            input=json.dumps(self.graph()),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
