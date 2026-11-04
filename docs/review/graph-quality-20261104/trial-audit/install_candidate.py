"""Activate an independently downloaded Skill after exact package verification.

The previous installation is moved into a project-local backup. Application
source, runtime copies, business data and managed approvals are not changed.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil


def check_files(folder, manifest):
    """Check all reviewed package bytes without executing downloaded source."""
    expected = {}
    for item in manifest["files"]:
        name = item["path"].removeprefix("vibelens/")
        expected[name] = item["sha256"]
    actual = {
        path.relative_to(folder).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert actual == expected, "Downloaded installation differs from the reviewed package"
    return len(expected)


def main():
    """Verify both installations, bound every move and retain its origin receipt."""
    repository = Path(__file__).resolve().parents[4]
    trial = (repository.parent / "VibeLensTrials/graph-quality-dialogue-20261104-01").resolve()
    active = trial / ".agents/skills/vibelens"
    staged = trial / ".stategraph/install-v0.11.1-c56fd19f/vibelens"
    backup = trial / ".stategraph/installation-backups/v0.11.0/vibelens"
    receipt = trial / "review/installation/github-install-v0.11.1-candidate.json"
    for path in (active, staged, backup, receipt):
        assert path.resolve().is_relative_to(trial), "Installation path escaped the trial"
    assert not backup.exists() and not receipt.exists(), "Retain the earlier installation evidence"
    old = json.loads((repository / "docs/review/release-v0.11.0/manifest.json").read_text())
    new = json.loads((repository / "docs/review/release-v0.11.1/manifest.json").read_text())
    old_count, new_count = check_files(active, old), check_files(staged, new)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(active), str(backup))
    try:
        shutil.move(str(staged), str(active))
        check_files(active, new)
    except Exception:
        if not active.exists():
            shutil.move(str(backup), str(active))
        raise
    result = {
        "valid": True,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "source": "GitHub via official Skill Installer, method git",
        "ref": "c56fd19f87b7803932f3a979da9efcc61058c6d7",
        "version": "0.11.1",
        "release_status_at_install": "Candidate; official tag parity remains a separate check",
        "files": new_count,
        "skill_tree": new["skill_tree"],
        "archive_sha256": new["archive_sha256"],
        "previous_files": old_count,
        "backup": backup.relative_to(trial).as_posix(),
        "runtime_upgrade_performed": False,
    }
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
