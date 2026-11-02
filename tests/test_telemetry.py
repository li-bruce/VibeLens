"""Real SDK traces must supplement, never replace, graph and capture evidence."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.adapters.python.bo_otel import BOOpenTelemetry, BOOpenTelemetryProcessor
from bo_observer.observation.provenance import trace_references, object_metadata, export_provenance
from bo_observer.observation.telemetry import validate_registrations, business_layer_errors
from bo_observer.observation.telemetry import load_registrations, runtime_errors, automatic_sites
from bo_observer.workflow.observation_requirements import invocation_closure
from bo_observer.protocol import schema_check, validate_event
from bo_observer.observation.observation_scope import bo_internal
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import use_span, StatusCode
from test_multilanguage import project_fixture


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.temp.cleanup)
        self.project = project_fixture(Path(self.temp.name))
        worker = Path(self.temp.name) / "worker.py"
        worker.write_text(
            worker.read_text(encoding="utf-8") + "\ndef may_share():\n    return True\n",
            encoding="utf-8",
        )
        self.project["model"]["nodes"].extend(
            [
                {
                    "id": "check",
                    "kind": "decision",
                    "label": "May share",
                    "summary": "File sharing permission",
                    "source": {"path": "worker.py", "symbol": "may_share"},
                    "capture": {"out": {"value": "boolean"}},
                },
                {
                    "id": "api",
                    "kind": "function",
                    "source": {"path": "worker.py", "symbol": "advance"},
                    "label": "GET /files",
                    "summary": "List files route",
                    "capture": {"out": {"status": "number"}},
                },
            ]
        )
        self.events = []
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.addCleanup(self.provider.shutdown)
        self.tracer = self.provider.get_tracer("vibelens.tests")
        self.probe = BOProbe(
            self.project, "build", sink=lambda body, kind: self.events.append(body)
        )
        self.addCleanup(self.probe.close)
        self.backend = self.probe.bo_bind_tracing(BOOpenTelemetry(self.tracer))

    def check_events(self, events=None):
        self.assertTrue(self.probe.flush(3))
        events = self.events if events is None else events
        for event in events:
            validate_event(event, self.project, "build")
        result = invocation_closure(
            {"runs": [{"mode": "on", "events": events}]}, required=True, model=self.project["model"]
        )
        self.assertTrue(result["valid"], result)
        self.assertEqual(self.probe.bo_errors, 0, self.probe.bo_health())
        return result

    def test_real_sdk_identity_preserves_call_ids_values_and_business_machine(self):
        machine = deepcopy(self.project["model"]["machine"])
        with self.probe.span("advance", entity="file", attempt="request", call_id="native-call"):
            self.probe.record("check", "decision", lambda: {"outputs": {"value": False}})
        self.check_events()
        self.assertEqual(self.events[0]["call_id"], "native-call")
        self.assertEqual(self.events[1]["outputs"], {"value": False})
        self.assertEqual(len(self.exporter.get_finished_spans()), 1)
        self.assertEqual(len({e["trace"]["span_id"] for e in self.events}), 1)
        self.assertEqual(machine, self.project["model"]["machine"])

    def test_detached_async_child_after_parent_ends_is_causal_not_temporally_nested(self):
        async def operation():
            release = asyncio.Event()

            async def child():
                await release.wait()
                with self.probe.span("advance", entity="job"):
                    await asyncio.sleep(0)
                    self.probe.record("check", "decision", lambda: {"outputs": {"value": True}})

            with self.probe.span("advance", entity="request"):
                task = asyncio.create_task(child())
            release.set()
            await task

        asyncio.run(operation())
        self.check_events()
        self.assertEqual(
            [e["phase"] for e in self.events], ["enter", "return", "enter", "decision", "return"]
        )
        parent, child = self.events[0], self.events[2]
        self.assertEqual(child["parent_event_id"], parent["id"])
        self.assertEqual(child["trace"]["parent_span_id"], parent["trace"]["span_id"])

    def test_concurrent_tasks_do_not_share_roots(self):
        async def request(name):
            with self.probe.span("advance", entity=name):
                await asyncio.sleep(0.001)
                with self.probe.span("advance", entity="same-file"):
                    await asyncio.sleep(0)

        async def run():
            await asyncio.gather(request("alice"), request("ben"))

        asyncio.run(run())
        self.check_events()
        roots = [e for e in self.events if e["phase"] == "enter" and not e["parent_event_id"]]
        self.assertEqual(len({e["trace"]["trace_id"] for e in roots}), 2)

    def test_cross_producer_carrier_retains_business_reference_not_actor_authority(self):
        values = []
        remote = BOProbe(self.project, "build", sink=lambda body, kind: values.append(body))
        self.addCleanup(remote.close)
        backend = remote.bo_bind_tracing(BOOpenTelemetry(self.tracer))
        provenance = {
            "workflow_id": "review-1",
            "actor": {"id": "alice", "kind": "user"},
            "objects": [{"id": "f1", "type": "File", "role": "subject", "version": "1"}],
        }
        with self.probe.span("advance", entity="file", provenance=provenance):
            carrier = self.backend.inject()
        self.assertNotIn('"actor"', carrier["vibelens-context"])
        with backend.receive(carrier, trusted=True):
            with remote.span("advance"):
                pass
        self.assertTrue(remote.flush())
        self.check_events([*self.events, *values])
        self.assertEqual(values[0]["provenance"]["workflow_id"], "review-1")
        self.assertEqual(values[0]["trace"]["trace_id"], self.events[0]["trace"]["trace_id"])
        with backend.receive(carrier):
            self.assertEqual(
                remote.bo_current_context(),
                {},
                "public trace headers do not establish business identity",
            )
        bad = {
            **carrier,
            "vibelens-context": carrier["vibelens-context"].replace('"build"', '"other"'),
        }
        with self.assertRaises(ValueError):
            with backend.receive(bad, trusted=True, strict=True):
                pass

    def test_linked_job_is_a_distinct_execution(self):
        with self.probe.span("advance"):
            carrier = self.backend.inject()
        with self.backend.receive(carrier, trusted=True, link=True):
            with self.probe.span("advance", entity="job"):
                pass
        self.check_events()
        root, job = self.events[0], self.events[2]
        self.assertNotEqual(root["trace"]["trace_id"], job["trace"]["trace_id"])
        self.assertIsNone(job["parent_event_id"])
        self.assertEqual(job["trace"]["links"][0]["span_id"], root["trace"]["span_id"])

    def test_automatic_registration_streams_entry_before_sdk_span_ends(self):
        cfg = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "api",
                    "source": self.project["model"]["nodes"][-1]["source"],
                    "match": {"name": "GET /files"},
                    "capture": {"out": {"status": "http.response.status_code"}},
                }
            ],
        }
        processor = BOOpenTelemetryProcessor(self.backend, cfg)
        self.provider.add_span_processor(processor)
        span = self.tracer.start_span("GET /files")
        self.assertTrue(self.probe.flush())
        self.assertEqual([e["phase"] for e in self.events], ["enter"])
        self.assertEqual(len(self.exporter.get_finished_spans()), 0)
        with use_span(span):
            with self.probe.span("advance"):
                pass
        span.set_attribute("http.response.status_code", 403)
        span.end()
        self.check_events()
        self.assertEqual(self.events[-1]["outputs"], {"status": 403})
        self.assertIsNone(self.events[-1]["parent_event_id"])
        self.assertEqual(processor.errors, 0)
        self.assertEqual(len(self.events), 4, "own spans are not captured twice")
        with bo_internal():
            self.tracer.start_span("GET /files").end()
        self.assertEqual(len(self.events), 4)

    def test_focused_capture_omits_values_but_retains_trace_headers(self):
        self.probe.bo_set_scope(["check"])
        with self.probe.span(
            "advance",
            builder=lambda: self.fail("unselected builder"),
            provenance={"actor": {"id": "alice", "kind": "user"}},
        ):
            self.probe.record("check", "decision", lambda: {"outputs": {"value": True}})
        self.assertTrue(self.probe.flush())
        for event in self.events:
            schema_check(event, "event")
        self.assertTrue(self.events[0]["context_only"])
        self.assertNotIn("provenance", self.events[0])
        self.assertIn("trace", self.events[0])

    def test_invalid_metadata_and_changed_span_ids_fail(self):
        with self.probe.span("advance"):
            pass
        self.check_events()
        for change in (
            {"trace_id": "0" * 32},
            {"span_id": "bad"},
            {"trace_flags": True},
            {"extra": 1},
        ):
            bad = deepcopy(self.events[0])
            bad["trace"].update(change)
            with self.assertRaises(ValueError):
                schema_check(bad, "event")
        bad = deepcopy(self.events)
        bad[-1]["trace"]["span_id"] = "1" * 16
        self.assertFalse(trace_references(bad)["valid"])

    def test_multi_object_roles_and_export_preserve_identity(self):
        provenance = {
            "workflow_id": "share-1",
            "objects": [
                {"type": "File", "id": "f1", "role": "input", "version": "1"},
                {"type": "Share", "id": "s1", "role": "output"},
                {"type": "User", "id": "ben", "role": "recipient"},
            ],
        }
        with self.probe.span("advance", provenance=provenance):
            pass
        self.check_events()
        exported = export_provenance(self.events)
        self.assertEqual(len(exported["objects"]), 3)
        self.assertEqual(len(exported["event_objects"]), 6)
        self.assertEqual(exported["events"][0]["node"], "advance")
        bad = deepcopy(provenance)
        bad["objects"].append(bad["objects"][0])
        with self.assertRaises(ValueError):
            object_metadata(bad)

    def test_stale_source_registration_and_transport_business_label_fail(self):
        cfg = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "api",
                    "source": {"path": "worker.py", "symbol": "old"},
                    "match": {"name": "GET /files"},
                }
            ],
        }
        with self.assertRaises(ValueError):
            validate_registrations(cfg, self.project["model"])
        cfg["registrations"][0].update(
            node="advance", source=self.project["model"]["nodes"][0]["source"]
        )
        with self.assertRaises(ValueError):
            validate_registrations(cfg, self.project["model"])
        self.project["model"]["nodes"][0]["label"] = "网页请求"
        self.assertTrue(business_layer_errors(self.project["model"]))

    def test_python_to_node_to_python_uses_the_same_w3c_trace(self):
        with self.probe.span("advance", entity="file-1"):
            carrier = self.backend.inject()
        self.assertTrue(self.probe.flush())
        result = subprocess.run(
            ["node", "tools/test_telemetry_node.mjs", "--receive"],
            cwd=ROOT,
            input=json.dumps(carrier),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["health"]["errors"], 0)
        with self.backend.receive(value["carrier"], trusted=True):
            with self.probe.span("advance", entity="callback"):
                pass
        self.assertTrue(self.probe.flush())
        events = [*self.events[:2], *value["events"], *self.events[2:]]
        self.check_events(events)
        self.assertEqual(len({event["trace"]["trace_id"] for event in events}), 1)
        self.assertEqual(events[4]["parent_event_id"], events[2]["id"])

    def test_real_sqlite_adapter_inherits_trace_and_object_references(self):
        from sqlalchemy import create_engine
        from bo_observer.data.runtime import BODataRuntime
        from test_database_runtime import bo_fixture

        project, cfg = bo_fixture()
        project["model"]["nodes"].append(self.project["model"]["nodes"][0])
        values = []
        probe = BOProbe(project, "build", sink=lambda body, kind: values.append(body))
        self.addCleanup(probe.close)
        probe.bo_bind_tracing(BOOpenTelemetry(self.tracer))
        runtime = BODataRuntime(probe, cfg)
        self.addCleanup(runtime.close)
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        runtime.attach_sqlalchemy(engine)
        with probe.span(
            "advance", provenance={"objects": [{"id": "files", "type": "Dataset", "role": "input"}]}
        ):
            with runtime.operation("query"), engine.connect() as connection:
                self.assertEqual(connection.exec_driver_sql("SELECT 1").scalar(), 1)
        self.assertTrue(probe.flush())
        self.assertEqual(probe.bo_errors, 0, probe.bo_health())
        self.assertEqual(runtime.bo_errors, 0)
        query = next(event for event in values if event["node"] == "query")
        self.assertEqual(query["trace"]["parent_span_id"], values[0]["trace"]["span_id"])
        self.assertEqual(query["provenance"]["objects"][0]["type"], "Dataset")

    def test_registration_iteration_changes_build_and_cannot_pass_with_native_health(self):
        from bo_observer.graph.behavior_model import capture
        from bo_observer.sources import scan

        root = Path(self.temp.name)
        model = self.project["model"]
        configuration = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [],
        }
        path = root / "bo_stategraph/telemetry.json"
        path.write_text(json.dumps(configuration), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_registrations(root, model)
        model["source_files"].append("bo_stategraph/telemetry.json")
        self.assertEqual(load_registrations(root, model), configuration)
        before = capture(root, model)["build_id"]
        item = {
            "node": "api",
            "source": model["nodes"][-1]["source"],
            "match": {"name": "GET /files"},
        }
        configuration["registrations"].append(item)
        path.write_text(json.dumps(configuration), encoding="utf-8")
        self.assertNotEqual(before, capture(root, model)["build_id"])
        self.assertEqual(len(automatic_sites(configuration, scan(root, ["worker.py"]))), 3)
        with self.assertRaises(ValueError):
            automatic_sites(configuration, {"symbols": {}})
        self.assertTrue(
            runtime_errors(
                configuration, {"runs": [{"mode": "on", "probe_health": {}, "events": []}]}
            )
        )

    def test_session_rejects_wrong_parent_before_publishing(self):
        from bo_observer.observation.session import GraphSession

        with self.probe.span("advance"):
            pass
        self.assertTrue(self.probe.flush())
        session = GraphSession(self.temp.name)
        entry, exit_event = deepcopy(self.events)
        for event in (entry, exit_event):
            event["build_id"] = session.manifest["build_id"]
        bad = {**entry, "parent_event_id": entry["id"]}
        with self.assertRaisesRegex(ValueError, "parent itself"):
            session.event(bad)
        self.assertEqual(session.sequence, 0)
        session.event(entry)
        bad = {**exit_event, "parent_event_id": entry["id"], "parent_call_id": "other"}
        with self.assertRaisesRegex(ValueError, "identity disagree"):
            session.event(bad)
        self.assertEqual(session.sequence, 1)
        session.event(exit_event)
        self.assertEqual(session.sequence, 2)

    def test_links_cannot_create_a_causal_cycle(self):
        with self.probe.span("advance"):
            pass
        self.assertTrue(self.probe.flush())
        a, b = deepcopy(self.events)
        b.update(id="second", call_id="second", phase="enter")
        b["trace"]["span_id"] = "2" * 16
        a["trace"]["links"] = [
            {"trace_id": b["trace"]["trace_id"], "span_id": b["trace"]["span_id"]}
        ]
        b["trace"]["links"] = [
            {"trace_id": a["trace"]["trace_id"], "span_id": a["trace"]["span_id"]}
        ]
        self.assertFalse(trace_references([a, b])["valid"])
        external = deepcopy(a)
        external["trace"]["links"] = [{"trace_id": "3" * 32, "span_id": "4" * 16}]
        result = trace_references([external])
        self.assertEqual(result["external_link_spans"], [["3" * 32, "4" * 16]])

    def test_invalid_runtime_carrier_does_not_change_business_result(self):
        with self.backend.receive({"vibelens-context": "bad"}, trusted=True):
            with self.probe.span("advance"):
                result = 42
        self.assertEqual(result, 42)
        self.assertTrue(self.probe.flush())
        self.assertEqual(self.probe.bo_health()["errors"], 1)
        self.assertIsNone(self.events[0]["parent_event_id"])

    def test_batch_fan_in_uses_links_once_and_does_not_guess_business_owner(self):
        carriers = []
        for entity in ("a", "b"):
            with self.probe.span("advance", entity=entity):
                carriers.append(self.backend.inject())
        with self.backend.linked(carriers):
            with self.probe.span("advance", entity="batch"):
                with self.probe.span("advance", entity="result"):
                    pass
        self.check_events()
        batch, nested = self.events[4], self.events[5]
        self.assertEqual(len(batch["trace"]["links"]), 2)
        self.assertEqual(nested["trace"]["links"], [])
        self.assertIsNone(batch["parent_event_id"])
        self.assertEqual(nested["parent_event_id"], batch["id"])

    def test_upstream_flask_instrumentation_captures_real_denied_response(self):
        from flask import Flask
        from opentelemetry.instrumentation.flask import FlaskInstrumentor

        app = Flask(__name__)

        @app.get("/files")
        def files():
            with self.probe.span("advance"):
                return "Denied", 403

        cfg = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "api",
                    "source": self.project["model"]["nodes"][-1]["source"],
                    "match": {"name": "GET /files"},
                    "capture": {"out": {"status": "http.status_code"}},
                }
            ],
        }
        processor = BOOpenTelemetryProcessor(self.backend, cfg)
        self.provider.add_span_processor(processor)
        FlaskInstrumentor.instrument_app(app, tracer_provider=self.provider)
        self.addCleanup(FlaskInstrumentor.uninstrument_app, app)
        with app.test_client() as client:
            self.assertEqual(client.get("/files").status_code, 403)
        self.check_events()
        self.assertEqual(
            [event["node"] for event in self.events], ["api", "advance", "advance", "api"]
        )
        self.assertEqual(self.events[-1]["outputs"], {"status": 403})

    def test_upstream_flask_closes_at_the_actual_500_response_after_a_native_exception(self):
        from flask import Flask
        from opentelemetry.instrumentation.flask import FlaskInstrumentor

        app = Flask(__name__)
        app.config["PROPAGATE_EXCEPTIONS"] = False
        app.logger.disabled = True

        @app.get("/files")
        def files():
            with self.probe.span("advance"):
                raise RuntimeError("native_storage_unavailable")

        cfg = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "api",
                    "source": self.project["model"]["nodes"][-1]["source"],
                    "match": {"name": "GET /files"},
                    "capture": {"out": {"status": "http.status_code"}},
                }
            ],
        }
        self.provider.add_span_processor(BOOpenTelemetryProcessor(self.backend, cfg))
        FlaskInstrumentor.instrument_app(app, tracer_provider=self.provider)
        self.addCleanup(FlaskInstrumentor.uninstrument_app, app)
        with app.test_client() as client:
            response = client.get("/files")
            self.assertEqual(response.status_code, 500)
        self.check_events()
        self.assertEqual(
            [event["phase"] for event in self.events], ["enter", "enter", "error", "return"]
        )
        self.assertEqual(self.events[-1]["outputs"], {"status": response.status_code})
        self.assertEqual(self.events[2]["node"], "advance")
        self.assertEqual(self.events[2]["exception"], {"type": "RuntimeError"})
        self.assertIn("RuntimeError", self.events[-1]["exception"]["type"])
        self.assertNotIn("native_storage_unavailable", json.dumps(self.events))

    def test_browser_form_commands_capture_native_redirect_denial_and_error_responses(self):
        from flask import Flask, abort, redirect, has_request_context, request
        from opentelemetry.instrumentation.flask import FlaskInstrumentor

        app = Flask(__name__)
        app.config["PROPAGATE_EXCEPTIONS"] = False
        app.logger.disabled = True
        self.project["model"]["nodes"][-1]["capture"]["in"] = {
            "path": "string",
            "operation": "string",
        }

        class NativeRouteFields(SpanProcessor):
            def on_start(self, span, parent_context=None):
                if (
                    span.instrumentation_scope.name == FlaskInstrumentor.__module__
                    and has_request_context()
                    and request.view_args
                ):
                    span.set_attribute("test.operation", request.view_args["operation"])

        @app.post("/command/<operation>")
        def command(operation):
            with self.probe.span("advance"):
                if operation == "denied":
                    abort(403)
                if operation == "broken":
                    raise RuntimeError("native_command_storage_unavailable")
                return redirect("/", code=303)

        @app.get("/observer/graph")
        def observer():
            return "Observer UI"

        @app.get("/api/events")
        def business_events():
            with self.probe.span("advance"):
                return "Application events"

        cfg = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "api",
                    "source": self.project["model"]["nodes"][-1]["source"],
                    "match": {"name": "POST /command/<operation>"},
                    "capture": {
                        "in": {"path": "http.target", "operation": "test.operation"},
                        "out": {"status": "http.status_code"},
                    },
                },
                {
                    "node": "api",
                    "source": self.project["model"]["nodes"][-1]["source"],
                    "match": {"name": "GET /api/events"},
                    "capture": {
                        "in": {"path": "http.target"},
                        "out": {"status": "http.status_code"},
                    },
                },
            ],
        }
        # Read source-specific arguments before the bridge emits the entry fact.
        self.provider.add_span_processor(NativeRouteFields())
        self.provider.add_span_processor(BOOpenTelemetryProcessor(self.backend, cfg))
        FlaskInstrumentor.instrument_app(
            app, tracer_provider=self.provider, excluded_urls=r"/observer/graph"
        )
        self.addCleanup(FlaskInstrumentor.uninstrument_app, app)
        actual = []
        with app.test_client() as client:
            for operation, expected in (("review", 303), ("denied", 403), ("broken", 500)):
                response = client.post("/command/" + operation)
                self.assertEqual(response.status_code, expected)
                actual.append(response.status_code)
            # This path belongs to the application, despite sharing a common
            # observer endpoint name. Only the registered observer UI is excluded.
            response = client.get("/api/events")
            self.assertEqual(response.status_code, 200)
            actual.append(response.status_code)
            before = len(self.exporter.get_finished_spans())
            self.assertEqual(client.get("/observer/graph").status_code, 200)
            self.assertEqual(len(self.exporter.get_finished_spans()), before)

        self.check_events()
        responses = [
            event for event in self.events if event["node"] == "api" and event["phase"] == "return"
        ]
        self.assertEqual([event["outputs"]["status"] for event in responses], actual)
        self.assertEqual(
            [event["inputs"]["path"] for event in responses],
            ["/command/review", "/command/denied", "/command/broken", "/api/events"],
        )
        self.assertEqual(len(responses), 4)
        entries = [e for e in self.events if e["node"] == "api" and e["phase"] == "enter"]
        self.assertEqual(
            [e["inputs"]["operation"] for e in entries if "operation" in e["inputs"]],
            ["review", "denied", "broken"],
        )
        self.assertNotIn("native_command_storage_unavailable", json.dumps(self.events))

    def test_exception_class_is_physical_metadata_even_without_a_business_error_field(self):
        with self.assertRaisesRegex(ValueError, "selected-private-value"):
            with self.probe.span("advance"):
                raise ValueError("selected-private-value")
        self.check_events()
        self.assertEqual(self.events[-1]["outputs"], {})
        self.assertEqual(self.events[-1]["exception"], {"type": "ValueError"})
        sdk = self.exporter.get_finished_spans()[-1]
        self.assertEqual(sdk.attributes["error.type"], "ValueError")
        self.assertEqual(sdk.status.status_code, StatusCode.ERROR)
        self.assertEqual(
            sdk.events, (), "native BO facts do not introduce deprecated exception span events"
        )
        self.assertNotIn("selected-private-value", json.dumps(self.events))
        from bo_observer.observation.capture_context import minimal_boundary

        header = minimal_boundary(self.events[-1], self.project["model"]["nodes"][0])
        self.assertNotIn("exception", header)
        schema_check(header, "event")

    def test_error_status_alone_does_not_invent_a_physical_exception(self):
        from opentelemetry.trace import StatusCode

        cfg = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "api",
                    "source": self.project["model"]["nodes"][-1]["source"],
                    "match": {"name": "GET /files"},
                    "capture": {"out": {"status": "http.response.status_code"}},
                }
            ],
        }
        self.provider.add_span_processor(BOOpenTelemetryProcessor(self.backend, cfg))
        span = self.tracer.start_span("GET /files")
        span.set_status(StatusCode.ERROR)
        span.set_attribute("http.response.status_code", 500)
        span.end()
        self.check_events()
        self.assertNotIn("exception", self.events[-1])
        self.assertEqual(self.events[-1]["outputs"]["status"], 500)

    def test_exception_metadata_is_strict_and_does_not_escape_capture_scope(self):
        self.probe.bo_set_scope(["check"])
        with self.assertRaises(RuntimeError):
            with self.probe.span("advance"):
                raise RuntimeError("not selected")
        self.assertTrue(self.probe.flush(3))
        self.assertTrue(all(event.get("context_only") for event in self.events))
        self.assertTrue(all("exception" not in event for event in self.events))
        for event in self.events:
            schema_check(event, "event")
        raw = {**self.events[-1], "context_only": False}
        raw.pop("context_boundary", None)
        for value in (
            None,
            {},
            {"type": "TypeError", "message": "private"},
            {"type": "not a class"},
            {"type": "A..B"},
        ):
            bad = {**raw, "exception": value}
            with self.assertRaises(ValueError):
                validate_event(bad, self.project, "build")
            bad.pop("trace", None)
            self.assertFalse(trace_references([bad])["valid"])
        self.assertEqual(self.probe.bo_health()["errors"], 0)

    def test_standalone_native_adapter_retains_exceptions_without_sdk_imports(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "isolated_native_probe",
            ROOT / "skills/vibelens/scripts/bo_observer/adapters/python/bo_probe.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        events = []
        probe = module.BOProbe(self.project, "build", sink=lambda body, kind: events.append(body))
        try:
            with self.assertRaises(TypeError):
                with probe.span("advance"):
                    raise TypeError("not collected")
            self.assertTrue(probe.flush(3))
            self.assertEqual(events[-1]["exception"], {"type": "TypeError"})
            self.assertEqual(probe.bo_health()["errors"], 0)
            validate_event(events[-1], self.project, "build")
        finally:
            probe.close()

    def test_automatic_ownership_uses_trace_and_span_together(self):
        from opentelemetry.sdk.trace.id_generator import IdGenerator

        class RepeatedSpanId(IdGenerator):
            counter = 0

            def generate_trace_id(self):
                self.counter += 1
                return self.counter

            def generate_span_id(self):
                return 7

        cfg = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "api",
                    "source": self.project["model"]["nodes"][-1]["source"],
                    "match": {"name": "GET /files"},
                    "capture": {"out": {"status": "http.response.status_code"}},
                }
            ],
        }
        provider = TracerProvider(id_generator=RepeatedSpanId())
        self.addCleanup(provider.shutdown)
        provider.add_span_processor(BOOpenTelemetryProcessor(self.backend, cfg))
        tracer = provider.get_tracer("independent-traces")
        first, second = tracer.start_span("GET /files"), tracer.start_span("GET /files")
        try:
            self.assertTrue(self.probe.flush())
            a, b = self.events[:2]
            self.assertEqual(a["trace"]["span_id"], b["trace"]["span_id"])
            self.assertNotEqual(a["trace"]["trace_id"], b["trace"]["trace_id"])
            self.assertNotEqual(a["call_id"], b["call_id"])
            for span, owner in ((first, a), (second, b)):
                with use_span(span):
                    self.assertEqual(
                        self.probe.bo_current_context()["parent_event_id"], owner["id"]
                    )
                    self.probe.record("check", "decision", lambda: {"outputs": {"value": True}})
                span.set_attribute("http.response.status_code", 200)
        finally:
            first.end()
            second.end()
        self.check_events()

    def test_old_build_queue_keeps_cause_but_never_old_model_ownership(self):
        source = BOProbe(self.project, "previous-build", sink=lambda body, kind: None)
        old = source.bo_bind_tracing(BOOpenTelemetry(self.tracer))
        try:
            with source.span(
                "advance", entity="old-entity", provenance={"workflow_id": "old-process"}
            ):
                carrier = old.inject()
            with self.backend.receive(carrier, trusted=True):
                with self.probe.span("advance", entity="current-job"):
                    pass
            self.check_events()
            entry = self.events[0]
            self.assertIsNone(entry["parent_event_id"])
            self.assertIsNone(entry["parent_call_id"])
            self.assertNotIn("provenance", entry)
            self.assertEqual(entry["trace"]["links"][0]["source_build_id"], "previous-build")
            self.assertEqual(self.backend.health()["external_build_contexts"], 1)
            with self.assertRaises(ValueError):
                with self.backend.receive(carrier, trusted=True, strict=True):
                    pass
        finally:
            source.close()

    def test_old_version_does_not_bypass_private_identity_validation(self):
        with self.probe.span("advance"):
            carrier = self.backend.inject()
        for identity in (
            {"provenance": {"actor": None}},
            {"scope": ""},
            {"provenance": {"objects": "invalid"}},
        ):
            value = json.loads(carrier["vibelens-context"])
            value.update(build_id="previous-build", identity=identity)
            with self.assertRaises(ValueError):
                with self.backend.receive(
                    {**carrier, "vibelens-context": json.dumps(value)}, trusted=True, strict=True
                ):
                    pass
        self.assertEqual(self.backend.health()["external_build_contexts"], 0)

    def test_upstream_urllib_instrumentation_does_not_record_observer_transport(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        from opentelemetry.instrumentation.urllib import URLLibInstrumentor

        class Collector(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Collector)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        instrumentor = URLLibInstrumentor()
        instrumentor.instrument(tracer_provider=self.provider)
        self.addCleanup(instrumentor.uninstrument)
        probe = BOProbe(self.project, "build", endpoint=f"http://127.0.0.1:{server.server_port}")
        self.addCleanup(probe.close)
        probe.bo_bind_tracing(BOOpenTelemetry(self.tracer))
        with probe.span("advance"):
            pass
        self.assertTrue(probe.flush(3))
        spans = self.exporter.get_finished_spans()
        self.assertEqual([span.name for span in spans], ["advance"])
        self.assertEqual(probe.bo_errors, 0, probe.bo_health())

    def test_noop_provider_does_not_masquerade_as_working_capture(self):
        from opentelemetry.trace import NoOpTracerProvider

        events = []
        probe = BOProbe(self.project, "build", sink=lambda body, kind: events.append(body))
        self.addCleanup(probe.close)
        probe.bo_bind_tracing(BOOpenTelemetry(NoOpTracerProvider().get_tracer("missing-sdk")))
        with probe.span("advance"):
            result = 42
        self.assertEqual(result, 42)
        self.assertTrue(probe.flush())
        self.assertGreater(probe.bo_health()["errors"], 0)
        self.assertEqual(events, [])

    def test_completion_builder_records_identity_and_objects_only_when_they_exist(self):
        native_actor = {"id": "verified-user", "kind": "user"}
        created = {"type": "File", "id": "native-file-id", "role": "output"}
        with self.probe.span("advance", provenance={"actor": None}) as observed:
            observed.result(
                lambda: {
                    "outputs": {"state": "running"},
                    "provenance": {"actor": native_actor, "objects": [created]},
                }
            )
        self.check_events()
        self.assertIsNone(self.events[0]["provenance"]["actor"])
        self.assertEqual(self.events[-1]["provenance"]["actor"], native_actor)
        self.assertEqual(self.events[-1]["provenance"]["objects"], [created])
        self.assertEqual(self.events[0]["trace"]["span_id"], self.events[-1]["trace"]["span_id"])


if __name__ == "__main__":
    unittest.main()
