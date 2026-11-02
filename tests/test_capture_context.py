"""Focused native observations preserve callers without executing omitted builders."""

from copy import deepcopy
from contextlib import closing, redirect_stdout
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.session import GraphSession
from bo_observer.observation.ownership import observation_ownership, parent_references
from bo_observer.workflow.observation_requirements import invocation_closure
from bo_observer.protocol import schema_check
from bo_observer.data.runtime import BODataRuntime
from bo_observer.service import make_server
from bo_observer.control.cli import main as control_main


class CaptureContextTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.directory.name)
        self.project = project_fixture(self.root)
        for identity in ("permission", "secondary", "unrelated"):
            self.project["model"]["nodes"].append(
                {
                    "id": identity,
                    "kind": "decision" if identity == "permission" else "function",
                    "label": identity,
                    "summary": "Native selected value",
                    "source": {"path": "worker.py", "symbol": "advance"},
                    "capture": {"in": {}, "out": {"value": "boolean"}},
                    "requirements": ["R1"],
                }
            )
        self.project["model"]["nodes"][-3]["parent"] = "advance"
        (self.root / "bo_stategraph/project.json").write_text(
            json.dumps(self.project), encoding="utf-8"
        )
        self.session = GraphSession(self.root)
        self.received = []

        def receive(body, kind):
            self.received.append(deepcopy(body))
            return self.session.bo_sink(body, kind)

        self.probe = BOProbe(self.project, self.session.manifest["build_id"], sink=receive)
        self.session.bo_bind_capture(
            scope_setter=self.probe.bo_set_scope,
            flush_capture=lambda: self.probe.flush(3),
            health=self.probe.bo_health,
        )

    def tearDown(self):
        self.probe.flush(3)
        self.probe.close()
        self.session.close()
        self.directory.cleanup()

    def omitted(self):
        self.fail("An unselected value builder was evaluated")

    def test_control_context_does_not_assemble_runtime_history(self):
        """The standard session exposes exactly the model used by its full view."""
        full = self.session.view()
        self.session.web.control_view = self.session.view
        with (
            patch.object(
                self.session, "current_events", side_effect=AssertionError("history read")
            ),
            patch.object(
                self.session.graph, "bo_instances", side_effect=AssertionError("instances read")
            ),
            patch.object(self.session.history, "health", side_effect=AssertionError("health read")),
        ):
            context = self.session.web.get("/api/vibelens/control/context")
        self.assertEqual(context["model"], full["model"])
        self.assertEqual(context["manifest"], full["manifest"])
        self.assertEqual(context["layout_id"], full["layout_id"])
        self.assertEqual(set(context), {"schema", "stage", "model", "manifest", "layout_id"})
        self.assertTrue(self.session.web.is_observer_request("/api/vibelens/control/context"))
        context["model"]["nodes"][0]["label"] = "Local display copy"
        self.assertNotEqual(self.session.model["nodes"][0]["label"], "Local display copy")

    def test_standard_http_server_exposes_scoped_model_controls(self):
        """Exercise the shipped server dispatcher rather than a controller-only fixture."""
        server = make_server(self.session, 0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = "http://127.0.0.1:" + str(server.server_port)
        try:
            with patch.object(
                self.session, "current_events", side_effect=AssertionError("history read")
            ):
                with urlopen(base + "/api/vibelens/control/context", timeout=5) as response:
                    context = json.load(response)
            self.assertEqual(context["manifest"], self.session.manifest)
            before = self.session.current_events()
            spec = self.root / "control-request.json"
            spec.write_text(
                json.dumps(
                    {
                        "action": "view",
                        "label": "Task",
                        "anchors": ["advance"],
                        "depth": 0,
                        "nodes": ["business"],
                        "edges": ["flow"],
                        "layout": "layered",
                    }
                ),
                encoding="utf-8",
            )
            results = {}
            with patch.dict(os.environ, {"CODEX_THREAD_ID": "standard-control-http"}):
                for command in ("activate", "inspect", "plan", "apply"):
                    with self.subTest(command=command), redirect_stdout(io.StringIO()) as output:
                        code = control_main(
                            [
                                command,
                                "--root",
                                str(self.root),
                                "--url",
                                base,
                                "--message",
                                "$vibelens" if command == "activate" else "/vibelens show task",
                                "--spec",
                                str(spec),
                            ]
                        )
                        self.assertEqual(code, 0, output.getvalue())
                        results[command] = json.loads(output.getvalue())["result"]
            token = results["activate"]["session"]
            with urlopen(base + "/api/vibelens/control?vl_session=" + token, timeout=5) as response:
                queued = json.load(response)
            self.assertEqual(queued["plan"]["id"], results["apply"]["plan"]["id"])
            self.assertEqual(queued["plan"]["base"]["build_id"], self.session.manifest["build_id"])
            with self.assertRaises(HTTPError) as denied:
                urlopen(
                    Request(
                        base + "/api/vibelens/control/context",
                        headers={"Origin": "http://foreign.test"},
                    ),
                    timeout=5,
                )
            self.assertEqual(denied.exception.code, 403)
            self.session.web.set_mode("disabled")
            with self.assertRaises(HTTPError) as disabled:
                urlopen(base + "/api/vibelens/control/context", timeout=5)
            self.assertEqual(disabled.exception.code, 404)
            with urlopen(base + "/api/bo/health", timeout=5) as response:
                self.assertEqual(json.load(response)["build_id"], self.session.manifest["build_id"])
            self.assertEqual(self.session.current_events(), before)
        finally:
            self.session.web.set_mode("visible")
            server.shutdown()
            server.server_close()
            worker.join(3)

    def point(self):
        with closing(sqlite3.connect(":memory:")) as connection:
            allowed = connection.execute("select 1").fetchone()[0] == 1
        return self.probe.record(
            "permission",
            "decision",
            lambda: {"outputs": {"value": allowed}},
            entity="file-a",
            attempt="check-a",
            scope="entity",
        )

    def test_single_rule_keeps_real_ancestors_and_drops_unrelated_headers(self):
        identifier = self.session.recordings.start(
            scope={"mode": "focused", "roots": ["permission"]}
        )["id"]
        with self.probe.span("unrelated", self.omitted):
            pass
        with self.probe.span("advance", self.omitted, entity="actor", attempt="request") as outer:
            with self.probe.span("secondary", self.omitted) as inner:
                identity = self.point()
                inner.result(self.omitted)
            outer.result(self.omitted)
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(saved["capture"]["value_nodes"], ["permission"])
        self.assertEqual(saved["capture"]["nodes"], ["advance", "permission"])
        self.assertEqual(saved["capture"]["runtime_boundary_nodes"], ["advance", "secondary"])
        self.assertEqual(len(saved["events"]), 5)
        self.assertNotIn("unrelated", {event["node"] for event in saved["events"]})
        point = next(event for event in saved["events"] if event["id"] == identity)
        self.assertEqual(point["outputs"], {"value": True})
        self.assertEqual(point["parent_event_id"], inner.entry_id)
        self.assertEqual(point["entity"], "file-a")
        for event in self.received:
            schema_check(event, "event")
            if event.get("context_only"):
                self.assertEqual(event["inputs"], {})
                self.assertEqual(event["outputs"], {})
                self.assertEqual(event["basis"], {})
        self.assertTrue(parent_references(saved["events"], complete=True)["valid"])
        self.assertTrue(observation_ownership(saved["events"], self.project["model"])["valid"])
        payload = {"runs": [{"mode": "on", "events": saved["events"]}]}
        self.assertTrue(invocation_closure(payload, model=self.project["model"])["valid"])
        report = invocation_closure(payload, required=True, model=self.project["model"])
        self.assertFalse(
            report["valid"], "Partial headers cannot substitute for a complete acceptance run"
        )
        self.assertTrue(
            any(error.get("partial_boundary_in_complete_run") for error in report["errors"])
        )
        self.assertEqual(saved["gaps"], [])
        self.assertEqual(self.session.bo_open_invocations, {})
        self.assertIsNone(self.probe.bo_capture_nodes)
        self.assertIsNotNone(self.probe.record("unrelated", "read", lambda: {}))

    def test_mid_call_focus_preserves_entry_after_real_history_expiry(self):
        self.session.history.limits["memory_events"] = 2
        with self.probe.span("advance", entity="actor", attempt="long-request") as outer:
            self.assertTrue(self.probe.flush())
            for _ in range(5):
                self.probe.record("unrelated", "read", lambda: {})
            self.assertTrue(self.probe.flush())
            self.assertNotIn(
                outer.entry_id, {event["id"] for event in self.session.history.snapshot()}
            )
            exported = self.session.export()["runtime"]["open_invocations"]
            self.assertIn(outer.entry_id, {event["id"] for event in exported})
            self.assertTrue(
                all(event["inputs"] == {} and event["outputs"] == {} for event in exported)
            )
            identifier = self.session.recordings.start(
                scope={"mode": "focused", "roots": ["permission"]}
            )["id"]
            self.point()
            outer.result(self.omitted)
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        entries = {event["id"]: event for event in saved["context"]["events"]}
        self.assertIn(outer.entry_id, entries)
        self.assertTrue(entries[outer.entry_id]["context_only"])
        self.assertEqual(entries[outer.entry_id]["outputs"], {})
        self.assertEqual(saved["events"][-1]["context_boundary"], "end")
        combined = [*saved["context"]["events"], *saved["events"]]
        self.assertTrue(parent_references(combined, complete=True)["valid"])
        self.assertTrue(observation_ownership(combined, self.project["model"])["valid"])
        self.assertEqual(saved["gaps"], [])

    def test_header_schema_rejects_values_wrong_phase_and_missing_boundary(self):
        self.probe.bo_set_scope(["permission"])
        with self.probe.span("advance", self.omitted):
            pass
        self.assertTrue(self.probe.flush())
        header = self.received[0]
        for change in (
            {"outputs": {"value": True}},
            {"inputs": {"state": "private"}},
            {"phase": "decision"},
            {"context_only": False},
            {"revision": 1},
            {"context_boundary": "maybe"},
        ):
            with self.assertRaises(ValueError):
                schema_check({**header, **change}, "event")
        broken = deepcopy(header)
        broken.pop("context_boundary")
        with self.assertRaises(ValueError):
            schema_check(broken, "event")

    def test_reused_call_ids_do_not_retain_an_unrelated_earlier_invocation(self):
        identifier = self.session.recordings.start(
            scope={"mode": "focused", "roots": ["permission"]}
        )["id"]
        with self.probe.span("advance", self.omitted, call_id="reused") as first:
            pass
        with self.probe.span("advance", self.omitted, call_id="reused") as second:
            self.point()
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(len(saved["events"]), 3)
        self.assertNotIn(first.entry_id, {event["id"] for event in saved["events"]})
        self.assertIn(second.entry_id, {event["id"] for event in saved["events"]})

    def test_native_call_entered_before_focus_keeps_exit_without_running_summary(self):
        data = BODataRuntime(self.probe, {"operations": [{"id": "secondary", "action": "read"}]})
        identifiers, result = [], object()

        def callback():
            identifiers.append(
                self.session.recordings.start(scope={"mode": "focused", "roots": ["permission"]})[
                    "id"
                ]
            )
            self.point()
            return result

        with self.probe.span("advance"):
            actual = data.execute("secondary", callback, summarize=lambda _: self.omitted())
        self.assertIs(actual, result)
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifiers[0])
        point = next(event for event in saved["events"] if event["node"] == "permission")
        entries = {event["id"]: event for event in saved["context"]["events"]}
        self.assertEqual(entries[point["parent_event_id"]]["node"], "secondary")
        exits = [event for event in saved["events"] if event["node"] == "secondary"]
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0]["context_boundary"], "end")
        self.assertEqual(exits[0]["outputs"], {})
        self.assertEqual(data.bo_errors, 0)
        self.assertEqual(saved["gaps"], [])

    def test_real_context_loss_is_disclosed_but_cache_expiry_is_not_fabricated_loss(self):
        with patch("bo_observer.observation.session.OPEN_CONTEXT_LIMIT", 1):
            for start_before_entries in (True, False):
                identifier = None
                if start_before_entries:
                    identifier = self.session.recordings.start(
                        scope={"mode": "focused", "roots": ["permission"]}
                    )["id"]
                self.session.history.limits["memory_events"] = 2
                with self.probe.span("advance") as outer:
                    with self.probe.span("secondary"):
                        for _ in range(5):
                            self.probe.record("unrelated", "read", lambda: {})
                        self.assertTrue(self.probe.flush())
                        if not start_before_entries:
                            identifier = self.session.recordings.start(
                                scope={"mode": "focused", "roots": ["permission"]}
                            )["id"]
                        self.point()
                self.session.recordings.stop()
                saved = self.session.recordings.get(identifier)
                self.assertGreater(saved["final"]["health"]["context_evictions"], 0)
                if start_before_entries:
                    self.assertEqual(saved["ownership_gaps"], [])
                    self.assertEqual(saved["gaps"], [])
                else:
                    self.assertTrue(
                        any(
                            gap["parent_event_id"] == outer.entry_id
                            for gap in saved["ownership_gaps"]
                        )
                    )
                    self.assertTrue(
                        any("parent invocation entry" in message for message in saved["gaps"])
                    )

    def test_focused_exception_keeps_exit_without_reading_error_payload(self):
        identifier = self.session.recordings.start(
            scope={"mode": "focused", "roots": ["permission"]}
        )["id"]
        original = ValueError("Unselected private message")
        with self.assertRaises(ValueError) as caught:
            with self.probe.span("advance", self.omitted):
                self.point()
                raise original
        self.assertIs(caught.exception, original)
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(saved["events"][-1]["phase"], "error")
        self.assertEqual(saved["events"][-1]["outputs"], {})
        self.assertEqual(self.session.bo_open_invocations, {})
        self.assertNotIn(str(original), json.dumps(saved))

    def test_native_node_headers_cross_the_strict_python_collector(self):
        runtime = (
            ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"
        ).as_uri()
        script = f"""import assert from 'node:assert/strict';
import {{ readFile }} from 'node:fs/promises';
import {{ AsyncLocalStorage }} from 'node:async_hooks';
import {{ BOProbe, bo_use_context_store }} from {json.dumps(runtime)};
bo_use_context_store(new AsyncLocalStorage());
const received = [];
const probe = new BOProbe({{project: {json.dumps(self.project)}, buildId: {json.dumps(self.session.manifest["build_id"])},
  sink: event => received.push(event)}});
probe.bo_set_scope(['permission']);
await probe.span('advance', async () => {{
  const text = await readFile({json.dumps(str(self.root / "worker.py"))}, 'utf8');
  probe.record('permission', 'decision', () => ({{outputs: {{value: text.length > 0}}}}),
    {{entity: 'file-a', attempt: 'native-node', scope: 'entity'}});
}}, {{inputs: () => assert.fail('Unselected input'), outputs: () => assert.fail('Unselected output')}});
assert.equal(await probe.flush(), true);
assert.equal(probe.bo_errors, 0);
console.log(JSON.stringify(received));"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        events = json.loads(result.stdout)
        self.assertEqual(len(events), 3)
        for event in events:
            self.assertTrue(self.session.event(event)["accepted"])
        self.assertEqual(events[1]["parent_event_id"], events[0]["id"])
        self.assertTrue(parent_references(events, complete=True)["valid"])
        self.assertEqual(self.session.bo_open_invocations, {})


if __name__ == "__main__":
    unittest.main()
