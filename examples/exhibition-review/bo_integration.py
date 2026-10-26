"""VibeLens adapter. Domain methods never depend on transport or graph storage."""

from contextlib import contextmanager, nullcontext
import uuid

from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.data.runtime import BODataRuntime
from bo_observer.observation.observation_scope import bo_internal


class BOObservation:
    """Capture explicit values around native calls and actual SQL operations."""

    def __init__(self, session, engine, config):
        self.session, self.engine = session, engine
        self.errors, self.last_event = [], None
        self.attempt = "idle"
        self.parent = None

        def receive(value, kind):
            try:
                return session.event(value) if kind == "events" else session.snapshot(value)
            except Exception as error:
                self.errors.append(str(error))
                raise

        self.probe = BOProbe(session.project, session.manifest["build_id"], sink=receive)
        self.data = BODataRuntime(self.probe, config)
        self.data.attach_sqlalchemy(engine)

    def context(self):
        return {
            "attempt": self.attempt,
            "entity": "artwork:1",
            "scope": "application",
            "parent_call_id": self.parent,
        }

    def call(self, node, function, values):
        """Capture only declared fields; image bytes and arbitrary bodies are excluded."""
        call_id = uuid.uuid4().hex
        before = self.probe.record(
            node, "enter", lambda: {"inputs": values}, call_id=call_id, **self.context()
        )
        if node == "choose-version":
            result = self.data.transform(
                "version-selection",
                function,
                values["current_version"],
                before=lambda value: {"current_version": value},
                after=lambda value: {"selected": value},
                **self.context(),
            )
        else:
            result = function(**values)
        field = {"image-check": "valid", "review-policy": "verdict", "choose-version": "selected"}[
            node
        ]
        self.last_event = self.probe.record(
            node,
            "return",
            lambda: {"outputs": {field: result}},
            call_id=call_id,
            depends=[{"event": before, "type": "control"}],
            **self.context(),
        )
        return result

    def operation(self, node, parameters):
        return self.data.operation(node, parameters=parameters, **self.context())

    def transaction(self):
        # SQLAlchemy's native transaction remains the authority for commit/rollback.
        return self.data.transaction("review-transaction", nullcontext(), **self.context())

    @contextmanager
    def request(self, node, values):
        """Keep one request's probe identity stable across its nested native calls."""
        self.attempt, self.parent = uuid.uuid4().hex, uuid.uuid4().hex
        self.api_call = uuid.uuid4().hex
        self.probe.record(
            "api." + node,
            "enter",
            lambda: {"inputs": values},
            call_id=self.api_call,
            **{k: v for k, v in self.context().items() if k != "parent_call_id"},
        )
        self.probe.record(
            node,
            "enter",
            lambda: {"inputs": values},
            call_id=self.parent,
            parent_call_id=self.api_call,
            **{k: v for k, v in self.context().items() if k != "parent_call_id"},
        )
        yield

    def finish(self, node, result, repository, revision):
        """Read state independently, then associate it with the actual completion event."""
        # These queries describe a snapshot; they are not application operations.
        with bo_internal():
            row = repository.read_artwork()
            public = repository.public()
        context = {
            "image_version": row["image_version"],
            "reviewed_version": result.get("reviewed_version", 0),
            "published_version": public["published_version"] or 0,
        }
        event = self.probe.record(
            node,
            "return",
            lambda: {"outputs": result},
            call_id=self.parent,
            revision=revision,
            **{k: v for k, v in self.context().items() if k != "parent_call_id"},
        )
        self.probe.snapshot("artwork:1", row["status"], context, revision, event)
        self.probe.record(
            "api." + node,
            "return",
            lambda: {"outputs": result},
            call_id=self.api_call,
            **{k: v for k, v in self.context().items() if k != "parent_call_id"},
        )
        if not self.probe.flush(5) or self.errors or self.probe.bo_errors or self.data.bo_errors:
            raise RuntimeError(
                {
                    "observation_errors": self.errors,
                    "probe_errors": self.probe.bo_errors,
                    "data_errors": self.data.bo_errors,
                }
            )

    def close(self):
        self.probe.close()
        self.data.close()
