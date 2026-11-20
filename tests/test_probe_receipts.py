"""HTTP success and accepted observation are distinct in both native adapters."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import JS, project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe


class ReceiptHandler(BaseHTTPRequestHandler):
    """Return a chosen application receipt after consuming the actual HTTP body."""

    def log_message(self, *_):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        receipt = (
            self.server.receipt if self.path.endswith(self.server.channel) else {"accepted": True}
        )
        raw = json.dumps(receipt).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class ProbeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.project = project_fixture(Path(self.folder.name))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ReceiptHandler)
        self.server.receipt = {"accepted": True}
        self.server.channel = "events"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.folder.cleanup()

    def produce(self, language, channel, *, local=False):
        """Exercise original queue delivery, not the HTTP helper in isolation."""
        if language == "python":
            probe = BOProbe(
                self.project,
                "fixture-build",
                endpoint=self.url,
                token="synthetic-receipt",
                sink=(lambda value, kind: self.server.receipt) if local else None,
            )
            try:
                if channel == "events":
                    probe.record("advance", "read", lambda: {"outputs": {"state": "pending"}})
                else:
                    probe.snapshot("task:1", "pending", {"slots": 1}, 0, "existing-evidence")
                self.assertTrue(probe.flush(3))
                return probe.bo_health()
            finally:
                probe.close()
        program = f"""
import {{ BOProbe }} from {json.dumps(JS.as_uri())};
import fs from 'node:fs';
const config = JSON.parse(fs.readFileSync(0, 'utf8'));
const probe = new BOProbe({{project:config.project, buildId:'fixture-build',
  endpoint:config.url, token:'synthetic-receipt',
  sink:config.local ? (() => config.receipt) : null}});
if (config.channel === 'events')
  probe.record('advance','read',()=>({{outputs:{{state:'pending'}}}}));
else probe.snapshot('task:1','pending',{{slots:1}},0,'existing-evidence');
if (!await probe.flush(3000)) throw Error('Queue did not settle');
console.log(JSON.stringify(probe.bo_health()));
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", program],
            input=json.dumps(
                {
                    "project": self.project,
                    "url": self.url,
                    "channel": channel,
                    "local": local,
                    "receipt": self.server.receipt,
                }
            ),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_negative_and_missing_http_receipts_are_capture_errors(self):
        for language in ("python", "node"):
            for channel in ("events", "snapshots"):
                for receipt in ({"accepted": False}, {}, None, {"accepted": 1}):
                    with self.subTest(language=language, channel=channel, receipt=receipt):
                        self.server.channel, self.server.receipt = channel, receipt
                        health = self.produce(language, channel)
                        self.assertEqual(health["errors"], 1, health)
                        self.assertEqual(health["pending"], 0)

    def test_accepted_and_duplicate_http_receipts_remain_successful(self):
        for language in ("python", "node"):
            for receipt in ({"accepted": True}, {"accepted": True, "duplicate": True}):
                with self.subTest(language=language, receipt=receipt):
                    self.server.receipt = receipt
                    self.assertEqual(self.produce(language, "events")["errors"], 0)

    def test_explicit_local_rejection_is_reported(self):
        self.server.receipt = {"accepted": False}
        for language in ("python", "node"):
            with self.subTest(language=language):
                self.assertEqual(self.produce(language, "snapshots", local=True)["errors"], 1)

    def test_legacy_local_callbacks_can_return_no_receipt(self):
        self.server.receipt = None
        for language in ("python", "node"):
            with self.subTest(language=language):
                self.assertEqual(self.produce(language, "events", local=True)["errors"], 0)


if __name__ == "__main__":
    unittest.main()
