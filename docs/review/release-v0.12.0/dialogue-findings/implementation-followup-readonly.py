"""Check saved trial evidence without importing or running its application.

Pass the trial or extracted checkpoint project directory as the first argument.
An extracted public release's scripts directory can supply --runtime. This script reads existing JSON
and source files, invokes only the installed pure evidence validators, and writes
its report to stdout. It does not serve HTTP, run scenarios, or modify the trial.
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("project", type=Path)
parser.add_argument(
    "--runtime", type=Path, help="Public v0.12.0 vibelens/scripts directory"
)
args = parser.parse_args()
trial = args.project
runtime = args.runtime or trial / "observer_runtime"
sys.path.insert(0, str(runtime))
from bo_observer.concepts.runtime import runtime_errors
from bo_observer.workflow.observation_requirements import invocation_closure


def read(name):
    """Read one retained artifact; never regenerate it during this audit."""
    return json.loads((trial / name).read_text(encoding="utf-8"))


def sha(name):
    """Keep release-runtime provenance separate from checkpoint-owned files."""
    path = (
        runtime / name.removeprefix("observer_runtime/")
        if name.startswith("observer_runtime/")
        else trial / name
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


payload = read("review/implementation-01/observations-corrected.json")
model = read("bo_stategraph/project.json")["model"]
discovery = read("discovery.json")
manifest = read("manifest.json")
run = next(
    r for r in payload["runs"] if r["case"] == "full-workflow" and r["mode"] == "on"
)
events = {e["id"]: e for e in run["events"]}
checks = []
for witness in run["semantic_observations"]:
    if witness["label"] == "review-entry-commit-completion":
        entry, commit, completion = [events[eid] for eid in witness["event_ids"]]
        valid = (
            entry["node"] == completion["node"] == "retain_review_record"
            and (entry["phase"], commit["phase"], completion["phase"])
            == ("enter", "commit", "commit")
            and commit["node"] == "transaction"
            and entry["call_id"] == completion["call_id"] == witness["review_id"]
            and all(
                e["outputs"]["transaction_id"] == witness["transaction_id"]
                for e in (entry, commit, completion)
            )
            and entry["entity"] == completion["entity"] == entry["outputs"]["file_id"]
            and entry["attempt"] == commit["attempt"] == completion["attempt"]
            and entry["seq"] < commit["seq"] < completion["seq"]
            and entry["outputs"]["committed"] is False
            and commit["outputs"]["committed"] is True
            and completion["outputs"]["committed"] is True
            and any(
                j["transaction_id"] == witness["transaction_id"]
                and j["object_id"] == entry["entity"]
                for j in run["authority_snapshot"]["journal"]
            )
        )
        checks.append(
            {
                **witness,
                "valid": valid,
                "sequence": [entry["seq"], commit["seq"], completion["seq"]],
            }
        )
        continue
    selected = [events[eid] for eid in witness["events"]]
    forbidden = [e["id"] for e in selected if e["node"] in witness["absent"]]
    required = witness["required"]
    matches = [
        e["id"]
        for e in selected
        if required
        and e["node"] == required["node"]
        and all(e["outputs"].get(k) == v for k, v in required["values"].items())
    ]
    checks.append(
        {
            **witness,
            "valid": not forbidden and (not required or bool(matches)),
            "matching_events": matches,
            "forbidden_events": forbidden,
        }
    )

framework = [e for e in events.values() if e["node"] == "api:framework_error"]
assert len(framework) == 2
assert framework[0]["inputs"] == {
    "method": "GET",
    "path": "/missing-route",
    "request_id": framework[0]["entity"],
}
assert framework[1]["outputs"]["status_code"] == 404
assert framework[0]["call_id"] == framework[1]["call_id"]
assert all(c["valid"] for c in checks)
assert all(item["native"] == item["sqlite"] for item in run["native_fact_reads"])
assert all(r["status_code"] == r["expected_status"] for r in run["receipts"])

files = [
    "app.py",
    "service.py",
    "bo_integration.py",
    "build_model.py",
    "tests/scenarios.py",
    "tests/observe.py",
    "bo_stategraph/project.json",
    "discovery.json",
    "manifest.json",
    "sync.json",
    "implementation.json",
    "observer_runtime/bo_observer/concepts/runtime.py",
    "observer_runtime/bo_observer/workflow/observation_requirements.py",
    "review/implementation-01/observations-corrected.json",
    "review/implementation-01/verify-initial.json",
    "review/implementation-01/api-corrected.json",
    "review/implementation-01/database-check.json",
    "review/implementation-01/docs-corrected.json",
]
result = {
    "stage": "implementation-01 corrected evidence; pre-browser; not final acceptance",
    "audited_at": datetime.now(timezone.utc).isoformat(),
    "trial": str(trial),
    "build_id": payload["build_id"],
    "build_matches_manifest": payload["build_id"] == manifest["build_id"],
    "manifest_source_mismatches": [
        name for name, digest in manifest["files"].items() if sha(name) != digest
    ],
    "sha256": {name: sha(name) for name in files},
    "concept_runtime_errors": runtime_errors(discovery, model, payload),
    "invocation_closure": invocation_closure(payload, required=True, model=model),
    "closure_count_note": "The effect-expectation case intentionally references full-workflow events again; closed_calls is not a distinct invocation count.",
    "unique_events": len(events),
    "node_phase_counts": {
        f"{node}/{phase}": count
        for (node, phase), count in sorted(
            Counter((e["node"], e["phase"]) for e in events.values()).items()
        )
        if node
        in {
            "retain_review_record",
            "notify",
            "deny_old_link",
            "api:framework_error",
            "permission",
        }
    },
    "semantic_checks": checks,
    "framework_events": framework,
    "mode_summaries": [
        {
            "mode": r["mode"],
            "events": len(r["events"]),
            "outcomes": r["outcomes"],
            "probe_health": r["probe_health"],
            "fact_reads": len(r["native_fact_reads"]),
            "receipts": len(r["receipts"]),
        }
        for r in payload["runs"]
        if r["case"] == "full-workflow"
    ],
    "retained_checks": {
        name: read("review/implementation-01/" + name)
        for name in ("api-corrected.json", "database-check.json", "docs-corrected.json")
    },
    "latest_full_verify_still_precedes_correction": not read(
        "review/implementation-01/verify-initial.json"
    )["valid"],
}
print(json.dumps(result, ensure_ascii=False, indent=2))
