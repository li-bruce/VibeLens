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
            staged.history = []
            # _accept_event changes only these maps, sequence/gap counters and
            # history. Copied counters are integers; no graph snapshot is applied.
            for value in values:
                staged._accept_event(value)
            if session.binding()["status"] != "current":
                raise ValueError("source or declaration changed during event admission")
            return [session._accept_event(value) for value in values]
