"""Verify recorded policy paths without executing application predicates."""

from .definition import validate, fingerprint, dependencies, matches
from .runtime import combine


def binding_errors(policy, structure):
    """Bind predicates to independently parsed source signatures, not graph copies."""
    index = validate(policy)
    errors = []
    symbols = structure.get("symbols", {})
    for pred in index["predicates"].values():
        source = pred["source"]
        symbol = symbols.get(source["path"] + "::" + source["symbol"])
        if symbol is None:
            # Existing parsers own the canonical symbol separator.
            symbol = next(
                (
                    s
                    for s in symbols.values()
                    if s.get("path") == source["path"] and s.get("symbol") == source["symbol"]
                ),
                None,
            )
        if symbol is None:
            errors.append("policy source function is missing: " + pred["id"])
            continue
        parameters = {p["name"] for p in symbol.get("parameters", [])}
        if set(pred["parameters"]) - parameters:
            errors.append("policy source parameters differ: " + pred["id"])
        types = {
            "str": "string",
            "string": "string",
            "bool": "boolean",
            "boolean": "boolean",
            "int": "number",
            "float": "number",
            "number": "number",
        }
        for parameter in symbol.get("parameters", []):
            declared = pred["parameters"].get(parameter["name"])
            annotated = types.get(parameter.get("annotation"))
            if declared and annotated and declared != annotated:
                errors.append(
                    "policy source parameter type differs: " + pred["id"] + "/" + parameter["name"]
                )
    return errors


def evaluation_errors(policy, evaluation, *, manifest=None):
    """Validate identity, input bindings, short circuit and all visited dependencies.

    Predicate truth is a recorded application fact. This checks its placement and
    composition; independent business cases must still check that truth itself.
    """
    index = validate(policy)
    errors = []
    if not isinstance(evaluation, dict):
        return ["policy evaluation must be an object"]
    trace = evaluation.get("trace")
    if (
        not isinstance(trace, list)
        or len(trace) > 4096
        or any(not isinstance(step, dict) for step in trace)
    ):
        return ["policy trace must be a bounded list of expression records"]
    if (
        evaluation.get("schema") != "bo-policy-evaluation/v1"
        or evaluation.get("policy_hash") != fingerprint(policy)
        or evaluation.get("policy_revision") != policy["revision"]
    ):
        return ["policy evaluation belongs to another declaration"]
    for field in ("check_id", "fact_revision"):
        if not isinstance(evaluation.get(field), str) or not evaluation[field]:
            errors.append("missing policy " + field)
    operation = (
        index["operations"].get(evaluation.get("operation"))
        if isinstance(evaluation.get("operation"), str)
        else None
    )
    if not operation or operation["root"] != evaluation.get("root"):
        return errors + ["unknown policy operation/root"]
    bindings = evaluation.get("bindings", {})
    if not isinstance(bindings, dict) or any(not isinstance(v, dict) for v in bindings.values()):
        return errors + ["invalid native predicate binding evidence"]
    for pred in index["predicates"].values():
        binding = bindings.get(pred["id"], {})
        if any(binding.get(k) != v for k, v in pred["source"].items()) or not binding.get(
            "file_sha256"
        ):
            errors.append("native predicate binding differs: " + pred["id"])
        if manifest and binding.get("file_sha256") != manifest.get("files", {}).get(
            pred["source"]["path"]
        ):
            errors.append("native predicate evidence is stale: " + pred["id"])
    inputs = evaluation.get("inputs", {})
    if not isinstance(inputs, dict) or set(inputs) - set(policy["inputs"]):
        return errors + ["undeclared policy input evidence"]
    if any(not matches(v, policy["inputs"][k]) for k, v in inputs.items()):
        return errors + ["policy input evidence type differs"]
    seen = {}
    for step in trace:
        ident = step.get("node")
        if not isinstance(ident, str) or ident not in index["nodes"] or ident in seen:
            errors.append("unknown or repeated expression evidence: " + str(ident))
            continue
        node = index["nodes"][ident]
        op, refs = node["op"], dependencies(node)
        used, skipped = step.get("used", []), step.get("skipped", [])
        if (
            not isinstance(used, list)
            or not isinstance(skipped, list)
            or used + skipped != refs
            or any(ref not in seen for ref in used)
        ):
            errors.append("missing, reordered or fabricated child evidence: " + ident)
            continue
        value, status = step.get("value"), step.get("status")
        if (
            not isinstance(status, str)
            or status not in {"completed", "unknown", "error"}
            or (value is None) != (status != "completed")
        ):
            errors.append("invalid expression status/value: " + ident)
        if value is not None and not matches(value, index["types"][ident]):
            errors.append("expression value type differs: " + ident)
        if op == "input" and value != inputs.get(node["name"]):
            errors.append("input evidence differs: " + ident)
        elif op == "constant" and value != node["value"]:
            errors.append("constant evidence differs: " + ident)
        elif op == "predicate":
            expected = {argument: seen[ref]["value"] for argument, ref in node["arguments"].items()}
            if step.get("arguments") != expected or skipped:
                errors.append("predicate argument evidence differs: " + ident)
            if any(value is None for value in expected.values()) and (
                value is not None or status != "unknown"
            ):
                errors.append("predicate evaluated with missing input: " + ident)
        elif op in {"all", "any", "not"}:
            values = [seen[ref]["value"] for ref in used]
            decisive = False if op == "all" else True if op == "any" else None
            if (
                not used
                or (skipped and values[-1] is not decisive)
                or any(v is decisive for v in values[:-1])
                or value is not combine(op, values)
            ):
                errors.append("logical composition/short circuit differs: " + ident)
        seen[ident] = step
    root = seen.get(operation["root"])
    if not root or root["value"] is not evaluation.get("value"):
        errors.append("missing or mismatched root result")
    expected_decision = (
        "allow"
        if evaluation.get("value") is True
        else "deny" if evaluation.get("value") is False else "unknown"
    )
    if evaluation.get("decision") != expected_decision:
        errors.append("policy decision differs from root")
    reachable = set()

    def visit(ident):
        if ident in reachable or ident not in seen:
            return
        reachable.add(ident)
        for reference in seen[ident]["used"]:
            visit(reference)

    visit(operation["root"])
    if reachable != set(seen):
        errors.append("unrelated expression evidence mixed into check")
    return errors


