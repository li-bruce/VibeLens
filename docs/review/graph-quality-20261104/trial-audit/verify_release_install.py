"""Compare the official tag download with the candidate already used by the trial."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from install_candidate import check_files


def main():
    """Verify every reviewed file; keep the candidate-install chronology explicit."""
    repository = Path(__file__).resolve().parents[4]
    trial = repository.parent / "VibeLensTrials/graph-quality-dialogue-20261104-01"
    manifest = json.loads((repository / "docs/review/release-v0.11.1/manifest.json").read_text())
    tag = subprocess.check_output(
        ["git", "rev-parse", "v0.11.1^{commit}"], cwd=repository, text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "rev-parse", "v0.11.1:skills/vibelens"], cwd=repository, text=True
    ).strip()
    assert tree == manifest["skill_tree"]
    official = trial / ".stategraph/install-v0.11.1-release/vibelens"
    active = trial / ".agents/skills/vibelens"
    official_count = check_files(official, manifest)
    active_count = check_files(active, manifest)
    result = {
        "valid": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "source": "Official Skill Installer, GitHub tag v0.11.1, method git",
        "tag_commit": tag,
        "skill_tree": tree,
        "official_download_files": official_count,
        "active_candidate_files": active_count,
        "all_bytes_identical": True,
        "active_copy_replaced": False,
        "chronology": "V1 used official v0.11.0. Iteration installed the c56fd19f candidate; its 305 Skill files equal the later official v0.11.1 tag download.",
    }
    destinations = (
        Path(__file__).parent / "release-install-parity.json",
        trial / "review/installation/github-install-v0.11.1-tag.json",
    )
    assert not any(path.exists() for path in destinations), "Retain prior installation receipts"
    for path in destinations:
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
