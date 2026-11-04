"""Project-local observation wiring; business functions remain usable without it."""

from contextvars import ContextVar
from functools import wraps
import inspect
import json
from pathlib import Path
import uuid

from flask import g, request
import service as native
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.policy.bindings import callable_binding
from bo_observer.policy.definition import fingerprint
from bo_observer.policy.recording import record_evaluation
from bo_observer.data.runtime import BODataRuntime
from bo_observer.adapters.python.bo_otel import BOOpenTelemetry
from opentelemetry.sdk.trace import TracerProvider

bo_facts = ContextVar("bo_current_facts", default={})
bo_predicates = ContextVar("bo_predicate_results", default=None)
bo_operation = ContextVar("bo_database_operation", default=None)


class BOConnection:
    """Observe real SQLite execute calls; leave fetching and commit behavior native."""

    def __init__(self, connection, runtime):
        self.bo_connection, self.bo_runtime = connection, runtime

    def execute(self, statement, parameters=()):
        node = bo_operation.get()
        if node is None:
            return self.bo_connection.execute(statement, parameters)
        return self.bo_runtime.execute(
            node,
            lambda: self.bo_connection.execute(statement, parameters),
            connection=self.bo_connection,
            statement=statement,
            language="sql",
        )

    def __enter__(self):
        self.bo_connection.__enter__()
        return self

    def __exit__(self, *args):
        return self.bo_connection.__exit__(*args)


