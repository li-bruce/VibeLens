"""Actual Python spans, strict source equivalence and an isolated live browser service.

The application reads a real SQLite grant and writes a share after a user release.
The observer remains a separate service; its requests do not become business calls.
"""

import argparse
import asyncio
from copy import deepcopy
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from test_multilanguage import project_fixture
from bo_contracts import validate_graph
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.adapters.python.bo_executor import BOExecutor
from bo_observer.code_graph.service import CodeGraph
from bo_observer.service import GraphSession, make_server

BUSINESS = '''"""Minimal sharing operation; all SQL acts on synthetic local records."""
import sqlite3
from contextlib import closing

def read_grant(db):
    return db.execute("select allowed from grants where actor = ?", ("owner",)).fetchone()[0]

def write_share(db):
    db.execute("insert into shares(file_id, recipient) values (?, ?)", ("file-1", "reader"))
    db.commit()
    return db.execute("select count(*) from shares").fetchone()[0]

def advance(state, probe, gate, path, engine, report):
    with probe.span("advance", lambda: {"inputs": {"state": state}}, entity="job", attempt="attempt-1", scope="entity") as operation:
        state = engine.step(state, "start", {"slots": 1})["state"]
        report(state, 1, "start")
        with closing(sqlite3.connect(path)) as db:
            with probe.span("check") as check:
                with probe.span("query") as query:
                    allowed = bool(read_grant(db))
                    query.result(lambda: {"outputs": {"allowed": allowed}})
                check.result(lambda: {"outputs": {"allowed": allowed}})
            if not allowed:
                raise PermissionError("Share denied")
            waiting_event = operation.record("wait", lambda: {"outputs": {"state": state}})
            if not gate.wait(25):
                raise TimeoutError("Sharing operation was not released")
            probe.record("advance", "read", lambda: {"outputs": {"state": state}},
                         entity="job", attempt="attempt-1", scope="entity",
                         call_id=operation.call_id, lifecycle="span",
                         depends=[{"event": waiting_event, "type": "control"}] if waiting_event else [])
            with probe.span("write") as commit:
                count = write_share(db)
                commit.result(lambda: {"outputs": {"count": count}})
        state = engine.step(state, "finish", {"slots": 1})["state"]
        report(state, 2, "finish")
        operation.result(lambda: {"outputs": {"state": state}})
        return state
'''


