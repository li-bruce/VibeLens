"""Freeze trial source and declared contracts without copying its live secrets/data."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--change", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.out.exists() or args.out.with_suffix(".json").exists():
        raise FileExistsError("A frozen source archive cannot be overwritten")
    files = {path for path in root.iterdir() if path.is_file()}
    for name in (
        "app",
        "bo_stategraph",
        "integrations",
        "observer_runtime",
        "static",
        "tests",
        "tooling",
    ):
        files.update(path for path in (root / name).rglob("*") if path.is_file())
    change = root / ".stategraph" / args.change
    files.update(path for path in change.rglob("*") if path.is_file())
    cfg = json.loads((root / "sync.json").read_text(encoding="utf-8"))
    files.update(root / name for name in cfg["watch_files"] if (root / name).is_file())
    selected = {}
    for path in sorted(files):
        relative = path.relative_to(root).as_posix()
        if (
            set(path.relative_to(root).parts) & {"__pycache__", "node_modules", ".venv"}
            or relative.startswith("bo_stategraph/data/")
            or path.suffix in {".pyc", ".sqlite3", ".db"}
        ):
            continue
        selected[relative] = path.read_bytes()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.out, "x", compression=ZIP_DEFLATED) as archive:
        for name, content in selected.items():
            archive.writestr(name, content)
    result = {
        "scope": "Source, installed runtime/viewer, contracts and protected change evidence. Live application data, observer recordings and session secrets are omitted.",
        "change": args.change,
        "files": {name: sha256(value).hexdigest() for name, value in selected.items()},
        "archive_sha256": sha256(args.out.read_bytes()).hexdigest(),
    }
    args.out.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "files": len(selected),
                "bytes": args.out.stat().st_size,
                "archive_sha256": result["archive_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
