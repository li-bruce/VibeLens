"""Verify served HTTP projection and preservation after the native restart."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

EVIDENCE = Path(__file__).parent
REPOSITORY = EVIDENCE.parents[3]
TRIAL = REPOSITORY.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04"
PHASE = "api-observation"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fetch(path):
    with urlopen("http://127.0.0.1:50958" + path, timeout=30) as response:
        return response.read()


def main():
    before = read_json(EVIDENCE / f"protected-before-{PHASE}.json")
    changes = []
    for name, expected in before.items():
        path = TRIAL / name
        current = sha(path.read_bytes()) if path.is_file() else None
        if current != expected["sha256"]:
            changes.append({"path": name, "before": expected["sha256"], "current": current})
    database = bytearray((TRIAL / "runtime/team-files.sqlite3").read_bytes())
    counter, valid_for = int.from_bytes(database[24:28], "big"), int.from_bytes(
        database[92:96], "big"
    )
    counter_only = None
    for difference in range(1, min(counter, valid_for, 32) + 1):
        candidate = bytearray(database)
        candidate[24:28] = (counter - difference).to_bytes(4, "big")
        candidate[92:96] = (valid_for - difference).to_bytes(4, "big")
        if sha(candidate) == before["runtime/team-files.sqlite3"]["sha256"]:
            counter_only = {
                "counter_increment": difference,
                "changed_header_ranges": [[24, 28], [92, 96]],
                "all_other_database_bytes_identical": True,
            }
            break
    allowed = {".stategraph/code-graph.json"}
    if counter_only:
        allowed.add("runtime/team-files.sqlite3")
    unexpected = [item for item in changes if item["path"] not in allowed]

    plan = read_json(EVIDENCE / f"plan-{PHASE}.json")
    assets = []
    for name in plan["changes"]:
        installed = (TRIAL / name).read_bytes()
        if name.startswith("static/graph/"):
            relative = name.removeprefix("static/graph/")
            canonical = (
                REPOSITORY / "skills/vibelens/assets/stategraph-viewer" / relative
            ).read_bytes()
            served = fetch("/" + relative)
            assets.append(
                {
                    "path": name,
                    "canonical_sha256": sha(canonical),
                    "installed_sha256": sha(installed),
                    "served_sha256": sha(served),
                    "valid": canonical == installed == served,
                }
            )
        else:
            canonical = (
                REPOSITORY / "skills/vibelens/scripts" / name.removeprefix("observer_runtime/")
            ).read_bytes()
            assets.append(
                {
                    "path": name,
                    "canonical_sha256": sha(canonical),
                    "installed_sha256": sha(installed),
                    "valid": canonical == installed,
                }
            )

    health = json.loads(fetch("/api/bo/health"))
    view = json.loads(fetch("/api/view"))
    graph = view["api_structure"]
    sources = [item for node in graph["nodes"] for item in node.get("observation_sources", [])]
    projection_valid = (
        len(graph["nodes"]) == 4
        and len(sources) == 5
        and all(node.get("observation_projection") is True for node in graph["nodes"])
        and not graph["observation_issues"]
        and not graph["errors"]
    )
    identity_valid = (
        health["project_id"] == "team-files-otel-dialogue-20261101-03"
        and health["build_id"] == "2a84d16935506ba30e1071d3a4bbd74fc25c3ac12270cdf023ef79535b7c630b"
        and health["binding"]["status"] == "current"
    )
    result = {
        "valid": not unexpected
        and all(item["valid"] for item in assets)
        and projection_valid
        and identity_valid,
        "protected_files": len(before),
        "changed": changes,
        "unexpected_changes": unexpected,
        "database_restart_metadata": counter_only,
        "assets": assets,
        "health": health,
        "launcher": read_json(TRIAL / "runtime/launcher.json"),
        "api_structure": {
            "revision": graph["revision"],
            "nodes": len(graph["nodes"]),
            "sources": len(sources),
            "source_ids": sorted(item["node"] for item in sources),
            "edges": len(graph["edges"]),
            "observation_issues": graph["observation_issues"],
            "errors": graph["errors"],
        },
        "business_requests_executed": False,
    }
    (EVIDENCE / f"final-verification-{PHASE}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "assets"}, ensure_ascii=False
        )
    )
    return int(not result["valid"])


if __name__ == "__main__":
    raise SystemExit(main())
