"""Read frozen artifacts, retain evidence, and verify historical byte integrity."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ROUND = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, value):
    (ROUND / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    preflight = read(ROUND / "preflight.json")
    historical_changed = [name for name, digest in preflight["historical_review"].items()
        if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
    protected_changed = [name for name, digest in preflight["protected"].items()
        if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
    view = read(ROUND / "final-view.json")
    code = read(ROUND / "final-code-graph.json")
    recording = read(ROUND / "final-recording-58875516febf4f77862f1ce4f29f5f86.json")
    events = view["events"]
    entries = {event["call_id"]: event for event in events if event.get("phase") == "enter"}
    data = [event for event in events if event.get("node", "").startswith("db_")]
    parent_examples = []
    for event in data:
        if event.get("phase") != "enter":
            continue
        parent = entries.get(event.get("parent_call_id"))
        parent_examples.append({"event_id": event["id"], "node": event["node"],
            "call_id": event["call_id"], "parent_call_id": event.get("parent_call_id"),
            "parent_node": parent.get("node") if parent else None,
            "entity": event.get("entity"), "attempt": event.get("attempt"),
            "run_id": event.get("run_id"), "producer_id": event.get("producer_id")})
    routes = []
    source = ROOT / "app/web.py"
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_url_rule":
            routes.append({"path": ast.literal_eval(node.args[0]),
                "endpoint": ast.literal_eval(node.args[1]), "handler": ast.unparse(node.args[2]),
                "line": node.lineno,
                "methods": next((ast.literal_eval(item.value) for item in node.keywords if item.arg == "methods"), "framework default")})
    routes.sort(key=lambda item: item["line"])
    project_entries = code.get("project", {}).get("entries", [])
    temporary_entries = [item for item in project_entries if ".tmp" in json.dumps(item)]
    verification = read(ROUND / "verify.stdout.log")
    audit = {
        "disposition": "frozen_before_acceptance_pending_shared_source_scanner_repair",
        "business_user": "coordinating AI simulation; not independent human acceptance",
        "active_change": read(ROOT / ".stategraph/active.json"),
        "accept_performed": False,
        "accepted_json_exists": (ROOT / "resume-first-integration-20261031/accepted.json").exists(),
        "build_id": view["manifest"]["build_id"],
        "binding_status": view["binding_status"],
        "four_category_receipt": {name: result["status"] for name, result in verification["reports"].items()},
        "four_category_receipt_limit": "Configured checks passed; API coverage and full Web acceptance remain blocked/unrun.",
        "events": len(events),
        "data_events": len(data),
        "data_events_with_parent": sum(bool(event.get("parent_call_id")) for event in data),
        "data_nodes": dict(Counter(event["node"] for event in data)),
        "data_entry_parent_examples": parent_examples,
        "parent_interpretation": "Raw identity links only. This round did not finish independent concurrent ownership or error-path acceptance.",
        "health": view["health"],
        "recording": {key: recording.get(key) for key in ("id", "status", "started_at", "ended_at", "gaps", "build_id")},
        "recording_events": len(recording["events"]),
        "api_gap": {"source_routes": routes, "graph_nodes": len(code["nodes"]),
            "endpoint_nodes": [item for item in code["nodes"] if item.get("kind") == "endpoint"],
            "source_scanner": "observer_runtime/bo_observer/code_graph/endpoints.py"},
        "temporary_project_entries": temporary_entries,
        "historical_review_files": len(preflight["historical_review"]),
        "historical_review_changed": historical_changed,
        "protected_changed": protected_changed,
        "baseline_sha256": sha(ROOT / "resume-first-integration-20261031/baseline.json"),
        "stopped_services": read(ROUND / "owned-process-stop.json"),
        "browser_download": read(ROUND / "browser-download-check.json"),
    }
    save("freeze-verification.json", audit)
    selected = []
    for name in ("app", "bo_stategraph", "observer_runtime", "integrations", "static", "templates", "tooling", ".stategraph", "resume-first-integration-20261031"):
        for path in (ROOT / name).rglob("*"):
            relative = path.relative_to(ROOT).as_posix()
            if path.is_file() and "__pycache__" not in path.parts and not relative.startswith(("bo_stategraph/config/views/", "bo_stategraph/config/control/")) and not relative.endswith(".lock"):
                selected.append(path)
    selected.extend(path for path in ROOT.iterdir() if path.is_file())
    selected.append(ROOT / "var/team-files.sqlite3")
    archive = ROUND / "source-runtime-snapshot.zip"
    if not archive.exists():
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(set(selected)):
                bundle.write(path, path.relative_to(ROOT).as_posix())
    save("freeze-manifest.json", {
        "source_files": {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(set(selected))},
        "archive": {"path": archive.name, "sha256": sha(archive)},
        "exclusions": ["dependencies", "temporary installation trees", "personal views/control", "session secret", "historical review directory"],
        "meaning": "Current frozen source/runtime snapshot, not an accepted release. No publication."
    })
    print(json.dumps({"events": len(events), "data_events": len(data),
        "recording_events": len(recording["events"]), "routes": len(routes),
        "temporary_entries": len(temporary_entries), "historical_changed": historical_changed,
        "protected_changed": protected_changed, "snapshot_files": len(set(selected))}, ensure_ascii=False))
