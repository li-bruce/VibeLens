"""Freeze an accepted trial build and inspect its original source/event references.

This review helper does not alter the application or infer execution from static
edges. Run it before the next business iteration changes the accepted files.
"""

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from audit_view import audit


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def native_routes(source):
    """Read actual literal registrations independently of the observer scanner."""
    routes = []
    for call in ast.walk(ast.parse(source)):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
            continue
        if call.func.attr != "add_url_rule" or len(call.args) < 3:
            continue
        path = ast.literal_eval(call.args[0])
        handler = ast.unparse(call.args[2]).replace("routes.", "WebRoutes.")
        methods = next(
            (ast.literal_eval(k.value) for k in call.keywords if k.arg == "methods"), ["GET"]
        )
        routes.append({"path": path, "handler": handler, "methods": methods, "line": call.lineno})
    return routes


def prior_contracts(baseline, model, implementation):
    """List removed capture/case declarations without deciding business intent."""
    previous = baseline.parent / "model.json"
    if not previous.is_file():
        return {"available": False}
    nodes = {node["id"]: node for node in model["nodes"]}
    removed = []
    for old in read(previous)["nodes"]:
        for direction in ("in", "out"):
            before = set(old.get("capture", {}).get(direction, {}))
            after = set(nodes.get(old["id"], {}).get("capture", {}).get(direction, {}))
            removed.extend(
                {"node": old["id"], "direction": direction, "field": field}
                for field in sorted(before - after)
            )
    old_features = read(baseline.parent / "accepted-source/implementation.json")["features"]
    new_features = {feature["id"]: feature for feature in implementation["features"]}
    removed_cases = []
    for feature in old_features:
        current = new_features.get(feature["id"], {})
        cases = {json.dumps(case, sort_keys=True) for case in current.get("cases", [])}
        removed_cases.extend(
            {"feature": feature["id"], "case": case}
            for case in feature.get("cases", [])
            if json.dumps(case, sort_keys=True) not in cases
        )
    return {
        "available": True,
        "removed_declared_capture_fields": removed,
        "removed_features": sorted({f["id"] for f in old_features} - set(new_features)),
        "removed_feature_case_contracts": removed_cases,
        "meaning": "Declaration differences only; a legitimate business change still needs explicit review.",
    }


def freeze(root, review, baseline, out, recording):
    """Bind the independent audit to exact accepted source bytes and raw facts."""
    view = read(review / "handoff-view.json")
    manifest, model = view["manifest"], view["model"]
    mismatches = []
    for name, expected in manifest["files"].items():
        path = root / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            mismatches.append(name)
    if mismatches:
        raise RuntimeError("Accepted source changed before snapshot: " + ", ".join(mismatches))
    out.mkdir(parents=True, exist_ok=False)
    source_out = out / "accepted-source"
    for name in manifest["files"]:
        target = source_out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    code = read(root / ".stategraph/code-graph.json")
    catalog = read(root / "bo_stategraph/database-catalog.json")
    sync = read(root / "sync.json")
    for name, value in [
        ("manifest.json", manifest),
        ("model.json", model),
        ("code-graph.json", code),
        ("database-catalog.json", catalog),
        ("sync.json", sync),
    ]:
        write(out / name, value)
    raw = read(review / recording)
    interval = audit({"model": model, "manifest": manifest, "events": raw["events"]})
    write(out / "recording-interval-audit.json", interval)
    old = read(baseline)
    current_ids = {n["id"] for n in model["nodes"]}
    static_nodes = {n["id"]: n for n in code["nodes"]}
    endpoints = [n for n in code["nodes"] if n.get("code_role") == "endpoint"]
    api_matches = []
    for native in native_routes((source_out / "app/web.py").read_text(encoding="utf-8")):
        matches = [
            n
            for n in endpoints
            if n["api"]["path"] == native["path"] and n["api"].get("handler") == native["handler"]
        ]
        api_matches.append(
            {
                "native": native,
                "projected_ids": [n["id"] for n in matches],
                "valid": len(matches) == 1,
            }
        )
    refs = [
        e for e in code["edges"] if e["from"] not in static_nodes or e["to"] not in static_nodes
    ]
    new_ids = sorted(current_ids - set(old["node_ids"]))
    states = model["machine"]["states"]
    summary = {
        "build_id": manifest["build_id"],
        "source_hashes_match": True,
        "raw_recording_sha256": hashlib.sha256((review / recording).read_bytes()).hexdigest(),
        "recording_status": raw["status"],
        "interval_events": len(raw["events"]),
        "interval_closed_calls": interval["invocation_closure"],
        "interval_unowned_points": interval["unowned_internal_points"],
        "interval_missing_parent_entries": interval["unresolved_parent_references"],
        "retained_window_gaps": raw.get("gaps", []),
        "retained_context_ownership_gaps": len(raw.get("ownership_gaps", [])),
        "old_states": old["declared_states"],
        "new_states": states,
        "state_node_values": sorted(
            n.get("value", n["id"]) for n in model["nodes"] if n.get("layer") == "state"
        ),
        "new_model_node_ids": new_ids,
        "native_api_projection": api_matches,
        "static_nodes": len(code["nodes"]),
        "static_edges": len(code["edges"]),
        "static_dangling_edges": refs,
        "static_roles": dict(Counter(n.get("code_role", "other") for n in code["nodes"])),
        "prior_contracts": prior_contracts(
            baseline, model, read(source_out / "implementation.json")
        ),
        "ordinary_case_reports": read(review / "handoff-final-verification.json"),
        "meaning": "Accepted source bytes and observed interval only. Static project/API/schema links do not claim runtime calls; pre-start context gaps are separate.",
    }
    write(out / "summary.json", summary)
    print(
        json.dumps(
            {
                "out": str(out),
                "build_id": manifest["build_id"],
                "events": len(raw["events"]),
                "native_routes": len(api_matches),
                "all_native_routes_projected": all(item["valid"] for item in api_matches),
                "new_states": states,
                "new_node_ids": new_ids,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--recording", default="current-actual-recording.json")
    args = parser.parse_args()
    freeze(
        args.root.resolve(),
        args.review.resolve(),
        args.baseline.resolve(),
        args.out.resolve(),
        args.recording,
    )
