"""Store new full event/view evidence losslessly, retaining hashes and a local raw copy."""

import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/review/dialogue-acceptance-20261031"
BACKUP = ROOT / ".validation/dialogue-followup-raw"
MANIFEST = REVIEW / "followup-compressed-evidence.json"


def main():
    tracked = {
        Path(name).resolve()
        for name in subprocess.check_output(
            ["git", "ls-files", "-z", "--", str(REVIEW.relative_to(ROOT))], cwd=ROOT
        )
        .decode("utf-8")
        .split("\0")
        if name
    }
    report = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    count = 0
    for name in (
        "actual-recording.json",
        "actual-view-before.json",
        "actual-view-after.json",
        "restored-full-recording.json",
    ):
        for source in sorted(REVIEW.rglob(name)):
            source = source.resolve()
            source.relative_to(REVIEW.resolve())
            if source in tracked:
                continue
            raw = source.read_bytes()
            if len(raw) < 65536:
                continue
            target = source.with_suffix(source.suffix + ".gz")
            if target.exists():
                raise ValueError("Existing compressed evidence must not be overwritten")
            backup = (BACKUP / source.relative_to(REVIEW)).resolve()
            backup.relative_to(BACKUP.resolve())
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                if backup.read_bytes() != raw:
                    raise ValueError("An earlier raw backup has different contents")
            else:
                shutil.copyfile(source, backup)
            compressed = gzip.compress(raw, compresslevel=9, mtime=0)
            target.write_bytes(compressed)
            assert gzip.decompress(target.read_bytes()) == raw
            assert backup.read_bytes() == raw
            report.append(
                {
                    "original": source.relative_to(REVIEW).as_posix(),
                    "gzip": target.relative_to(REVIEW).as_posix(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                    "gzip_sha256": hashlib.sha256(compressed).hexdigest(),
                    "gzip_bytes": len(compressed),
                }
            )
            source.unlink()  # The resolved evidence path, gzip and raw backup were checked above.
            count += 1
    MANIFEST.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"new_files": count, "total": len(report), "raw_copy_retained": True}))


if __name__ == "__main__":
    main()
