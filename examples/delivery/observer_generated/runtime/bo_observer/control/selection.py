"""Bounded graph-path selection and non-destructive recorded-event filtering."""

from collections import deque
from copy import deepcopy
import re

from ..graph.behavior_model import digest
from ..graph.observation_scope import capture_owners, display_graph
from ..data.protocol import OPERATION_ROLES

NODE_TYPES = {
    "business",
    "function",
    "state",
    "decision",
    "resource",
    "data",
    "effect",
    "wait",
    "store",
    "dataset",
    "column",
    "query",
    "write",
    "transaction",
    "transform",
    "code-file",
    "code-directory",
    "code-class",
    "code-function",
    "code-parameter",
    "code-unresolved",
    "code-endpoint",
    "code-reference",
}
RELATIONS = {
    "call",
    "flow",
    "transition",
    "guard",
    "data",
    "resource",
    "join",
    "shared",
    "other",
    "contains",
    "reads",
    "writes",
    "transforms",
    "maps",
    "references",
    "code-defines",
    "code-contains",
    "code-exports",
    "code-links",
    "code-dependency",
    "code-inherits",
    "code-calls",
    "code-parameter",
    "code-imports",
    "code-handles",
    "code-maps",
}


class ClarificationRequired(ValueError):
    def __init__(self, query, candidates):
        self.question = {
            "query": query,
            "candidates": [
                {"id": node["id"], "label": node["label"], "source": node.get("source")}
                for node in candidates
            ],
        }
        super().__init__("Choose the graph node that matches: " + query)


def model_revision(view):
    """Design has no runtime revision; its declaration digest identifies the draft."""
    revision = view["model"].get("revision")
    if revision is None and view.get("stage") == "design":
        revision = view.get("manifest", {}).get("build_id")
    if not isinstance(revision, str) or not revision:
        raise ValueError("A runtime revision or a versioned design declaration is required")
    return revision


def resolve(nodes, query):
    """Resolve exact identities first; ambiguous labels need dialogue, not a guess."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("A graph node identity or label is required")
    if query in nodes:
        return query
    matches = [
        node for node in nodes.values() if query.casefold() == str(node.get("label", "")).casefold()
    ]
    if len(matches) != 1:
        raise ClarificationRequired(query, matches)
    return matches[0]["id"]


def relation_type(edge):
    if edge.get("origin") in {"code-index", "source-ast"} and edge.get("code_relation"):
        return "code-" + edge["code_relation"]
    if edge.get("type") == "data" and edge.get("data_relation") in RELATIONS:
        return edge["data_relation"]
    if edge.get("origin") in {"python-ast", "source-ast"} and edge.get("type") == "flow":
        return "call"
    return edge["type"] if edge.get("type") in RELATIONS else "other"


def view_types(node):
    """Match graph-core.js membership: one physical node may serve several views."""
    if node.get("code_role"):
        return {"code-" + node["code_role"]}
    data_role = node.get("data_role")
    if data_role in {"store", "dataset", "column"} | OPERATION_ROLES:
        return {data_role}
    kind, role = node.get("kind"), node.get("execution_role")
    if node.get("layer") == "business":
        visual = "business"
    elif kind == "state":
        visual = "state"
    elif kind == "resource" or role == "resource":
        visual = "resource"
    elif kind == "decision" or role == "join":
        visual = "decision"
    elif kind in {"data", "effect", "wait"}:
        visual = kind
    else:
        visual = "function"
    types = {visual}
    if "business" in (node.get("semantic_roles") or []):
        types.add("business")
    if node.get("semantic_role") == "state_parameter":
        types.add("state")

    # Empty JSON objects/arrays are truthy in the browser. A field descriptor is
    # still a descriptor when empty; it must not become a callable source node.
    def js_truthy(value):
        return value is not None and value is not False and value != "" and value != 0

    if js_truthy(node.get("source")) and kind != "state" and not js_truthy(node.get("field")):
        types.add("function")
    return types


def check_path_context(nodes, edges, selected, eligible, edge_types):
    """Keep real cross-type bridges within the viewer's one-hop boundary contract."""
    context = set(nodes)
    if not context:
        return
    adjacent = {identity: set() for identity in selected}
    for edge in edges:
        if (
            edge["from"] == edge["to"]
            or edge["type"] == "contains"
            or relation_type(edge) not in edge_types
            or edge["from"] not in selected
            or edge["to"] not in selected
        ):
            continue
        adjacent[edge["from"]].add(edge["to"])
        adjacent[edge["to"]].add(edge["from"])
    if any(len(adjacent[node]) < 2 or not adjacent[node] & eligible for node in context):
        raise ValueError("The path needs additional node types beyond one-hop boundary context")


