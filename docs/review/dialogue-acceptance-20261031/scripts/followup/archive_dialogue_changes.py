"""Retain closed dialogue change gates, including failed attempts, without editing them."""

import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
OUT = ROOT / "docs/review/dialogue-acceptance-20261031/iteration"


def main():
    phase, *names = sys.argv[1:]
    if not names or any(
        not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in name)
        for name in [phase, *names]
    ):
        raise ValueError("Supply a new simple phase and accepted change names")
    target = OUT / (phase + ".zip")
    index = OUT / (phase + ".json")
    if target.exists() or index.exists():
        raise ValueError("Do not replace earlier evidence")
    sources, accepted = {}, {}
    for name in names:
        folder = TRIAL / ".stategraph" / name
        accepted[name] = json.loads((folder / "accepted.json").read_text(encoding="utf-8"))
        for source in folder.rglob("*"):
            if source.is_file():
                source.resolve().relative_to(TRIAL.resolve())
                sources[source.relative_to(TRIAL).as_posix()] = source
        for source in (TRIAL / "review/attempts").glob(name + "-*"):
            if source.is_file():
                sources[source.relative_to(TRIAL).as_posix()] = source
        for source in (TRIAL / "review").glob(name + "-*"):
            if source.is_file():
                sources[source.relative_to(TRIAL).as_posix()] = source
        handoff = TRIAL / "review" / ("handoff-" + name + ".json")
        if handoff.exists():
            sources[handoff.relative_to(TRIAL).as_posix()] = handoff
    hashes = {}
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, source in sorted(sources.items()):
            raw = source.read_bytes()
            archive.writestr(name, raw)
            hashes[name] = hashlib.sha256(raw).hexdigest()
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist()) == set(hashes)
        for name, digest in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    report = {"kind": "Closed original conversation changes and every matching attempt; not replacement approval",
              "archive": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
              "accepted": accepted, "files": hashes}
    index.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archive": target.name, "files": len(hashes), "changes": names}))


if __name__ == "__main__":
    main()
