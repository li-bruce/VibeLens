"""Challenge an accepted real trial's evidence without editing that trial.

Each mutant removes or corrupts a retained implementation fact. Independent
business observations are preserved byte-for-byte so mapping is tested separately.
These are verifier negative controls, not newly executed application scenarios.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[1]
TRIAL = REPOSITORY.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
sys.path.insert(0, str(REPOSITORY / "skills/vibelens/scripts"))

from bo_observer.workflow.implementation_coverage import runtime_errors
from bo_observer.workflow.mapping_contract import assess
from bo_observer.workflow.sync_verify import assess_observations, assess_probe_health
from bo_stategraph import BOStateGraph


def read(name):
    return json.loads((TRIAL / name).read_text(encoding="utf-8"))


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main():
    phase = sys.argv[1]
    output = REPOSITORY / "docs/review/dialogue-acceptance-20261031/iteration" / phase
    output.mkdir(parents=True, exist_ok=True)
    receipt = output / "negative-controls.json"
    if receipt.exists():
        raise ValueError("Retain earlier evidence; use a new phase for a rerun")
    active = read(".stategraph/active.json")
    if not (TRIAL / active["change"] / "accepted.json").is_file():
        raise ValueError(
            "Original project must be accepted before testing verifier mutations"
        )
    execution = read(active["change"] + "/checks/observations.json")
    if execution["exit_code"] != 0:
        raise ValueError("The accepted observation command did not exit successfully")
    payload = json.loads(execution["stdout"])
    model = read("bo_stategraph/project.json")["model"]
    config = read("sync.json")
    plan = read(config["mapping_contract"])
    contract = read(config["acceptance"])
    business = lambda value: assess_observations(
        model, contract, value, config["probe_modes"]
    )
    mapping = lambda value: assess(
        value, required=True, plan=plan, model=model, build_id=payload["build_id"]
    )
    baseline = {
        "mapping": mapping(payload),
        "business": business(payload),
        "health": assess_probe_health(payload, required=True),
        "implementation": runtime_errors(
            model["implementation"], model, payload, root=TRIAL
        ),
    }
    result = {
        "kind": __doc__,
        "phase": phase,
        "build_id": payload["build_id"],
        "source_payload_sha256": fingerprint(payload),
        "source_execution": active["change"] + "/checks/observations.json",
        "baseline": baseline,
        "checks": [],
    }
    try:
        assert baseline["mapping"]["valid"] and not baseline["business"]
        assert baseline["health"]["valid"] and not baseline["implementation"]["errors"]
        original_observations = fingerprint(
            [run["observations"] for run in payload["runs"]]
        )

        def exercise(name, edit, checker):
            candidate = deepcopy(payload)
            edit(candidate)
            report = checker(candidate)
            errors = report.get("errors", [])
            business_errors = business(candidate)
            same_observations = (
                fingerprint([run["observations"] for run in candidate["runs"]])
                == original_observations
            )
            row = {
                "name": name,
                "mapping_errors": errors,
                "business_errors": business_errors,
                "independent_observations_unchanged": same_observations,
                "passed": bool(errors) and not business_errors and same_observations,
            }
            result["checks"].append(row)
            assert row["passed"], name

        graph = BOStateGraph(model, build_id=payload["build_id"])

        def mutate_projection(candidate, edit):
            # Rebuild through the public API so a checksum or malformed JSON is
            # not the only reason rejection occurs. Storage facts stay unchanged.
            run = next(
                run
                for run in candidate["runs"]
                if run["case"] == plan["export"]["case"]
                and run["mode"] == plan["export"]["mode"]
            )
            machine = run["projection"]["machine"]
            edit(machine)
            run["projection"]["instances"] = graph.bo_instances(machine)
            candidate["stategraph_export"] = graph.bo_export(
                runtime={"machine": machine}
            )

        def stale_revision(machine):
            configuration = machine["configurations"][0]
            configuration["revision"] -= 1
            configuration["state_revision"] -= 1

        exercise(
            "Missing actual exported instance",
            lambda value: mutate_projection(
                value, lambda machine: machine.update(configurations=[])
            ),
            mapping,
        )
        exercise(
            "Stale projected revision",
            lambda value: mutate_projection(value, stale_revision),
            mapping,
        )
        context_field = next(iter(model["machine"]["context"]))
        exercise(
            "Missing projected context field: " + context_field,
            lambda value: mutate_projection(
                value,
                lambda machine: machine["configurations"][0]["context"].pop(
                    context_field
                ),
            ),
            mapping,
        )
        exercise(
            "Missing implementation witnesses",
            lambda value: value.update(mapping_checks=[]),
            mapping,
        )
        exercise(
            "Actual producer reports capture error",
            lambda value: next(run for run in value["runs"] if run["mode"] == "on")[
                "probe_health"
            ].update(errors=1),
            lambda value: assess_probe_health(value, required=True),
        )

        def remove_return(value):
            run = next(
                run
                for run in value["runs"]
                if run["mode"] == "on" and run["case"] == "approved"
            )
            original = len(run["events"])
            run["events"] = [
                event
                for event in run["events"]
                if not (event["node"] == "download" and event["phase"] == "return")
            ]
            assert (
                len(run["events"]) < original
            ), "The real case never captured a download return"

        exercise(
            "Missing real download return boundary",
            remove_return,
            lambda value: runtime_errors(
                model["implementation"], model, value, root=TRIAL
            ),
        )
        result["passed"] = all(row["passed"] for row in result["checks"])
    except Exception as error:
        result["passed"] = False
        result["error"] = repr(error)
    receipt.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": len(result["checks"]),
                "error": result.get("error"),
            }
        )
    )
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