def build_plan(view, spec, recording=None):
    """Produce a view specification over current identities; never rewrite the graph."""
    allowed = {
        "action",
        "label",
        "anchors",
        "depth",
        "direction",
        "nodes",
        "edges",
        "layout",
        "max_nodes",
        "loop",
    }
    if (
        not isinstance(spec, dict)
        or set(spec) - allowed
        or spec.get("action") not in {"view", "replay"}
    ):
        raise ValueError("Only view and replay presentation specifications are supported")
    label, anchors = spec.get("label"), spec.get("anchors")
    if (
        not isinstance(label, str)
        or not 1 <= len(label.strip()) <= 40
        or not isinstance(anchors, list)
        or not 1 <= len(anchors) <= 12
    ):
        raise ValueError("A short view name and one to twelve focus nodes are required")
    depth, budget = spec.get("depth", 1), spec.get("max_nodes", 80)
    direction, layout = spec.get("direction", "both"), spec.get("layout", "layered")
    if (
        type(depth) is not int
        or not 0 <= depth <= 4
        or type(budget) is not int
        or not 1 <= budget <= 300
        or direction not in {"both", "forward", "backward"}
        or layout not in {"layered", "cluster", "stress"}
    ):
        raise ValueError("Invalid depth, direction, display budget or layout")
    node_types, edge_types = spec.get("nodes", sorted(NODE_TYPES)), spec.get(
        "edges", sorted(RELATIONS)
    )
    if (
        not isinstance(node_types, list)
        or not node_types
        or any(node not in NODE_TYPES for node in node_types)
        or not isinstance(edge_types, list)
        or not edge_types
        or any(edge not in RELATIONS for edge in edge_types)
    ):
        raise ValueError("Unknown or empty node/relation type selection")
    if "loop" in spec and type(spec["loop"]) is not bool:
        raise ValueError("loop must be boolean")
    model = display_graph(view)
    nodes = {node["id"]: node for node in model["nodes"]}
    if len(nodes) != len(model["nodes"]):
        raise ValueError("Duplicate graph identities")
    edges = model["edges"]
    if len({edge["id"] for edge in edges}) != len(edges):
        raise ValueError("Duplicate relation identities")
    if any(edge["from"] not in nodes or edge["to"] not in nodes for edge in edges):
        raise ValueError("Graph contains an unknown relation endpoint")
    seeds = list(dict.fromkeys(resolve(nodes, query) for query in anchors))
    requested_types = set(node_types)
    eligible = {identity for identity, node in nodes.items() if view_types(node) & requested_types}
    adjacent = {node: [] for node in nodes}
    for edge in edges:
        if relation_type(edge) not in edge_types:
            continue
        if direction in {"forward", "both"}:
            adjacent[edge["from"]].append((edge["to"], edge["id"]))
        if direction in {"backward", "both"}:
            adjacent[edge["to"]].append((edge["from"], edge["id"]))
    selected = set(seeds)
    # Ordered anchors describe a chain. Keep an actual shortest path between
    # successive anchors; failure to connect is an ambiguity, not an invented edge.
    for start, end in zip(seeds, seeds[1:]):
        previous, queue = {start: None}, deque([start])
        while queue and end not in previous:
            here = queue.popleft()
            for other, _ in adjacent[here]:
                if other not in previous:
                    previous[other] = here
                    queue.append(other)
        if end not in previous:
            raise ValueError(
                "No declared path connects focus nodes under these node/relation filters: "
                + start
                + " -> "
                + end
            )
        here = end
        while here is not None:
            selected.add(here)
            here = previous[here]
    if not set(seeds) <= eligible:
        raise ValueError("Focus nodes are excluded by the requested node type filter")
    path_context = selected - eligible
    check_path_context(path_context, edges, selected, eligible, edge_types)
    if len(selected) > budget:
        raise ValueError("The focus path exceeds the display budget; narrow the chain")
    queue, visited = deque((node, 0) for node in sorted(selected)), set(selected)
    limited = False
    while queue:
        node, level = queue.popleft()
        if level >= depth:
            continue
        for other, _ in sorted(adjacent[node]):
            if other in visited or other not in eligible:
                continue
            if len(selected) >= budget:
                limited = True
                continue
            visited.add(other)
            selected.add(other)
            queue.append((other, level + 1))
    included = [
        edge["id"]
        for edge in edges
        if edge["from"] in selected and edge["to"] in selected and relation_type(edge) in edge_types
    ]
    boundaries = [
        deepcopy(edge) for edge in edges if (edge["from"] in selected) != (edge["to"] in selected)
    ]
    base = {
        "project_id": view.get("layout_id")
        or model.get("project_id")
        or model.get("presentation", {}).get("layout_id"),
        "model_revision": model_revision(view),
        "model_hash": digest(model),
        "build_id": view.get("manifest", {}).get("build_id"),
    }
    result = {
        "schema": "vibelens-control-plan/v1",
        "base": base,
        "action": spec["action"],
        "label": label.strip(),
        "anchors": seeds,
        "node_ids": sorted(selected),
        "context_node_ids": sorted(path_context),
        "edge_ids": included,
        "boundaries": boundaries[:300],
        "limits_hit": limited or len(boundaries) > 300,
        "filters": {
            "nodes": sorted(set(node_types)),
            "regions": sorted(set(node_types)),
            "edges": sorted(set(edge_types)),
        },
        "layout": layout,
        "recording": None,
    }
    if spec["action"] == "replay":
        if not recording or recording.get("status") == "recording":
            raise ValueError("Choose a stopped recording before filtering replay")
        if (
            recording.get("build_id") != base["build_id"]
            or recording.get("context", {}).get("model", {}).get("revision")
            != base["model_revision"]
        ):
            raise ValueError("Recording belongs to a different model/build")
        observed = set(capture_owners(view, selected, strict=False))
        events = [event for event in recording["events"] if event.get("node") in observed]
        if not events:
            raise ValueError("This recording contains no observed events on the selected path")
        if any(
            event.get("build_id") != base["build_id"]
            or event.get("model_revision") != base["model_revision"]
            for event in events
        ):
            raise ValueError("Recording contains stale events on the selected path")
        result["recording"] = {
            "id": recording["id"],
            "build_id": recording["build_id"],
            "event_ids": [event["id"] for event in events],
            "events_hash": digest(recording["events"]),
            "selected_events": len(events),
            "total_events": len(recording["events"]),
            "loop": spec.get("loop", False),
        }
    result["view_id"] = digest({"label": result["label"]})[:16]
    result["id"] = "control-" + digest(result)[:20]
    return validate_plan(result)


