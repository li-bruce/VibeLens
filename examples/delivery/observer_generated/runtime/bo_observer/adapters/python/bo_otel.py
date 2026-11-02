"""OpenTelemetry task context and propagation behind the existing BOProbe interface.

The application supplies its tracer/provider. No global provider, state executor,
business function or authorization mechanism is replaced. Import only when the
optional telemetry requirements are installed.
"""

from collections import OrderedDict
from contextlib import contextmanager
import json
import threading
from types import SimpleNamespace

from opentelemetry import context, trace
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.instrumentation.utils import suppress_instrumentation

from ...observation.observation_scope import bo_is_internal
from ...observation.provenance import trace_metadata, object_metadata, exception_metadata
from ...observation.telemetry import match_registration, validate_registrations

_ACTIVATION = context.create_key("vibelens.activation")
_LINKS = context.create_key("vibelens.links")
_CARRIER = "vibelens-context"


def bo_span_metadata(span, parent=None, links=()):
    """Copy standard identity only; parameters remain governed by graph capture specs."""
    sc = span.get_span_context()
    if not sc.is_valid:
        return None
    parent = parent if parent is not None else getattr(span, "parent", None)
    return trace_metadata(
        {
            "trace_id": format(sc.trace_id, "032x"),
            "span_id": format(sc.span_id, "016x"),
            "trace_flags": int(sc.trace_flags),
            "parent_span_id": (
                format(parent.span_id, "016x") if parent and parent.is_valid else None
            ),
            "tracestate": sc.trace_state.to_header(),
            "links": [
                {
                    "trace_id": format(link.context.trace_id, "032x"),
                    "span_id": format(link.context.span_id, "016x"),
                    "relation": (link.attributes or {}).get("vibelens.relation", "trigger"),
                    **(
                        {"source_build_id": link.attributes["vibelens.source_build_id"]}
                        if (link.attributes or {}).get("vibelens.source_build_id")
                        else {}
                    ),
                }
                for link in links
            ],
        }
    )


