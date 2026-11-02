"""Compare mapped observations with independently read implementation facts.

No desired business outcome belongs here. A faithfully displayed defect can pass
this check while the separately authored business contract fails.
"""

import json

try:
    from ...bo_stategraph import BOStateGraph, bo_validate_export
except ImportError:
    from bo_stategraph import BOStateGraph, bo_validate_export


def at(value, path):
    for key in path:
        value = value[key]
    return value


def equal(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(
        b, sort_keys=True, allow_nan=False
    )


def context_path(path, *, native=False):
    """Validate a concrete JSON path and exclude observation-derived native roots."""
    if not isinstance(path, list) or not path or any(type(part) not in (str, int) for part in path):
        raise ValueError("invalid context mapping path")
    if native and path[0] in {"events", "projection", "mapping_checks", "stategraph_export"}:
        raise ValueError("context mapping requires native facts independent of observation")


def context_fields(plan):
    """Validate optional event-context rows before any acceptance code consumes them."""
    fields = (plan or {}).get("context_fields", [])
    if not isinstance(fields, list):
        raise ValueError("context_fields must be a list")
    for field in fields:
        required = {
            "id",
            "node",
            "phase",
            "case",
            "actual",
            "mapped",
            "source",
        }
        if not isinstance(field, dict) or not required <= set(field) <= required | {"each"}:
            raise ValueError("context mapping needs exact source/event/native bindings")
        for name in ("id", "node", "phase", "case", "source"):
            if not isinstance(field[name], str) or not field[name].strip():
                raise ValueError("context mapping needs nonempty string bindings")
        for name in ("actual", "mapped"):
            context_path(field[name], native=name == "actual")
        if field["mapped"][0] not in {"trace", "provenance", "exception"}:
            raise ValueError("context mapping must address tracing metadata")
        if "each" in field:
            selected = field["each"]
            if not isinstance(selected, dict) or set(selected) != {
                "collection",
                "actual_key",
                "mapped_key",
            }:
                raise ValueError("context collection needs exact native/event key bindings")
            context_path(selected["collection"], native=True)
            if (
                not isinstance(selected["actual_key"], list)
                or not selected["actual_key"]
                or not isinstance(selected["mapped_key"], list)
                or len(selected["actual_key"]) != len(selected["mapped_key"])
            ):
                raise ValueError("context collection needs matching nonempty key paths")
            for name in ("actual_key", "mapped_key"):
                for path in selected[name]:
                    context_path(path, native=name == "actual_key")
    return fields


def context_pairs(run, field):
    """Join complete event facts to native rows without pairing by arrival order.

    Legacy rows compare one native fact with every matching event. Collection
    rows require both sides of each explicit key; no native sample or observed
    invocation may silently disappear. Several equal-key point facts are all
    compared, while duplicate native keys are ambiguous and rejected.
    """
    events = [
        event
        for event in run.get("events", [])
        if event.get("node") == field["node"]
        and event.get("phase") == field["phase"]
        and not event.get("context_only")
    ]
    if not events:
        raise ValueError("required context observation is missing")
    if "each" not in field:
        actual = at(run, field["actual"])
        return [(actual, event) for event in events]
    selected = field["each"]
    records = at(run, selected["collection"])
    if not isinstance(records, list) or not records:
        raise ValueError("required native context records are missing")

    def key(value, paths):
        parts = tuple(at(value, path) for path in paths)
        if any(type(part) not in (str, int) or part == "" for part in parts):
            raise ValueError("context join keys must be concrete strings or integers")
        return parts

    indexed = {}
    for record in records:
        identity = key(record, selected["actual_key"])
        if identity in indexed:
            raise ValueError("duplicate native context join key")
        indexed[identity] = at(record, field["actual"])
    seen, pairs = set(), []
    for event in events:
        identity = key(event, selected["mapped_key"])
        if identity not in indexed:
            raise ValueError("observed invocation has no independent native context record")
        seen.add(identity)
        pairs.append((indexed[identity], event))
    if seen != set(indexed):
        raise ValueError("native invocation has no required context observation")
    return pairs


def validate_plan(plan, model):
    """The project owns a protected list, not a list inferred from submitted checks."""
    if not isinstance(plan, dict) or plan.get("schema") != "bo-mapping/v1":
        raise ValueError("implementation mapping plan bo-mapping/v1 is required")
    for name in ("cases", "modes", "fields"):
        if not isinstance(plan.get(name), list) or not plan[name]:
            raise ValueError("mapping plan needs " + name)
    if len(set(plan["cases"])) != len(plan["cases"]) or len(set(plan["modes"])) != len(
        plan["modes"]
    ):
        raise ValueError("duplicate mapping case or mode")
    if set(plan["modes"]) - {"on", "off", "fault"}:
        raise ValueError("unknown mapping mode")
    if not plan.get("source"):
        raise ValueError("mapping source is required")
    for name in ("actual_collection", "actual_id"):
        if not isinstance(plan.get(name), list) or not plan[name]:
            raise ValueError("mapping plan needs " + name)
    nodes = {n["id"] for n in model["nodes"]}
    ids, mapped = set(), set()
    for field in plan["fields"]:
        if not field.get("id") or field["id"] in ids or field.get("node") not in nodes:
            raise ValueError("mapping field needs a unique identity and graph node")
        ids.add(field["id"])
        for name in ("actual", "mapped"):
            if not isinstance(field.get(name), list) or (name == "mapped" and not field[name]):
                raise ValueError("mapping field needs actual and mapped paths")
        if "keys" in field and (not field["keys"] or len(set(field["keys"])) != len(field["keys"])):
            raise ValueError("mapping selected keys must be nonempty and unique")
        mapped.add(tuple(field["mapped"]))
    if not {("state",), ("revision",), ("build_id",)} <= mapped:
        raise ValueError("mapping plan must cover state, complete revision and build identity")
    for name in model["machine"]["context"]:
        if ("context",) not in mapped and ("context", name) not in mapped:
            raise ValueError("mapping plan omits context field: " + name)
    if model["machine"].get("execution") and ("configuration",) not in mapped:
        raise ValueError("mapping plan must cover the complete activity configuration")
    selected = plan.get("export", {})
    if selected.get("case") not in plan["cases"] or selected.get("mode") not in plan["modes"]:
        raise ValueError("mapping plan must select the actual public export case and mode")
    for field in context_fields(plan):
        if not field["id"] or field["id"] in ids or field["node"] not in nodes:
            raise ValueError("context mapping needs a unique identity and known node")
        ids.add(field["id"])
        if field["case"] not in plan["cases"] or not field["source"]:
            raise ValueError("context mapping needs a protected case and native source")
        if field["phase"] not in {
            "enter",
            "return",
            "read",
            "decision",
            "wait",
            "commit",
            "change",
            "error",
        }:
            raise ValueError("invalid context mapping phase")
    return plan


def protected_plan_errors(before, after):
    if not before:
        return []
    if not after:
        return ["mapping plan was removed"]
    errors = []
    for name in ("cases", "modes", "fields"):
        if any(v not in after.get(name, []) for v in before[name]):
            errors.append("mapping coverage was removed or changed: " + name)
    if any(
        field not in after.get("context_fields", []) for field in before.get("context_fields", [])
    ):
        errors.append("mapping coverage was removed or changed: context_fields")
    for name in ("source", "actual_collection", "actual_id", "export"):
        if before.get(name) != after.get(name):
            errors.append("mapping binding changed: " + name)
    return errors


def assess_context_fields(payload, plan):
    """Compare observed identity/object context with separately read native facts.

    Missing is not null. A known absent principal must be explicitly observed as
    null; a missing field is an incomplete witness, even when business HTTP is right.
    """
    errors, checked = [], 0
    try:
        fields = context_fields(plan)
    except (ValueError, TypeError, AttributeError) as error:
        return {"valid": False, "checks": 0, "errors": ["invalid context mapping: " + str(error)]}
    for field in fields:
        try:
            runs = [
                run
                for run in payload.get("runs", [])
                if run.get("case") == field["case"] and run.get("mode") == "on"
            ]
            if len(runs) != 1:
                raise ValueError("context mapping needs one actual enabled case")
            run = runs[0]
            for actual, event in context_pairs(run, field):
                checked += 1
                mapped = at(event, field["mapped"])
                if not equal(actual, mapped):
                    errors.append(
                        {
                            "check": field["id"],
                            "case": field["case"],
                            "event": event["id"],
                            "error": "observed context differs from native implementation",
                            "actual": actual,
                            "mapped": mapped,
                            "source": field["source"],
                        }
                    )
        except (ValueError, TypeError, KeyError, IndexError) as error:
            errors.append({"check": field["id"], "error": str(error)})
    return {"valid": not errors, "checks": checked, "errors": errors}


def context_coverage_errors(payload, plan):
    """New observation metadata cannot bypass the existing independent mapping plan."""
    try:
        fields = context_fields(plan)
    except (ValueError, TypeError, AttributeError) as error:
        return ["invalid context mapping: " + str(error)]
    observed = {
        (run.get("case"), event.get("id"), event.get("node"), event.get("phase"), key)
        for run in payload.get("runs", [])
        if run.get("mode") == "on"
        for event in run.get("events", [])
        if not event.get("context_only")
        for key in event.get("provenance", {})
    }
    covered, errors = set(), []
    for field in fields:
        for run in payload.get("runs", []):
            if run.get("case") != field["case"] or run.get("mode") != "on":
                continue
            try:
                for _, event in context_pairs(run, field):
                    for key in ("actor", "workflow_id", "objects"):
                        if field["mapped"] in (["provenance"], ["provenance", key]):
                            covered.add(
                                (field["case"], event.get("id"), field["node"], field["phase"], key)
                            )
            except (ValueError, TypeError, KeyError, IndexError) as error:
                errors.append({"check": field["id"], "error": str(error)})
    missing = {(case, node, phase, key) for case, _, node, phase, key in observed - covered}
    return [
        "native context mapping omits observed component: " + "/".join(map(str, item))
        for item in sorted(missing, key=str)
    ] + errors


def assess_projections(payload, plan, model, build_id):
    validate_plan(plan, model)
    errors, checks = [], 0
    public = bo_validate_export(payload["stategraph_export"])
    if (
        public["model"] != model
        or public["build_id"] != build_id
        or payload.get("build_id") != build_id
    ):
        raise ValueError("mapping projection belongs to another model or build")
    graph = BOStateGraph(model, build_id=build_id)
    runs = {}
    for run in payload.get("runs", []):
        key = (run["case"], run["mode"])
        if key in runs:
            raise ValueError("duplicate actual scenario: " + str(key))
        runs[key] = run
    required = {(case, mode) for case in plan["cases"] for mode in plan["modes"]}
    if required != set(runs):
        raise ValueError("mapping scenario coverage differs from protected plan")
    for key in sorted(required):
        run = runs[key]
        sample = run["projection"]
        if sample["build_id"] != build_id:
            raise ValueError("scenario projection has wrong build")
        instances = sample["instances"]
        if not equal(instances, graph.bo_instances(sample["machine"])):
            raise ValueError("scenario instances differ from its runtime machine")
        for item in instances:
            if item.get("missing"):
                errors.append(
                    {
                        "case": key,
                        "instance": item["observed"]["instance_id"],
                        "error": "required runtime evidence is incomplete",
                        "missing": item["missing"],
                    }
                )
        mapped = {item["observed"]["instance_id"]: item["observed"] for item in instances}
        records = at(run, plan["actual_collection"])
        actual = {at(item, plan["actual_id"]): item for item in records}
        if len(actual) != len(records) or len(mapped) != len(instances):
            raise ValueError("duplicate actual or mapped instance")
        checks += 1
        if sorted(actual) != sorted(mapped):
            errors.append({"case": key, "error": "actual and exported instance identities differ"})
        for ident, raw in actual.items():
            if ident not in mapped:
                continue
            for field in plan["fields"]:
                checks += 1
                a, b = at(raw, field["actual"]), at(mapped[ident], field["mapped"])
                if "keys" in field:
                    if set(a) != set(field["keys"]):
                        raise ValueError("actual configuration fields differ from mapping plan")
                    a, b = ({k: value[k] for k in field["keys"]} for value in (a, b))
                if not equal(a, b):
                    errors.append(
                        {
                            "case": key,
                            "instance": ident,
                            "field": field["id"],
                            "node": field["node"],
                            "source": plan["source"],
                            "error": "actual value differs from exported projection",
                        }
                    )
    selected = runs[(plan["export"]["case"], plan["export"]["mode"])]["projection"]
    if not equal(public["instances"], selected["instances"]) or not equal(
        public["runtime"]["machine"], selected["machine"]
    ):
        errors.append("public export differs from its protected scenario projection")
    return errors, checks


def instance_witnesses(instances, actual, *, case, source):
    """actual is read from the application's store by the scenario runner."""
    mapped = {i["observed"]["instance_id"]: i["observed"] for i in instances}
    result = [
        {
            "id": case + ":instances",
            "source": source,
            "projection": "bo_instances.instance_id",
            "actual": sorted(actual),
            "mapped": sorted(mapped),
        }
    ]
    for ident, fields in actual.items():
        for name, value in fields.items():
            result.append(
                {
                    "id": f"{case}:{ident}:{name}",
                    "source": source,
                    "projection": "bo_instances." + name,
                    "actual": value,
                    "mapped": mapped.get(ident, {}).get(name),
                }
            )
    return result


def assess(payload, *, required=False, plan=None, model=None, build_id=None):
    checks = payload.get("mapping_checks", [])
    errors = []
    context = assess_context_fields(payload, plan)
    errors.extend(context["errors"])
    if required:
        errors.extend(context_coverage_errors(payload, plan))
    if required and not checks:
        errors.append("no implementation mapping witnesses")
    projected = 0
    if plan is not None or required:
        try:
            projection_errors, projected = assess_projections(payload, plan, model, build_id)
            errors.extend(projection_errors)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            errors.append("invalid or incomplete implementation mapping: " + str(exc))
    seen = set()
    for check in checks:
        ident = check.get("id")
        if not ident or ident in seen:
            errors.append("missing or duplicate mapping check identity")
        seen.add(ident)
        if not check.get("source") or not check.get("projection"):
            errors.append({"check": ident, "error": "source and projection provenance required"})
        if "actual" not in check or "mapped" not in check:
            errors.append({"check": ident, "error": "missing actual or mapped value"})
            continue
        encode = lambda value: json.dumps(
            value, sort_keys=True, allow_nan=False, ensure_ascii=False
        )
        if encode(check["actual"]) != encode(check["mapped"]):
            errors.append(
                {
                    "check": ident,
                    "error": "mapped value differs from implementation",
                    "actual": check["actual"],
                    "mapped": check["mapped"],
                }
            )
    return {
        "valid": not errors,
        "errors": errors,
        "checks": len(checks),
        "projection_checks": projected,
        "context_checks": context["checks"],
        "scope": "Protected scenario/field plan against actual source facts and public projections; unexercised behavior remains unknown.",
    }
