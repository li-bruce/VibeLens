"""Archive only this followup's superseded example approvals, keeping exact backups."""

import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "docs/review/dialogue-acceptance-20261031/checkpoint-history"
CACHE = ROOT / ".validation/dialogue-history-unpacked"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    index = json.loads((HISTORY / "index.json").read_text(encoding="utf-8"))
    additions = []
    for name in ("delivery", "team-archive"):
        base = (ROOT / "examples" / name / ".release/stategraph").resolve()
        base.relative_to(ROOT.resolve())
        active = Path(json.loads((base / "active.json").read_text())["change"]).name
        checkpoints = sys.argv[1:] or ["dialogue-byte-identity-20261031", "dialogue-batch-sink-20261031"]
        allowed = {"dialogue-byte-identity-20261031", "dialogue-batch-sink-20261031", "dialogue-viewer-backlog-20261031"}
        if set(checkpoints) - allowed:
            raise ValueError("Only this followup's named superseded approvals may be archived")
        for checkpoint in checkpoints:
            if checkpoint == active:
                raise ValueError("Never archive the current approval")
            source = (base / checkpoint).resolve()
            source.relative_to(base)
            if not source.is_dir():
                raise ValueError("Expected one superseded approval")
            relative = source.relative_to(ROOT.resolve())
            cache = (CACHE / relative).resolve()
            cache.relative_to(CACHE.resolve())
            archive = HISTORY / ("--".join(relative.parts) + ".zip")
            if archive.exists() or cache.exists():
                raise ValueError("Do not replace an earlier archive or backup")
            hashes = {}
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as output:
                for path in sorted(source.rglob("*")):
                    if path.is_file():
                        path.resolve().relative_to(source)
                        raw = path.read_bytes()
                        member = path.relative_to(source).as_posix()
                        output.writestr(member, raw)
                        hashes[member] = sha(raw)
            with zipfile.ZipFile(archive) as output:
                assert set(output.namelist()) == set(hashes)
                assert all(sha(output.read(member)) == digest for member, digest in hashes.items())
            cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(cache))
            item = {"original_directory": relative.as_posix(), "archive": archive.name,
                    "sha256": sha(archive.read_bytes()), "files": hashes}
            index.append(item)
            additions.append(item)
    (HISTORY / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"new_archives": len(additions), "total_archives": len(index),
                      "files_preserved": sum(len(item["files"]) for item in additions)}))


if __name__ == "__main__":
    main()