class BOOpenTelemetry:
    """Replace custom ambient context with SDK context, preserving event/call IDs."""

    def __init__(self, tracer, *, limit=10000):
        self.tracer, self.limit = tracer, limit
        self.probe = None
        self.spans, self.automatic = {}, OrderedDict()
        self.processors = []
        self.external_build_contexts = 0
        self.lock = threading.RLock()
        self.propagator = TraceContextTextMapPropagator()

    def bind(self, probe):
        if self.probe is not None:
            raise ValueError("tracing backend already bound to a producer")
        self.probe = probe

    def health(self):
        return {
            "backend": "opentelemetry",
            "open_spans": len(self.spans),
            "automatic_open": sum(len(p.open) for p in self.processors),
            "automatic_errors": sum(p.errors for p in self.processors),
            "ignored": sum(p.ignored for p in self.processors),
            "external_build_contexts": self.external_build_contexts,
        }

    def internal(self):
        """Upstream instrumentors suppress observer transport, not application work."""
        return suppress_instrumentation()

    def current(self):
        sc = trace.get_current_span().get_span_context()
        with self.lock:
            automatic = self.automatic.get((sc.trace_id, sc.span_id)) if sc.is_valid else None
        return automatic or context.get_value(_ACTIVATION)

    @contextmanager
    def activate(self, activation):
        """SDK context is copied by asyncio; an ended causal parent remains identifiable."""
        with self.lock:
            record = self.spans.get(activation.call_id)
        ctx = context.set_value(_ACTIVATION, activation)
        if record:
            ctx = trace.set_span_in_context(record[0], ctx)
            ctx = context.set_value(_LINKS, (), ctx)
        token = context.attach(ctx)
        try:
            yield
        finally:
            context.detach(token)

    def observe(self, node, phase, call_id, boundary):
        """Start/end hooks do no network I/O; the probe still owns bounded delivery."""
        with self.lock:
            record = self.spans.get(call_id)
            if boundary == "start" and not record and call_id:
                if len(self.spans) >= self.limit:
                    raise ValueError("open telemetry span limit reached")
                parent = trace.get_current_span().get_span_context()
                links = context.get_value(_LINKS) or ()
                span = self.tracer.start_span(
                    node, attributes={"vibelens.node_id": node}, links=links
                )
                record = (span, parent, links)
                self.spans[call_id] = record
            if record:
                metadata = bo_span_metadata(*record)
                if metadata is None:
                    raise ValueError("selected tracing backend lacks a configured SDK SpanContext")
                return metadata
        return bo_span_metadata(trace.get_current_span())

    def complete(self, call_id, phase, boundary):
        if boundary != "end":
            return
        with self.lock:
            record = self.spans.pop(call_id, None)
        if record:
            record[0].end()

    def exception(self, call_id, value):
        """Annotate the actual escaping exception, without adding legacy span events."""
        with self.lock:
            record = self.spans.get(call_id)
        if record:
            record[0].set_attribute("error.type", exception_metadata(value)["type"])
            record[0].set_status(trace.StatusCode.ERROR)

    def inject(self):
        """Use W3C headers plus a bounded project-owned envelope for internal jobs.

        Actor identity is deliberately absent. Never trust a browser-supplied
        VibeLens envelope as business identity or authorization.
        """
        carrier = {}
        self.propagator.inject(carrier)
        activation = self.current()
        if activation and activation.bo_probe is self.probe:
            identity = {
                key: value
                for key, value in activation.bo_options.items()
                if key in {"entity", "attempt", "scope"}
            }
            provenance = activation.bo_options.get("provenance", {})
            if provenance:
                identity["provenance"] = {
                    k: v for k, v in object_metadata(provenance).items() if k != "actor"
                }
            carrier[_CARRIER] = json.dumps(
                {
                    "project_id": self.probe.bo_project["project_id"],
                    "build_id": self.probe.bo_build,
                    "model_revision": self.probe.bo_project["model"]["revision"],
                    "call_id": activation.call_id,
                    "entry_id": activation.entry_id,
                    "identity": identity,
                },
                separators=(",", ":"),
            )
        return carrier

    def _receive_context(self, carrier, *, trusted=False, link=False, strict=False):
        """Extract a remote context, or link a new job trace to its triggering span.

        ``trusted`` means an application-owned internal queue envelope, not an
        authenticated user. Public HTTP accepts only standard trace context.
        """
        ctx = self.propagator.extract(carrier, context=context.Context())
        sc = trace.get_current_span(ctx).get_span_context()
        identity, activation, source_build = {}, None, None
        if trusted and _CARRIER in carrier:
            if not sc.is_valid:
                raise ValueError("internal carrier lacks valid W3C trace context")
            raw = carrier[_CARRIER]
            if not isinstance(raw, str) or len(raw) > 16384:
                raise ValueError("invalid internal trace carrier")
            value = json.loads(raw)
            if not isinstance(value, dict) or set(value) != {
                "project_id",
                "build_id",
                "model_revision",
                "call_id",
                "entry_id",
                "identity",
            }:
                raise ValueError("invalid internal trace carrier fields")
            if any(
                not isinstance(value[key], str) or not value[key] or len(value[key]) > 512
                for key in ("call_id", "entry_id")
            ):
                raise ValueError("invalid internal invocation reference")
            if value["project_id"] != self.probe.bo_project["project_id"]:
                raise ValueError("internal trace carrier belongs to another project")
            if any(
                not isinstance(value[key], str) or not value[key]
                for key in ("build_id", "model_revision")
            ):
                raise ValueError("invalid internal build identity")
            changed_build = (
                value["build_id"] != self.probe.bo_build
                or value["model_revision"] != self.probe.bo_project["model"]["revision"]
            )
            identity = value.get("identity", {})
            if not isinstance(identity, dict) or set(identity) - {
                "entity",
                "attempt",
                "scope",
                "provenance",
            }:
                raise ValueError("invalid internal observation identity")
            if any(
                not isinstance(identity[k], str) or not identity[k] or len(identity[k]) > 256
                for k in ("entity", "attempt")
                if k in identity
            ):
                raise ValueError("invalid internal business instance reference")
            if "scope" in identity and identity["scope"] not in {
                "application",
                "entity",
                "attempt",
            }:
                raise ValueError("invalid internal observation scope")
            if "provenance" in identity:
                object_metadata(identity["provenance"])
                if "actor" in identity["provenance"]:
                    raise ValueError("actor cannot be propagated as trusted trace identity")
            activation = SimpleNamespace(
                bo_probe=self.probe,
                bo_options=identity,
                call_id=value.get("call_id"),
                entry_id=value.get("entry_id"),
                bo_active=False,
            )
            if changed_build:
                if strict or len(value["build_id"]) > 256:
                    raise ValueError("internal trace carrier belongs to another graph build")
                # A valid technical cause survives a deployment. Old graph call
                # IDs, entities and parameter context must not enter the new model.
                source_build = value["build_id"]
                self.external_build_contexts += 1
                identity, activation, link = {}, None, True
        if link:
            ctx = context.set_value(
                _LINKS,
                (
                    [
                        trace.Link(
                            sc,
                            {
                                "vibelens.relation": "trigger",
                                **(
                                    {"vibelens.source_build_id": source_build}
                                    if source_build
                                    else {}
                                ),
                            },
                        )
                    ]
                    if sc.is_valid
                    else []
                ),
                context.Context(),
            )
            # A link connects executions without manufacturing a parent call.
            if activation is not None:
                activation = SimpleNamespace(
                    bo_probe=self.probe,
                    bo_options=identity,
                    call_id=None,
                    entry_id=None,
                    bo_active=False,
                )
        ctx = context.set_value(_ACTIVATION, activation, ctx)
        return ctx

    @contextmanager
    def receive(self, carrier, *, trusted=False, link=False, strict=False):
        """Invalid telemetry is diagnosed; native work continues unless strict is requested."""
        try:
            ctx = self._receive_context(carrier, trusted=trusted, link=link, strict=strict)
        except (ValueError, TypeError):
            self.probe.bo_errors += 1
            self.probe.bo_last_error = {"stage": "trace_context", "type": "ValueError"}
            if strict:
                raise
            ctx = context.Context()
        token = context.attach(ctx)
        try:
            yield
        finally:
            context.detach(token)

    @contextmanager
    def linked(self, carriers):
        """Start a fan-in execution with several witnessed causes and explicit object roles."""
        if not isinstance(carriers, list) or not 1 <= len(carriers) <= 32:
            raise ValueError("linked execution requires 1 to 32 carriers")
        links = []
        for carrier in carriers:
            ctx = self.propagator.extract(carrier, context=context.Context())
            sc = trace.get_current_span(ctx).get_span_context()
            if not sc.is_valid:
                raise ValueError("linked execution lacks valid W3C context")
            links.append(trace.Link(sc, {"vibelens.relation": "trigger"}))
        token = context.attach(context.set_value(_LINKS, links, context.Context()))
        try:
            yield
        finally:
            context.detach(token)


