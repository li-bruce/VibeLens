"""Freeze the staged Skill into a reproducible, independently checked ZIP."""

from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
DESTINATION = Path(__file__).resolve().parent


def build():
    """Package Git blobs, excluding untracked dependencies and personal data."""
    tree = subprocess.check_output(["git", "write-tree"], cwd=ROOT, text=True).strip()
    skill_tree = subprocess.check_output(
        ["git", "rev-parse", tree + ":skills/vibelens"], cwd=ROOT, text=True
    ).strip()
    original = subprocess.check_output(
        ["git", "archive", "--format=zip", tree, "skills/vibelens"], cwd=ROOT
    )
    destination = DESTINATION / "archives/vibelens-v0.11.2.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = []
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member in sorted(source.namelist()):
                if member.endswith("/"):
                    continue
                data = source.read(member)
                name = member.removeprefix("skills/")
                metadata = zipfile.ZipInfo(name, date_time=(2026, 11, 4, 0, 0, 0))
                metadata.compress_type = zipfile.ZIP_DEFLATED
                metadata.external_attr = 0o100644 << 16
                archive.writestr(metadata, data)
                files.append({"path": name, "sha256": sha256(data).hexdigest()})
    with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
        with zipfile.ZipFile(destination) as archive:
            archive.extractall(folder)
        for item in files:
            assert sha256((Path(folder) / item["path"]).read_bytes()).hexdigest() == item["sha256"]
        settings = (Path(folder) / "vibelens/agents/openai.yaml").read_text(encoding="utf-8")
        assert "allow_implicit_invocation: false" in settings
        assert not any("node_modules" in item["path"] or "__pycache__" in item["path"] for item in files)
    report = {
        "passed": True,
        "tag": "v0.11.2",
        "skill_tree": skill_tree,
        "scope": "Staged Skill Git blobs and a fresh ZIP extraction; no credentials or runtime data",
        "archive": destination.relative_to(ROOT).as_posix(),
        "archive_sha256": sha256(destination.read_bytes()).hexdigest(),
        "archive_size": destination.stat().st_size,
        "skill_files": len(files),
        "fresh_install_matches_archive": True,
        "implicit_invocation": False,
        "files": files,
    }
    (DESTINATION / "manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "files"}))


if __name__ == "__main__":
    build()
