"""Send native evaluation steps through the existing bounded application probe."""


def record_evaluation(policy, evaluation, probe, *, entity, attempt, basis=None):
    """Retain actual values and causal links; never rerun predicates while recording.

    The caller owns the evaluation's business authority. A missing probe event is
    an observation gap and must be reported by verification, not repaired here.
    """
    emitted = {}
    for step in evaluation["trace"]:
        identity = step["node"]
        emitted[identity] = probe.record(
            "policy:" + identity,
            "decision",
            lambda step=step: {
                "inputs": {
                    "bo_check": evaluation["check_id"],
                    "bo_basis": evaluation["fact_revision"],
                    **step["arguments"],
                },
                "outputs": {"value": step["value"], "status": step["status"]},
            },
            entity=entity,
            attempt=attempt,
            scope="entity",
            basis=basis,
            call_id=evaluation["check_id"] + ":" + identity,
            depends=[
                {"event": emitted[ref], "type": "data"} for ref in step["used"] if emitted.get(ref)
            ],
        )
    return emitted
