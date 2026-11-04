"""Compare accepted example inputs with the exact Git index bytes before export.

This evidence helper never regenerates a model or changes an approval. It also
checks the historical review that is intentionally excluded from staging.
"""

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
HISTORY = "examples/delivery/.release/stategraph/whitebox-v04/review.json"


def read_json(path):
    """Read a JSON report, allowing the Python launcher diagnostic before it."""
    value = path.read_text(encoding="utf-8")
    return json.loads(value[value.index("{") :])


def index_objects(paths):
    """Load selected blobs in one Git process without line-ending conversion."""
    listing = subprocess.check_output(
        [
            "git",
            "ls-files",
            "-s",
            "-z",
            "--",
            "examples/delivery",
            "examples/team-archive",
        ],
        cwd=ROOT,
    )
    entries = {}
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        header, path = entry.split(b"\t", 1)
        _, object_id, stage = header.split()
        assert stage == b"0", "Unmerged example input"
        entries[path.decode("utf-8")] = object_id.decode("ascii")
    selected = {path: entries[path] for path in paths}
    object_ids = sorted(set(selected.values()))
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        input=("\n".join(object_ids) + "\n").encode("ascii"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        check=True,
    )
    stream = io.BytesIO(result.stdout)
    objects = {}
    for object_id in object_ids:
        actual_id, kind, length = stream.readline().split()
        assert actual_id.decode("ascii") == object_id and kind == b"blob"
        objects[object_id] = stream.read(int(length))
        assert stream.read(1) == b"\n"
    return selected, objects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pass-label", required=True)
    parser.add_argument("--check-label", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    destination = EVIDENCE / args.out
    assert not destination.exists(), "Never overwrite evidence"
    expected = {}
    reports = []
    for name, short in (("delivery", "delivery"), ("team-archive", "archive")):
        prefix = "examples/" + name + "/"
        root = ROOT / "examples" / name
        summary = read_json(
            EVIDENCE / f"examples-{name}-{args.pass_label}-acceptance-summary.json"
        )
        check = read_json(
            EVIDENCE / f"examples-{short}-{args.check_label}-post-freeze-check.log"
        )
        assert summary["valid"] and summary["canonical_runtime_current"]
        assert check["valid"] and check["status"] == "current"
        assert check["candidate_id"] == summary["candidate_id"]
        manifest = read_json(root / ".release/manifest.json")
        runtime = read_json(root / "bo_stategraph/runtime-version.json")
        sync = read_json(root / "sync.json")
        scan = read_json(EVIDENCE / f"examples-{name}-{args.pass_label}-scan.log")
        selected = {}

        def add(relative, digest=None):
            """Keep native expected hashes authoritative for overlapping inputs."""
            path = root / relative
            actual = sha256(path.read_bytes()).hexdigest()
            assert (
                digest is None or digest == actual
            ), "Local accepted input differs: " + str(path)
            prior = selected.setdefault(relative, digest or actual)
            assert prior == actual, "Conflicting accepted input hashes: " + relative

        for mapping in (manifest["files"], runtime["files"]):
            for relative, digest in mapping.items():
                add(relative, digest)
        for key in ("watch_files", "code_files", "source_files"):
            for relative in sync.get(key, []):
                add(relative)
        add("sync.json")
        # These maintained examples keep user intent beside sync.json, rather
        # than declaring its path as a sync option. It is a native build input.
        if (root / "intent.json").is_file():
            add("intent.json")
        for key in (
            "model",
            "intent",
            "acceptance",
            "discovery",
            "whitebox",
            "mapping_contract",
            "reconciliation",
        ):
            relative = sync.get(key)
            if isinstance(relative, str):
                add(relative)
        intent = str(Path(sync["model"]).with_name("model.intent.json"))
        if (root / intent).is_file():
            add(intent)
        for relative, digest in scan["inventory"]["scope_inputs"].items():
            add(relative, digest)
        for relative, digest in selected.items():
            expected[prefix + relative.replace("\\", "/")] = digest
        reports.append(
            {
                "example": name,
                "release": runtime["release"],
                "candidate_id": summary["candidate_id"],
                "baseline_sha256": summary["baseline_sha256"],
                "frozen_change": summary["frozen_change"],
                "post_freeze_current_check": True,
                "frozen_model_files": len(manifest["files"]),
                "managed_expected_hashes": len(runtime["files"]),
                "watch_files": len(sync.get("watch_files", [])),
                "selected_inputs": len(selected),
                "gitignore_bytes": len((root / ".gitignore").read_bytes()),
                "gitignore_sha256": sha256(
                    (root / ".gitignore").read_bytes()
                ).hexdigest(),
            }
        )
    indices, blobs = index_objects([*expected, HISTORY])
    mismatches = []
    for path, digest in expected.items():
        actual = sha256(blobs[indices[path]]).hexdigest()
        if actual != digest:
            mismatches.append(
                {"path": path, "expected_sha256": digest, "staged_sha256": actual}
            )
    historical_id = subprocess.check_output(
        ["git", "rev-parse", "HEAD:" + HISTORY], cwd=ROOT, text=True
    ).strip()
    historical_matches = indices[HISTORY] == historical_id
    result = {
        "valid": not mismatches and historical_matches,
        "scope": "Current native approvals plus exact Git staged blob parity; no approval or hash guard changes",
        "examples": reports,
        "compared_current_inputs": len(expected),
        "mismatches": mismatches,
        "historical_review_index_equals_head": historical_matches,
        "historical_review_sha256": sha256(blobs[indices[HISTORY]]).hexdigest(),
    }
    destination.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(result, indent=2))
    assert result["valid"], "Git staged bytes differ from accepted native inputs"


if __name__ == "__main__":
    main()
