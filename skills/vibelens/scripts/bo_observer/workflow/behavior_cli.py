"""Read-only behavior-definition command; normal iteration remains change_sync.

This P1 entrypoint is intentionally limited to validation. It neither migrates
canonical definitions nor writes a receipt claiming native or formal acceptance.
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
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contract", default="bo_stategraph/behavior.json")
    parser.add_argument("--discovery", default="discovery.json")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        contract = json.loads(
            contained(root, args.contract).read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_object,
        )
        discovery = json.loads(
            contained(root, args.discovery).read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_object,
        )
        report = assess(contract, discovery)
    except (OSError, ValueError) as error:
        report = {
            "valid": False,
            "status": "input_error",
            "errors": [{"code": "behavior_input", "path": "/", "message": str(error)}],
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return int(not report["valid"])