def runtime_errors(policy, payload, *, manifest=None):
    """Require configured cases, and keep checks from different requests separate."""
    index = validate(policy)
    errors, identities, covered = [], set(), set()
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return ["policy runtime payload needs case runs"]
    for run in payload.get("runs", []):
        if not isinstance(run, dict) or not isinstance(run.get("policy_evaluations", []), list):
            errors.append("invalid policy case run")
            continue
        if run.get("mode") != "on":
            continue
        for evaluation in run.get("policy_evaluations", []):
            if not isinstance(evaluation, dict):
                errors.append("invalid policy evaluation record")
                continue
            identity = evaluation.get("check_id")
            if not isinstance(identity, str) or not identity:
                errors.append("invalid policy check identity")
                continue
            if identity in identities:
                errors.append("duplicate policy check identity")
            identities.add(identity)
            failures = evaluation_errors(policy, evaluation, manifest=manifest)
            if failures:
                errors.extend(failures)
                continue
            events = run.get("events")
            if not isinstance(events, list) or any(not isinstance(event, dict) for event in events):
                errors.append("policy case needs graph event records")
                continue
            if any(
                not isinstance(event.get("inputs"), dict)
                or not isinstance(event.get("outputs"), dict)
                or not isinstance(event.get("depends", []), list)
                or any(not isinstance(ref, dict) for ref in event.get("depends", []))
                for event in events
            ):
                errors.append("invalid policy graph event fields")
                continue
            # A sidecar report alone is insufficient: the same check must exist
            # on the graph's original event stream with matching values/links.
            event_ids = {}
            for step in evaluation.get("trace", []):
                graph_matches = [
                    e
                    for e in events
                    if e.get("node") == "policy:" + step["node"]
                    and e.get("phase") == "decision"
                    and e.get("inputs", {}).get("bo_check") == identity
                ]
                if len(graph_matches) != 1:
                    failures.append("missing unique policy graph event: " + step["node"])
                    continue
                event = graph_matches[0]
                observed_value = event.get("outputs", {}).get("value")
                if observed_value is not None and not matches(
                    observed_value, index["types"][step["node"]]
                ):
                    failures.append("policy graph value type differs: " + step["node"])
                node = index["nodes"][step["node"]]
                if node["op"] == "predicate":
                    parameters = index["predicates"][node["predicate"]]["parameters"]
                    if any(
                        value is not None and not matches(value, parameters[name])
                        for name, value in event["inputs"].items()
                        if name in parameters
                    ):
                        failures.append("policy graph argument types differ: " + step["node"])
                expected_inputs = {
                    "bo_check": identity,
                    "bo_basis": evaluation["fact_revision"],
                    **step["arguments"],
                }
                if (
                    event.get("inputs") != expected_inputs
                    or event.get("outputs") != {"value": step["value"], "status": step["status"]}
                    or event.get("call_id") != identity + ":" + step["node"]
                ):
                    failures.append("policy graph values differ: " + step["node"])
                wanted = {event_ids[r] for r in step["used"] if r in event_ids}
                actual = {
                    d.get("event") for d in event.get("depends", []) if d.get("type") == "data"
                }
                if wanted != actual:
                    failures.append("policy graph dependencies differ: " + step["node"])
                event_ids[step["node"]] = event.get("id")
            errors.extend(failures)
            if not failures:
                covered.add((evaluation["operation"], run.get("case")))
    for operation in policy["operations"]:
        for case in operation.get("cases", []):
            if (operation["id"], case) not in covered:
                errors.append("missing policy case: " + operation["id"] + "/" + case)
    return errors
