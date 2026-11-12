"""Preserve conceptual identities in runtime views without changing the native model."""

from copy import deepcopy

try:
    from ...bo_models import binding_machines
except ImportError:
    from bo_models import binding_machines

from ..graph.relation_identity import relation_ids
from .anchors import native_anchors
from .binding import check_binding
from .common import canonical_id
from .model import build
from .occurrences import separate_occurrences


def bind_projection(doc, model, bindings=None, *, acceptance=None, scope=None):
    """Return metadata for the viewer/recording, leaving model.machine and raw IDs intact.

    Implementation maps are static links. They do not assign a lifecycle, call ID,
    success verdict or execution witness to an unobserved concept.
    """
    checked = check_binding(doc, model, bindings, acceptance=acceptance, scope=scope)
    if not checked["valid"]:
        raise ValueError("concept binding failed: " + str(checked["errors"]))
    binding = bindings if bindings is not None else model["concepts"]
    data = build(doc)
    graph = deepcopy(data["graph"])
    anchors = native_anchors(doc, model, binding, data, lambda code, item: None)
    actual = {node["id"]: node for node in model["nodes"]}
    selected = set(checked["scope"])
    graph["nodes"] = [node for node in graph["nodes"] if node["id"] in selected]
    selected_nodes = {node["id"] for node in graph["nodes"]}
    graph["edges"] = [
        edge
        for edge in graph["edges"]
        if selected.intersection(relation_ids(edge))
        and edge["from"] in selected_nodes
        and edge["to"] in selected_nodes
    ]
    # Scope and confirmation use canonical concept IDs; only display occurrences
    # are separated. A variable reused in several conceptual roles stays one
    # physical declaration with several explicit concept-to-implementation maps.
    graph["graph_roots"] = [key for key in graph["graph_roots"] if key in selected_nodes]
    aliases = separate_occurrences(graph, model)
    machines = binding_machines(binding, model)
    for node in graph["nodes"]:
        for conceptual, native in machines.items():
            if node.get("concept_kind") in {
                "state",
                "state_model",
                "event",
                "guard",
                "logical_effect",
                "transition",
            } and (
                node["id"] == canonical_id("state-model", conceptual)
                or any(
                    node["id"].startswith(canonical_id(kind, conceptual) + ":")
                    for kind in ("state", "event", "guard", "effect", "transition")
                )
            ):
                if "machines" in model:
                    node["state_model_id"] = native
    for network in graph.get("networks", []):
        network["nodes"] = [
            aliases.get(key, key)
            for key in network["nodes"]
            if aliases.get(key, key) in {node["id"] for node in graph["nodes"]}
        ]
        network["edges"] = [
            edge["id"]
            for edge in graph["edges"]
            if edge["from"] in network["nodes"] and edge["to"] in network["nodes"]
        ]
    graph["networks"] = [network for network in graph.get("networks", []) if network["nodes"]]
    selected_nodes = {node["id"] for node in graph["nodes"]}
    for concept, targets in anchors.items():
        concept = aliases.get(concept, concept)
        if concept not in selected_nodes:
            continue
        for target in targets:
            if target not in actual or target == concept:
                continue
            if target not in selected_nodes:
                graph["nodes"].append(deepcopy(actual[target]))
                selected_nodes.add(target)
            graph["edges"].append(
                {
                    "id": canonical_id("concept-implements", concept, target),
                    "from": concept,
                    "to": target,
                    "type": "maps",
                    "code_relation": "maps",
                    "mapping_role": "implements",
                    "origin": "concept-binding",
                    "label": "Implemented by",
                    "evidence_kind": "binding",
                    "observed": False,
                }
            )
    return {
        "schema": "bo-concept-projection/v1",
        "revision": checked["semantic_revision"],
        "nodes": graph["nodes"],
        "networks": graph.get("networks", []),
        "edges": graph["edges"],
        "graph_roots": [key for key in graph["graph_roots"] if key in selected_nodes],
        "index": deepcopy(data["index"]),
        "occurrences": aliases,
        "relation_occurrences": graph["relation_occurrences"],
        "stage": "bound",
        "execution_authority": False,
    }
