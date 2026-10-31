"""Corrupt a new observed length while keeping a real two-round business run intact."""

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
sys.path[:0] = [str(TRIAL), str(TRIAL / "observer_runtime")]
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.graph.behavior_model import capture
from bo_observer.workflow.mapping_contract import assess
from tooling.observe import run_case


def main():
    output = ROOT / "docs/review/dialogue-acceptance-20261031/iteration" / sys.argv[1]
    output.mkdir(parents=True, exist_ok=True)
    receipt = output / "supplement-probe-control.json"
    if receipt.exists():
        raise ValueError("Keep earlier evidence and choose a new phase")
    project = json.loads((TRIAL / "bo_stategraph/project.json").read_text(encoding="utf-8"))
    build = capture(TRIAL, project["model"])["build_id"]
    original = BOProbe.record
    checks = []
    result = {
        "build_id": build,
        "checks": checks,
        "injection": "return_share.return.outputs.reason_length += 1 before actual capture",
    }

    def wrong_length(probe, node, phase, builder, **options):
        if node == "return_share" and phase == "return":
            native_builder = builder

            def builder():
                fields = native_builder()
                # Copy only the observation; never mutate native application results.
                values = {**fields["outputs"]}
                values["reason_length"] += 1
                return {**fields, "outputs": values}

        return original(probe, node, phase, builder, **options)

    try:
        baseline = None
        for name, injected in (
            ("baseline", False),
            ("wrong-observation", True),
            ("restored", False),
        ):
            BOProbe.record = wrong_length if injected else original
            with tempfile.TemporaryDirectory(
                prefix="supplement-observation-", dir=ROOT / ".validation"
            ) as directory:
                run = run_case("multiple_supplement_rounds", "on", project, build, directory)
            mapping = assess({"mapping_checks": run["mapping_checks"]})
            if baseline is None:
                baseline = run["observations"]
            item = {
                "name": name,
                "injected": injected,
                "mapping": mapping,
                "probe_health": run["probe_health"],
                "native_observations": run["observations"],
                "business_unchanged": run["observations"] == baseline,
                "passed": mapping["valid"] != injected
                and run["observations"] == baseline
                and run["probe_health"]["errors"] == 0
                and run["probe_health"]["data_errors"] == 0,
            }
            checks.append(item)
            assert item["passed"], name
        result["passed"] = True
    except Exception as error:
        result.update(passed=False, error=repr(error))
    finally:
        BOProbe.record = original
    result["source_build_unchanged"] = capture(TRIAL, project["model"])["build_id"] == build
    result["passed"] = result["passed"] and result["source_build_unchanged"]
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"passed": result["passed"], "checks": len(checks), "error": result.get("error")}
        )
    )
    raise SystemExit(not result["passed"])


if __name__ == "__main__":
    main()