class BOIntegration:
    """Capture witnessed native calls and final framework responses in one session."""

    def __init__(self, root, session, files, mode="on"):
        self.root = Path(root)
        self.session = session
        self.project = json.loads(
            (self.root / "bo_stategraph/project.json").read_text(encoding="utf-8")
        )
        self.transport_errors = []

        def receive(envelope, kind):
            try:
                return session.bo_sink(envelope, kind)
            except Exception as error:
                self.transport_errors.append(
                    {"kind": kind, "error": str(error), "envelope": envelope}
                )
                raise

        def unavailable(*args):
            raise ConnectionError("Deliberate observer outage in fault-mode acceptance")

        self.probe = BOProbe(
            self.project,
            session.manifest["build_id"],
            sink=unavailable if mode == "fault" else receive,
            enabled=mode != "off",
            capacity=4096,
        )
        self.provider = TracerProvider()
        self.probe.bo_bind_tracing(BOOpenTelemetry(self.provider.get_tracer("colleague-files")))
        self.data = BODataRuntime(
            self.probe,
            json.loads((self.root / "bo_stategraph/databases.json").read_text(encoding="utf-8")),
        )
        self.evaluations = []
        self.fact_reads = []
        self.bo_initialized = set()
        self.originals = {}
        self.policy = self.project["model"]["policy"]
        self.binding = callable_binding(
            native.same_identity, {"path": "service.py", "symbol": "same_identity"}, self.root
        )
        self.bo_wrap_predicates()
        connection = files.connect
        files.connect = lambda: BOConnection(connection(), self.data)
        for symbol, node in [
            ("upload", "upload"),
            ("share", "share"),
            ("revoke", "revoke"),
            ("download", "read"),
            ("received", "list"),
            ("facts", "facts"),
        ]:
            self.bo_wrap_method(files, symbol, node)
        session.bo_bind_capture(
            scope_setter=self.probe.bo_set_scope,
            flush_capture=lambda: self.probe.flush(30),
            health=lambda: {**self.probe.bo_health(), "data_errors": self.data.bo_errors},
        )

    def bo_wrap_predicates(self):
        """Translate actual native Boolean returns and visited predicate calls."""
        original = native.same_identity
        self.originals["same_identity"] = original

        @wraps(original)
        def predicate(left, right):
            result = original(left, right)
            observed = bo_predicates.get()
            if observed is not None:
                observed.append({"left": left, "right": right, "value": result})
            return result

        native.same_identity = predicate
        for symbol, operation in [("can_manage", "manage"), ("can_read", "read")]:
            function = getattr(native, symbol)
            self.originals[symbol] = function

            def observe(*args, bo_function=function, bo_operation=operation, **kwargs):
                token = bo_predicates.set([])
                try:
                    result = bo_function(*args, **kwargs)
                    visited = list(bo_predicates.get())
                finally:
                    bo_predicates.reset(token)
                # A source-bound adapter records the real returned value and
                # real predicate invocation, never calls a predicate again.
                facts = dict(bo_facts.get())
                try:
                    self.bo_policy_result(bo_operation, facts, visited, result)
                except Exception:
                    # A failed observer adapter must not authorize or reject the
                    # native operation. The acceptance gate reads this counter.
                    self.probe.bo_errors += 1
                return result

            setattr(native, symbol, wraps(function)(observe))

    def bo_policy_result(self, operation, facts, visited, result):
        """Preserve short-circuit evidence for the two registered native functions."""
        if len(visited) != 1:
            raise ValueError("Native permission adapter no longer matches its observed calls")
        target = "owner" if operation == "manage" else "recipient"
        predicate = "is_owner" if operation == "manage" else "is_recipient"
        trace = [
            dict(
                node=name, value=facts[name], status="completed", arguments={}, used=[], skipped=[]
            )
            for name in ["actor", target]
        ]
        trace.append(
            dict(
                node=predicate,
                value=visited[0]["value"],
                status="completed",
                arguments={"left": visited[0]["left"], "right": visited[0]["right"]},
                used=["actor", target],
                skipped=[],
            )
        )
        if operation == "read":
            used, skipped = [predicate], ["active"]
            if visited[0]["value"]:
                trace.append(
                    dict(
                        node="active",
                        value=facts["active"],
                        status="completed",
                        arguments={},
                        used=[],
                        skipped=[],
                    )
                )
                used.append("active")
                skipped = []
            trace.append(
                dict(
                    node="may_read",
                    value=result,
                    status="completed",
                    arguments={},
                    used=used,
                    skipped=skipped,
                )
            )
        root = predicate if operation == "manage" else "may_read"
        report = {
            "schema": "bo-policy-evaluation/v1",
            "policy_revision": self.policy["revision"],
            "policy_hash": fingerprint(self.policy),
            "check_id": uuid.uuid4().hex,
            "fact_revision": facts["file_id"] + ":" + str(facts["revision"]),
            "operation": operation,
            "inputs": {key: facts[key] for key in self.policy["inputs"]},
            "bindings": {"same_identity": self.binding},
            "root": root,
            "value": result,
            "decision": "allow" if result else "deny",
            "trace": trace,
            "diagnostics": [],
        }
        self.evaluations.append(report)
        record_evaluation(
            self.policy, report, self.probe, entity=facts["file_id"], attempt="request"
        )

    def bo_wrap_method(self, files, symbol, node):
        """Keep selected fields beside a real method's entry and exit boundaries."""
        original = getattr(files, symbol)
        signature = inspect.signature(original)

        @wraps(original)
        def observed(*args, **kwargs):
            arguments = signature.bind(*args, **kwargs).arguments
            selected = {
                key: value
                for key, value in arguments.items()
                if key in {"actor", "file_id", "recipient", "name"}
            }
            if "content" in arguments:
                selected["content_size"] = len(arguments["content"])
            entity = selected.get("file_id", "application")
            with self.probe.span(
                node, lambda: {"inputs": selected}, entity=entity, attempt="request", scope="entity"
            ) as span:
                token = bo_operation.set(
                    "db." + node if "db." + node in self.data.bo_operations else None
                )
                try:
                    value = original(*args, **kwargs)
                finally:
                    bo_operation.reset(token)
                result = value if isinstance(value, dict) else {"count": len(value)}
                span.result(lambda: {"outputs": result})
                if node == "facts":
                    bo_facts.set(dict(value))
                    self.fact_reads.append(dict(value))
                    identity = json.dumps(
                        [value["file_id"], value["recipient"]], separators=(",", ":")
                    )
                    if identity not in self.bo_initialized:
                        witness = self.probe.record(
                            "facts", "read", lambda: {"outputs": value}, revision=value["revision"]
                        )
                        queued = self.probe.snapshot(
                            identity,
                            "active" if value["active"] else "inactive",
                            {},
                            value["revision"],
                            witness,
                        )
                        # A focused scope can omit the evidence read. Retry the
                        # first actual state when capture includes this instance.
                        if queued:
                            self.bo_initialized.add(identity)
                if node in {"share", "revoke"}:
                    evidence = self.probe.record(
                        node,
                        "change",
                        lambda: {"inputs": {"event": node}, "outputs": value},
                        revision=value["revision"],
                    )
                    identity = json.dumps(
                        [value["file_id"], value["recipient"]], separators=(",", ":")
                    )
                    queued = self.probe.snapshot(
                        identity,
                        value["state"],
                        {},
                        value["revision"],
                        evidence,
                        event=node,
                        guards={"may_manage": True},
                        payload={"recipient_id": value["recipient"]},
                    )
                    # A selected post-state may be the first witnessed state.
                    # Keep that fact; never later claim a second initial snapshot.
                    if queued:
                        self.bo_initialized.add(identity)
                return value

        setattr(files, symbol, observed)

    def bo_bind_flask(self, app):
        """Close HTTP intervals after Flask has resolved normal and error responses."""

        @app.before_request
        def bo_request_start():
            if request.endpoint not in {
                "home",
                "upload",
                "share",
                "revoke",
                "received",
                "download",
            }:
                return
            token = bo_facts.set({})
            g.bo_facts_token = token
            manager = self.probe.span(
                "http." + request.endpoint,
                lambda: {
                    "inputs": {
                        "method": request.method,
                        "route": request.url_rule.rule,
                        **(request.view_args or {}),
                    }
                },
                entity="application",
                attempt=uuid.uuid4().hex,
                scope="application",
            )
            g.bo_manager = manager
            g.bo_activation = manager.__enter__()

        @app.after_request
        def bo_request_finish(response):
            if hasattr(g, "bo_manager"):
                status = response.status_code
                g.bo_activation.result(lambda: {"outputs": {"status": status}})
                g.bo_manager.__exit__(None, None, None)
                bo_facts.reset(g.bo_facts_token)
            return response

    def close(self):
        """Stop this trial's transport and restore process-local native functions."""
        self.probe.flush(30)
        self.probe.close()
        self.provider.shutdown()
        for name, function in self.originals.items():
            setattr(native, name, function)
