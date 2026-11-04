"""Scoped capture omits unobserved snapshots without masking real capture errors."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "skills/vibelens/scripts")]
from test_multilanguage import project_fixture  # noqa: E402
from bo_observer.adapters.python.bo_probe import BOProbe  # noqa: E402
from bo_observer.service import GraphSession  # noqa: E402

JS = ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"


class SnapshotScopeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)

    def tearDown(self):
        self.folder.cleanup()

    def test_python_filtered_witness_does_not_submit_an_invalid_snapshot(self):
        """The same native instrumentation works before, during and after focus."""
        session = GraphSession(self.root)
        probe = BOProbe(self.project, session.manifest["build_id"], sink=session.bo_sink)
        try:
            probe.bo_set_scope([])
            evidence = probe.record("advance", "read", lambda: {}, revision=1)
            self.assertIsNone(evidence)
            self.assertFalse(probe.snapshot("job", "waiting", {"slots": 0}, 1, evidence))
            self.assertTrue(probe.flush(10))
            self.assertEqual(probe.bo_health()["errors"], 0)
            self.assertEqual(session.history.snapshot(), [])

            probe.bo_set_scope(None)
            evidence = probe.record("advance", "read", lambda: {}, revision=1)
            self.assertTrue(probe.snapshot("job", "waiting", {"slots": 0}, 1, evidence))
            self.assertTrue(probe.flush(10))
            self.assertEqual(session.graph.bo_instances()[0]["observed"]["state"], "waiting")

            # An explicit but fabricated identity still reaches strict admission.
            probe.snapshot("job", "running", {"slots": 1}, 2, "not-recorded")
            probe.flush(10)
            self.assertEqual(probe.bo_health()["errors"], 1)
            self.assertEqual(session.graph.bo_instances()[0]["observed"]["state"], "waiting")
        finally:
            probe.close()
            session.close()

    def test_python_failed_capture_remains_unhealthy_when_snapshot_is_omitted(self):
        probe = BOProbe(self.project, "build", sink=lambda *_: None)
        try:

            def fail():
                raise ValueError("A real capture adapter failure")

            evidence = probe.record("advance", "read", fail)
            before = probe.bo_health()
            self.assertIsNone(evidence)
            self.assertFalse(probe.snapshot("job", "waiting", {"slots": 0}, 1, evidence))
            after = probe.bo_health()
            self.assertEqual(after["errors"], 1)
            self.assertEqual(after["last_error"], before["last_error"])
        finally:
            probe.close()

    def test_javascript_filtered_failed_and_selected_witnesses_remain_distinct(self):
        code = f"""
import {{BOProbe}} from {json.dumps(JS.as_uri())};
import fs from 'node:fs';
const project = JSON.parse(fs.readFileSync(0, 'utf8'));
const sent = [];
const probe = new BOProbe({{project, buildId:'build', sink:(value, kind)=>sent.push({{value, kind}})}});
probe.bo_set_scope([]);
const omitted = probe.record('advance', 'read', ()=>({{}}), {{revision:1}});
const skipped = probe.snapshot('job', 'waiting', {{slots:0}}, 1, omitted);
await probe.flush();
const scoped = {{health:probe.bo_health(), sent:sent.length, skipped}};
probe.bo_set_scope(null);
const evidence = probe.record('advance', 'read', ()=>({{}}), {{revision:1}});
const selected = probe.snapshot('job', 'waiting', {{slots:0}}, 1, evidence);
probe.snapshot('job', 'running', {{slots:1}}, 2, 'not-recorded');
await probe.flush();
const failed = probe.record('advance', 'read', ()=>{{throw Error('capture failed')}});
probe.snapshot('job', 'waiting', {{slots:0}}, 1, failed);
await probe.flush();
console.log(JSON.stringify({{scoped, selected, sent, health:probe.bo_health()}}));
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", code],
            input=json.dumps(self.project),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value["scoped"]["skipped"])
        self.assertEqual(value["scoped"]["sent"], 0)
        self.assertEqual(value["scoped"]["health"]["errors"], 0)
        self.assertTrue(value["selected"])
        self.assertEqual(
            [item["kind"] for item in value["sent"]],
            ["events", "snapshots", "snapshots"],
        )
        self.assertEqual(value["sent"][1]["value"]["evidence_id"], value["sent"][0]["value"]["id"])
        self.assertEqual(value["sent"][2]["value"]["evidence_id"], "not-recorded")
        self.assertEqual(value["health"]["errors"], 1)
        self.assertEqual(value["health"]["last_error"]["stage"], "capture")


if __name__ == "__main__":
    unittest.main()
