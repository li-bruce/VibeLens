"""Launch a fresh, repaired gallery and its observer with one local command."""

import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys

from prepare import prepare, SKILL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--port", type=int, default=8894)
    args = parser.parse_args()
    root = (
        args.root
        or Path(".validation") / ("afterlight-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    ).resolve()
    prepare(root, 2)
    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(root / "app.py"),
            "--root",
            str(root),
            "--skill",
            str(SKILL),
            "--port",
            str(args.port),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        child.wait()
    except KeyboardInterrupt:
        child.terminate()
        child.wait(timeout=10)
    return child.returncode


if __name__ == "__main__":
    raise SystemExit(main())
