"""Verify intermediate captured snapshots through the live admission reducer.

Final storage projections and zero producer errors do not establish that the
collector accepts a sequence. Replay only submitted facts, in submitted order,
in a fresh in-memory observer for each enabled scenario. No files are written.
"""

from ..observation.snapshot_admission import admit_snapshot
from ..protocol import validate_event, validate_snapshot

try:
    from ...bo_stategraph import BOStateGraph, bo_digest
except ImportError:
    from bo_stategraph import BOStateGraph, bo_digest


def assess_snapshot_admission(project, build_id, payload, *, required=False):
    """Report capture admission separately from observed invalid business states.

    Canonical revision-bearing events require a snapshot when observation closure
    is required. Legacy event formats retain their existing validation paths;
    they are never reported as verified by this canonical-protocol check.
    Off/fault modes retain their independent native-effect/parity checks.
    """
    errors, state_errors, checks = [], [], []
    for run in payload.get("runs", []):
        if run.get("mode") != "on":
            continue
        case = run.get("case")
        snapshots = run.get("snapshots", [])
        if not isinstance(snapshots, list):
            errors.append({"case": case, "snapshot_admission": "snapshots must be an array"})
            continue
        events, needed = {}, set()
        for event in run.get("events", []):
            if event.get("protocol") != "bo-event/v1":
                continue
            ident = event.get("id")
            if ident in events and bo_digest(events[ident]) != bo_digest(event):
                errors.append(
                    {"case": case, "event": ident, "snapshot_admission": "event identity collision"}
                )
            events[ident] = event
            if type(event.get("revision")) is int:
                needed.add(ident)
        if not snapshots and not (required and needed):
            continue
        graph = BOStateGraph(project["model"], build_id=build_id, mode=project["selection"]["mode"])
        owners, seen, retained, cursors = {}, {}, set(), {}
        submitted = set()
        for position, raw in enumerate(snapshots):
            row = {
                "case": case,
                "position": position,
                "evidence_id": raw.get("evidence_id") if isinstance(raw, dict) else None,
            }
            try:
                value = validate_snapshot(raw, project, build_id)
                evidence_id = value["evidence_id"]
                submitted.add(evidence_id)
                if evidence_id not in seen:
                    if evidence_id not in events:
                        raise ValueError("snapshot lacks a matching recorded event")
                    seen[evidence_id] = validate_event(events[evidence_id], project, build_id)
                evidence = seen[evidence_id]
                producer = (evidence["run_id"], evidence["producer_id"])
                # Do not sort a bad sequence into a good one. Exact retried frames
                # remain legal; a new older state read cannot rewind the cursor.
                if evidence_id not in retained and evidence["seq"] <= cursors.get(producer, 0):
                    raise ValueError("snapshot evidence is out of producer order")
                result, _, _ = admit_snapshot(graph, value, evidence, owners, retained)
                row.update(
                    accepted=result["accepted"],
                    state_model_id=value.get("state_model_id"),
                    instance_id=value["instance_id"],
                    revision=value["revision"],
                )
                if not result["accepted"]:
                    errors.append({**row, "snapshot_admission": result["errors"]})
                else:
                    retained.add(evidence_id)
                    cursors[producer] = max(cursors.get(producer, 0), evidence["seq"])
                    if result.get("missing"):
                        errors.append({**row, "snapshot_incomplete": result["missing"]})
                    if result.get("errors"):
                        state_errors.append({**row, "observed_state_errors": result["errors"]})
            except (ValueError, TypeError, KeyError) as exc:
                row.update(accepted=False, error=str(exc))
                errors.append({**row, "snapshot_admission": str(exc)})
            checks.append(row)
        if required:
            errors.extend(
                {"case": case, "event": ident, "missing_state_snapshot": True}
                for ident in sorted(needed - submitted)
            )
    return {
        "valid": not errors,
        "required": required,
        "status": "checked" if checks or errors else "not_applicable",
        "checks": checks,
        "errors": errors,
        "state_errors": state_errors,
        "scope": "Canonical captured snapshot admission; transport and native value witnesses remain separate",
    }
