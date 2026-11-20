"""Export captured protocol facts for verification without replaying business code.

The recorder assigns receipt sequences for animation. Native verification needs
the producer sequences and the original submitted snapshots instead. This bridge
reverses only that documented envelope change; it never infers historical state
from display frames, current storage, or the final checkpoint.
"""

from copy import deepcopy

from ..protocol import validate_event, validate_snapshot


def native_event(event, project, build_id, *, stream_id):
    """Validate a detached native envelope; reject unknown recorder metadata."""
    value = deepcopy(event)
    if "source_seq" in value or "stream_id" in value:
        if (
            value.get("stream_id") != stream_id
            or not isinstance(stream_id, str)
            or not stream_id
            or type(value.get("source_seq")) is not int
            or value["source_seq"] < 1
            or type(value.get("seq")) is not int
            or value["seq"] < 1
        ):
            raise ValueError("recorded event has invalid stream or sequence identity")
        value["seq"] = value.pop("source_seq")
        value.pop("stream_id")
    return validate_event(value, project, build_id)


def frame_snapshot(frame, event, project, build_id):
    """Read an original snapshot only when all event/frame identities agree."""
    value = validate_snapshot(frame["native_snapshot"], project, build_id)
    if (
        type(frame.get("snapshot_seq")) is not int
        or frame["snapshot_seq"] < 1
        or frame.get("event_id") != event["id"]
        or frame.get("run_id") != event["run_id"]
        or frame.get("build_id") != build_id
        or frame.get("revision") != event.get("revision")
        or value["evidence_id"] != event["id"]
        or value["run_id"] != event["run_id"]
        or value["producer_id"] != event["producer_id"]
        or value["revision"] != event.get("revision")
    ):
        raise ValueError("recorded native snapshot identity differs from its event")
    return value


def export_evidence(recording, project, build_id):
    """Return evidence fields for one on-mode run, retaining missing facts as gaps.

    Callers add independently observed native outcomes and actual policy reports.
    This export is not an acceptance result. Missing old snapshot envelopes stay
    missing and fail the existing snapshot gate; they cannot be reconstructed.
    The input recording and all event IDs, values and times remain unchanged.
    """
    if (
        recording.get("schema") != "stategraph-recording/v1"
        or recording.get("status") != "stopped"
        or recording.get("build_id") != build_id
        or recording.get("context", {}).get("manifest", {}).get("build_id") != build_id
        or recording.get("gaps") != []
        or recording.get("producer_settlement", {}).get("flushed") is not True
    ):
        raise ValueError("evidence export requires a settled recording of the current build")
    events = [
        native_event(event, project, build_id, stream_id=recording["run_id"])
        for event in recording["events"]
    ]
    by_id = {event["id"]: event for event in events}
    if len(by_id) != len(events):
        raise ValueError("recording contains duplicate event identities")
    snapshots, orders, seen = [], set(), set()
    for frame in recording.get("runtime_frames", {}).get("frames", []):
        if "native_snapshot" not in frame:
            continue  # Legacy display frames cannot substitute for native evidence.
        event = by_id.get(frame.get("event_id"))
        if event is None:
            raise ValueError("native snapshot has no event inside this recording")
        snapshot = frame_snapshot(frame, event, project, build_id)
        order = frame["snapshot_seq"]
        if order in orders or event["id"] in seen:
            raise ValueError("duplicate snapshot receipt or event identity")
        orders.add(order)
        seen.add(event["id"])
        snapshots.append((order, snapshot))
    # Frames are arranged by event for playback. Restore the separate recorded
    # snapshot-receipt order, never sort by state revision or producer time.
    snapshots.sort(key=lambda pair: pair[0])
    return {
        "events": events,
        "snapshots": [snapshot for _, snapshot in snapshots],
        "probe_health": deepcopy(recording["final"]["health"].get("producer", {})),
        "recording_id": recording["id"],
    }
