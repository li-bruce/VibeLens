"""Freeze actual trial inputs and public projections without changing the project.

Run at accepted coding boundaries. The snapshot contains synthetic test sources,
contracts and read-only database structure; it never copies credentials or files.
"""

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from urllib.request import urlopen
import zipfile

REPOSITORY = Path(__file__).resolve().parents[1]
TRIAL = REPOSITORY.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
OUTPUT = REPOSITORY / "docs/review/dialogue-acceptance-20261031/iteration"


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def get_json(url):
    with urlopen(url, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"Actual endpoint returned {response.status}: {url}")
        return json.load(response)


def main():
    phase = sys.argv[1]
    if not phase or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in phase
    ):
        raise ValueError("Use a simple evidence phase name")
    destination = OUTPUT / phase
    destination.mkdir(parents=True, exist_ok=False)
    process = json.loads(
        (TRIAL / "review/runtime-process.json").read_text(encoding="utf-8")
    )
    base = process["graph_url"].removesuffix("/graph")
    public = {
        name: get_json(base + route)
        for name, route in {
            "view": "/api/view",
            "preferences": "/api/preferences",
            "recordings": "/api/recordings",
        }.items()
    }
    if public["view"]["binding_status"]["status"] != "current":
        raise ValueError(
            "The actual service still reports stale source or declarations"
        )
    if public["view"]["manifest"]["build_id"] != process["build_id"]:
        raise ValueError(
            "Runtime process and actual public view disagree about the build"
        )
    active = json.loads((TRIAL / ".stategraph/active.json").read_text(encoding="utf-8"))
    change = (TRIAL / active["change"]).resolve()
    change.relative_to(TRIAL.resolve())
    if not (change / "accepted.json").is_file():
        raise ValueError(
            "The original conversation has not accepted its current change"
        )
    accepted = json.loads((change / "accepted.json").read_text(encoding="utf-8"))
    sources = {}
    for directory in (
        "app",
        "integrations",
        "bo_stategraph",
        "tooling",
        "tests",
        "templates",
        "static",
    ):
        for source in (TRIAL / directory).rglob("*"):
            relative = source.relative_to(TRIAL)
            if (
                source.is_file()
                and source.suffix in {".py", ".html", ".css", ".json"}
                and not set(relative.parts) & {"__pycache__", "graph", "data", "config"}
            ):
                sources[relative.as_posix()] = source
    for name in (
        "AGENTS.md",
        "acceptance.json",
        "whitebox.json",
        "discovery.json",
        "intent.json",
        "behavior.json",
        "sync.json",
        "mapping.json",
        "implementation.json",
        "ownership.json",
        "manifest.json",
        "requirements.txt",
    ):
        source = TRIAL / name
        if source.is_file():
            sources[name] = source
    for source in change.rglob("*.json"):
        if source.stat().st_size < 3_000_000:
            sources[source.relative_to(TRIAL).as_posix()] = source
    for name in (".stategraph/code-graph.json", ".stategraph/maintenance.json"):
        source = TRIAL / name
        if source.is_file():
            sources[name] = source
    hashes = {}
    with zipfile.ZipFile(
        destination / "source-and-contracts.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for relative, source in sorted(sources.items()):
            raw = source.read_bytes()
            hashes[relative] = hashlib.sha256(raw).hexdigest()
            archive.writestr(relative, raw)
    for name, value in public.items():
        with gzip.open(destination / f"{name}.json.gz", "wb") as output:
            output.write(
                json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
            )
    execution = json.loads((change / "checks/observations.json").read_text(encoding="utf-8"))
    if execution["exit_code"] != 0:
        raise ValueError("The accepted observation command failed")
    observations = execution["stdout"].encode("utf-8")
    with gzip.open(destination / "runtime-observations.json.gz", "wb") as output:
        output.write(observations)
    database = (TRIAL / "data/application.sqlite3").as_uri() + "?mode=ro"
    with sqlite3.connect(database, uri=True) as connection:
        structure = [
            dict(zip(("type", "name", "table", "sql"), row))
            for row in connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
            )
        ]
    write_json(destination / "sqlite-structure.json", structure)
    model = public["view"]["model"]
    summary = {
        "phase": phase,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "kind": "Accepted original conversation snapshot, not an isolated repaired copy",
        "thread_id": "01a18f4d-11b3-7553-bbeb-6410929a9146",
        "runtime": process,
        "active": active,
        "accepted": accepted,
        "observations_sha256": hashlib.sha256(observations).hexdigest(),
        "build_id": public["view"]["manifest"]["build_id"],
        "nodes": {
            node["id"]: {
                key: node[key]
                for key in ("type", "kind", "label", "source")
                if key in node
            }
            for node in model["nodes"]
        },
        "edges": model["edges"],
        "source_hashes": hashes,
    }
    write_json(destination / "snapshot.json", summary)
    print(
        json.dumps(
            {
                "phase": phase,
                "build_id": summary["build_id"],
                "source_files": len(hashes),
                "nodes": len(summary["nodes"]),
                "edges": len(summary["edges"]),
            }
        )
    )


if __name__ == "__main__":
    main()
