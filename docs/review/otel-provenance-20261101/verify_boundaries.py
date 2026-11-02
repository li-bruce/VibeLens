"""Read-only checks for the protected core and the fresh trial's installed SDK.

This does not accept an application or advance any source baseline. It records
the exact code used by this round so runtime results can be assessed separately.
"""

from hashlib import sha256
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TRIAL = ROOT.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-03"


def digest(path):
    return sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", type=Path, default=TRIAL)
    parser.add_argument("--out", type=Path, default=OUT / "boundary-and-installed-runtime-04.json")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Review evidence cannot be overwritten")
    baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
    cores = [
        {
            "path": item["path"],
            "sha256": digest(ROOT / item["path"]),
            "unchanged": digest(ROOT / item["path"]) == item["sha256"],
        }
        for item in baseline["protected_sources"]
    ]
    native_path = "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"
    old = (
        subprocess.check_output(["git", "show", baseline["head"] + ":" + native_path], cwd=ROOT)
        .decode("utf-8")
        .replace("\r\n", "\n")
    )
    current = (ROOT / native_path).read_text(encoding="utf-8")
    # Capture selection and task-context helpers follow the native executor.
    # They are deliberately replaceable and are not part of this core boundary.
    marker = "export function bo_selected"
    if marker not in old or marker not in current:
        raise ValueError("native/capture source boundary is missing")
    native_before = old.split(marker, 1)[0]
    native_after = current.split(marker, 1)[0]
    sdk_files = [
        "bo_observer/adapters/python/bo_probe.py",
        "bo_observer/adapters/python/bo_otel.py",
        "bo_observer/adapters/javascript/bo_runtime.mjs",
        "bo_observer/adapters/javascript/bo_otel.mjs",
        "bo_observer/observation/provenance.py",
        "bo_observer/observation/telemetry.py",
        "bo_observer/workflow/mapping_contract.py",
        "bo_observer/schemas/event.schema.json",
        "bo_observer/observation/session.py",
        "bo_observer/workflow/observation_requirements.py",
    ]
    copies = [
        {
            "path": path,
            "canonical": digest(ROOT / "skills/vibelens/scripts" / path),
            "installed": digest(args.trial / "observer_runtime" / path),
        }
        for path in sdk_files
    ]
    for item in copies:
        item["matches"] = item["canonical"] is not None and item["canonical"] == item["installed"]
    viewer = []
    for name in ("runtime-frames.js", "replay-steps.js", "graph-layers.js"):
        canonical = digest(ROOT / "skills/vibelens/assets/stategraph-viewer" / name)
        installed = digest(args.trial / "static/graph" / name)
        viewer.append(
            {
                "path": name,
                "canonical": canonical,
                "installed": installed,
                "matches": canonical is not None and canonical == installed,
            }
        )
    value = {
        "valid": all(item["unchanged"] for item in cores)
        and native_before == native_after
        and all(item["matches"] for item in copies + viewer),
        "protected_cores": cores,
        "javascript_native_engine": {
            "unchanged": native_before == native_after,
            "sha256": sha256(native_after.encode()).hexdigest(),
        },
        "trial_runtime": copies,
        "trial_viewer": viewer,
        "meaning": "Core preservation and installed bytes only; application, mapping and UI acceptance are separate.",
    }
    args.out.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": value["valid"], "cores": len(cores), "runtime_files": len(copies)}))
    raise SystemExit(not value["valid"])


if __name__ == "__main__":
    main()
