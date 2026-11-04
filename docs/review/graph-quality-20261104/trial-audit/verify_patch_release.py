"""Compare an official release download with the recorded trial installation."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from install_candidate import check_files
from install_patch import (
    bounded,
    manifest_for,
    release_version,
    require,
    resolve_ref,
    skill_tree,
    write_receipt,
)


def main():
    """Retain exact tag, package and installation parity without app changes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=release_version, default="0.11.2")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[4]
    trial = (repository.parent / "VibeLensTrials/graph-quality-dialogue-20261104-01").resolve()
    tag = "v" + args.version
    destinations = (
        bounded(
            Path(__file__).parent / ("release-v" + args.version + "-tag-parity.json"), repository
        ),
        bounded(
            trial / ("review/installation/github-install-v" + args.version + "-tag.json"), trial
        ),
    )
    require(
        not any(path.exists() for path in destinations), "Retain previous installation evidence"
    )
    manifest = manifest_for(repository, args.version)
    commit = resolve_ref(repository, tag)
    tree = skill_tree(repository, commit)
    require(tree == manifest["skill_tree"], "Official tag differs from the frozen release")
    installation_path = bounded(
        Path(__file__).parent / ("release-v" + args.version + "-install.json"), repository
    )
    installation = json.loads(installation_path.read_text(encoding="utf-8"))
    original_receipt = bounded(
        trial / ("review/installation/github-install-v" + args.version + ".json"), trial
    )
    require(
        original_receipt.read_bytes() == installation_path.read_bytes(),
        "Trial installation receipt differs from its review copy",
    )
    require(
        installation.get("valid") is True
        and installation["version"] == args.version
        and installation["skill_tree"] == tree
        and installation["archive_sha256"] == manifest["archive_sha256"],
        "The recorded candidate installation differs from this release",
    )
    installed_commit = resolve_ref(repository, installation["commit"])
    require(
        installed_commit == installation["commit"]
        and skill_tree(repository, installed_commit) == tree,
        "The installed candidate commit does not contain this Skill",
    )
    official = bounded(trial / (".stategraph/install-v" + args.version + "-tag/vibelens"), trial)
    active = bounded(trial / ".agents/skills/vibelens", trial)
    result = {
        "valid": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "source": "Official Skill Installer, GitHub tag " + tag + ", method git",
        "version": args.version,
        "tag_commit": commit,
        "candidate_commit": installed_commit,
        "candidate_ref": installation["ref"],
        "candidate_installed_at": installation["installed_at"],
        "candidate_installation_receipt_sha256": sha256(installation_path.read_bytes()).hexdigest(),
        "skill_tree": tree,
        "official_download_files": check_files(official, manifest),
        "active_candidate_files": check_files(active, manifest),
        "all_bytes_identical": True,
        "active_copy_replaced": False,
        "chronology": (
            "The installation receipt records commit "
            + installed_commit
            + " at "
            + installation["installed_at"]
            + "; its Skill matches official tag "
            + tag
            + " at commit "
            + commit
            + "."
        ),
    }
    for path in destinations:
        write_receipt(path, result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
