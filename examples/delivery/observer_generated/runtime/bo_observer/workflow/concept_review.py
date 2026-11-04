"""Compact conceptual obligations restored at the start of a coding iteration.

The concept package owns definition and semantic validation. This adapter only
selects the information the coding agent needs; it never accepts a candidate or
changes the user's recorded answers.
"""

from __future__ import annotations


def compact_report(report):
    """Keep verdicts and scopes on stdout; complete graph data stays in artifacts."""
    result = {key: value for key, value in report.items() if key not in {"graph", "index"}}
    graph = report.get("graph")
    if graph is not None:
        result["graph_size"] = {key: len(graph.get(key, [])) for key in ("nodes", "edges")}
    if "concepts" in result:
        result["concepts"] = compact_report(result["concepts"])
    return result


def concept_recall(document, previous=None):
    """Summarize confirmed meaning, pending scopes and affected concepts.

    Legacy projects remain readable with an explicit compatibility status. They
    do not gain a semantic confirmation merely by installing a newer runtime.
    """
    if document is None:
        return {"status": "not_configured", "ready": False}
    if document.get("schema") != "business-discovery/v2":
        return {
            "status": "legacy",
            "ready": False,
            "schema": document.get("schema"),
            "action": "Migrate the affected scope before claiming three-model confirmation.",
        }

    from ..concepts import assess

    report = assess(document, previous=previous)
    return {
        "status": "confirmed" if report["ready"] else "needs_review",
        "ready": report["ready"],
        "semantic_revision": report.get("semantic_revision"),
        "blocked": report.get("blocked", []),
        "errors": report.get("errors", []),
        "changes": report.get("changes", {}),
        "confirmations": [
            {key: item.get(key) for key in ("id", "scope", "source_refs")}
            for item in document.get("confirmations", [])
        ],
        "state_models": [item["id"] for item in document.get("state_models", [])],
        "rule_operations": [
            item["id"] for item in (document.get("policy") or {}).get("operations", [])
        ],
        "expectations": [item["id"] for item in document.get("expectations", [])],
        "action": "Preserve confirmed meaning; bind actual source and evidence. Review only affected semantic changes.",
    }
