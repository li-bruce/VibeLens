"""Stable physical declaration identities shared by curated and complete source views."""

from .behavior_model import digest

try:
    from ...bo_contracts import source_declaration_id, validate_source_references
except ImportError:
    from bo_contracts import source_declaration_id, validate_source_references

# Public compatibility names keep existing adapter callers on the same contract.
validate_references = validate_source_references


def identity(role, value):
    """Identify a source fact without labels, line numbers or runtime call identity."""
    return "code:" + role + ":" + digest(value)[:24]


def declaration_id(source):
    """Resolve the exact project-relative path and qualified source symbol pair."""
    return source_declaration_id(source)


def attach_declarations(model, index):
    """Expose one physical declaration behind selected semantic/capture definitions.

    Only already-mapped symbols and their lexical ancestors are projected. The
    complete AST remains optional. Existing observation IDs and contextual helper
    IDs stay unchanged; context appearances explicitly reference the declaration.
    """
    from copy import deepcopy
    from ..code_graph.index import build

    selected = set()
    authored = list(model["nodes"])
    for node in authored:
        source = node.get("source")
        key = source["path"] + "::" + source["symbol"] if source else None
        if key not in index["symbols"]:
            continue
        selected.add(key)
        # A rule projector owns its exact node payload. Bind it through an edge
        # rather than attaching fields that a subsequent strict rule projection
        # would correctly reject as foreign metadata.
        if node.get("origin") != "policy-definition":
            node["declaration_id"] = declaration_id(source)
        if node.get("origin") == "source-ast":
            node.update(code_role="reference", representation_role="source-reference")

    mapped = set(selected)
    # A method/nested function belongs to its lexical declaration, independently
    # of the business region from which it was reached.
    for key in list(selected):
        symbol = index["symbols"][key]
        parts = symbol["symbol"].split(".")
        for end in range(1, len(parts)):
            ancestor = symbol["path"] + "::" + ".".join(parts[:end])
            if ancestor in index["symbols"]:
                selected.add(ancestor)
    if not selected:
        return model
    paths = {index["symbols"][key]["path"] for key in selected}
    subset = {
        **index,
        "symbols": {key: index["symbols"][key] for key in sorted(selected)},
        "units": {
            path: {
                **index["units"][path],
                "symbols": {
                    symbol["symbol"]: symbol
                    for key, symbol in index["symbols"].items()
                    if key in selected and symbol["path"] == path
                },
                "module_calls": [],
                "file_references": [],
                "http_registrations": [],
            }
            for path in sorted(paths)
        },
        "edges": [
            edge for edge in index["edges"] if edge["from"] in selected and edge["to"] in selected
        ],
        "unresolved": [],
    }
    physical = build(subset)
    keep = {
        node["id"]
        for node in physical["nodes"]
        if node.get("code_role") in {"directory", "file", "class", "function"}
    }
    known = {node["id"] for node in authored}
    for item in physical["nodes"]:
        if item["id"] not in keep:
            continue
        if item["id"] in known:
            raise ValueError("source declaration collides with an authored identity: " + item["id"])
        node = deepcopy(item)
        node["origin"] = "source-ast"
        node["capture"] = {"in": {}, "out": {}}
        node["summary"] = node.get("summary") or node["label"]
        if node.get("code_role") in {"class", "function"}:
            node["source"] = {key: node["source"][key] for key in ("path", "symbol")}
            node["declaration_id"] = node["id"]
            node["representation_role"] = "declaration"
            key = node["source"]["path"] + "::" + node["source"]["symbol"]
            node["declaration_scope"] = "mapped" if key in mapped else "lexical-owner"
        else:
            node.pop("source", None)
        model["nodes"].append(node)
    for item in physical["edges"]:
        if item["from"] in keep and item["to"] in keep:
            model["edges"].append(
                {
                    **item,
                    "origin": "source-ast",
                    "evidence": (
                        item["evidence"]
                        if isinstance(item.get("evidence"), str)
                        else "Source declaration and static syntax reference; execution unproven"
                    ),
                    **(
                        {"source_evidence": item["evidence"]}
                        if isinstance(item.get("evidence"), dict)
                        else {}
                    ),
                }
            )
    for node in authored:
        source = node.get("source")
        key = source["path"] + "::" + source["symbol"] if source else None
        target = node.get("declaration_id")
        if target is None and key in mapped:
            target = declaration_id(source)
        if not target:
            continue
        model["edges"].append(
            {
                "id": identity("binding", [node["id"], target]),
                "from": node["id"],
                "to": target,
                "type": "data",
                "code_relation": "maps",
                "mapping_role": (
                    "source-reference"
                    if node.get("representation_role") == "source-reference"
                    else "source-binding"
                ),
                "label": "Source binding",
                "origin": "source-ast",
                "evidence": "Exact source declaration binding; not an observed call",
                "source_binding": dict(node["source"]),
            }
        )
    validate_references(model)
    return model