def prepare(root, registered=False):
    root.mkdir(parents=True, exist_ok=True)
    project = project_fixture(root)
    (root / "worker.py").write_text(BUSINESS, encoding="utf-8")
    model = project["model"]
    model["nodes"] = [
        {
            "id": "advance",
            "kind": "action",
            "layer": "business",
            "label": "Share file",
            "summary": "Share the file after checking its grant",
            "source": {"path": "worker.py", "symbol": "advance"},
            "capture": {"in": {"state": "string"}, "out": {"state": "string", "error": "string"}},
            "requirements": ["R1"],
        },
        *[
            {
                "id": ident,
                "kind": kind,
                "parent": "advance",
                "label": label,
                "summary": label,
                "source": {"path": "worker.py", "symbol": symbol},
                "capture": {"in": {}, "out": fields},
                **extra,
            }
            for ident, kind, label, symbol, fields, extra in [
                (
                    "check",
                    "decision",
                    "Check sharing permission",
                    "advance",
                    {"allowed": "boolean"},
                    {},
                ),
                ("query", "function", "Read grant", "read_grant", {"allowed": "boolean"}, {}),
                ("write", "function", "Save share", "write_share", {"count": "number"}, {}),
            ]
        ],
        {
            "id": "state-parameter",
            "kind": "data",
            "label": "Sharing status",
            "summary": "The state argument of advance",
            "semantic_role": "state_parameter",
            "event_node": "advance",
            "field": "state",
            "direction": "out",
            "represents": {"path": "worker.py", "symbol": "advance", "parameter": "state"},
        },
        *[
            {
                "id": "state-" + value,
                "kind": "state",
                "layer": "state",
                "value": value,
                "label": value,
                "summary": "Actual " + value + " state",
            }
            for value in model["machine"]["values"]
        ],
    ]
    if registered:
        model["nodes"][0]["lifecycle"] = {
            "states": [
                {"id": "checking", "label": "Checking access", "kind": "active"},
                {"id": "awaiting_release", "label": "Waiting for confirmation", "kind": "waiting"},
                {"id": "shared", "label": "File shared", "kind": "ended"},
            ],
            "bindings": [
                {"phase": "enter", "state": "checking", "boundary": "start"},
                {"phase": "wait", "state": "awaiting_release", "boundary": "update"},
                {"phase": "read", "state": "checking", "boundary": "update"},
                {
                    "phase": "return",
                    "state": "shared",
                    "boundary": "end",
                    "when": {"direction": "out", "field": "state", "equals": "done"},
                },
            ],
        }
    model["edges"] = [
        {
            "id": ident,
            "from": source,
            "to": target,
            "type": kind,
            "label": ident,
            "evidence": "worker.py explicit nested spans",
        }
        for ident, source, target, kind in [
            ("check-sharing", "advance", "check", "flow"),
            ("query-grant", "check", "query", "flow"),
            ("write-sharing", "advance", "write", "flow"),
            ("current-state", "advance", "state-parameter", "data"),
        ]
    ]
    (root / "bo_stategraph/project.json").write_text(
        json.dumps(project, indent=2), encoding="utf-8"
    )
    validate_graph(model)
    with closing(sqlite3.connect(root / "sharing.sqlite")) as db:
        db.execute("create table grants(actor text primary key, allowed integer not null)")
        db.execute("insert into grants values ('owner', 1)")
        db.execute("create table shares(file_id text, recipient text)")
        db.commit()
    return project


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)
        self.project = prepare(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_nested_python_spans_and_exception_identity(self):
        events = []
        probe = BOProbe(self.project, "build", sink=lambda body, kind: events.append(body))
        try:
            with probe.span("advance", entity="file-1", attempt="share-1") as parent:
                with probe.span("check") as child:
                    child.result(lambda: {"outputs": {"allowed": True}})
                parent.record("wait", lambda: {})
                parent.result(lambda: {"outputs": {"state": "done"}})
            error = RuntimeError("original error")
            with self.assertRaises(RuntimeError) as caught:
                with probe.span("advance"):
                    raise error
            self.assertIs(caught.exception, error)
            self.assertTrue(probe.flush())
            self.assertEqual(
                [e["phase"] for e in events],
                ["enter", "enter", "return", "wait", "return", "enter", "error"],
            )
            self.assertEqual(events[1]["parent_call_id"], events[0]["call_id"])
            self.assertEqual(events[1]["entity"], "file-1")
            self.assertEqual(events[4]["outputs"], {"state": "done"})
        finally:
            probe.close()

    def test_equivalent_parameter_retains_distinct_ids_and_rejects_renames(self):
        service = CodeGraph(self.root, persist=False)
        graph = service.view(limit=400)
        mapping = next(e for e in graph["edges"] if e.get("mapping_role") == "equivalent")
        self.assertEqual(mapping["from"], "state-parameter")
        self.assertNotEqual(mapping["from"], mapping["to"])
        self.assertEqual(sum(n["id"] == mapping["to"] for n in graph["nodes"]), 1)
        source = next(n for n in graph["nodes"] if n["id"] == mapping["to"])
        self.assertEqual(source["label"], "state")
        self.assertEqual(source["code_role"], "parameter")
        (self.root / "worker.py").write_text(
            BUSINESS.replace("def advance(state,", "def advance(renamed,"), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "Missing equivalent source parameter"):
            service.refresh()

    def test_malformed_semantic_parameter_cannot_pass(self):
        for bad in (
            {"path": "worker.py", "symbol": "advance"},
            {"path": "unknown.py", "symbol": "advance", "parameter": "state"},
        ):
            model = deepcopy(self.project["model"])
            next(n for n in model["nodes"] if n["id"] == "state-parameter")["represents"] = bad
            with self.assertRaises(ValueError):
                validate_graph(model)

    def test_child_inherits_scope_but_not_parent_revision_or_dependencies(self):
        events = []
        probe = BOProbe(self.project, "build", sink=lambda body, kind: events.append(body))
        try:
            with probe.span(
                "advance",
                entity="file-1",
                attempt="request-1",
                revision=3,
                depends=[{"event": "prior", "type": "data"}],
            ):
                with probe.span("check"):
                    pass
            self.assertTrue(probe.flush())
            child = next(e for e in events if e["node"] == "check")
            self.assertEqual(child["entity"], "file-1")
            self.assertEqual(child["parent_call_id"], events[0]["call_id"])
            self.assertNotIn("revision", child)
            self.assertEqual(child["depends"], [])
        finally:
            probe.close()

    def test_concurrent_async_spans_keep_parentage_local(self):
        events = []
        probe = BOProbe(self.project, "build", sink=lambda body, kind: events.append(body))

        async def task(entity):
            with probe.span("advance", entity=entity):
                await asyncio.sleep(0)
                with probe.span("check"):
                    await asyncio.sleep(0)

        async def both():
            await asyncio.gather(task("first"), task("second"))

        try:
            asyncio.run(both())
            self.assertTrue(probe.flush())
            parents = {
                e["entity"]: e["call_id"]
                for e in events
                if e["node"] == "advance" and e["phase"] == "enter"
            }
            for event in events:
                if event["node"] == "check":
                    self.assertEqual(event["parent_call_id"], parents[event["entity"]])
        finally:
            probe.close()

    def test_observation_modes_preserve_actual_sql_result(self):
        spec = importlib.util.spec_from_file_location("lifecycle_modes", self.root / "worker.py")
        application = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(application)
        engine = BOExecutor(
            self.project["model"]["machine"], {"available": lambda context, payload: True}
        )

        def broken_sink(body, kind):
            raise OSError("unavailable observer")

        for mode in ("on", "off", "fault", "limited"):
            with self.subTest(mode=mode):
                with closing(sqlite3.connect(self.root / "sharing.sqlite")) as db:
                    db.execute("delete from shares")
                    db.commit()
                probe = BOProbe(
                    self.project,
                    "build",
                    enabled=mode != "off",
                    capacity=1 if mode == "limited" else 256,
                    sink=broken_sink if mode == "fault" else lambda body, kind: None,
                )
                gate = threading.Event()
                gate.set()
                try:
                    result = application.advance(
                        "pending",
                        probe,
                        gate,
                        self.root / "sharing.sqlite",
                        engine,
                        lambda *args: None,
                    )
                    self.assertEqual(result, "done")
                    self.assertTrue(probe.flush())
                    with closing(sqlite3.connect(self.root / "sharing.sqlite")) as db:
                        self.assertEqual(db.execute("select count(*) from shares").fetchone()[0], 1)
                    if mode == "fault":
                        self.assertGreater(probe.bo_errors, 0)
                finally:
                    probe.close()


def serve(root, registered=False, telemetry=False):
    """Run the same real SQLite operation with native or standard tracing context."""
    project = prepare(root, registered=registered)
    session = GraphSession(root)
    probe = BOProbe(
        project,
        session.manifest["build_id"],
        capacity=256,
        sink=lambda body, kind: session.event(body) if kind == "events" else session.snapshot(body),
    )
    provider = None
    if telemetry:
        from opentelemetry.sdk.trace import TracerProvider
        from bo_observer.adapters.python.bo_otel import BOOpenTelemetry

        provider = TracerProvider()
        probe.bo_bind_tracing(BOOpenTelemetry(provider.get_tracer("vibelens.browser")))
    gate = threading.Event()
    engine = BOExecutor(
        project["model"]["machine"], {"available": lambda context, payload: context["slots"] > 0}
    )
    result = {"running": False, "state": "pending", "error": None}

    def report(state, revision, event=None):
        ident = probe.record(
            "advance",
            "change",
            lambda: {"outputs": {"state": state}},
            entity="job",
            attempt="attempt-1",
            scope="entity",
            revision=revision,
        )
        probe.snapshot(
            "job",
            state,
            {"slots": 1},
            revision,
            ident,
            event=event,
            guards={"available": True} if event == "start" else {},
            payload={} if event else None,
        )
        if not probe.flush():
            raise RuntimeError("Capture did not drain")

    report("pending", 0)
    spec = importlib.util.spec_from_file_location("lifecycle_application", root / "worker.py")
    application = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(application)

    def operate():
        try:
            result["state"] = application.advance(
                "pending", probe, gate, root / "sharing.sqlite", engine, report
            )
        except Exception as error:
            result["error"] = str(error)
        finally:
            probe.flush()
            result["running"] = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path == "/begin" and not result["running"]:
                result["running"] = True
                threading.Thread(target=operate, daemon=True).start()
            elif self.path == "/release":
                gate.set()
            else:
                self.send_error(400)
                return
            self.reply({"accepted": True})

        def do_GET(self):
            with closing(sqlite3.connect(root / "sharing.sqlite")) as db:
                count = db.execute("select count(*) from shares").fetchone()[0]
            self.reply(
                {
                    **result,
                    "shares": count,
                    "events": len(session.history.snapshot()),
                    "probe_errors": probe.bo_errors,
                }
            )

        def reply(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    business = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    observer = make_server(session, 0)
    session.program_url = f"http://127.0.0.1:{business.server_port}"
    threading.Thread(target=business.serve_forever, daemon=True).start()
    print(
        json.dumps(
            {
                "observer": f"http://127.0.0.1:{observer.server_port}",
                "application": session.program_url,
            }
        ),
        flush=True,
    )
    try:
        observer.serve_forever()
    finally:
        business.shutdown()
        probe.close()
        if provider:
            provider.shutdown()
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", type=Path)
    parser.add_argument("--registered", action="store_true")
    parser.add_argument("--telemetry", action="store_true")
    options, rest = parser.parse_known_args()
    if options.serve:
        serve(options.serve.absolute(), registered=options.registered, telemetry=options.telemetry)
    else:
        unittest.main(argv=[sys.argv[0], *rest])
