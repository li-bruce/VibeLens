"""Review and verify this viewer-only upgrade without replacing prior baselines.

The already changed canonical dependency prevents starting a fresh baseline.
Continue the existing change, retain its frozen release evidence, and publish
the newly verified receipt under a separate release name.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "skills/vibelens/scripts"
os.environ["BO_ADAPTER_HOME"] = str(SCRIPTS / "bo_observer/adapters/javascript")
REASON = (
    "Update only the shared viewer presentation clock and paused replay for "
    "slow rendering. Preserve application code, business and state definitions, "
    "capture requirements and independent expectations."
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def run(project, label, *args, inspect=False):
    result = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", *map(str, args)],
        cwd=project, capture_output=True, text=True, encoding="utf-8",
    )
    (OUT / f"{project.name}-{label}.log").write_text(
        result.stdout + result.stderr, encoding="utf-8", newline="\n"
    )
    value = json.loads(result.stdout)
    if result.returncode and not (inspect and value.get("candidate_id")):
        raise RuntimeError(f"{project.name} {label}: {result.returncode}; inspect saved log")
    return value


def main():
    receipts = []
    for name, runtime, viewers in (
        ("delivery", "observer_generated/runtime", ["integrations/bo_view", "observer_generated/static"]),
        ("team-archive", "observer_runtime", ["static/graph"]),
    ):
        project = ROOT / "examples" / name
        cfg = read(project / "sync.json")
        change = project / read(project / ".stategraph/active.json")["change"]
        previous = read(change / "review.json")
        # These exact inputs were reviewed in the original accepted release.
        protected = set(cfg["code_files"]) | {
            cfg[key] for key in ("intent", "discovery", "acceptance", "whitebox", "mapping")
            if isinstance(cfg.get(key), str)
        }
        before = {p: (project / p).read_bytes() for p in protected}
        model = read(project / cfg["model"])
        write(OUT / "before-upgrade" / name / "review.json", previous)
        write(OUT / "before-upgrade" / name / "accepted.json", read(change / "accepted.json"))
        args = ["--root", project, "--runtime", runtime]
        for viewer in viewers:
            args.extend(["--viewer", viewer])
        run(project, "managed-plan", SCRIPTS / "bo_upgrade.py", "plan", *args)
        run(project, "managed-apply", SCRIPTS / "bo_upgrade.py", "apply", *args)
        if name == "delivery":
            run(project, "graph", "tooling/dev.py", "graph", "--reason", REASON)
        else:
            run(project, "graph", "tooling/build_model.py")
            run(project, "seal", runtime + "/architecture_guard.py", "seal", "--root", ".", "--reason", REASON)
        assert all((project / p).read_bytes() == data for p, data in before.items())
        assert read(project / cfg["model"]) == model, "Viewer update changed the graph definition"
        cli = project / runtime / "change_sync.py"
        impact = run(project, "inspect", cli, "inspect", "--root", ".", inspect=True)
        review = {
            **previous,
            "candidate_id": impact["candidate_id"],
            "decisions": {
                key: {"action": "updated" if key == "abstraction" else "unchanged", "reason": REASON}
                for key in ("business", "state_machine", "probes", "abstraction")
            },
        }
        write(change / "review.json", review)
        verification = run(project, "verify", cli, "verify", "--root", ".")
        accepted = run(project, "accept", cli, "accept", "--root", ".")
        checked = run(project, "check", cli, "check", "--root", ".")
        assert verification["valid"] and accepted["valid"] and checked["valid"]
        target = project / ".release/stategraph/release-v0.14.0-animation"
        shutil.copytree(change, target)
        write(project / ".release/stategraph/active.json", {"change": ".stategraph/" + target.name})
        for name_part in ("source-baseline.json", "maintenance.json"):
            shutil.copyfile(project / ".stategraph" / name_part, project / ".release/stategraph" / name_part)
        shutil.copyfile(project / cfg["manifest"], project / ".release/manifest.json")
        receipts.append({
            "project": name, "candidate_id": impact["candidate_id"],
            "check": checked, "graph_definition_unchanged": True,
            "protected_files": {p: hashlib.sha256(data).hexdigest() for p, data in before.items()},
        })
        print(name, "verified and frozen; original release retained", flush=True)
    write(OUT / "example-upgrades.json", receipts)


if __name__ == "__main__":
    main()