def validate_plan(plan):
    """An explicit prefix never grants an arbitrary command or file-edit capability."""
    fields = {
        "schema",
        "base",
        "action",
        "label",
        "anchors",
        "node_ids",
        "edge_ids",
        "boundaries",
        "limits_hit",
        "filters",
        "layout",
        "recording",
        "view_id",
        "id",
    }
    if (
        not isinstance(plan, dict)
        or set(plan) - {"context_node_ids"} != fields
        or plan.get("schema") != "vibelens-control-plan/v1"
        or plan.get("action") not in {"view", "replay"}
    ):
        raise ValueError("Unsupported control plan; no source or business commands are allowed")

    def text(value, maximum=256):
        return isinstance(value, str) and 1 <= len(value) <= maximum

    def identities(value, maximum, *, empty=True):
        return (
            isinstance(value, list)
            and (empty or bool(value))
            and len(value) <= maximum
            and all(text(item) for item in value)
            and len(value) == len(set(value))
        )

    base = plan["base"]
    if (
        not isinstance(base, dict)
        or set(base) != {"project_id", "model_revision", "model_hash", "build_id"}
        or not text(base["project_id"])
        or not text(base["model_revision"])
        or not text(base["build_id"])
        or not isinstance(base["model_hash"], str)
        or not re.fullmatch(r"[a-f0-9]{64}", base["model_hash"])
        or not text(plan["label"], 40)
        or plan["label"] != plan["label"].strip()
        or plan["view_id"] != digest({"label": plan["label"]})[:16]
        or not identities(plan["node_ids"], 300, empty=False)
        or not identities(plan["anchors"], 12, empty=False)
        or not set(plan["anchors"]) <= set(plan["node_ids"])
        or not identities(plan.get("context_node_ids", []), 300)
        or not set(plan.get("context_node_ids", [])) <= set(plan["node_ids"])
        or bool(set(plan.get("context_node_ids", [])) & set(plan["anchors"]))
        or not identities(plan["edge_ids"], 50000)
        or type(plan["limits_hit"]) is not bool
    ):
        raise ValueError("Invalid control identity, evidence or selection budget")
    if not isinstance(plan["boundaries"], list) or len(plan["boundaries"]) > 300:
        raise ValueError("Invalid boundary relations")
    if any(
        not isinstance(edge, dict) or any(not text(edge.get(key)) for key in ("id", "from", "to"))
        for edge in plan["boundaries"]
    ):
        raise ValueError("Boundary relations need original identities and endpoints")
    if (
        plan["layout"] not in {"layered", "cluster", "stress"}
        or not isinstance(plan["filters"], dict)
        or set(plan["filters"])
        != {
            "nodes",
            "edges",
            "regions",
        }
    ):
        raise ValueError("Invalid presentation fields")
    for key, vocabulary in [("nodes", NODE_TYPES), ("regions", NODE_TYPES), ("edges", RELATIONS)]:
        values = plan["filters"][key]
        if not identities(values, len(vocabulary), empty=False) or not set(values) <= vocabulary:
            raise ValueError("Unknown presentation type selection")
    recorded = plan["recording"]
    if plan["action"] == "view" and recorded is not None:
        raise ValueError("A live view cannot contain a replay instruction")
    if plan["action"] == "replay" and (
        not isinstance(recorded, dict)
        or set(recorded)
        != {"id", "build_id", "event_ids", "events_hash", "selected_events", "total_events", "loop"}
        or not text(recorded["id"])
        or recorded["build_id"] != base["build_id"]
        or not identities(recorded["event_ids"], 50000, empty=False)
        or type(recorded["selected_events"]) is not int
        or recorded["selected_events"] != len(recorded["event_ids"])
        or type(recorded["total_events"]) is not int
        or not recorded["selected_events"] <= recorded["total_events"] <= 50000
        or type(recorded["loop"]) is not bool
        or not isinstance(recorded["events_hash"], str)
        or not re.fullmatch(r"[a-f0-9]{64}", recorded["events_hash"])
    ):
        raise ValueError("Invalid bounded replay instruction")
    unsigned = {key: value for key, value in plan.items() if key != "id"}
    if plan["id"] != "control-" + digest(unsigned)[:20]:
        raise ValueError("Control plan contents changed after interpretation")
    return plan


