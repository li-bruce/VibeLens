"""Project observation adapter; never decides permissions or changes business storage."""
import json
from contextlib import contextmanager, nullcontext
from pathlib import Path
from collections import deque
from opentelemetry.sdk.trace import TracerProvider
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.adapters.python.bo_otel import BOOpenTelemetry, BOOpenTelemetryProcessor
from bo_observer.policy.recording import record_evaluation
from bo_observer.data.runtime import BODataRuntime


class BODiagnosticSink:
    def __init__(self, target):
        self.target = target
        self.failures = deque(maxlen=32)

    def __call__(self, value, kind):
        try:
            return self.target(value, kind)
        except Exception as error:
            self.failures.append({"kind": kind, "node": value.get("node"), "error": type(error).__name__, "message": str(error)[:500]})
            raise

    def bo_accept_many(self, events):
        return self.target.bo_accept_many(events)


class BOHooks:
    def __init__(self, session, *, mode="on", capacity=8192):
        self.session = session
        self.policy_reports = deque(maxlen=10000)
        self.native_states = deque(maxlen=10000)
        self.mode = mode
        self.bo_sink = BODiagnosticSink(session.bo_sink)
        sink = self.bo_sink
        if mode == "fault":
            sink = self.bo_failed_sink
        self.bo_probe = BOProbe(session.project, session.manifest["build_id"], enabled=mode != "off", sink=sink, capacity=capacity)
        self.bo_provider = TracerProvider()
        self.bo_tracing = self.bo_probe.bo_bind_tracing(BOOpenTelemetry(self.bo_provider.get_tracer("team-files")))
        config = json.loads((session.root / "bo_stategraph/telemetry.json").read_text(encoding="utf-8"))
        self.bo_provider.add_span_processor(BOOpenTelemetryProcessor(self.bo_tracing, config))
        self.bo_data = BODataRuntime(self.bo_probe, json.loads((session.root / "bo_stategraph/databases.json").read_text(encoding="utf-8")))
        session.bo_bind_capture(scope_setter=self.bo_probe.bo_set_scope, flush_capture=self.bo_probe.flush, health=self.bo_health)

    def bo_failed_sink(self, value, kind):
        raise ConnectionError("deliberate_observer_transport_failure")

    def bo_health(self):
        return {**self.bo_probe.bo_health(), "data_errors": self.bo_data.bo_errors, "capture_failures": list(self.bo_sink.failures)}

    def span(self, node, builder=lambda: {}, **options):
        return self.bo_probe.span(node, builder, **options)

    def record(self, node, phase, builder, **options):
        return self.bo_probe.record(node, phase, builder, **options)

    def policy(self, declaration, evaluation):
        self.policy_reports.append(evaluation)
        context = self.bo_probe.bo_current_context()
        record_evaluation(declaration, evaluation, self.bo_probe, entity=context.get("entity") or "application", attempt=context.get("attempt", "application"))

    def inject(self):
        return self.bo_tracing.inject()

    def receive(self, carrier):
        return self.bo_tracing.receive(carrier, trusted=True, link=True) if carrier else nullcontext()

    def state(self, file_id, state, context, revision, evidence, **options):
        self.native_states.append({"id": file_id, "state": state, "context": context, "revision": revision})
        if evidence:
            self.bo_probe.snapshot(file_id, state, context, revision, evidence, **options)

    @contextmanager
    def http(self, operation):
        with self.bo_provider.get_tracer("team-http").start_as_current_span("team.http", attributes={"team.operation": operation}) as span:
            yield span

    def data(self, node, callback, **options):
        return self.bo_data.execute(node, callback, **options)

    def transaction(self, node, manager):
        return self.bo_data.transaction(node, manager)

    def transform(self, node, function, value):
        return self.bo_data.transform(node, function, value, before=lambda item: {"filename": item}, after=lambda item: {"filename": item})

    def close(self):
        self.bo_probe.flush(10)
        self.bo_probe.close()
        self.bo_provider.shutdown()
