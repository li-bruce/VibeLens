"""Activate the GitHub-downloaded patch without changing the trial application."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

from install_candidate import check_files


def main():
    """Require exact package parity and retain the previous installation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ref", required=True, help="Published Git commit or release tag"
    )
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[4]
    trial = (
        repository.parent / "VibeLensTrials/graph-quality-dialogue-20261104-01"
    ).resolve()
    active = trial / ".agents/skills/vibelens"
    staged = trial / ".stategraph/install-v0.11.2/vibelens"
    backup = trial / ".stategraph/installation-backups/v0.11.1/vibelens"
    receipt = trial / "review/installation/github-install-v0.11.2.json"
    copy_receipt = Path(__file__).parent / "release-v0.11.2-install.json"
    for path in (active, staged, backup, receipt):
        assert path.resolve().is_relative_to(
            trial
        ), "Installation path escaped the trial"
    assert not backup.exists() and not receipt.exists() and not copy_receipt.exists()
    old = json.loads(
        (repository / "docs/review/release-v0.11.1/manifest.json").read_text()
    )
    new = json.loads(
        (repository / "docs/review/release-v0.11.2/manifest.json").read_text()
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", args.ref + "^{commit}"], cwd=repository, text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "rev-parse", commit + ":skills/vibelens"], cwd=repository, text=True
    ).strip()
    assert tree == new["skill_tree"], "Published ref differs from the frozen package"
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
        "source": "Official Skill Installer, GitHub, method git",
        "ref": args.ref,
        "commit": commit,
        "version": "0.11.2",
        "files": new_count,
        "skill_tree": tree,
        "archive_sha256": new["archive_sha256"],
        "previous_files": old_count,
        "backup": backup.relative_to(trial).as_posix(),
        "runtime_upgrade_performed": False,
    }
    for path in (receipt, copy_receipt):
        path.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
