"""Versioned concept-first design interfaces; never an application authority."""

from copy import deepcopy

from .binding import check_binding
from .common import digest
from .model import VERSION, build, policy_semantics
from .projection import bind_projection
from .semantics import (
    confirm,
    snapshot,
    snapshot_records,
    diff,
    resolve,
    check_confirmations,
    semantic_projection,
)

__all__ = [
    "assess",
    "assemble",
    "resolve",
    "snapshot",
    "confirm",
    "diff",
    "check_confirmations",
    "check_binding",
    "bind_projection",
    "semantic_projection",
    "policy_semantics",
]


def assemble(doc):
    """Return a source-free design graph, not a valid runtime model."""
    return deepcopy(build(doc)["graph"])


def assess(doc, previous=None, model=None, bindings=None, *, scope=None, acceptance=None):
    """Report legality, scoped confirmation and binding separately as portable JSON."""
    if isinstance(doc, dict) and doc.get("schema") == "business-discovery/v1":
        return {
            "valid": True,
            "ready": False,
            "errors": [],
            "warnings": [
                {"code": "legacy_discovery_not_concept_confirmed", "item": "business-discovery/v1"}
            ],
            "blocked": [],
            "compatibility": "legacy-v1",
            "index": {},
            "graph": None,
            "semantic_revision": None,
        }
    try:
        data = build(doc)
        confirmation = check_confirmations(doc, previous, scope=scope)
        snap = snapshot_records(
            {key: data["records"][key] for key in confirmation["coverage_scope"]}
        )
        changes = (
            diff(previous, doc, scope)
            if previous
            else {
                "semantic_change": False,
                "added": [],
                "removed": [],
                "changed": [],
                "affected": [],
            }
        )
        report = {
            "valid": confirmation["valid"],
            "ready": confirmation["ready"],
            "errors": confirmation["errors"],
            "warnings": [],
            "blocked": confirmation["blocked"],
            "compatibility": VERSION,
            "graph": data["graph"],
            "index": data["index"],
            "semantic_revision": snap["semantic_revision"],
            "full_semantic_revision": digest(data["records"]),
            "coverage_scope": confirmation["coverage_scope"],
            "confirmation": confirmation,
            "changes": changes,
        }
        if previous and previous.get("schema") == "business-discovery/v1":
            report["warnings"].append(
                {
                    "code": "legacy_migration_requires_fresh_confirmation",
                    "item": "business-discovery/v1",
                }
            )
        for decision in doc["decisions"]:
            if decision.get("blocking") and decision.get("status") != "resolved":
                from .semantics import resolve_index

                affected = [
                    resolve_index(data["index"], ident) for ident in decision.get("affects", [])
                ]
                if not affected or set(affected).intersection(confirmation["coverage_scope"]):
                    report["blocked"].append("decision:" + decision["id"])
                    report["ready"] = False
        if model is not None:
            report["binding"] = check_binding(
                doc, model, bindings, scope=scope, acceptance=acceptance
            )
            report["errors"] = report["errors"] + report["binding"]["errors"]
            report["valid"] = report["valid"] and report["binding"]["valid"]
            report["ready"] = report["ready"] and report["binding"]["valid"]
        return report
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        return {
            "valid": False,
            "ready": False,
            "errors": [{"code": "invalid_concept_design", "item": str(exc)}],
            "warnings": [],
            "blocked": [],
            "compatibility": VERSION,
            "index": {},
            "graph": None,
            "semantic_revision": None,
        }
