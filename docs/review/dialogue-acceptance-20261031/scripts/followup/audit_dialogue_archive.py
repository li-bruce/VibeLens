"""Verify lossless event archives, retained failed checkpoints and review links."""

import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/review/dialogue-acceptance-20261031"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    phase = sys.argv[1]
    target = REVIEW / ("archive-audit-" + phase + ".json")
    if target.exists():
        raise ValueError("Retain each audit receipt; choose a new phase")
    history = read(REVIEW / "checkpoint-history/index.json")
    checks = []
    result = {"phase": phase, "checks": checks}
    try:
        for item in history:
            path = REVIEW / "checkpoint-history" / item["archive"]
            assert sha(path.read_bytes()) == item["sha256"], str(path)
            with zipfile.ZipFile(path) as archive:
                assert set(archive.namelist()) == set(item["files"])
                for name, expected in item["files"].items():
                    assert sha(archive.read(name)) == expected, name
        checks.append(
            {
                "name": "Original failed and superseded checkpoints remain exact",
                "archives": len(history),
                "files": sum(len(item["files"]) for item in history),
            }
        )

        def bytes_at(relative):
            path = REVIEW / relative
            if path.is_file():
                return path.read_bytes()
            root_relative = path.relative_to(ROOT).as_posix()
            for item in history:
                prefix = item["original_directory"] + "/"
                if root_relative.startswith(prefix):
                    with zipfile.ZipFile(
                        REVIEW / "checkpoint-history" / item["archive"]
                    ) as archive:
                        return archive.read(root_relative[len(prefix) :])
            raise FileNotFoundError(relative)

        entries = []
        for manifest in ("compressed-evidence.json", "followup-compressed-evidence.json"):
            for item in read(REVIEW / manifest):
                raw = gzip.decompress(bytes_at(item.get("gzip", item.get("compressed"))))
                assert len(raw) == item["bytes"] and sha(raw) == item["sha256"], item["original"]
                json.loads(raw)
                entries.append(item["original"])
        checks.append(
            {"name": "Complete event/view JSON restores exactly from gzip", "files": entries}
        )
        for snapshot in (REVIEW / "iteration").glob("*/snapshot.json"):
            value = read(snapshot)
            with zipfile.ZipFile(snapshot.parent / "source-and-contracts.zip") as archive:
                for name, expected in value["source_hashes"].items():
                    assert sha(archive.read(name)) == expected, name
        checks.append({"name": "All iteration source/contract snapshots retain their exact bytes"})
        retained_changes = []
        for index in (REVIEW / "iteration").glob("*-evidence.json"):
            value = read(index)
            path = index.parent / value["archive"]
            assert sha(path.read_bytes()) == value["sha256"], str(path)
            with zipfile.ZipFile(path) as archive:
                assert set(archive.namelist()) == set(value["files"])
                for name, expected in value["files"].items():
                    assert sha(archive.read(name)) == expected, name
            retained_changes.append(value["archive"])
        checks.append({"name": "Closed dialogue changes and failed attempts restore exactly", "archives": retained_changes})
        followup = REVIEW / "scripts/followup/manifest.json"
        if followup.exists():
            for name, expected in read(followup)["sha256"].items():
                assert sha((followup.parent / name).read_bytes()) == expected, name
            checks.append({"name": "Final executed followup harnesses match their archived hashes"})
        missing = []
        for text in (REVIEW / "README.md").read_text(encoding="utf-8").splitlines():
            for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
                if link.startswith(("https:", "http:", "codex:", "#")):
                    continue
                path = REVIEW / link.split("#", 1)[0]
                if not path.exists():
                    missing.append(link)
        assert not missing, missing
        checks.append({"name": "Review index file and screenshot links resolve"})
        result["passed"] = True
    except Exception as error:
        result.update(passed=False, error=repr(error))
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"passed": result["passed"], "checks": len(checks), "error": result.get("error")}
        )
    )
    raise SystemExit(not result["passed"])


if __name__ == "__main__":
    main()
