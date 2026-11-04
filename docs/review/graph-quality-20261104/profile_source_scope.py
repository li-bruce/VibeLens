"""Measure actual source boundaries without modifying a project's source or data."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.code_graph.service import CodeGraph


def main():
    """Compare cold/warm snapshots and count visited directories, not descendants."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Use a distinct receipt for every measurement")
    project = args.root.resolve()
    index = CodeGraph(project, persist=False)
    original = os.scandir
    results = []
    for phase in ("cold", "warm_same_instance"):
        visited = set()
        support_reads = set()

        def scandir(directory):
            path = Path(directory).absolute()
            if path.is_relative_to(project):
                visited.add(path.relative_to(project).as_posix())
            else:
                # A validator may load its own packaged JSON schemas. Those
                # resource reads are not project-source discovery or AST work.
                support_reads.add(path)
            return original(directory)

        started = time.perf_counter()
        with patch("os.scandir", side_effect=scandir):
            snapshot = index.api_snapshot()
        elapsed = time.perf_counter() - started
        results.append(
            {
                "phase": phase,
                "seconds": elapsed,
                "visited_directories": len(visited),
                "external_framework_resource_directories": len(support_reads),
                "runtime_artifact_directory_visited": any(
                    p == "review/runtime" or p.startswith("review/runtime/")
                    for p in visited
                ),
                "source_files": len(snapshot["scope"]["files"]),
                "api_nodes": len(snapshot["nodes"]),
                "errors": snapshot["errors"],
                "revision": snapshot["revision"],
                "scope": snapshot["scope"],
            }
        )
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Canonical read-only CodeGraph, persist=False; no application execution or data queries",
        "project": project.name,
        "samples": results,
        "stable_revision": results[0]["revision"] == results[1]["revision"],
        "valid": all(
            not r["errors"] and not r["runtime_artifact_directory_visited"]
            for r in results
        ),
        "limits": "Observed Windows samples under concurrent work, not isolated latency guarantees",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}))
    print(json.dumps([{k: v for k, v in r.items() if k != "scope"} for r in results]))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