class BOOpenTelemetryProcessor(SpanProcessor):
    """Bridge explicitly registered automatic spans into the same live event stream."""

    def __init__(self, backend, configuration):
        self.backend = backend
        self.items = validate_registrations(configuration, backend.probe.bo_project["model"])[
            "registrations"
        ]
        self.open = {}
        self.errors = self.ignored = self.suppressed = 0
        backend.processors.append(self)

    def on_start(self, span, parent_context=None):
        try:
            attributes = dict(span.attributes or {})
            if attributes.get("vibelens.node_id") or bo_is_internal():
                self.suppressed += 1
                return
            item = match_registration(self.items, span.name, attributes)
            if item is None:
                self.ignored += 1
                return
            backend, probe = self.backend, self.backend.probe
            if len(self.open) >= backend.limit:
                raise ValueError("automatic telemetry span limit reached")
            sc = span.get_span_context()
            identity = {
                "parent_call_id": None,
                "parent_event_id": None,
                **probe.bo_context_options({}, allow_ended=True),
            }
            key = (sc.trace_id, sc.span_id)
            call_id = format(sc.trace_id, "032x") + ":" + format(sc.span_id, "016x")
            entry = probe.record(
                item["node"],
                "enter",
                lambda: self.values(item, attributes),
                call_id=call_id,
                lifecycle="span",
                trace=bo_span_metadata(span, links=span.links),
                **identity,
            )
            activation = SimpleNamespace(
                bo_probe=probe, bo_options=identity, call_id=call_id, entry_id=entry, bo_active=True
            )
            with backend.lock:
                backend.automatic[key] = activation
                while len(backend.automatic) > backend.limit:
                    backend.automatic.popitem(last=False)
            self.open[key] = (
                item,
                identity,
                call_id,
                bo_span_metadata(span, links=span.links),
            )
        except Exception:
            self.errors += 1
            self.backend.probe.bo_errors += 1
            self.backend.probe.bo_last_error = {"stage": "tracing", "type": "Error"}

    @staticmethod
    def values(item, attributes):
        return {
            direction: {
                field: attributes[attr]
                for field, attr in item.get("capture", {}).get(short, {}).items()
                if attr in attributes
            }
            for direction, short in (("inputs", "in"), ("outputs", "out"))
        }

    def on_end(self, span):
        try:
            key = (span.context.trace_id, span.context.span_id)
            state = self.open.pop(key, None)
            if state is None:
                return
            item, identity, call_id, metadata = state
            self.backend.probe.record(
                item["node"],
                "return",
                lambda: {
                    **self.values(item, span.attributes or {}),
                    **self.exception_values(span.events),
                },
                call_id=call_id,
                lifecycle="span",
                trace=metadata,
                **identity,
            )
            with self.backend.lock:
                self.backend.automatic[key].bo_active = False
        except Exception:
            self.errors += 1
            self.backend.probe.bo_errors += 1
            self.backend.probe.bo_last_error = {"stage": "tracing", "type": "Error"}

    @staticmethod
    def exception_values(events):
        """Read legacy upstream events for compatibility; status is not exception evidence."""
        for event in reversed(events):
            value = (event.attributes or {}).get("exception.type")
            if event.name == "exception" and value:
                return {"exception": exception_metadata({"type": value})}
        return {}

    def shutdown(self):
        """Provider shutdown must not close or fabricate unfinished application work."""

    def force_flush(self, timeout_millis=30000):
        return self.backend.probe.flush(timeout_millis / 1000)
