"""Bounded JSON transport with an optional standard tracing backend."""

from contextvars import ContextVar
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import json
import math
import queue
import threading
import time
from urllib.request import Request, urlopen
import uuid

try:
    from ...observation.observation_scope import bo_internal, bo_is_internal
except ImportError:
    # This probe is also distributed as a standalone standard-library module.
    bo_internal = nullcontext

    def bo_is_internal():
        return False


_bo_internal = ContextVar("bo_transport_internal", default=False)


def bo_exception_metadata(value):
    """Keep this adapter usable as a standalone standard-library module."""
    if not isinstance(value, dict) or set(value) != {"type"}:
        raise ValueError("invalid exception metadata fields")
    name = value["type"]
    if (
        not isinstance(name, str)
        or not 0 < len(name) <= 256
        or any(not part.replace("$", "_").isidentifier() for part in name.split("."))
    ):
        raise ValueError("exception type must identify a code class")
    return {"type": name}


_bo_span = ContextVar("bo_activation_scope", default=None)
_bo_unset = object()


class BOActivation:
    """One witnessed operation; the enclosing context owns its real completion."""

    def __init__(self, probe, node, options):
        self.bo_probe, self.bo_node, self.bo_options = probe, node, options
        self.call_id = options["call_id"]
        self.entry_id = None
        self.bo_result = lambda: {}
        self.bo_active = True

    def result(self, builder):
        """Select completion values lazily; transport failures do not alter the result."""
        self.bo_result = builder

    def record(self, phase, builder):
        return self.bo_probe.record(self.bo_node, phase, builder, **self.bo_options)


def bo_selected(value, spec, depth=0):
    """Copy only declared fields, with bounded nesting, string length, arrays, and numbers."""
    if depth > 6:
        raise ValueError("capture depth exceeded")
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            raise ValueError("expected selected object")
        return {k: bo_selected(value[k], s, depth + 1) for k, s in spec.items() if k in value}
    if isinstance(spec, list):
        if not isinstance(value, list) or len(spec) != 1 or len(value) > 64:
            raise ValueError("bounded array required")
        return [bo_selected(v, spec[0], depth + 1) for v in value]
    if value is None:
        return None
    if (
        spec in ("number", "scalar")
        and type(value) in (int, float)
        and math.isfinite(value)
        and (type(value) is not int or abs(value) <= 9007199254740991)
    ):
        return value
    if spec in ("boolean", "scalar") and type(value) is bool:
        return value
    if spec in ("string", "scalar") and isinstance(value, str) and len(value) <= 256:
        return value
    raise ValueError("unapproved capture type")


