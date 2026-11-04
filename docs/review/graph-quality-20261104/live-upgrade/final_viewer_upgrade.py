"""Apply managed viewer or parser-script corrections without a native restart."""

import hashlib
import json
from pathlib import Path
import re
import sys

EVIDENCE = Path(__file__).parent
REPOSITORY = EVIDENCE.parents[3]
TRIAL = REPOSITORY.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04"
sys.path.insert(0, str(REPOSITORY / "skills/vibelens/scripts"))
from bo_upgrade import plan, apply

PHASE = sys.argv[1] if len(sys.argv) > 1 else "final"
if not re.fullmatch(r"[a-z0-9-]+", PHASE):
    raise SystemExit("Use a simple evidence phase name")


def write(name, value):
    name = name.replace("-final.json", "-" + PHASE + ".json")
    (EVIDENCE / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


paths = json.loads((EVIDENCE / "protected-before.json").read_text(encoding="utf-8"))
before = {name: hashlib.sha256((TRIAL / name).read_bytes()).hexdigest() for name in paths}
launcher_before = (TRIAL / "runtime/launcher.json").read_bytes()
options = {"runtime": "observer_runtime", "viewers": ["static/graph"]}
proposed = plan(TRIAL, **options)
write("plan-final.json", {key: proposed[key] for key in ("valid", "release", "changes", "conflicts", "retired_files")})
allowed_runtime_script = "observer_runtime/bo_observer/adapters/javascript/scan.mjs"
if not proposed["valid"] or proposed["retired_files"] or any(
    not name.startswith("static/graph/")
    and not (PHASE == "adapter-compat" and name == allowed_runtime_script)
    for name in proposed["changes"]
):
    raise SystemExit("Correction must be a conflict-free viewer or explicit parser-script update")
write("protected-before-final.json", before)
result = apply(TRIAL, **options)
write("applied-final.json", result)
after = {name: hashlib.sha256((TRIAL / name).read_bytes()).hexdigest() for name in paths}
write("protected-after-final.json", after)
verification = {
    "changed_assets": result["changes"],
    "protected_files": len(before),
    "unexpected_changes": [name for name in paths if before[name] != after[name]],
    "same_process_launcher": (TRIAL / "runtime/launcher.json").read_bytes() == launcher_before,
    "restarted": False,
}
verification["valid"] = not verification["unexpected_changes"] and verification["same_process_launcher"]
write("protected-verification-final.json", verification)
print(json.dumps(verification))
raise SystemExit(int(not verification["valid"]))
