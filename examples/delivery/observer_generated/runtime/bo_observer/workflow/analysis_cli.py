"""Opt-in finite design analysis through configured profiles and a fixed toolchain."""

import argparse
import json
from pathlib import Path


def main(argv=None):
    """No arbitrary command text; the ordinary sync gate remains the acceptance owner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "check", "install-tool"])
    parser.add_argument("--root", type=Path)
    parser.add_argument("--sync-config", default="sync.json")
    parser.add_argument("--profile", help="Configured profile ID, not a filesystem path")
    args = parser.parse_args(argv)
    try:
        if args.command == "install-tool":
            from ..analysis.tla.toolchain import install

            print(install())
            return 0
        if not args.root:
            raise ValueError("A project root is required")
        from .sync_config import config, snapshot

        snap = snapshot(args.root, config(args.root, args.sync_config))
        if not snap.get("behavior"):
            raise ValueError("Configure the pinned behavior contract first")
        if args.command == "run":
            if not args.profile:
                raise ValueError("Select a configured --profile ID")
            from ..analysis.runner import run_profile

            report = run_profile(args.root, snap, args.profile)
            report.pop("receipt", None)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return int(report["status"] != "pass")
        from ..analysis.artifacts import collect

        receipts, tools, diagnostics = collect(args.root.resolve(), snap)
        print(
            json.dumps(
                {"receipts": receipts, "tools": tools, "diagnostics": diagnostics},
                ensure_ascii=False,
                indent=2,
            )
        )
        return int(bool(diagnostics))
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "reason": str(error)}))
        return 1
