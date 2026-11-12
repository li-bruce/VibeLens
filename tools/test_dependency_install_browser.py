"""Run the real collector/browser acceptance from a cold, extracted release Skill."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from build_distribution import build
from setup_viewer import ROOT
from bo_observer.delivery.dependencies import check_assets, locked_assets


def main():
    evidence = ROOT / os.environ.get(
        "BO_DEPENDENCY_BROWSER_EVIDENCE", ".validation/dependency-cold-browser"
    )
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cold-skill-", dir=ROOT / ".validation") as folder:
        work = Path(folder)
        report = build(work / "packages")
        archive = work / "packages" / ("vibelens-v" + report["version"] + ".zip")
        with zipfile.ZipFile(archive) as packed:
            packed.extractall(work / "installed")
        skill = work / "installed/vibelens"
        assets = skill / "assets/stategraph-viewer"
        assert all(not (assets / entry["name"]).exists() for entry in locked_assets(assets))
        environment = {
            **os.environ,
            "VIBELENS_TEST_SKILL": str(skill),
            "VIBELENS_DEPENDENCY_CACHE": str(work / "empty-cache"),
            "BO_MODEL_NETWORK_EVIDENCE": str(evidence),
        }
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(ROOT / "tools/test_model_networks_browser.py")],
            cwd=ROOT, env=environment, capture_output=True, text=True, encoding="utf-8",
        )
        ready = check_assets(assets)
        record = {
            "version": report["version"], "initial_dependencies": 0,
            "initial_cache": "empty", "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
            "final_dependency_check": ready,
        }
        (evidence / "installation.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
        result.check_returncode()
        assert ready["valid"], ready
    print("Cold release installation, downloads, 2D/3D, recording and iteration passed.")


if __name__ == "__main__":
    main()
