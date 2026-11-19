"""Read-only definition validation and finite-adapter admission.

Normal iteration remains change_sync. Admission neither runs a checker nor
writes a receipt claiming native or formal acceptance.
"""

import argparse
import json
from pathlib import Path

from ..behavior import assess
from ..graph.behavior_model import contained


def _unique_object(pairs):
    """Reject duplicate JSON keys instead of accepting the last definition."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def main(argv=None):
    """Load project-contained inputs and print scoped definition diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["validate", "admit", "capabilities", "bindings", "runtime"]
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contract", default="bo_stategraph/behavior.json")
    parser.add_argument("--discovery", default="discovery.json")
    parser.add_argument("--profile", help="Project-relative optional analysis profile")
    parser.add_argument(
        "--sync-config", default="sync.json", help="Existing iteration configuration"
    )
    parser.add_argument("--observations", help="Project-relative saved native observation payload")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == "capabilities":
            from ..analysis.capabilities import CAPABILITIES

            print(json.dumps(CAPABILITIES, ensure_ascii=False, indent=2))
            return 0
        if args.command in {"bindings", "runtime"}:
            report = native_report(root, args)
            print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
            return int(not report["valid"])
        contract = json.loads(
            contained(root, args.contract).read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_object,
        )
        discovery = json.loads(
            contained(root, args.discovery).read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_object,
        )
        if args.command == "admit":
            from ..analysis.capabilities import admit

            if not args.profile:
                raise ValueError("admit requires --profile")
            profile = json.loads(
                contained(root, args.profile).read_text(encoding="utf-8-sig"),
                object_pairs_hook=_unique_object,
            )
            report = admit(contract, discovery, profile)
            report["valid"] = report["status"] != "invalid"
        else:
            report = assess(contract, discovery)
    except (OSError, ValueError) as error:
        report = {
            "valid": False,
            "status": "input_error",
            "errors": [{"code": "behavior_input", "path": "/", "message": str(error)}],
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return int(not report["valid"] or (args.command == "admit" and not report.get("eligible")))


def native_report(root, args):
    """Use the normal independent inventory and pinned artifacts for preflight.

    This read-only command does not accept an iteration or replace its protected
    semantic, business, probe-health and observation-mode checks.
    """
    from .sync_config import config, snapshot
    from .implementation_coverage import inventory_errors
    from ..project_artifacts import parse
    from ..behavior.bindings import assess_bindings
    from ..behavior.native_runtime import assess_runtime

    cfg = config(root, args.sync_config)
    snap = snapshot(root, cfg)
    if snap.get("behavior") is None:
        raise ValueError("Configure a pinned behavior artifact in bo-project/v2")
    kwargs = {
        "index": snap["structure"],
        "case_ids": {c["case"] for c in snap["acceptance"].get("checks", [])},
    }
    inputs = (snap["behavior"], snap["behavior_discovery"], snap["model"])
    if args.command == "runtime":
        if not args.observations:
            raise ValueError("runtime requires --observations")
        report = assess_runtime(
            *inputs, parse(contained(root, args.observations).read_bytes()), **kwargs
        )
    else:
        report = assess_bindings(*inputs, **kwargs)
    report["errors"].extend(inventory_errors(cfg, snap["source_inventory"]))
    report["valid"] = not report["errors"]
    report["iteration_acceptance"] = "use_existing_verify_accept_check"
    return report
