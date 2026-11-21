"""The common JSON boundary. Structural validation and semantic checks are distinct."""

from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from .data.protocol import OPERATION_ROLES

try:
    from ..bo_models import machine_registry, select_machine
except ImportError:
    from bo_models import machine_registry, select_machine

SCHEMAS = Path(__file__).parent / "schemas"
# A group amortizes admission over several ordinary envelopes. Its wire budget
# is separate; no event or snapshot gains a larger individual payload allowance.
ENVELOPE_BYTES = 24 * 1024
EVENT_BATCH_BYTES = 256 * 1024


def _shared():
    try:
        from ..bo_contracts import validate_chart
        from ..behavior_model import validate_events
        from ..observation_scope import observer_nodes
    except ImportError:
        from bo_contracts import validate_chart
        from behavior_model import validate_events
        from observation_scope import observer_nodes
    return validate_chart, validate_events, observer_nodes


@lru_cache(maxsize=32)
def _validator(directory, name):
    """Load a packaged protocol once for this observer process/version.

    Schemas belong to the installed runtime, like its Python validation code.
    Managed schema upgrades reload that runtime. Project declarations are still
    validated on every call; this cache contains no application values or source.
    """
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as exc:
        raise ValueError(
            "Install the Skill requirements.txt before using the JSON service"
        ) from exc
    path = directory / (name + ".schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    registry = Registry()
    if name == "analysis-profile":
        behavior = json.loads((directory / "behavior.schema.json").read_text(encoding="utf-8"))
        registry = registry.with_resource(behavior["$id"], Resource.from_contents(behavior))
    if name in {"project", "project-v2"}:
        # Project envelopes reference the same model contract as standalone
        # models. Register the bundled resource; validation never fetches it.
        model = json.loads((directory / "model.schema.json").read_text(encoding="utf-8"))
        registry = registry.with_resource(model["$id"], Resource.from_contents(model))
    return Draft202012Validator(schema, registry=registry)


@lru_cache(maxsize=32)
def _fast_event_validator(directory):
    """Compile the same bundled event schema; never resolve external resources.

    The native Draft 2020-12 implementation avoids Python keyword dispatch for
    every valid observation. Other schemas and detailed rejection diagnostics
    retain jsonschema. Minimal installations can still use that original path.
    """
    try:
        from jsonschema_rs import Draft202012Validator
    except ImportError:
        return None
    return Draft202012Validator(
        _validator(directory, "event").schema, validate_formats=False, offline=True
    )


def schema_check(value, name, *, max_bytes=None):
    """Validate every envelope and portable number against the loaded protocol."""
    accepted = False
    if name == "event":
        validator = _fast_event_validator(SCHEMAS)
        if validator is not None:
            try:
                accepted = validator.is_valid(value)
            except (TypeError, ValueError, OverflowError):
                # Non-JSON Python values retain the original error path. An
                # accelerator conversion error must never imply acceptance.
                pass
    if not accepted:
        errors = sorted(
            _validator(SCHEMAS, name).iter_errors(value),
            key=lambda e: str(list(e.path)),
        )
        if errors:
            raise ValueError("; ".join(f"{list(e.path)}: {e.message}" for e in errors[:12]))

    # Python accepts non-finite JSON numbers and integers wider than JS can retain.
    def portable(v):
        if type(v) is int and abs(v) > 9007199254740991:
            raise ValueError("integer exceeds JSON safe range; encode as a typed string")
        if isinstance(v, dict):
            for x in v.values():
                portable(x)
        elif isinstance(v, list):
            for x in v:
                portable(x)

    portable(value)
    encoded = json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"))
    if max_bytes is not None and len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError("observation envelope exceeds payload limit")


def schema_diagnostics(value, name):
    """Expose strict schema failures with JSON pointers for new contract callers.

    Existing throwing validators keep their original behavior. This read-only
    interface adds stable structural codes; semantic callers supply their own
    reference/ownership checks after it returns no errors.
    """
    issues = []
    for error in sorted(
        _validator(SCHEMAS, name).iter_errors(value), key=lambda e: str(list(e.path))
    ):
        pointer = "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in error.path)
        issues.append(
            {"code": "schema_" + error.validator, "path": pointer, "message": error.message}
        )
    if not issues:
        try:
            schema_check(value, name)
        except (ValueError, TypeError) as error:
            issues.append({"code": "nonportable_json", "path": "/", "message": str(error)})
    return issues


def validate_project(project):
    """Check project identity, mode choice, and machine declaration; return a detached copy."""
    schema_check(project, "project-v2" if project.get("protocol") == "bo-project/v2" else "project")
    if "behavior_bindings" in project["model"]:
        schema_check(project["model"]["behavior_bindings"], "behavior-bindings")
        if not (project.get("contracts") or {}).get("behavior"):
            raise ValueError("Native behavior bindings require a pinned behavior artifact")
    if project.get("protocol") == "bo-project/v2":
        from .project_artifacts import validate_references

        validate_references(project)
    from .policy.projection import projection_errors

    policy_errors = projection_errors(project["model"])
    if policy_errors:
        raise ValueError("Invalid policy graph: " + "; ".join(policy_errors))
    validate_chart, _, _ = _shared()
    validate_chart(project["model"])
    from .data.protocol import validate_data_projection

    validate_data_projection(project["model"])
    from .graph.relations.model import validate as validate_relations

    validate_relations(project["model"])
    if project["model"].get("project_id", project["project_id"]) != project["project_id"]:
        raise ValueError("project identity differs from graph")
    if project["selection"]["mode"] == "drive" and any(
        chart["engine"] == "python.explicit"
        for chart in machine_registry(project["model"]).values()
    ):
        raise ValueError(
            "drive mode requires an executable adapter, not an observation-only declaration"
        )
    return deepcopy(project)


def validate_event(event, project, build_id):
    """Check build identity and allowlisted capture fields; return the validated event copy."""
    return _validate_event(event, project, build_id, _event_declarations(project))


def _event_declarations(project):
    """Resolve this call's declared owners once, without a persistent model cache."""
    _, _, internal_nodes = _shared()
    nodes = {}
    for node in project["model"]["nodes"]:
        nodes.setdefault(node["id"], node)
    return nodes, internal_nodes(project["model"])


def validate_event_batch(events, project, build_id):
    """Validate every event against one request-local declaration index.

    A batch shares its project, not its validation result. Rebuilding the index
    for each request preserves edited capture declarations and observer exclusions.
    Source checks and atomic publication remain the session sink's responsibility.
    """
    declarations = _event_declarations(project)
    return [_validate_event(event, project, build_id, declarations) for event in events]


def _validate_event(event, project, build_id, declarations):
    """Apply the same schema, provenance and capture checks to one envelope."""
    schema_check(event, "event", max_bytes=ENVELOPE_BYTES)
    from .observation.provenance import trace_metadata, object_metadata, exception_metadata

    if "trace" in event:
        trace_metadata(event["trace"])
    if "provenance" in event:
        object_metadata(event["provenance"])
    if "exception" in event:
        exception_metadata(event["exception"])
    if (event["project_id"], event["model_revision"], event["build_id"]) != (
        project["project_id"],
        project["model"]["revision"],
        build_id,
    ):
        raise ValueError("event belongs to a different project, model revision or build")
    nodes, internal_nodes = declarations
    if event["node"] in internal_nodes:
        raise ValueError("observer infrastructure is not a business event")
    node = nodes.get(event["node"])
    if node is None:
        raise ValueError("unknown event node")
    if node.get("data_role") in OPERATION_ROLES and "target_source" in event["outputs"]:
        from .data.protocol import TARGET_SOURCES

        provenance = event["outputs"]["target_source"]
        if not isinstance(provenance, str) or provenance not in TARGET_SOURCES:
            raise ValueError("invalid database target_source provenance")
    if node.get("data_role") in OPERATION_ROLES:
        from .data.protocol import validate_target_access

        validate_target_access(event["outputs"])
    try:
        from ..semantic_probe import selected
    except ImportError:
        from semantic_probe import selected
    for key, direction in [("inputs", "in"), ("outputs", "out")]:
        fields = node.get("capture", {}).get(direction, {})
        if set(event[key]) - set(fields):
            raise ValueError("undeclared capture fields")
        if selected(event[key], fields) != event[key]:
            raise ValueError("capture does not match declaration")
    return deepcopy(event)


def validate_snapshot(value, project, build_id):
    """Validate snapshot identity and declared context fields.

    State mismatches remain runtime evidence for BOStateGraph to report.
    """
    schema_check(value, "snapshot", max_bytes=ENVELOPE_BYTES)
    if (value["project_id"], value["model_revision"], value["build_id"]) != (
        project["project_id"],
        project["model"]["revision"],
        build_id,
    ):
        raise ValueError("snapshot belongs to a different project, revision or build")
    if "machines" in project["model"] and value["protocol"] != "bo-snapshot/v2":
        raise ValueError("machine registry requires a v2 snapshot with state_model_id")
    _, chart = select_machine(project["model"], value.get("state_model_id"))
    if set(value["context"]) - set(chart["context"]):
        raise ValueError("snapshot has undeclared context fields")
    # Actual invalid states remain facts. BOStateGraph diagnoses, never corrects them.
    return deepcopy(value)
