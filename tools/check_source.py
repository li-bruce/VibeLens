"""Check every maintained Python/JavaScript source without executing the viewer.

Use one owned-source inventory for syntax, lint and optional formatting. Runtime,
business and mapping checks remain separate and are never replaced by this gate.
"""

import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys
from source_scope import ROOT, owned_sources


def check_source(*, formatting=False, out=None):
    """Run pinned lint tools and return nonzero if any source or dependency fails."""
    groups = owned_sources()
    for name in groups["python"]:
        ast.parse((ROOT / name).read_text(encoding="utf-8-sig"), filename=name)
    commands = [
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            "tools/formatting/ruff.toml",
            *groups["python"],
        ],
        [
            "node",
            "tools/formatting/node_modules/eslint/bin/eslint.js",
            "--config",
            "tools/formatting/eslint.config.mjs",
            *groups["javascript"],
        ],
    ]
    if formatting:
        commands.append([sys.executable, "-B", "-X", "utf8", "tools/format_source.py", "--check"])
    results = []
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        results.append(
            {
                "command": command[:6],
                "exit_code": result.returncode,
                "output": result.stdout + result.stderr,
            }
        )
        print(result.stdout + result.stderr, end="")
    report = {
        "valid": all(r["exit_code"] == 0 for r in results),
        "python_modules": len(groups["python"]),
        "javascript_modules": len(groups["javascript"]),
        "scope": groups,
        "checks": results,
        "boundary": "Syntax/lint/formatting only; execution, business and mapping require their own tests.",
    }
    if out:
        Path(out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format", action="store_true", help="Also run both pinned formatters in check mode"
    )
    parser.add_argument("--out")
    options = parser.parse_args()
    raise SystemExit(not check_source(formatting=options.format, out=options.out)["valid"])
