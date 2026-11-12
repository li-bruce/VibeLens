"""Maintain AI-authored, layer-specific names as a separate presentation artifact.

The coding assistant translates the inventory. This module validates identities,
locales and freshness; it never calls a model, renames source or changes behavior.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

try:
    from ...bo_models import machine_registry
except ImportError:
    from bo_models import machine_registry

from ..graph.behavior_model import contained
from ..workflow.sync_io import write

FILE = "bo_stategraph/config/semantic-names.json"
SCHEMA = "bo-semantic-names/v1"
CATEGORIES = ("nodes", "concepts", "edges", "states", "events")


def signature(value):
    """Fingerprint meaning and source context, excluding coordinates and runtime values."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def validate(document):
    """Reject invalid locale maps before a renderer can use them."""
    try:
        from ...bo_contracts import validate_names
    except ImportError:
        from bo_contracts import validate_names

    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError("Invalid semantic names schema")
    if set(document) - {"schema", "locales", "names", "basis"}:
        raise ValueError("Unknown semantic names field")
    locales = document.get("locales")
    if (
        not isinstance(locales, list)
        or not locales
        or any(not isinstance(locale, str) or locale not in {"en", "zh-CN"} for locale in locales)
        or len(set(locales)) != len(locales)
    ):
        raise ValueError("Semantic names need en and/or zh-CN")
    validate_names({"presentation": {"names": document.get("names")}})
    basis = document.get("basis")
    if (
        not isinstance(basis, dict)
        or set(basis) - set(CATEGORIES)
        or any(not isinstance(entries, dict) for entries in basis.values())
    ):
        raise ValueError("Invalid semantic names basis")
    for category, entries in document["names"].items():
        for identity, labels in entries.items():
            if not isinstance(labels, dict) or not set(locales).issubset(labels):
                raise ValueError("Semantic name is missing a requested locale: " + identity)
            digest = basis.get(category, {}).get(identity)
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
            ):
                raise ValueError("Semantic name needs its inventory basis: " + identity)
    return document


def read_names(root):
    """Load presentation-only names; an absent artifact keeps legacy projects readable."""
    path = contained(root, FILE)
    return validate(json.loads(path.read_text(encoding="utf-8-sig"))) if path.is_file() else None


def overlay_model(root, model):
    """Detach display metadata while preserving exact business, source and event identities."""
    document = read_names(root)
    if not document:
        return model
    result = deepcopy(model)
    names = result.setdefault("presentation", {}).setdefault("names", {})
    for category, entries in document["names"].items():
        names.setdefault(category, {}).update(entries)
    return result


def inventory(view):
    """Describe actual graph items for the coding assistant, including generated fields."""
    items, nodes, edges = {}, {}, {}
    for graph in [
        view.get("concept_structure"),
        # Native declarations retain capture ownership when a bound concept
        # reuses the ID. A conceptual empty capture must not erase real fields.
        view.get("model"),
        view.get("project_structure"),
        view.get("api_structure"),
        view.get("code_structure"),
    ]:
        if not graph:
            continue
        for node in graph.get("nodes", []):
            nodes[node["id"]] = {**nodes.get(node["id"], {}), **node}
        edges.update({edge["id"]: edge for edge in graph.get("edges", [])})

    def add(category, identity, context):
        key = (category, identity)
        item = {"category": category, "id": identity, **context}
        items[key] = {**item, "basis": signature(item)}

    def field(owner, direction, name, spec, path=()):
        identity = f"field:{owner['id']}:{direction}:{name}" + "".join(
            ":" + quote(p, safe="~()*!.'-") for p in path
        )
        add(
            "nodes",
            identity,
            {
                "layer": "symbols",
                "label": path[-1] if path else name,
                "owner": owner["id"],
                "direction": direction,
                "field_type": spec,
            },
        )
        if isinstance(spec, dict):
            for key, child in spec.items():
                field(owner, direction, name, child, (*path, key))

    for node in nodes.values():
        conceptual = bool(node.get("concept_kind"))
        category = "concepts" if conceptual else "nodes"
        identity = node.get("concept_id", node["id"]) if conceptual else node["id"]
        context = {
            key: node[key]
            for key in (
                "layer",
                "kind",
                "concept_kind",
                "label",
                "summary",
                "concept_definition",
                "source",
                "documentation",
                "code_role",
                "data_role",
                "parent",
                "api",
            )
            if key in node
        }
        # Current line numbers are navigation coordinates, not a new meaning.
        if "source" in context:
            context["source"] = {
                key: value
                for key, value in context["source"].items()
                if key not in {"line", "end_line", "column", "end_column"}
            }
        add(category, identity, context)
        for direction, fields in node.get("capture", {}).items():
            for name, spec in fields.items():
                # Match capture-fields.js: old declarations can list transaction
                # outcomes on queries that never produce such a field.
                action = node.get("data_metadata", {}).get("action")
                if (
                    node.get("data_role") in {"query", "write", "transaction", "transform"}
                    and name == "committed"
                    and action
                    and action != "transaction"
                ):
                    continue
                field(node, direction, name, spec)
    for edge in edges.values():
        # Mechanical containment/mapping captions already use localized type grammar.
        # Authored relationship details require their own translation, not a type rename.
        if edge.get("label") and edge.get("origin") not in {
            "capture-field",
            "source-ast",
            "python-ast",
            "code-index",
            "concept-binding",
        }:
            add(
                "edges",
                edge["id"],
                {
                    key: edge[key]
                    for key in ("from", "to", "type", "label", "event", "origin")
                    if key in edge
                },
            )
    model = view.get("model", {})
    # Keep translation identity separate from local values: two objects may both
    # be "ready" while requiring different business language and explanations.
    for model_id, chart in (
        machine_registry(model) if "machine" in model or "machines" in model else {}
    ).items():
        for category, values, labels in (
            ("states", chart.get("values", []), chart.get("labels", {})),
            ("events", chart.get("events", {}), chart.get("event_labels", {})),
        ):
            for value in values:
                key = (
                    json.dumps([model_id, value], ensure_ascii=False, separators=(",", ":"))
                    if "machines" in model
                    else value
                )
                context = {"layer": "state", "label": labels.get(value, value)}
                if "machines" in model:
                    context.update(state_model_id=model_id, value=value)
                add(category, key, context)
    return sorted(items.values(), key=lambda item: (item["category"], item["id"]))


