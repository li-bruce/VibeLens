"""A compact review workbook derived from the canonical conceptual models.

There is no second forest registry. Each review group uses existing network
membership, semantic snapshots and the same focus projection as the Web viewer.
Generating this workbook does not record presentation or user confirmation.
"""

from copy import deepcopy
from urllib.parse import urlsplit

from ..concepts.model import build
from ..concepts.construction import MODEL_KINDS, affects_scope
from ..concepts.semantics import snapshot_records, selection
from ..graph.focus_graph import extract
from ..graph.relation_identity import relation_ids
from ..web.design_preview import diagram
from .question_routing import present_question


def workbook(document, report, *, model_ref=None, max_nodes=12, locale=None, url=None):
    """Return the inventory, pending work and one inspectable network per round.

    All current gaps stay in the report. A small preview identifies its omitted
    scope, so it cannot stand in for review of a larger semantic snapshot.
    """
    if not report["valid"]:
        return {"valid": False, "errors": report["errors"], "models": [], "preview": None}
    if type(max_nodes) is not int or not 1 <= max_nodes <= 1000:
        raise ValueError("Review node budget must be 1..1000")
    locale = locale or document.get("participation", {}).get("language", "en")
    if locale not in {"en", "zh-CN"}:
        raise ValueError("Review language must be en or zh-CN")
    if url:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or any(c in url for c in '\r\n<>"()\\')
        ):
            raise ValueError("Review URL must be an HTTP(S) viewer address without credentials")
    data = build(document)
    graph, records = data["graph"], data["records"]
    graph = {
        **graph,
        "revision": snapshot_records(records)["semantic_revision"],
        "project_id": document.get("project_id", "project"),
    }
    concepts = report["concepts"]
    coverage = set(concepts["coverage_scope"])
    pending = set(concepts["confirmation"]["blocked"])
    construction = concepts.get("construction", {})
    targets = construction.get("targets", {})
    gaps = construction.get("gaps", [])
    questions = [
        present_question(item, document.get("participation", {}), locale=locale)
        for item in report.get("questions", [])
    ]
    groups = []
    nodes = {node["id"]: node for node in graph["nodes"]}
    reviewed = set()
    for confirmation in document["confirmations"]:
        if document["schema"] != "business-discovery/v3" or confirmation.get("presentation_ref"):
            reviewed.update(
                ref
                for ref, value in confirmation["snapshot"]["records"].items()
                if records.get(ref) == value
            )
    model_snapshots = {}
    for network in graph["networks"]:
        root = next(ref for ref in network["nodes"] if records[ref]["kind"] in MODEL_KINDS)
        members = set(network["nodes"]) | set(network["edges"])
        related = [
            gap
            for gap in gaps
            if not gap.get("scope_refs")
            or any(affects_scope(ref, data["index"], targets, members) for ref in gap["scope_refs"])
        ]
        model_scope = set(selection(data, [root]))
        model_snapshots[root] = snapshot_records({ref: records[ref] for ref in model_scope})
        groups.append(
            {
                "model_ref": root,
                "network_id": network["id"],
                "kind": records[root]["kind"],
                "label": nodes[root]["label"],
                "nodes": network["nodes"],
                "edges": network["edges"],
                "in_scope": bool(members & coverage),
                "definition": "valid",
                "intent": (
                    "pending" if pending & model_scope or model_scope - reviewed else "confirmed"
                ),
                "binding": "not_checked",
                "engine_support": "not_checked",
                "runtime": "not_checked",
                "gaps": [item["id"] for item in related],
                "question_ids": [
                    item["id"]
                    for item in questions
                    if any(
                        affects_scope(ref, data["index"], targets, members)
                        for ref in item["affects"]
                    )
                ],
            }
        )
    order = {"business_network": 0, "state_model": 1, "rule_operation": 2}
    groups.sort(key=lambda group: (order[group["kind"]], group["model_ref"]))
    selected = (
        next((group for group in groups if group["model_ref"] == model_ref), None)
        if model_ref
        else next((group for group in groups if group["in_scope"]), None)
    )
    if model_ref and selected is None:
        raise ValueError("Unknown model review scope: " + model_ref)
    preview = None
    if selected:
        members = selected["nodes"]
        anchors = [
            selected["model_ref"],
            *[ref for ref in members if ref != selected["model_ref"]],
        ][:max_nodes]
        view = extract(graph, anchors, depth=0, max_nodes=max_nodes)
        # Projected edges retain original assertion identities. Only those
        # assertions actually shown belong to the reviewed presentation scope.
        shown = {node["id"] for node in view["nodes"]}
        for edge in view["edges"]:
            shown.update(relation_ids(edge))
        snap = model_snapshots[selected["model_ref"]]
        shown &= set(snap["scope"])
        preview = {
            "model_ref": selected["model_ref"],
            "snapshot": snap,
            "visible_refs": sorted(shown),
            "omitted_refs": sorted(set(snap["scope"]) - shown),
            "focus": view,
            "diagram": diagram(view, locale),
            "url": url,
            "presentation_recorded": False,
            "confirmation": "not_recorded",
        }
    return {
        "valid": True,
        "schema": "bo-construction-review/v1",
        "locale": locale,
        "semantic_revision": snapshot_records(records)["semantic_revision"],
        "models": groups,
        "targets": deepcopy(list(targets.values())),
        "gaps": deepcopy(gaps),
        "deferred_gaps": deepcopy(construction.get("deferred_gaps", [])),
        "questions": deepcopy(questions),
        "routing": deepcopy(report.get("routing", {})),
        "preview": preview,
        "source_scope": "Recorded request sources and explicit construction obligations",
    }


def markdown(workbook):
    """Render a human review using the same graph and pending decision identities."""
    chinese = workbook["locale"] == "zh-CN"
    lines = ["# 当前模型" if chinese else "# Current models", ""]
    for model in workbook["models"]:
        lines.append(f'- {model["label"]} · `{model["model_ref"]}`')
    preview = workbook["preview"]
    if preview:
        lines.extend(["", "```mermaid", preview["diagram"], "```", ""])
        if preview["url"]:
            lines.append(
                f'[{"打开动态图" if chinese else "Open the live graph"}]({preview["url"]})'
            )
        if preview["omitted_refs"]:
            lines.append(
                "还有相关条件与边界未在本图展开。"
                if chinese
                else "Related conditions and boundaries remain outside this view."
            )
    if workbook["targets"]:
        lines.extend(["", "待梳理：" if chinese else "Still to model:", ""])
        lines.extend(
            "- " + target["meaning"]
            for target in workbook["targets"]
            if not target.get("promoted_to")
        )
    if workbook["questions"]:
        lines.extend(["", "待确认：" if chinese else "To confirm:", ""])
        lines.extend("- " + question["question"] for question in workbook["questions"])
    return "\n".join(lines) + "\n"
