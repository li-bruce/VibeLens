"""Apply only conflict-free managed observer updates to already-open changes."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
UPGRADE = ROOT / "skills/vibelens/scripts/bo_upgrade.py"
os.environ["BO_ADAPTER_HOME"] = str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript")


def run(root, name, *args):
    name += "-" + os.environ.get("BO_UPGRADE_ROUND", "01")
    result = subprocess.run([str(PYTHON), "-B", "-X", "utf8", *map(str, args)], cwd=root,
                            capture_output=True, text=True, encoding="utf-8")
    (OUT / (name + ".stdout.log")).write_text(result.stdout, encoding="utf-8")
    (OUT / (name + ".stderr.log")).write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(name + " failed; inspect its preserved logs")
    return json.loads(result.stdout) if result.stdout.strip().startswith("{") else result.stdout


def main():
    targets = [("delivery", ROOT / "examples/delivery", "observer_generated/runtime",
                ["observer_generated/static", "integrations/bo_view"]),
               ("archive", ROOT / "examples/team-archive", "observer_runtime", ["static/graph"])]
    if sys.argv[1:] == ["trial"]:
        targets = [("trial", ROOT.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04",
                    "observer_runtime", ["static/graph"])]
    for name, root, runtime, viewers in targets:
        active = json.loads((root / ".stategraph/active.json").read_text(encoding="utf-8"))
        if Path(active["change"]).name != os.environ.get("BO_CHANGE_NAME", "graph-usability-20261102"):
            raise ValueError("Open the matching managed change before upgrading " + name)
        args = [UPGRADE, "plan", "--root", root, "--runtime", runtime]
        for viewer in viewers:
            args.extend(["--viewer", viewer])
        planned = run(ROOT, f"{name}-upgrade-all-plan", *args)
        if not planned.get("valid") or planned.get("conflicts"):
            raise ValueError("Upgrade conflicts for " + name)
        args[1] = "apply"
        run(ROOT, f"{name}-upgrade-all-apply", *args)
        print(name + " managed copies updated", flush=True)


if __name__ == "__main__":
    main()
