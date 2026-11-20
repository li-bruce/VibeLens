"""Recognize a new read witness of an already validated native state version.

Reading an unchanged state does not execute a transition or create a revision.
The session keeps that read's own frame while the state engine retains its
original transition evidence. Other same-version submissions use the engine's
existing conflict checks.
"""

from ..graph.behavior_model import digest


def matches_current_read(value, evidence, entry):
    """Require a read event, no transition claim and identical complete state.

    The caller has already validated the envelope, build, owner, model, instance
    and evidence revision. Partial/mismatched prior states cannot authorize this
    path. Canonical JSON comparison preserves bool/number and other type
    distinctions that Python equality would otherwise erase.
    """
    if not entry or entry.get("status") != "observed" or evidence["phase"] != "read":
        return False
    if (
        value["event"] is not None
        or value["guards"] not in (None, {})
        or value["payload"] not in (None, {})
    ):
        return False
    previous = entry["observed"]
    fields = ("state", "context", "configuration", "revision", "build_id")
    return digest({key: value[key] for key in fields}) == digest(
        {key: previous[key] for key in fields}
    )
