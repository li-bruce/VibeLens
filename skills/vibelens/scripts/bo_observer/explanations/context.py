"""Build a bounded evidence packet from the current server-owned graph snapshot."""

from copy import deepcopy
import json

try:
    from ...bo_models import select_machine
except ImportError:
    from bo_models import select_machine

from ..graph.behavior_model import digest
from ..graph.observation_scope import display_graph
from .derived import resolve_derived

NODE_FIELDS = {
    "id",
    "label",
    "summary",
    "kind",
    "layer",
    "state_model_id",
    "network_ids",
    "concept_kind",
    "concept_id",
    "concept_definition",
    "value",
    "code_role",
    "data_role",
    "source",
    "documentation",
    "operator",
    "policy_node",
    "capture",
    "lifecycle",
    "semantic_role",
    "field",
    "field_path",
    "direction",
    "value_type",
    "event_node",
    "project_role",
    "project_path",
    "data_key",
    "data_store",
}
EDGE_FIELDS = {
    "id",
    "from",
    "to",
    "type",
    "label",
    "trigger",
    "conditions",
    "unless",
    "mapping_role",
    "code_relation",
    "data_relation",
    "evidence_kind",
    "observed",
}


def revision(view):
    """Pin both native build and conceptual/code revisions, including draft graphs."""
    return digest(
        {
            "build": view.get("manifest", {}).get("build_id"),
            "model": view.get("manifest", {}).get("model_hash"),
            "concept": view.get("concept_structure", {}).get("revision"),
            "code": view.get("code_structure", {}).get("revision"),
            "project": view.get("layout_id"),
        }
    )


def packet(view, identity, language="en"):
    """Include definitions, immediate relations and verified source, never runtime values.

    The client submits an ID, not a prompt, path, endpoint or graph. Source snippets
    come from the build's manifest rather than a second unverified file read.
    """
    if not isinstance(identity, str) or not identity or len(identity) > 2000:
        raise ValueError("Invalid explanation node identity")
    if not isinstance(language, str) or language not in {"en", "zh-CN"}:
        raise ValueError("Unsupported explanation language")
    graph = display_graph(view)
    nodes = {node["id"]: node for node in graph["nodes"]}
    if identity not in nodes:
        derived_nodes, derived_edges = resolve_derived(graph, identity)
        nodes.update((node["id"], node) for node in derived_nodes)
        graph["edges"] = [*graph["edges"], *derived_edges]
    if identity not in nodes:
        raise ValueError("Node is absent from the current graph")
    # Native declarations own capture fields. Restore the matched concept's
    # definition only for the evidence packet, mirroring the viewer overlay.
    selected = deepcopy(nodes[identity])
    if selected.get("kind") == "state" and selected.get("origin") != "concept-design":
        _, chart = select_machine(graph, selected.get("state_model_id"))
        selected["concept_definition"] = {
            "states": chart.get("states", []),
            "values": chart.get("values", []),
            "transitions": chart.get("transitions", []),
        }
    for concept in view.get("concept_structure", {}).get("nodes", []):
        if concept["id"] == identity and concept.get("concept_definition") is not None:
            for key in ("concept_id", "concept_kind", "concept_definition", "layer", "label"):
                if key in concept:
                    selected[key] = deepcopy(concept[key])
    related = sorted(
        (edge for edge in graph["edges"] if identity in (edge["from"], edge["to"])),
        key=lambda edge: (edge.get("mapping_role") != "implements", edge["id"]),
    )
    edges = related[:24]
    adjacent = sorted({edge[k] for edge in edges for k in ("from", "to")} - {identity})
    bindings = {
        **view.get("code_structure", {}).get("bindings", {}),
        **view.get("manifest", {}).get("bindings", {}),
    }
    source_ids = [identity] + [
        edge["to"] for edge in edges if edge.get("mapping_role") == "implements"
    ]
    if selected.get("event_node"):
        source_ids.append(selected["event_node"])
    sources = []
    for key in dict.fromkeys(source_ids):
        binding = bindings.get(key)
        if not binding:
            continue
        sources.append(
            {
                "node": key,
                **{
                    k: binding[k]
                    for k in (
                        "path",
                        "symbol",
                        "line",
                        "end_line",
                        "file_sha256",
                        "signature",
                        "documentation",
                    )
                    if k in binding
                },
                "snippet": binding.get("snippet", "")[:4000],
                "truncated": len(binding.get("snippet", "")) > 4000,
            }
        )
        if len(sources) == 3:
            break
    result = {
        "schema": "vibelens-explanation-context/v1",
        "revision": revision(view),
        "language": language,
        "node": {k: selected[k] for k in NODE_FIELDS if k in selected},
        "neighbors": [
            {
                k: nodes[key][k]
                for k in ("id", "label", "kind", "layer", "concept_kind")
                if k in nodes[key]
            }
            for key in adjacent
        ],
        "relations": [{k: edge[k] for k in EDGE_FIELDS if k in edge} for edge in edges],
        "sources": sources,
        "omitted_relations": max(0, len(related) - len(edges)),
        "runtime_values_included": False,
    }
    # Route methods and paths describe an API node's purpose. Runtime headers,
    # request bodies and host connection settings remain outside this packet.
    if isinstance(selected.get("api"), dict):
        result["node"]["api"] = {
            key: selected["api"][key] for key in ("methods", "path") if key in selected["api"]
        }
    if len(json.dumps(result, ensure_ascii=False).encode()) > 48000:
        raise ValueError("Node definition exceeds explanation size limit")
    return result


def validate_answer(answer, context):
    """Accept display text with exact evidence IDs; reject stale or invented identities."""
    if not isinstance(answer, dict) or set(answer) != {"node_id", "text", "evidence"}:
        raise ValueError("AI explanation has an invalid response shape")
    if answer["node_id"] != context["node"]["id"]:
        raise ValueError("AI explanation refers to another node")
    if not isinstance(answer["text"], str) or not 1 <= len(answer["text"].strip()) <= 3000:
        raise ValueError("AI explanation must contain concise text")
    allowed = {context["node"]["id"]} | {
        item["id"] for item in context["neighbors"] + context["relations"]
    }
    evidence = answer["evidence"]
    if (
        not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 16
        or any(not isinstance(key, str) or key not in allowed for key in evidence)
    ):
        raise ValueError("AI explanation cited an unknown graph identity")
    return {**answer, "text": answer["text"].strip(), "evidence": list(dict.fromkeys(evidence))}