def validate_evidence(plan, view, recording=None):
    """Recheck queued control evidence against the actual currently served graph."""
    validate_plan(plan)
    base = plan["base"]
    model = display_graph(view)
    if (
        digest(model) != base["model_hash"]
        or view.get("manifest", {}).get("build_id") != base["build_id"]
        or (
            view.get("layout_id")
            or view["model"].get("project_id")
            or view["model"].get("presentation", {}).get("layout_id")
        )
        != base["project_id"]
    ):
        raise ValueError(
            "The graph changed after this control was prepared; resolve the request again"
        )
    nodes = {node["id"] for node in model["nodes"]}
    selected = set(plan["node_ids"])
    expected_edges = [
        edge["id"]
        for edge in model["edges"]
        if edge["from"] in selected
        and edge["to"] in selected
        and relation_type(edge) in plan["filters"]["edges"]
    ]
    expected_boundaries = [
        edge for edge in model["edges"] if (edge["from"] in selected) != (edge["to"] in selected)
    ][:300]
    if (
        not selected <= nodes
        or plan["edge_ids"] != expected_edges
        or plan["boundaries"] != expected_boundaries
    ):
        raise ValueError("The selection must retain original nodes and declared relations")
    requested_types = set(plan["filters"]["nodes"])
    eligible = {node["id"] for node in model["nodes"] if view_types(node) & requested_types}
    context = set(plan.get("context_node_ids", []))
    if context != selected - eligible:
        raise ValueError("The selection contains unmarked context outside its node type filter")
    check_path_context(context, model["edges"], selected, eligible, plan["filters"]["edges"])
    if plan["action"] == "replay" and (
        not recording
        or recording.get("id") != plan["recording"]["id"]
        or recording.get("build_id") != base["build_id"]
        or digest(recording["events"]) != plan["recording"]["events_hash"]
    ):
        raise ValueError(
            "The selected recording changed; keep the original facts and prepare a new filter"
        )
    if plan["action"] == "replay":
        observed = set(capture_owners(view, selected, strict=False))
        expected = [event["id"] for event in recording["events"] if event.get("node") in observed]
        if (
            recording.get("status") == "recording"
            or plan["recording"]["event_ids"] != expected
            or plan["recording"]["total_events"] != len(recording["events"])
        ):
            raise ValueError("Replay selection must contain the actual events on the selected path")
