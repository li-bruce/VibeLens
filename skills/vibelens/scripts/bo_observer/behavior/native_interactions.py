"""Check declared cross-model facts using existing causal references.

Equal payloads, timestamps and object names do not establish delivery or ownership.
These checks establish observation correspondence, not transaction atomicity,
delivery guarantees or the correctness of application permissions.
"""

from collections import defaultdict

from ..concepts.runtime import InvocationEvidence
from .domains import value_key
from .native_values import at, compare_values, matches
from .native_lineage import owning_entries


def boundary_errors(interaction, records, events):
    """Check one case's explicit boundary relations without guessing missing links.

    Records have already passed independent value comparison. A pending send or
    acquired resource may legitimately remain open; a receive/release needs its
    actual predecessor. Caller-defined cases decide whether progress was expected.
    """
    errors = []
    index = InvocationEvidence(events)
    by_role = defaultdict(list)
    for record in records:
        by_role[record["role"]].append(record)

    def reject(code, record):
        errors.append({"code": code, "event": record["event"]["id"]})

    def same(left, right, fields):
        return all(
            value_key(left["values"][name]) == value_key(right["values"][name]) for name in fields
        )

    def predecessors(record, role, fields):
        ancestors = index.upstream(record["event"]) - {record["event"]["id"]}
        return [
            other
            for other in by_role[role]
            if other["event"]["id"] in ancestors and same(other, record, fields)
        ]

    kind = interaction["kind"]
    if kind == "handoff":
        for receive in by_role["receive"]:
            if not predecessors(receive, "send", {"correlation", "payload"}):
                reject("handoff_send_unwitnessed", receive)
        for ack in by_role["acknowledge"]:
            if not predecessors(ack, "receive", {"correlation"}):
                reject("handoff_receive_unwitnessed", ack)
    elif kind == "resource":
        released = set()
        for release in by_role["release"]:
            parents = predecessors(release, "acquire", {"resource", "holder", "operation"})
            if len(parents) != 1 or parents[0]["event"]["id"] in released:
                reject("resource_owner_unwitnessed", release)
            else:
                released.add(parents[0]["event"]["id"])
    elif kind == "join":
        for joined in by_role["join"]:
            members = joined["values"]["members"]
            if (
                not isinstance(members, list)
                or not members
                or len({value_key(v) for v in members}) != len(members)
            ):
                reject("join_members_invalid", joined)
                continue
            arrivals = predecessors(joined, "arrive", {"correlation"})
            actual = [value_key(a["values"]["member"]) for a in arrivals]
            if len(actual) != len(set(actual)) or set(actual) != {value_key(v) for v in members}:
                reject("join_arrivals_unwitnessed", joined)
    elif kind == "transaction":
        for commit in by_role["commit"]:
            members = predecessors(commit, "member", {"transaction"})
            # The commit action can itself be a member at its final boundary.
            members += [
                m
                for m in by_role["member"]
                if m["event"]["id"] == commit["event"]["id"] and same(m, commit, {"transaction"})
            ]
            if {m["action"] for m in members} != set(interaction["member_actions"]):
                reject("transaction_members_unwitnessed", commit)
    elif kind == "shared_read" and interaction["consistency"] != "independent":
        consistency = interaction["consistency"]
        groups = defaultdict(list)
        for read in by_role["read"]:
            groups[value_key(read["values"]["group"])].append(read)
        for reads in groups.values():
            first = reads[0]
            if {r["action"] for r in reads} != set(interaction["reader_actions"]) or any(
                not same(first, r, {consistency, "value"}) for r in reads
            ):
                reject("joint_read_evidence_inconsistent", first)
            if consistency == "transaction":
                commits = [
                    c
                    for c in by_role["commit"]
                    if same(first, c, {"group", "transaction"})
                    and all(r["event"]["id"] in index.upstream(c["event"]) for r in reads)
                ]
                if len(commits) != 1:
                    reject("joint_read_commit_unwitnessed", first)
    return errors


def assess_interactions(contract, binding, runs, build_id):
    """Compare fields independently, then inspect their declared causal boundary."""
    actions = {a["id"]: a for a in contract["actions"]}
    errors, reports = [], []
    for interaction in contract.get("interactions", []):
        witnesses = binding["interactions"][interaction["id"]]["witnesses"]
        for case in sorted({case for w in witnesses for case in w["cases"]}):
            candidates = runs.get(case, [])
            if len(candidates) != 1:
                errors.append(
                    {
                        "code": "interaction_case_missing_or_duplicate",
                        "interaction": interaction["id"],
                        "case": case,
                    }
                )
                continue
            run = candidates[0]
            invocation_index = InvocationEvidence(run.get("events", []))
            records, current_errors = [], []
            for witness in witnesses:
                if case not in witness["cases"]:
                    continue
                owners = set(actions[witness["action"]]["model_refs"])
                passed = True
                for name, field in witness["fields"].items():
                    result = compare_values(run, field, build_id=build_id, owners=owners)
                    current_errors.extend(
                        {**error, "field": name, "role": witness["role"]}
                        for error in result["errors"]
                    )
                    passed = passed and result["valid"]
                if passed:
                    entry_site = binding["actions"][witness["action"]]["entry"]
                    entries = [
                        e
                        for e in run.get("events", [])
                        if matches(e, entry_site) and not e.get("context_only")
                    ]
                    for event in run.get("events", []):
                        if matches(event, witness["site"]) and not event.get("context_only"):
                            if len(owning_entries(invocation_index, entries, event)) != 1:
                                current_errors.append(
                                    {
                                        "code": "interaction_action_unowned",
                                        "event": event["id"],
                                        "action": witness["action"],
                                    }
                                )
                                continue
                            records.append(
                                {
                                    "role": witness["role"],
                                    "action": witness["action"],
                                    "event": event,
                                    "values": {
                                        name: at(event, field["observation"]["path"])
                                        for name, field in witness["fields"].items()
                                    },
                                }
                            )
            current_errors.extend(boundary_errors(interaction, records, run.get("events", [])))
            reports.append(
                {
                    "interaction": interaction["id"],
                    "case": case,
                    "witnesses": len(records),
                    "valid": not current_errors,
                }
            )
            errors.extend(
                {**error, "interaction": interaction["id"], "case": case}
                for error in current_errors
            )
    return {"valid": not errors, "errors": errors, "checks": reports}
