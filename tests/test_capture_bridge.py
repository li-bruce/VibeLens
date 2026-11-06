"""Real HTTP controls drain native Python/Node queues without collecting controls."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.observation.session import GraphSession
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.adapters.python.bo_capture import BOCaptureClient
from bo_observer.service import make_server
from bo_observer.delivery.integration import install
from unittest.mock import patch
from bo_observer.adapters.python import bo_capture
from bo_observer.observation.observation_scope import bo_is_internal


class CaptureBridgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.session = GraphSession(self.root)
        self.token = "synthetic-capture-test"
        self.server = make_server(self.session, port=0, token=self.token)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.clients = []

    def tearDown(self):
        for probe, client in self.clients:
            client.close()
            probe.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.session.close()
        self.folder.cleanup()

    def client(self):
        probe = BOProbe(
            self.project, self.session.manifest["build_id"], endpoint=self.url, token=self.token
        )
        client = BOCaptureClient(probe).start()
        self.clients.append((probe, client))
        return probe, client

    def test_python_http_capture_is_scoped_and_settled(self):
        probe, _ = self.client()
        self.session.bo_capture_bridge.set_scope([])
        self.assertIsNone(
            probe.record("advance", "return", lambda: self.fail("excluded builder ran"))
        )
        self.session.bo_capture_bridge.set_scope(None)
        recording = self.session.recordings.start()["id"]
        ids = [
            probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
            for _ in range(12)
        ]
        self.session.recordings.stop()
        saved = self.session.recordings.get(recording)
        self.assertEqual([event["id"] for event in saved["events"]], ids)
        self.assertEqual(saved["status"], "stopped")
        self.assertEqual(saved["gaps"], [])
        self.assertEqual(len(self.session.history.snapshot()), 12)

    def test_missing_producer_ack_is_not_a_complete_recording(self):
        _, client = self.client()
        ident = self.session.recordings.start()["id"]
        client.close()
        self.session.bo_capture_bridge.timeout = 0.15
        self.assertFalse(self.session.bo_capture_bridge.flush())
        self.session.recordings.stop()
        saved = self.session.recordings.get(ident)
        self.assertEqual(saved["status"], "interrupted")
        self.assertTrue(any("restore failed" in gap for gap in saved["gaps"]))

    def test_controls_reject_cross_build_and_application_commands(self):
        base = {
            "protocol": "bo-capture-control/v1",
            "project_id": self.project["project_id"],
            "build_id": self.session.manifest["build_id"],
            "producer_id": "p",
        }
        for fields in (
            {"action": "execute"},
            {"action": "poll", "source": "app.py"},
            {"action": "register", "build_id": "old"},
            {"action": "register", "ack": {}},
            {"action": "ack"},
        ):
            with self.assertRaises(ValueError):
                self.session.bo_capture_bridge.exchange({**base, **fields})
        self.assertEqual(len(self.session.history.snapshot()), 0)
        with self.assertRaisesRegex(ValueError, "unsupported capture control command"):
            self.session.bo_capture_bridge.request("execute", source="app.py")

    def test_malformed_health_does_not_complete_a_request(self):
        bridge = self.session.bo_capture_bridge
        base = {
            "protocol": "bo-capture-control/v1",
            "project_id": self.project["project_id"],
            "build_id": self.session.manifest["build_id"],
            "producer_id": "strict-producer",
        }
        bridge.exchange({**base, "action": "register"})
        bridge.pending["pending-1"] = {
            "command": {"id": "pending-1", "action": "flush"},
            "waiting": {"strict-producer"},
            "ok": True,
        }
        try:
            for health in (
                {"errors": 0, "dropped": 0, "pending": 0, "queue_submitted": "12"},
                {"errors": 0, "dropped": 0, "pending": False},
            ):
                with self.assertRaises(ValueError):
                    bridge.exchange(
                        {
                            **base,
                            "action": "ack",
                            "ack": {"id": "pending-1", "ok": True, "health": health},
                        }
                    )
                self.assertEqual(bridge.pending["pending-1"]["waiting"], {"strict-producer"})
        finally:
            bridge.pending.clear()

    def test_all_producers_must_acknowledge(self):
        a, _ = self.client()
        b, _ = self.client()
        self.session.bo_capture_bridge.set_scope([])
        self.assertEqual(a.bo_capture_nodes, frozenset())
        self.assertEqual(b.bo_capture_nodes, frozenset())
        self.assertTrue(self.session.bo_capture_bridge.flush())
        self.assertEqual(self.session.bo_capture_bridge.health()["producers"], 2)

    def test_control_transport_is_suppressed_without_hiding_application_events(self):
        actual_urlopen = bo_capture.urlopen
        calls = []

        def observed(request, **kwargs):
            self.assertTrue(bo_is_internal(), "control HTTP must be excluded from automatic probes")
            calls.append(request.full_url)
            return actual_urlopen(request, **kwargs)

        with patch.object(bo_capture, "urlopen", observed):
            probe, client = self.client()
            self.session.bo_capture_bridge.set_scope(None)
            self.assertFalse(bo_is_internal())
            probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
            self.assertTrue(self.session.bo_capture_bridge.flush())
            client.close()
        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual(len(self.session.history.snapshot()), 1)

    def test_node_process_records_through_external_python_service(self):
        install(self.root, "javascript")
        adapter = (self.root / "bo_stategraph/bo_runtime.mjs").as_uri()
        control = (self.root / "bo_stategraph/bo_capture.mjs").as_uri()
        script = f"""
import {{BOProbe}} from {json.dumps(adapter)};
import {{BOCaptureClient}} from {json.dumps(control)};
const url = {json.dumps(self.url)};
const probe = new BOProbe({{project:{json.dumps(self.project)}, buildId:{json.dumps(self.session.manifest['build_id'])}, endpoint:url, token:{json.dumps(self.token)}}});
const originalFetch = globalThis.fetch;
let controlCalls = 0;
globalThis.fetch = (...args) => {{
  if (String(args[0]).endsWith('/api/bo/capture')) {{
    if (!probe.bo_internal) throw Error('Observer control was not suppressed');
    controlCalls++;
  }}
  return originalFetch(...args);
}};
const client = await new BOCaptureClient(probe).start();
const request = async (path, body) => {{const r = await fetch(url+path, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}}); if(!r.ok) throw Error(await r.text()); return r.json();}};
try {{
 const started = await request('/api/recordings/start', {{}});
 probe.record('advance','return',()=>({{outputs:{{state:'running'}}}}));
 await request('/api/recordings/stop', {{}});
 const saved = await (await fetch(url+'/api/recordings/'+started.id)).json();
 if(saved.status !== 'stopped' || saved.events.length !== 1 || saved.gaps.length || controlCalls < 3 || probe.bo_internal) throw Error(JSON.stringify(saved));
 console.log(JSON.stringify({{status:saved.status,events:saved.events.length}}));
}} finally {{await client.close(); await probe.flush();}}
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            timeout=25,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["events"], 1)
        self.assertEqual(len(self.session.history.snapshot()), 1)


if __name__ == "__main__":
    unittest.main()
