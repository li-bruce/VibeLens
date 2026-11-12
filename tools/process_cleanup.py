"""Close subprocesses owned by local test runners before removing their fixtures."""

import os
import subprocess


def stop_process_tree(process, *, timeout=5):
    """Stop a test's process and Windows venv worker, then wait for handle release.

    On Windows, terminating only the venv launcher can leave its Python worker
    writing to the fixture's log. The PID always comes from this runner's Popen
    object; no process-name or workspace-wide termination is used.
    """
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=True,
            )
        else:
            process.terminate()
    process.wait(timeout=timeout)
