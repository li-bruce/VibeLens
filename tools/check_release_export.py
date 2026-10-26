"""Check frozen example approvals against a clean Git export, without reapproval.

Use HEAD in CI or --staged before a release commit. This catches line-ending,
missing-file and generated-copy differences that a warm checkout can conceal.
"""

import argparse
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check_export(*, ref="HEAD", staged=False):
    """Restore only frozen approvals, then require both native check commands to pass."""
    revision = subprocess.check_output(
        ["git", "write-tree"] if staged else ["git", "rev-parse", ref],
        cwd=ROOT,
        text=True,
    ).strip()
    data = subprocess.check_output(
        [
            "git",
            "archive",
            "--format=zip",
            revision,
            "examples/delivery",
            "examples/team-archive",
        ],
        cwd=ROOT,
    )
    results = []
    (ROOT / ".validation").mkdir(exist_ok=True)
    environment = {
        **os.environ,
        "BO_ADAPTER_HOME": str(
            ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript"
        ),
    }
    with tempfile.TemporaryDirectory(
        prefix="release-export-", dir=ROOT / ".validation"
    ) as folder:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.extractall(folder)
        for name, runtime, manifest in (
            (
                "delivery",
                "observer_generated/runtime",
                "observer_generated/manifest.json",
            ),
            ("team-archive", "observer_runtime", "manifest.json"),
        ):
            project = Path(folder) / "examples" / name
            shutil.copytree(project / ".release/stategraph", project / ".stategraph")
            if not (project / manifest).exists():
                shutil.copyfile(project / ".release/manifest.json", project / manifest)
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    runtime + "/change_sync.py",
                    "check",
                    "--root",
                    ".",
                ],
                cwd=project,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            results.append(
                {
                    "example": name,
                    "exit_code": process.returncode,
                    "output": process.stdout + process.stderr,
                }
            )
    return {
        "valid": all(item["exit_code"] == 0 for item in results),
        "revision": revision,
        "scope": "Clean Git export plus frozen approvals; no regeneration or reapproval",
        "examples": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    report = check_export(ref=args.ref, staged=args.staged)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    raise SystemExit(not report["valid"])
