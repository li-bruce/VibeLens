"""Inject one valid-typed but wrong probe value during a real isolated app run.

Native arguments, returns, SQLite effects and business assertions are unchanged.
The accepted project's independent readers must detect the false observation.
"""

import json
from pathlib import Path
import sys
import tempfile

REPOSITORY = Path(__file__).resolve().parents[1]
TRIAL = REPOSITORY.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
sys.path[:0] = [str(TRIAL), str(TRIAL / "observer_runtime")]

from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.graph.behavior_model import capture
from bo_observer.workflow.mapping_contract import assess
from tooling.observe import run_case


def main():
    phase = sys.argv[1]
    output = REPOSITORY / "docs/review/dialogue-acceptance-20261031/iteration" / phase
    output.mkdir(parents=True, exist_ok=True)
    receipt = output / "probe-value-control.json"
    if receipt.exists():
        raise ValueError("Retain the previous receipt and choose a new phase")
    project = json.loads(
        (TRIAL / "bo_stategraph/project.json").read_text(encoding="utf-8")
    )
    build = capture(TRIAL, project["model"])["build_id"]
    checks = []
    result = {
        "phase": phase,
        "build_id": build,
        "checks": checks,
        "injection": "download.return.outputs.size += 1 before actual capture",
    }
    original_record = BOProbe.record

    def wrong_size(probe, node, event_phase, builder, **options):
        if node == "download" and event_phase == "return":
            native_builder = builder

            def builder():
                fields = native_builder()
                fields["outputs"]["size"] += 1
                return fields

        return original_record(probe, node, event_phase, builder, **options)

    try:
        baseline_observations = None
        for name, injected in (
            ("baseline", False),
            ("wrong-observation", True),
            ("restored", False),
        ):
            BOProbe.record = wrong_size if injected else original_record
            with tempfile.TemporaryDirectory(
                prefix="dialogue-probe-value-", dir=REPOSITORY / ".validation"
            ) as directory:
                run = run_case("approved", "on", project, build, directory)
            report = assess({"mapping_checks": run["mapping_checks"]})
            if baseline_observations is None:
                baseline_observations = run["observations"]
            row = {
                "name": name,
                "injected": injected,
                "mapping": report,
                "probe_health": run["probe_health"],
                "independent_business_observations": run["observations"],
                "business_unchanged": run["observations"] == baseline_observations,
                "passed": report["valid"] != injected
                and run["observations"] == baseline_observations
                and run["probe_health"]["errors"] == 0
                and run["probe_health"]["data_errors"] == 0,
            }
            checks.append(row)
            assert row["passed"], name
        result["passed"] = True
    except Exception as error:
        result.update(passed=False, error=repr(error))
    finally:
        BOProbe.record = original_record
    result["source_build_unchanged"] = (
        capture(TRIAL, project["model"])["build_id"] == build
    )
    result["passed"] = result["passed"] and result["source_build_unchanged"]
    receipt.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": len(checks),
                "error": result.get("error"),
            }
        )
    )
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
