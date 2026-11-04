"""Display concerns and implementation facets, independent of execution identity.

The browser counterpart is graph-classification.js. Cross-language regression
cases compare both classifiers. Classification organizes evidence; it never
creates a call, changes a declaration ID or establishes business authorization.
"""

from __future__ import annotations

CODE_ROLES = {
    "directory",
    "file",
    "endpoint",
    "class",
    "function",
    "parameter",
    "unresolved",
    "reference",
}
DATA_ROLES = {"store", "dataset", "column", "query", "write", "transaction", "transform"}
OPERATION_ROLES = {"query", "write", "transaction", "transform"}


def visual_type(node):
    """Return a declared type or an explicit unknown diagnostic classification."""
    if node.get("origin") == "concept-design":
        concept = node.get("concept_kind", "")
        if node.get("layer") == "business":
            return "business"
        if concept == "fact":
            return "data"
        if concept.startswith("rule_") or concept == "guard":
            return "decision"
        if concept in {"event", "logical_effect"}:
            return "effect"
        if concept in {"state", "state_model", "transition"}:
            return "state"
    code_role = node.get("code_role")
    data_role = node.get("data_role")
    if code_role:
        return "code-" + code_role if code_role in CODE_ROLES else "unknown"
    if data_role:
        return data_role if data_role in DATA_ROLES else "unknown"
    if node.get("layer") == "business":
        return "business"
    kind = node.get("kind")
    if kind == "state":
        return "state"
    if kind == "resource" or node.get("execution_role") == "resource":
        return "resource"
    if kind == "decision" or node.get("execution_role") == "join":
        return "decision"
    if kind in {"data", "effect", "wait"}:
        return kind
    if kind in {"function", "action"}:
        return "function"
    return "unknown"


def implementation_facet(node):
    """Keep entrypoint, source grain and I/O detail as selectable facets."""
    if (node.get("data_role") or node.get("capture_owner_role")) in OPERATION_ROLES:
        return "operations"
    if node.get("api_role") == "capture" or node.get("capture_owner_api_role") == "capture":
        return "execution"
    if node.get("layer") == "api" or node.get("code_role") == "endpoint":
        return "api"
    if node.get("code_role") in {"directory", "file"} or node.get("reference_scope") == "project":
        return "project"
    if node.get("code_role") or node.get("origin") in {"python-ast", "source-ast"}:
        return "code"
    return "execution"


def classify(node):
    """Classify one model node without examining its name or observed values."""
    if node.get("origin") == "concept-design":
        kind = node.get("concept_kind", "")
        if node.get("layer") in {"business", "state", "rules"}:
            return {"layer": node["layer"], "facet": None}
        if node.get("layer") == "predicate" or kind.startswith("rule_") or kind == "fact":
            return {"layer": "rules", "facet": None}
        if kind == "object":
            return {"layer": "business", "facet": None}
    kind = visual_type(node)
    if kind == "unknown":
        return {"layer": "unknown", "facet": None, "diagnostic": "Unclassified node"}
    if (
        node.get("code_role")
        or node.get("api_role") == "capture"
        or node.get("capture_owner_api_role") == "capture"
        or (node.get("data_role") or node.get("capture_owner_role")) in OPERATION_ROLES
    ):
        return {"layer": "implementation", "facet": implementation_facet(node)}
    if kind == "business":
        return {"layer": "business", "facet": None}
    if (
        node.get("origin") == "policy-definition"
        or node.get("policy_node")
        or node.get("capture_owner_policy")
    ):
        return {"layer": "rules", "facet": None}
    if (
        node.get("semantic_role") == "state_parameter"
        or kind in {"state", "wait", "resource"}
        or node.get("execution_role") in {"resource", "join"}
    ):
        return {"layer": "state", "facet": None}
    if kind == "decision":
        return {"layer": "rules", "facet": None}
    if kind in {"store", "dataset", "column"}:
        return {"layer": "data", "facet": None}
    return {"layer": "implementation", "facet": implementation_facet(node)}


def layer_of(node):
    """Compatibility entrypoint for observation plans and evidence reports."""
    return classify(node)["layer"]
