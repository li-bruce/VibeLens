"""Verify the already-begun example upgrades without replacing their baselines."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
CHANGE = "dependency-downloads-20261112"
PRIOR = "model-networks-20261112-verified"
ENV = {**os.environ,
    "VIBELENS_SKILL": str(ROOT / "skills/vibelens"),
    "BO_ADAPTER_HOME": str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript"),
    "VIBELENS_DEPENDENCY_CACHE": str(ROOT / ".validation/dependency-cache-primary")}
REASON = (
    "Prepare pinned local-viewer dependencies independently of application source. "
    "Use verified CDN/GitHub downloads and cache reuse. Business source, state "
    "definitions, rule meanings, mapping requirements and scenario expectations are unchanged."
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def run(project, runtime, action):
    result = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", runtime + "/change_sync.py", action, "--root", "."],
        cwd=project, env=ENV, capture_output=True, text=True, encoding="utf-8",
    )
    target = EVIDENCE / "example-upgrade" / project.name / (action + ".json")
    if target.exists():
        attempt = 1
        while target.with_name(action + "-attempt-" + str(attempt) + ".json").exists():
            attempt += 1
        shutil.copyfile(target, target.with_name(action + "-attempt-" + str(attempt) + ".json"))
    write(target, {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    value = json.loads(result.stdout)
    # The initial inspect identifies the missing review; verify/accept must pass.
    if action != "inspect":
        result.check_returncode()
        assert value["valid"], value
    return value


def main():
    for name, runtime in (("delivery", "observer_generated/runtime"), ("team-archive", "observer_runtime")):
        project = ROOT / "examples" / name
        if (project / ".release/stategraph" / CHANGE).exists():
            run(project, runtime, "check")
            continue
        change = project / ".stategraph" / CHANGE
        baseline = read(change / "baseline.json")
        config = read(project / "sync.json")
        # Existing classifications can only be reused for the same business bytes.
        for source in config["code_files"]:
            assert hashlib.sha256((project / source).read_bytes()).hexdigest() == baseline["files"][source], source
        prior = read(project / ".stategraph" / PRIOR / "review.json")
        impact = run(project, runtime, "inspect")
        assert not impact["errors"], impact["errors"]
        write(change / "review.json", {
            "candidate_id": impact["candidate_id"], "excluded_symbols": prior["excluded_symbols"],
            "requirement_changes": {},
            "decisions": {part: {"action": "updated" if part in ("abstraction", "probes") else "unchanged",
                "reason": REASON} for part in ("business", "state_machine", "abstraction", "probes")},
        })
        run(project, runtime, "verify")
        run(project, runtime, "accept")
        run(project, runtime, "check")
        frozen = project / ".release/stategraph"
        target = frozen / CHANGE
        if target.exists():
            raise ValueError("Refusing to overwrite frozen acceptance: " + str(target))
        shutil.copytree(change, target)
        for filename in ("active.json", "source-baseline.json", "maintenance.json"):
            shutil.copyfile(project / ".stategraph" / filename, frozen / filename)
        shutil.copyfile(project / config["manifest"], project / ".release/manifest.json")
        print(name + ": verified, accepted and frozen", flush=True)


if __name__ == "__main__":
    main()
