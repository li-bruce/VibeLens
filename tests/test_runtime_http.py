"""Verify the shipped HTTP example against live states and committed SQLite rows."""

import json
from contextlib import closing
from pathlib import Path
import queue
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


# A source-binding response can outlast the demo's visual pacing interval.
# Hold real checks at their task hook until HTTP has observed resource waiting.
# The native scheduler, functions, probes and SQLite commit all execute unchanged.
CHECKER_BARRIER = """
from pathlib import Path
import time
from integrations.bo_server import Session, serve
from app.checks import run_checks

def synchronized_check(self, content, **kwargs):
    def wait_for_observation(activity):
        deadline = time.monotonic() + 20
        while not Path('scratch/check-release').exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('HTTP never observed the real waiting activities')
            time.sleep(0.01)
    return run_checks(content, task_hook=wait_for_observation, **kwargs)

Session.demo_check = synchronized_check
serve(0)
"""


class RuntimeTests(unittest.TestCase):
    def test_live_wait_completion_and_authoritative_effect(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            example = Path(folder) / "delivery"
            shutil.copytree(
                ROOT / "examples/delivery",
                example,
                ignore=shutil.ignore_patterns(
                    "scratch", "history", "dist", ".stategraph", "__pycache__"
                ),
            )
            with (Path(folder) / "server.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [sys.executable, "-B", "-X", "utf8", "-c", CHECKER_BARRIER],
                    cwd=example,
                    stdout=subprocess.PIPE,
                    stderr=log,
                    text=True,
                    encoding="utf-8",
                )
                startup = queue.Queue()
                threading.Thread(
                    target=lambda: startup.put(process.stdout.readline()), daemon=True
                ).start()
                try:
                    info = json.loads(startup.get(timeout=20))
                    base = info["url"]

                    def view():
                        with urlopen(base + "/api/view", timeout=5) as response:
                            return json.load(response)

                    def command(action, **values):
                        request = Request(
                            base + "/api/command",
                            data=json.dumps({"action": action, **values}).encode(),
                            headers={"Content-Type": "application/json"},
                        )
                        with urlopen(request, timeout=5) as response:
                            self.assertTrue(json.load(response)["ok"])

                    def finish():
                        frames = []
                        deadline = time.monotonic() + 12
                        while time.monotonic() < deadline:
                            frame = view()
                            frames.append(frame)
                            if any(
                                set(run["activities"].values())
                                == {"running", "waiting"}
                                for run in frame["machine"]["configurations"]
                            ):
                                (example / "scratch/check-release").touch()
                            if not frame["busy"]:
                                return frame, frames
                            time.sleep(0.08)
                        self.fail("The real operation did not finish.")

                    with urlopen(base, timeout=5) as page:
                        self.assertIn("canvas-host", page.read().decode())
                    # Every shipped module must be reachable from this older HTTP adapter.
                    for name, mime in (
                        ("conversation-controls.js", "javascript"),
                        ("detail-panel.js", "javascript"),
                        ("change-panel.js", "javascript"),
                        ("edge-panel.js", "javascript"),
                        ("spatial-renderer.js", "javascript"),
                        ("libavoid.wasm", "application/wasm"),
                    ):
                        with urlopen(base + "/" + name, timeout=5) as asset:
                            self.assertIn(mime, asset.headers["Content-Type"])
                            self.assertEqual(
                                asset.read(),
                                (
                                    example / "observer_generated/static" / name
                                ).read_bytes(),
                            )
                    # Use the shipped integration's actual view and scoped preference routes.
                    # These requests must not create a business event.
                    observed_before = view()["events"]

                    def control_cli(action, message):
                        completed = subprocess.run(
                            [
                                sys.executable,
                                "-B",
                                "-X",
                                "utf8",
                                str(ROOT / "skills/vibelens/scripts/bo_control.py"),
                                action,
                                "--root",
                                str(example),
                                "--url",
                                base,
                                "--message",
                                message,
                            ],
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            check=True,
                        )
                        return json.loads(completed.stdout)["result"]

                    activation = control_cli("activate", "$vibelens for this project")
                    token = activation["session"]
                    with urlopen(
                        base + "/api/vibelens/control?vl_session=" + token, timeout=5
                    ) as response:
                        self.assertTrue(json.load(response)["active"])
                    with urlopen(
                        base + "/api/preferences?vl_session=" + token, timeout=5
                    ) as response:
                        private = json.load(response)
                    request = Request(
                        base + "/api/preferences?vl_session=" + token,
                        data=json.dumps(private).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    with urlopen(request, timeout=5) as response:
                        self.assertGreater(
                            json.load(response)["revision"], private["revision"]
                        )
                    self.assertTrue(
                        (
                            example
                            / "bo_stategraph/config/views/conversations"
                            / (token + ".json")
                        ).exists()
                    )
                    self.assertEqual(view()["events"], observed_before)
                    control_cli("end", "/vibelens stop")
                    command("execute")
                    result, _ = finish()
                    self.assertEqual(result["authority"]["state"], "waiting")
                    self.assertEqual(result["authority"]["effects"], [])
                    command("edit", content="public release sample", capacity=1)
                    command("grant", id="G1", expires=200)
                    command("grant", id="G2", expires=220)
                    command("revoke", id="G1")
                    command("execute")
                    result, frames = finish()
                    self.assertEqual(result["authority"]["state"], "completed")
                    self.assertEqual(result["binding_status"]["status"], "current")
                    self.assertEqual(result["manifest"]["build_id"], info["build_id"])
                    self.assertTrue(
                        any(
                            set(r["activities"].values()) == {"running", "waiting"}
                            for frame in frames
                            for r in frame["machine"]["configurations"]
                        )
                    )
                    self.assertTrue(
                        any(
                            event["node"] == "commit" and event["phase"] == "commit"
                            for event in result["events"]
                        )
                    )
                    command("commit")
                    with closing(
                        sqlite3.connect(example / "scratch/live.sqlite")
                    ) as db:
                        rows = db.execute(
                            "SELECT version, checksum FROM artifact"
                        ).fetchall()
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(
                        rows[0][0], result["authority"]["basis"]["param_version"]
                    )
                    self.assertEqual(
                        rows[0][1], result["authority"]["effects"][0]["checksum"]
                    )
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
