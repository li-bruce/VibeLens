"""A bounded local sink that validates event groups before publishing their facts."""

from copy import copy

from ..protocol import validate_event


class BOSessionSink:
    """Keep the ordinary two-argument sink and offer optional event-only batching.

    Snapshots stay ordered barriers and use the normal snapshot validator. Every
    event retains its producer identity, fields and receipt; batching changes only
    the admission transaction, never the captured program behavior.
    """

    def __init__(self, session):
        self.session = session

    def __call__(self, value, kind):
        if kind == "events":
            return self.session.event(value)
        if kind == "snapshots":
            return self.session.snapshot(value)
        raise ValueError("unknown observation envelope kind")

    def bo_accept_many(self, events):
        """Preflight every event and both source boundaries before publishing any.

        The staged cursor owns separate producer/identity maps and an in-memory
        publication list. It runs the same acceptance rules as single events.
        Nothing reaches the live history or recording listener during preflight.
        """
        if not isinstance(events, list) or not 1 <= len(events) <= 64:
            raise ValueError("event batch requires 1 to 64 envelopes")
        session = self.session
        values = [
            validate_event(event, session.project, session.manifest["build_id"]) for event in events
        ]
        with session.lock:
            if session.binding()["status"] != "current":
                raise ValueError("source or declaration changed; reload after verification")
            staged = copy(session)
            staged.seen = session.seen.copy()
            staged.producers = session.producers.copy()
            staged.bo_open_invocations = session.bo_open_invocations.copy()
            staged.history = []
            # _accept_event changes only these maps, scalar counters and
            # history. Copied counters are integers; no graph snapshot is applied.
            receipts = [staged._accept_event(value) for value in values]
            if session.binding()["status"] != "current":
                raise ValueError("source or declaration changed during event admission")
            # Preflight already ran the exact single-event reducer. Publish its
            # detached cursor once, rather than recomputing signatures and call
            # ownership for every event a second time. No mutation precedes the
            # second source-byte check. Duplicate receipts publish no event.
            for name in (
                "seen",
                "producers",
                "bo_open_invocations",
                "bo_context_evictions",
                "sequence",
                "gaps",
            ):
                setattr(session, name, getattr(staged, name))
            session.history.append_many(staged.history)
            return receipts