def project_inventory(root, model=None):
    """Read current definitions and enabled source indexes without starting the application."""
    from ..model_io import read_model
    from ..observation.concept_context import ConceptContext
    from ..code_graph.service import CodeGraph

    root = Path(root).resolve()
    config = root / "sync.json"
    cfg = json.loads(config.read_text(encoding="utf-8-sig")) if config.is_file() else {}
    path = contained(root, cfg.get("model", "bo_stategraph/project.json"))
    if model is None and not path.is_file():
        from .bo_design import BODesign

        return inventory(BODesign(root).view())
    model = model if model is not None else read_model(path)
    source = CodeGraph(root, persist=False)
    # The API inventory already scans the owned source. Reuse that complete
    # snapshot rather than a viewport slice with a 5000-node display cap.
    complete = source.refresh()[0]
    project_nodes = [
        node
        for node in complete["nodes"]
        if node.get("code_role") in {"directory", "file"}
        or node.get("reference_scope") == "project"
    ]
    project_ids = {node["id"] for node in project_nodes}
    view = {
        "model": model,
        "concept_structure": ConceptContext(root, model).view(),
        "project_structure": {
            "nodes": project_nodes,
            "edges": [
                edge
                for edge in complete["edges"]
                if edge["from"] in project_ids and edge["to"] in project_ids
            ],
        },
        "api_structure": source.api_snapshot(),
    }
    if (root / ".stategraph/code-graph.json").is_file():
        # Names cover the enabled inventory, not just the current 5000-item
        # viewport slice. Refresh remains scoped to application-owned sources.
        view["code_structure"] = complete
    return inventory(view)


def assess(items, document):
    """List missing or stale meanings instead of silently passing untranslated graphs."""
    if document is None:
        return {
            "configured": False,
            "valid": True,
            "status": "not_configured",
            "missing": [],
            "stale": [],
        }
    validate(document)
    missing, stale = [], []
    for item in items:
        category, identity = item["category"], item["id"]
        labels = document["names"].get(category, {}).get(identity, {})
        for locale in document["locales"]:
            if not labels.get(locale):
                missing.append({"category": category, "id": identity, "locale": locale})
        if labels and document["basis"].get(category, {}).get(identity) != item["basis"]:
            stale.append({"category": category, "id": identity})
    return {
        "configured": True,
        "valid": not missing and not stale,
        "status": "needs_update" if missing or stale else "current",
        "missing": missing,
        "stale": stale,
    }


def check_project(root, model=None):
    """Ordinary iteration scans report naming gaps only after the artifact is enabled."""
    try:
        document = read_names(root)
        return assess(project_inventory(root, model) if document else [], document)
    except (ValueError, OSError, TypeError) as error:
        return {"configured": True, "valid": False, "status": "invalid", "errors": [str(error)]}


def install(root, document, items):
    """Accept only a complete translation of the current inventory; preserve stale evidence."""
    report = assess(items, document)
    if not report["valid"]:
        raise ValueError(json.dumps(report, ensure_ascii=False))
    write(contained(root, FILE), validate(document))
    return report
