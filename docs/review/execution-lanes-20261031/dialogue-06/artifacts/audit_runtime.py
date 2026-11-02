"""Independent route, source, database and actual call-ownership comparisons."""
from collections import Counter
import inspect
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app.web import create_app

def get(path):
    return json.load(urllib.request.urlopen("http://127.0.0.1:8983" + path, timeout=30))

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    graph = get("/api/code/graph?projection=all&limit=1500&depth=2")
    api = get("/api/code/graph?projection=api&limit=1500&depth=2")
    save("code-graph-web.json", graph)
    save("api-projection-web.json", api)
    with tempfile.TemporaryDirectory(dir=OUT, prefix="native-routes-") as directory:
        app = create_app(ROOT, database=Path(directory) / "routes.sqlite3")
        native = [{"path": rule.rule, "endpoint": rule.endpoint, "methods": sorted(rule.methods),
            "handler": app.view_functions[rule.endpoint].__qualname__,
            "source": inspect.getsourcefile(app.view_functions[rule.endpoint]),
            "line": inspect.getsourcelines(app.view_functions[rule.endpoint])[1]}
            for rule in app.url_map.iter_rules() if rule.endpoint != "static"]
        app.extensions["trial_store"].engine.dispose()
    endpoints = [node for node in graph["nodes"] if node.get("code_role") == "endpoint"]
    assert len(endpoints) == len(native) == 8
    nodes = {node["id"]: node for node in graph["nodes"]}
    comparisons = []
    for row in native:
        endpoint = next(node for node in endpoints if node["api"]["path"] == row["path"])
        handlers = [nodes[edge["to"]] for edge in graph["edges"] if edge["from"] == endpoint["id"] and edge.get("code_relation") == "handles"]
        assert len(handlers) == 1 and handlers[0]["source"]["symbol"] == row["handler"]
        assert endpoint["api"]["handler"] == row["handler"] and endpoint["api"]["handler_resolved"]
        declared_methods = endpoint["api"]["methods"]
        if declared_methods:
            assert set(declared_methods) == set(row["methods"]) - {"OPTIONS", "HEAD"}
        else:
            assert row["methods"] == ["GET", "HEAD", "OPTIONS"]
        comparisons.append({"native": row, "projected_id": endpoint["id"], "handler_id": handlers[0]["id"],
            "explicit_methods": declared_methods, "default_methods": "framework-resolved; static projection unspecified" if not declared_methods else None,
            "handler_matches": True})
    assert len([node for node in api["nodes"] if node.get("code_role") == "endpoint"]) == 8
    assert not [name for name in graph.get("project", {}).get("entries", {}) if name == ".tmp" or name.startswith(".tmp/")]
    save("native-api-comparison.json", {"valid": True, "comparisons": comparisons,
        "native_static_route_excluded": "/app/<path:filename>", "endpoint_count": 8,
        "handler_links": 8, "temporary_entries": 0,
        "evidence_boundary": "Native Flask route table and syntax projection agree. The projection is static; HTTP runtime evidence is reported separately."})

    view = get("/api/view")
    save("live-audited.json", view)
    events = view["events"]
    entries = {event["call_id"]: event for event in events if event["phase"] == "enter"}
    exits = {event["call_id"]: event for event in events if event["phase"] in {"return", "exception", "error", "commit", "change"}}
    data = [event for event in events if event["node"].startswith("db_")]
    parent_checks, roots = [], {}
    for event in entries.values():
        visited, current = [], event
        while current.get("parent_call_id"):
            assert current["parent_call_id"] in entries, ("missing parent", current)
            parent = entries[current["parent_call_id"]]
            assert all(parent[key] == current[key] for key in ("run_id", "producer_id", "build_id"))
            assert parent["call_id"] not in visited
            visited.append(parent["call_id"])
            current = parent
        roots[event["call_id"]] = current
    for event in data:
        assert event.get("parent_call_id") in entries, event
        parent = entries[event["parent_call_id"]]
        assert event["call_id"] in exits
        if event["node"] == "db_transaction":
            assert parent["node"] in {"upload_file", "review_file", "share_file"}
        if event["node"] == "db_metadata":
            assert parent["node"] == "upload_file"
        if event["node"] in {"db_insert", "db_update"}:
            assert parent["node"] == "db_transaction"
        root = roots[event["call_id"]]
        assert root["node"] == "http_request"
        parent_checks.append({"event_id": event["id"], "node": event["node"], "call_id": event["call_id"],
            "parent_call_id": parent["call_id"], "parent_node": parent["node"], "root_call_id": root["call_id"],
            "request": root.get("inputs", {})})
    uploads = [event for event in entries.values() if event["node"] == "upload_file" and event.get("inputs", {}).get("filename", "").startswith("concurrent-")]
    assert len(uploads) == 4
    assert len({roots[event["call_id"]]["call_id"] for event in uploads}) == 4
    concurrency = []
    for event in uploads:
        children = [item for item in entries.values() if item.get("parent_call_id") == event["call_id"] and item["node"] == "db_transaction"]
        assert len(children) == 1
        nested = [item for item in entries.values() if item.get("parent_call_id") == children[0]["call_id"]]
        assert {"db_users", "db_insert", "state_transition"} <= {item["node"] for item in nested}
        concurrency.append({"actor": event["inputs"]["actor"], "filename": event["inputs"]["filename"],
            "upload_call": event["call_id"], "http_call": roots[event["call_id"]]["call_id"],
            "transaction_call": children[0]["call_id"], "nested_nodes": [item["node"] for item in nested]})
    statuses = Counter(event.get("outputs", {}).get("status") for event in exits.values() if event["node"] == "http_request")
    assert {200, 302, 400, 401, 403, 404, 409} <= set(statuses)
    transaction_exceptions = [event for event in exits.values() if event["node"] == "db_transaction" and event["phase"] == "error"]
    assert transaction_exceptions
    for key in ("errors", "dropped"):
        assert view["health"][key] == 0
    assert all(view["health"]["producer"][key] == 0 for key in ("errors", "dropped", "data_errors", "integration_errors"))
    with sqlite3.connect(ROOT / "var/team-files.sqlite3") as db:
        structure = {table: {"columns": [list(row) for row in db.execute("PRAGMA table_info(" + table + ")")],
            "foreign_keys": [list(row) for row in db.execute("PRAGMA foreign_key_list(" + table + ")")]}
            for table in ("files", "users")}
    save("native-database-structure.json", structure)
    save("runtime-parent-audit.json", {"valid": True, "events": len(events), "data_events": len(data),
        "parent_checks": parent_checks, "concurrent_ownership": concurrency,
        "http_exit_status_counts": dict(statuses), "transaction_exception_count": len(transaction_exceptions),
        "transaction_exception_examples": transaction_exceptions[:3], "health": view["health"],
        "boundary": "Checks raw call identities and actual nested ownership. SQLite writes serialize; overlapping HTTP uploads do not imply overlapping write commits."})
    print(json.dumps({"routes": 8, "handlers": 8, "temporary_entries": 0, "data_events": len(data), "concurrent_uploads": len(uploads), "valid": True}))

if __name__ == "__main__":
    main()
