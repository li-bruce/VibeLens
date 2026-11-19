"""One bounded TLC child process; no shell, application imports or inherited secrets."""

from pathlib import Path
import subprocess
import time

from .toolchain import isolated_environment

MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_STATE_BYTES = 512 * 1024 * 1024


def command(java, jar, directory, budget):
    """Build the fixed checker invocation, also used to audit retained executions."""
    return [
        str(java),
        "-Dfile.encoding=UTF-8",
        "-Duser.language=en",
        "-Duser.country=US",
        "-XX:+UseParallelGC",
        "-Xmx" + str(budget["memory_mb"]) + "m",
        "-Djava.io.tmpdir=" + str(Path(directory) / "tmp"),
        "-cp",
        str(jar),
        "tlc2.TLC",
        "-tool",
        "-workers",
        "1",
        "-seed",
        "1",
        "-fp",
        "0",
        "-config",
        "Model.cfg",
        "-metadir",
        "states",
        "Model",
    ]


def execute(java, jar, directory, budget, *, cancel=None):
    """Preserve raw bytes even on cancellation; memory_mb bounds Java heap, not total RSS."""
    directory = Path(directory).resolve()
    temporary = directory / "tmp"
    temporary.mkdir()
    args = command(java, jar, directory, budget)
    start = time.monotonic()
    stop = None
    with (directory / "stdout.log").open("wb") as out, (directory / "stderr.log").open("wb") as err:
        child = subprocess.Popen(
            args,
            cwd=directory,
            stdout=out,
            stderr=err,
            env=isolated_environment(temporary),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            while child.poll() is None:
                if cancel and cancel.is_set():
                    stop = "cancelled"
                elif time.monotonic() - start >= budget["wall_seconds"]:
                    stop = "timeout"
                elif (
                    sum((directory / name).stat().st_size for name in ("stdout.log", "stderr.log"))
                    > MAX_OUTPUT_BYTES
                ):
                    stop = "output_budget"
                elif (
                    sum(p.stat().st_size for p in (directory / "states").rglob("*") if p.is_file())
                    > MAX_STATE_BYTES
                ):
                    stop = "state_storage_budget"
                if stop:
                    child.terminate()
                    try:
                        child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=3)
                    break
                time.sleep(0.05)
        except KeyboardInterrupt:
            # Ctrl+C is the CLI's cancellation gesture; retain the child's output
            # and an incomplete receipt rather than losing the analysis attempt.
            stop = "cancelled"
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=3)
    return {
        "exit_code": child.returncode,
        "stop_reason": stop,
        "elapsed_seconds": time.monotonic() - start,
        "arguments": args,
        "working_directory": str(directory),
        "memory_scope": "Java heap; VM/native overhead is additional",
    }
