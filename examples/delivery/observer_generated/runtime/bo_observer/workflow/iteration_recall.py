"""Small, source-derived iteration handoff for the coding agent, not user UI copy."""

from __future__ import annotations

from .observation_requirements import observation_plan
from ..graph.behavior_model import contained, read
from .sync_io import write


CONTEXT_MAPPING_PREVIEW = 12


def recall(root, cfg, current, previous=None):
    """Write durable requirements and return a concise current-source summary.

    Reading this output does not accept changed source or advance any baseline.
    The authoritative inputs remain intent, model, inventory and test contracts.
    """
    old = (previous or {}).get("files", {})
    changed = sorted(
        path
        for path in set(old) | set(current["files"])
        if old.get(path) != current["files"].get(path)
    )
    affected = set(changed)
    plan = observation_plan(current["model"], current["structure"])
    from ..observation.telemetry import load_registrations, CONFIG

    telemetry = load_registrations(root, current["model"])
    mapping_path = cfg.get("mapping_contract")
    mapping = read(contained(root, mapping_path)) if mapping_path else {}
    # Keep the handoff small; verification still reads every protected contract row.
    context_fields = mapping.get("context_fields", [])
    write(contained(root, ".stategraph/observation-plan.json"), plan)
    active_path = contained(root, cfg.get("active_change", ".stategraph/active.json"))
    active = read(active_path) if active_path.is_file() else None
    implementation = current["model"].get("implementation") or {}
    classified = set(implementation.get("support", {})) | set(implementation.get("excluded", {}))
    for feature in implementation.get("features", []):
        classified.update(feature.get("sources", []))
    requirements = current["intent"].get("requirements", [])
    value = {
        "schema": "bo-iteration-recall/v1",
        "candidate_id": current["id"],
        "mode": cfg.get("stategraph", {}).get("development_mode"),
        "active_change": active,
        "request": (previous or {}).get("request"),
        "changed_files": changed,
        "source_errors": current["structure"].get("errors", []),
        "verification": "not_run",
        "unregistered_files": sorted(
            set(current.get("source_inventory", {}).get("files", {}))
            - set(cfg.get("code_files", []))
        ),
        "unclassified_functions": sorted(
            sid
            for sid, symbol in current["structure"].get("symbols", {}).items()
            if symbol.get("kind") == "function" and sid not in classified
        ),
        "contracts": {
            key: cfg.get(key)
            for key in (
                "model",
                "acceptance",
                "whitebox",
                "mapping_contract",
                "reconciliation",
                "discovery",
            )
            if cfg.get(key)
        },
        "observation_module": cfg.get("stategraph", {}).get("module"),
        "observation_sources": [
            sid
            for sid, item in implementation.get("excluded", {}).items()
            if item.get("category") == "observer"
        ],
        "naming": {"wiring": "bo_", "adapters": "BO"},
        "layers": {
            layer: {
                "nodes": len(group["nodes"]),
                "scan": group["scan"],
                "observe": group["observe"],
                "affected_nodes": [
                    node["node"]
                    for node in group["nodes"]
                    if (node.get("source") or {}).get("path") in affected
                ],
            }
            for layer, group in plan["layers"].items()
        },
        "plan": ".stategraph/observation-plan.json",
        "telemetry": {
            "backend": "opentelemetry" if telemetry else "native",
            "registration_file": CONFIG if telemetry else None,
            "nodes": [item["node"] for item in telemetry["registrations"]] if telemetry else [],
            "preserve": [
                "state declaration and native executor",
                "source mappings and selected fields",
                "trace propagation across async/job boundaries",
                "observer exclusion and probe health",
                "native principal/object facts and protected context comparisons",
            ],
        },
        "context_mapping": [
            {key: item[key] for key in ("id", "case", "node", "phase", "mapped")}
            for item in context_fields[:CONTEXT_MAPPING_PREVIEW]
        ],
        "context_mapping_count": len(context_fields),
        "context_mapping_omitted": max(0, len(context_fields) - CONTEXT_MAPPING_PREVIEW),
        "requirements": [
            {"id": item.get("id"), "text": item.get("text", "")[:180], "status": item.get("status")}
            for item in requirements[:20]
        ],
        "requirement_count": len(requirements),
        "intent": current["model"].get("intent"),
        "test_commands": cfg.get("test_commands", []),
        "observations_command": cfg["observations_command"],
        "required_checks": {
            "source_first_inventory": True,
            "probe_health": cfg.get("require_probe_health", False),
            "invocation_closure": cfg.get("require_observation_closure", False),
            "mapping_witnesses": cfg.get("require_mapping_witnesses", False),
            "reports": ["mapping", "state_rules", "business", "project_checks"],
        },
        "next": "Preserve accepted obligations. Update affected layers and source bindings; run scan, inspect, verify, accept and check. Missing boundaries or values are mapping failures, independent of business results.",
    }
    write(contained(root, ".stategraph/iteration-recall.json"), value)
    return value
