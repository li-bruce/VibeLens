"""Run a review check once and retain its output, timing, and exit status."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    """Keep failed runs as independent evidence rather than overwriting them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or Path(args.name).name != args.name:
        parser.error("A simple evidence name and command are required")
    # Windows resolves executable paths before applying a child's working
    # directory. Resolve explicit relative paths against the requested cwd.
    if "/" in command[0] or "\\" in command[0]:
        executable = (args.cwd / command[0]).resolve()
        if executable.is_file():
            command[0] = str(executable)
    output = Path(__file__).resolve().parent
    status_path = output / (args.name + ".json")
    log_path = output / (args.name + ".log")
    if status_path.exists() or log_path.exists():
        raise FileExistsError("Choose a new run name; review evidence is immutable")
    environment = os.environ.copy()
    repository = Path(__file__).resolve().parents[3]
    environment["BO_ADAPTER_HOME"] = str(
        repository / "skills/vibelens/scripts/bo_observer/adapters/javascript"
    )
    started = datetime.now(timezone.utc)
    with log_path.open("w", encoding="utf-8", newline="\n") as stream:
        try:
            result = subprocess.run(
                command,
                cwd=args.cwd,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=args.timeout,
                check=False,
            )
            code = result.returncode
        except subprocess.TimeoutExpired:
            stream.write("\nReview command exceeded its configured timeout.\n")
            code = 124
        except OSError as error:
            stream.write(f"\nReview command could not start: {error}\n")
            code = 127
    report = {
        "command": command,
        "cwd": str(args.cwd.resolve()),
        "started_at": started.isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": code,
        "valid": code == 0,
        "log": log_path.name,
    }
    status_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    if code:
        # Preserve full diagnostics in the log while keeping console output usable
        # when a guard emits a large model or ownership manifest on one line.
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        print("\n".join(line[:800] for line in lines[-30:]))
    return code


if __name__ == "__main__":
    sys.exit(main())
