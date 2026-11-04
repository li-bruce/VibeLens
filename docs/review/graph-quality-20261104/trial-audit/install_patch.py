"""Activate the GitHub-downloaded patch without changing the trial application."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess

from install_candidate import check_files


def release_version(value):
    """Accept only a plain release version before using it in any file path."""
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value):
        raise argparse.ArgumentTypeError("Use a release version such as 0.11.3")
    return value


def require(condition, message):
    """Keep installation and evidence guards active even under optimized Python."""
    if not condition:
        raise ValueError(message)


def bounded(path, root):
    """Resolve links and bound each installation move or receipt to its owner."""
    resolved = path.resolve()
    require(
        resolved != root and resolved.is_relative_to(root), "Path escaped its owner: " + str(path)
    )
    return path


def manifest_for(repository, version):
    """Load a reviewed package identity; file bytes are checked before activation."""
    release_version(version)
    path = bounded(
        repository / "docs/review" / ("release-v" + version) / "manifest.json", repository
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    require(
        value.get("passed") is True and value.get("tag") == "v" + version,
        "Wrong or failed release manifest",
    )
    require(
        value.get("fresh_install_matches_archive") is True, "Archive extraction was not verified"
    )
    require(re.fullmatch(r"[0-9a-f]{40}", value["skill_tree"]), "Invalid frozen Skill tree")
    require(re.fullmatch(r"[0-9a-f]{64}", value["archive_sha256"]), "Invalid archive identity")
    require(
        value["skill_files"]
        == len(value["files"])
        == len({item["path"] for item in value["files"]}),
        "Incomplete or duplicate package file inventory",
    )
    return value


def resolve_ref(repository, ref):
    """Resolve one explicit ref without allowing it to become a Git option."""
    require(bool(ref) and not ref.startswith("-") and "\x00" not in ref, "Invalid Git ref")
    return subprocess.check_output(
        ["git", "rev-parse", "--verify", ref + "^{commit}"], cwd=repository, text=True
    ).strip()


def skill_tree(repository, commit):
    """Read the exact published Skill subtree without executing its contents."""
    return subprocess.check_output(
        ["git", "rev-parse", commit + ":skills/vibelens"], cwd=repository, text=True
    ).strip()


def write_receipt(path, result):
    """Create new evidence exclusively; an earlier receipt is never replaced."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")


def main():
    """Require exact package parity and retain the previous installation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="Published Git commit or release tag")
    parser.add_argument("--version", type=release_version, default="0.11.2")
    parser.add_argument("--previous", type=release_version, default="0.11.1")
    args = parser.parse_args()
    require(args.version != args.previous, "The new and previous versions must differ")
    repository = Path(__file__).resolve().parents[4]
    trial = (repository.parent / "VibeLensTrials/graph-quality-dialogue-20261104-01").resolve()
    active = trial / ".agents/skills/vibelens"
    staged = trial / (".stategraph/install-v" + args.version) / "vibelens"
    backup = trial / (".stategraph/installation-backups/v" + args.previous) / "vibelens"
    receipt = trial / ("review/installation/github-install-v" + args.version + ".json")
    copy_receipt = Path(__file__).parent / ("release-v" + args.version + "-install.json")
    for path in (active, staged, backup, receipt):
        bounded(path, trial)
    bounded(copy_receipt, repository)
    require(
        not any(path.exists() for path in (backup, receipt, copy_receipt)),
        "Retain the previous backup and installation receipts",
    )
    old, new = manifest_for(repository, args.previous), manifest_for(repository, args.version)
    commit = resolve_ref(repository, args.ref)
    tree = skill_tree(repository, commit)
    require(tree == new["skill_tree"], "Published ref differs from the frozen package")
    old_count, new_count = check_files(active, old), check_files(staged, new)
    backup.parent.mkdir(parents=True, exist_ok=True)
    bounded(active, trial)
    bounded(backup, trial)
    shutil.move(str(active), str(backup))
    try:
        bounded(staged, trial)
        bounded(active, trial)
        shutil.move(str(staged), str(active))
        check_files(active, new)
    except Exception:
        if not active.exists():
            bounded(backup, trial)
            bounded(active, trial)
            shutil.move(str(backup), str(active))
        raise
    result = {
        "valid": True,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "source": "Official Skill Installer, GitHub, method git",
        "ref": args.ref,
        "commit": commit,
        "version": args.version,
        "previous_version": args.previous,
        "files": new_count,
        "skill_tree": tree,
        "archive_sha256": new["archive_sha256"],
        "previous_files": old_count,
        "backup": backup.relative_to(trial).as_posix(),
        "runtime_upgrade_performed": False,
    }
    for path in (receipt, copy_receipt):
        write_receipt(path, result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