class BOProbe:
    bo_boundary_events = True

    def bo_current_context(self, *, allow_ended=False):
        """Copy the active same-probe invocation identity for native adapters."""
        parent = self.bo_tracing.current() if self.bo_tracing else _bo_span.get()
        if (
            parent is None
            or parent.bo_probe is not self
            or (not parent.bo_active and not allow_ended)
        ):
            return {}
        return {
            **{
                key: value
                for key, value in parent.bo_options.items()
                if key in {"entity", "attempt", "scope", "basis", "provenance"}
            },
            "parent_call_id": parent.call_id,
            "parent_event_id": parent.entry_id,
        }

    def bo_context_options(self, identity, *, allow_ended=False):
        """Inherit causal context while keeping explicit application identities.

        An explicit parent override cannot retain the other half of an inherited
        reference. In particular, null parent_call_id starts an independent scope.
        """
        current = self.bo_current_context(allow_ended=allow_ended)
        if "parent_call_id" in identity and identity["parent_call_id"] != current.get(
            "parent_call_id"
        ):
            current.pop("parent_event_id", None)
        if "parent_event_id" in identity and identity["parent_event_id"] != current.get(
            "parent_event_id"
        ):
            current.pop("parent_call_id", None)
        return {**current, **identity}

    @contextmanager
    def bo_call_context(self, node, call_id, *, entry_id=None, **identity):
        """Scope a native adapter's already-recorded call without emitting extra events."""
        activation = BOActivation(self, node, {**identity, "call_id": call_id})
        activation.entry_id = entry_id
        with self.bo_activation_context(activation):
            yield

    @contextmanager
    def bo_activation_context(self, activation):
        """Use SDK task context when configured; retain the dependency-free backend."""
        token = _bo_span.set(activation) if self.bo_tracing is None else None
        try:
            with self.bo_tracing.activate(activation) if self.bo_tracing else nullcontext():
                yield
        finally:
            activation.bo_active = False
            if token is not None:
                _bo_span.reset(token)

    def bo_bind_tracing(self, backend):
        """Bind one observation backend without changing execution or global providers."""
        if self.bo_tracing is not None:
            raise ValueError("tracing backend already bound")
        backend.bind(self)
        self.bo_tracing = backend
        return backend

    @contextmanager
    def span(self, node, builder=lambda: {}, **options):
        """Witness entry through completion, including awaited children and exceptions.

        Use ``with`` in synchronous or asynchronous code. Nested spans inherit only
        this probe's invocation context. Detached tasks must own a separate span.
        """
        options = self.bo_context_options(options, allow_ended=True)
        options.setdefault("call_id", uuid.uuid4().hex)
        options.setdefault("parent_call_id", None)
        options.setdefault("parent_event_id", None)
        options["lifecycle"] = "span"
        activation = BOActivation(self, node, options)
        activation.entry_id = activation.record("enter", builder)
        with self.bo_activation_context(activation):
            try:
                yield activation
            except BaseException as error:
                error_name = type(error).__name__
                activation.record(
                    "error",
                    lambda: {
                        "outputs": {"error": error_name},
                        "exception": {"type": error_name},
                    },
                )
                raise
            else:
                activation.record("return", activation.bo_result)

    def __init__(
        self,
        project,
        build_id,
        *,
        endpoint="",
        token="",
        run_id=None,
        producer_id=None,
        enabled=True,
        capacity=256,
        timeout=0.5,
        sink=None,
    ):
        self.bo_project, self.bo_build = project, build_id
        self.bo_endpoint, self.bo_token, self.bo_timeout, self.bo_sink = (
            endpoint,
            token,
            timeout,
            sink,
        )
        self.bo_run, self.bo_producer = (
            run_id or uuid.uuid4().hex,
            producer_id or uuid.uuid4().hex,
        )
        self.bo_enabled = enabled
        self.bo_tracing = None
        self.bo_seq = self.bo_errors = self.bo_dropped = self.bo_suppressed = 0
        self.bo_filtered = 0
        self.bo_capture_nodes = None
        self.bo_last_error = None
        self.bo_queue = queue.Queue(maxsize=max(1, capacity))
        self.bo_lock = threading.Lock()
        self.bo_progress = threading.Condition()
        self.bo_submitted = self.bo_completed = 0
        self.bo_flush_target = 0
        self.bo_closed = threading.Event()
        self.bo_nodes = {n["id"]: n for n in project["model"]["nodes"]}
        excluded = project["model"].get("implementation", {}).get("excluded", {})
        self.bo_excluded = {
            n["id"]
            for n in project["model"]["nodes"]
            if n.get("source")
            and excluded.get(n["source"]["path"] + "::" + n["source"]["symbol"], {}).get("category")
            == "observer"
        }
        self.bo_worker = threading.Thread(
            target=self.bo_drain, daemon=True, name="bo-json-transport"
        )
        if enabled:
            self.bo_worker.start()

    def bo_base(self, protocol):
        return {
            "protocol": protocol,
            "project_id": self.bo_project["project_id"],
            "model_revision": self.bo_project["model"]["revision"],
            "build_id": self.bo_build,
            "run_id": self.bo_run,
            "producer_id": self.bo_producer,
        }

    def bo_set_scope(self, nodes):
        """Select temporary capture owners before evaluating their field builders.

        None restores full capture. Filtering does not consume a producer sequence
        number, so deliberately excluded events do not resemble transport loss.
        """
        if nodes is not None and (
            not isinstance(nodes, list)
            or any(not isinstance(node, str) or node not in self.bo_nodes for node in nodes)
        ):
            raise ValueError("capture scope requires known node IDs or None")
        with self.bo_lock:
            self.bo_capture_nodes = None if nodes is None else frozenset(nodes)

    def bo_health(self):
        """Expose transport/capture counters without reading application state."""
        with self.bo_lock:
            return {
                "enabled": self.bo_enabled and not self.bo_closed.is_set(),
                "boundary_context": True,
                "run_id": self.bo_run,
                "producer_id": self.bo_producer,
                "enqueued": self.bo_seq,
                "pending": self.bo_queue.unfinished_tasks,
                "queue_submitted": self.bo_submitted,
                "queue_completed": self.bo_completed,
                "flush_target": self.bo_flush_target,
                "errors": self.bo_errors,
                "dropped": self.bo_dropped,
                "filtered": self.bo_filtered,
                "last_error": dict(self.bo_last_error) if self.bo_last_error else None,
                **({"tracing": self.bo_tracing.health()} if self.bo_tracing else {}),
            }

    def bo_put(self, kind, body):
        raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > 24576:
            raise ValueError("observation too large")
        with self.bo_progress:
            self.bo_queue.put_nowait((kind, raw))
            self.bo_submitted += 1
        return True

    def record(
        self,
        node,
        phase,
        builder,
        *,
        entity=_bo_unset,
        attempt=_bo_unset,
        scope=_bo_unset,
        basis=_bo_unset,
        call_id=None,
        parent_call_id=_bo_unset,
        parent_event_id=_bo_unset,
        depends=(),
        revision=None,
        lifecycle=None,
        bo_boundary=None,
        trace=None,
        provenance=_bo_unset,
    ):
        """Build and enqueue a selected observation without changing the business result.

        Suppress observer activity and recursive capture. Count failures locally and
        return None when an observation cannot be queued.
        """
        if not self.bo_enabled or self.bo_closed.is_set():
            return None
        if _bo_internal.get() or bo_is_internal() or node in self.bo_excluded:
            self.bo_suppressed += 1
            return None
        boundary = (
            bo_boundary
            if bo_boundary is not None
            else (
                {"enter": "start", "return": "end", "error": "end"}.get(phase)
                if lifecycle == "span"
                else None
            )
        )
        with self.bo_lock:
            filtered = self.bo_capture_nodes is not None and node not in self.bo_capture_nodes
            if filtered:
                self.bo_filtered += 1
                if boundary not in ("start", "end"):
                    return None
        token = _bo_internal.set(True)
        try:
            if phase not in {
                "enter",
                "return",
                "read",
                "decision",
                "wait",
                "commit",
                "change",
                "error",
            }:
                raise ValueError("invalid phase")
            identity = self.bo_context_options(
                {
                    key: value
                    for key, value in {
                        "entity": entity,
                        "attempt": attempt,
                        "scope": scope,
                        "basis": basis,
                        "parent_call_id": parent_call_id,
                        "parent_event_id": parent_event_id,
                        "provenance": provenance,
                    }.items()
                    if value is not _bo_unset
                },
                allow_ended=boundary == "start",
            )
            entity = identity.get("entity", "application")
            attempt = identity.get("attempt", "application")
            scope = identity.get("scope", "application")
            basis = identity.get("basis")
            parent_call_id = identity.get("parent_call_id")
            parent_event_id = identity.get("parent_event_id")
            provenance = identity.get("provenance")
            spec = self.bo_nodes[node].get("capture", {})
            values = {} if filtered else builder()
            # Identity and generated object references may become known only at
            # completion. A selected builder supplies facts for this event only.
            provenance = values.get("provenance", provenance)
            exception = values.get("exception")
            if "exception" in values and exception is None:
                raise ValueError("exception metadata must identify an observed class")
            if bo_boundary not in (None, "start", "end"):
                raise ValueError("invalid physical context boundary")
            if lifecycle not in (None, "span"):
                raise ValueError("invalid lifecycle boundary mode")
            if self.bo_tracing and trace is None:
                trace = self.bo_tracing.observe(node, phase, call_id, boundary)
            if trace is not None or provenance is not None:
                from ...observation.provenance import trace_metadata, object_metadata

                trace = trace_metadata(trace) if trace is not None else None
                provenance = object_metadata(provenance) if provenance is not None else None
            exception = bo_exception_metadata(exception) if exception is not None else None
            if exception is not None and self.bo_tracing:
                callback = getattr(self.bo_tracing, "exception", None)
                if callback:
                    callback(call_id, exception)
            with self.bo_lock:
                self.bo_seq += 1
                eid = f"{self.bo_run}:{self.bo_producer}:{self.bo_seq}"
                body = {
                    **self.bo_base("bo-event/v1"),
                    "schema_version": 3,
                    "seq": self.bo_seq,
                    "id": eid,
                    "node": node,
                    "phase": phase,
                    "entity": entity,
                    "attempt": attempt,
                    "scope": scope,
                    "basis": bo_selected(
                        basis or {},
                        {
                            "param_version": "number",
                            "epoch": "number",
                            "clock": "number",
                        },
                    ),
                    "call_id": call_id or eid,
                    "parent_call_id": parent_call_id,
                    "parent_event_id": parent_event_id,
                    "inputs": bo_selected(values.get("inputs", {}), spec.get("in", {})),
                    "outputs": bo_selected(values.get("outputs", {}), spec.get("out", {})),
                    "depends": list(depends),
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                }
                if revision is not None:
                    if type(revision) is not int or not 0 <= revision <= 9007199254740991:
                        raise ValueError("invalid state revision")
                    body["revision"] = revision
                if lifecycle is not None:
                    body["lifecycle"] = lifecycle
                if trace is not None:
                    body["trace"] = trace
                if provenance is not None and not filtered:
                    body["provenance"] = provenance
                if exception is not None and not filtered:
                    body["exception"] = exception
                if filtered:
                    body.update(
                        context_only=True,
                        context_boundary=boundary,
                        inputs={},
                        outputs={},
                        depends=[],
                        basis={},
                    )
                    body.pop("revision", None)
                self.bo_put("events", body)
            return eid
        except queue.Full:
            self.bo_dropped += 1
            self.bo_last_error = {"stage": "queue", "type": "Full"}
        except Exception as error:
            self.bo_errors += 1
            self.bo_last_error = {
                "stage": "capture",
                "type": type(error).__name__,
                "node": (node[:160] if isinstance(node, str) and node in self.bo_nodes else None),
                "phase": (
                    phase
                    if isinstance(phase, str)
                    and phase
                    in {
                        "enter",
                        "return",
                        "read",
                        "decision",
                        "wait",
                        "commit",
                        "change",
                        "error",
                    }
                    else None
                ),
            }
        finally:
            if self.bo_tracing:
                try:
                    self.bo_tracing.complete(call_id, phase, boundary)
                except Exception:
                    self.bo_errors += 1
                    self.bo_last_error = {"stage": "tracing", "type": "Error"}
            _bo_internal.reset(token)
        return None

    def snapshot(
        self,
        instance_id,
        state,
        context,
        revision,
        evidence_id,
        *,
        event=None,
        guards=None,
        payload=None,
        configuration=None,
    ):
        """Queue a snapshot only when its source event was captured.

        ``record`` returns None for deliberately filtered events and capture
        failures. Neither supplies evidence for a snapshot. Existing capture
        errors remain in health; an omitted event is never replaced or invented.
        Non-null evidence still passes through the collector's strict validator.
        """
        if not self.bo_enabled or self.bo_closed.is_set():
            return False
        if evidence_id is None:
            return False
        if _bo_internal.get() or bo_is_internal():
            self.bo_suppressed += 1
            return False
        try:
            return self.bo_put(
                "snapshots",
                {
                    **self.bo_base("bo-snapshot/v1"),
                    "instance_id": instance_id,
                    "state": state,
                    "context": context,
                    "revision": revision,
                    "evidence_id": evidence_id,
                    "event": event,
                    "guards": guards,
                    "payload": payload,
                    "configuration": configuration,
                },
            )
        except queue.Full:
            self.bo_dropped += 1
        except Exception as error:
            self.bo_errors += 1
            self.bo_last_error = {"stage": "snapshot", "type": type(error).__name__}
        return False

    def bo_send_one(self, kind, raw):
        """Deliver an original envelope through the existing local or HTTP contract."""
        if self.bo_sink:
            return self.bo_sink(json.loads(raw), kind)
        req = Request(
            self.bo_endpoint + "/api/bo/" + kind,
            data=raw,
            headers={"Content-Type": "application/json", "X-BO-Token": self.bo_token},
            method="POST",
        )
        with urlopen(req, timeout=self.bo_timeout) as response:
            response.read(32768)

    def bo_transport_error(self, error):
        self.bo_errors += 1
        self.bo_last_error = {"stage": "transport", "type": type(error).__name__}

    def bo_drain(self):
        """Drain bounded event groups; snapshots remain ordered completion barriers.

        Only explicitly batch-capable local sinks opt in. HTTP and plain callable
        sinks retain their single-envelope contract. Failed batch preflight falls
        back to the original envelopes, preserving per-message error isolation.
        """
        deferred = None
        while deferred is not None or not self.bo_closed.is_set() or not self.bo_queue.empty():
            if deferred is not None:
                kind, raw = deferred
                deferred = None
            else:
                try:
                    kind, raw = self.bo_queue.get(timeout=0.05)
                except queue.Empty:
                    continue
            batch = [raw]
            token = _bo_internal.set(True)
            try:
                with (
                    bo_internal(),
                    self.bo_tracing.internal() if self.bo_tracing else nullcontext(),
                ):
                    try:
                        accept_many = getattr(self.bo_sink, "bo_accept_many", None)
                    except Exception:
                        accept_many = None  # An optional capability cannot break a plain sink.
                    if kind == "events" and callable(accept_many):
                        # Amortize the sink's strict pre/post source checks over
                        # its existing 64-event contract during a real backlog.
                        # Ordinary traffic keeps the smaller low-latency group.
                        batch_limit = 64 if self.bo_queue.qsize() >= 64 else 16
                        while len(batch) < batch_limit:
                            try:
                                following = self.bo_queue.get_nowait()
                            except queue.Empty:
                                break
                            if following[0] != "events":
                                deferred = following
                                break
                            batch.append(following[1])
                    if len(batch) > 1:
                        try:
                            receipts = accept_many([json.loads(value) for value in batch])
                            if (
                                not isinstance(receipts, list)
                                or len(receipts) != len(batch)
                                or any(
                                    not isinstance(receipt, dict)
                                    or receipt.get("accepted") is not True
                                    for receipt in receipts
                                )
                            ):
                                raise ValueError("event batch lacks acceptance receipts")
                        except Exception:
                            for value in batch:
                                try:
                                    self.bo_send_one(kind, value)
                                except Exception as error:
                                    self.bo_transport_error(error)
                    else:
                        self.bo_send_one(kind, raw)
            except Exception as error:
                self.bo_transport_error(error)
            finally:
                _bo_internal.reset(token)
                for _ in batch:
                    self.bo_queue.task_done()
                with self.bo_progress:
                    self.bo_completed += len(batch)
                    self.bo_progress.notify_all()

    def flush(self, timeout=2):
        """Settle the accepted queue prefix; later business work cannot move this goal.

        Snapshot envelopes count too. Errors/loss still remain in producer health,
        and the original deadline still bounds a genuinely slow or stalled sink.
        """
        deadline = time.monotonic() + timeout
        with self.bo_progress:
            target = self.bo_submitted
            self.bo_flush_target = target
            while self.bo_completed < target:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self.bo_progress.wait(remaining)
            return True

    def close(self):
        """Request worker shutdown and bound the time spent joining it."""
        self.bo_closed.set()
        if self.bo_enabled:
            self.bo_worker.join(1)
