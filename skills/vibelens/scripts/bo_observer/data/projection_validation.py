"""Reuse pure projection validation during one database watcher's lifetime.

Collection, source reads, drift comparison and publication remain in sync.py.
This object remembers only the exact JSON value that passed the ordinary static
validators. Independent CLI checks do not use the memo.
"""

import json


def validate(candidate):
    """Apply the existing graph, data and project validators without changing them."""
    from ..protocol import validate_project
    from ..graph.behavior_model import validate_graph
    from .protocol import validate_data_projection

    is_project = candidate.get("protocol") in {"bo-project/v1", "bo-project/v2"}
    model = candidate["model"] if is_project else candidate
    validate_data_projection(model)
    validate_graph(model)
    if is_project:
        validate_project(candidate)


def json_bytes(value):
    """Preserve JSON type distinctions before using serialization as a cache key.

    Python tuples and non-string object keys can serialize like valid JSON values
    while failing the protocol. Never let such coercions reuse a valid receipt.
    """

    def portable(item):
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError("Projection object keys must be JSON strings")
            for child in item.values():
                portable(child)
        elif type(item) is list:
            for child in item:
                portable(child)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise ValueError("Projection contains a non-JSON value")

    portable(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")


class ProjectionValidation:
    """One-entry, process-local memo; a failed candidate never replaces success."""

    def __init__(self):
        self._validated = None

    def check(self, candidate):
        """Check each changed value and reuse only byte-identical validated JSON."""
        current = json_bytes(candidate)
        if current != self._validated:
            validate(candidate)
            self._validated = current
