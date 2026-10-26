"""Format maintained source; leave vendored bundles and frozen evidence untouched.

Install tools/formatting/requirements.txt and run npm ci in tools/formatting
before using this command. Pass --check in a development check or CI job.
"""

import argparse
from pathlib import Path
import subprocess
import sys
from source_scope import source_files

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Run both pinned formatters and propagate a failed check to the caller."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    python, web = source_files()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "black",
            "--line-length",
            "100",
            "--target-version",
            "py311",
            *(["--check"] if args.check else []),
            *map(str, python),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            "node",
            str(ROOT / "tools/formatting/node_modules/prettier/bin/prettier.cjs"),
            "--config",
            str(ROOT / "tools/formatting/prettier.json"),
            "--check" if args.check else "--write",
            *map(str, web),
        ],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
