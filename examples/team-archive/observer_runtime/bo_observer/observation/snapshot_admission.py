"""Shared state-snapshot admission for live capture and independent verification.

This reducer observes native facts; it never executes application transitions.
The caller validates the envelope/build and serializes access to these cursors.
"""

from .snapshot_reads import matches_current_read

try:
    from ...bo_models import instance_key
except ImportError:
    from bo_models import instance_key


def admit_snapshot(graph, value, evidence, owners, retained):
    """Check identity/version ownership and observe one complete native snapshot.

    Return the receipt, qualified instance and preceding native state. Successful
    admission reserves the evidence/owner; frame retention remains the caller's
    responsibility. ``retained`` contains evidence IDs already stored as frames.
    """
    if not evidence or (evidence["run_id"], evidence["producer_id"]) != (
        value["run_id"],
        value["producer_id"],
    ):
        raise ValueError("snapshot lacks a matching recorded event")
    if evidence.get("revision") != value["revision"]:
        raise ValueError("snapshot needs the same explicit state revision as its event")
    model_id = value.get("state_model_id")
    ident = instance_key(value["run_id"], value["instance_id"], model_id)
    owner = value["producer_id"]
    if ident in owners and owners[ident] != owner:
        raise ValueError("instance already has another authoritative producer")
    if ident not in owners and len(owners) >= 1024:
        raise ValueError("instance limit reached")
    if evidence.get("snapshot_instance") not in (None, ident):
        raise ValueError("event already belongs to another instance snapshot")
    previous_entry = next(
        (item for item in graph.bo_instances() if item["observed"]["instance_id"] == ident),
        None,
    )
    previous = previous_entry["observed"] if previous_entry else None
    if matches_current_read(value, evidence, previous_entry):
        result = {
            "accepted": True,
            "duplicate": value["evidence_id"] in retained,
            "observation": "read",
            "errors": [],
        }
    else:
        result = graph.bo_observe(
            ident,
            **({"state_model_id": model_id} if model_id is not None else {}),
            **{
                key: value[key]
                for key in (
                    "state",
                    "context",
                    "revision",
                    "evidence_id",
                    "build_id",
                    "configuration",
                    "event",
                    "guards",
                    "payload",
                )
            },
        )
    if result["accepted"]:
        owners[ident] = owner
        evidence["snapshot_instance"] = ident
    return result, ident, previous
