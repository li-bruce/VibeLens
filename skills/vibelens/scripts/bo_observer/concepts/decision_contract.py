"""Meaning, authority and answer history for construction decisions.

Schema checks own the wire shape. This module checks references and provenance;
it neither authenticates a quotation nor executes a claimed evidence artifact.
"""

from pathlib import PurePosixPath

from .construction import affects_scope


def condition_state(decision, decisions):
    """Return active, waiting or inactive without deleting conditional answers."""
    waiting = False
    for condition in decision.get("routing", {}).get("when", []):
        upstream = decisions.get(condition["decision"], {})
        if upstream.get("status") != "resolved":
            waiting = True
            continue
        if upstream.get("resolution", {}).get("choice") is None:
            waiting = True
            continue
        if upstream.get("resolution", {}).get("choice") != condition["choice"]:
            return "inactive"
    return "waiting" if waiting else "active"


def due_at(decision, stage):
    """Keep future work recorded; analysis assumptions never gate native execution."""
    order = {
        "before_implementation": 0,
        "during_coding": 1,
        "before_acceptance": 2,
        "before_analysis": 3,
    }
    if stage not in order:
        raise ValueError("Unknown construction stage: " + stage)
    expected = decision.get("routing", {}).get("stage", "before_implementation")
    return order[expected] <= order[stage]


def has_unanswered_prompt(decision):
    """A partial reply permits a follow-up; silence leaves the sent prompt pending."""
    asked = decision.get("asked_in", [])
    return bool(asked) and not any(
        answer.get("reply_to") == asked[-1] for answer in decision.get("answers", [])
    )


def validate(document, concepts, previous=None):
    """Check routed work; role preferences affect wording, never authority.

    Existing V1/V2 decision checks remain in the caller. V3 routing is optional
    during migration; an unclassified decision becomes agent work, not assent.
    """
    if document.get("schema") != "business-discovery/v3":
        return []
    errors = []
    sources = {item["id"]: item for item in document["sources"]}
    decisions = {item["id"]: item for item in document["decisions"]}
    obligations = {item["id"] for item in document["construction"]["obligations"]}
    targets = concepts.get("construction", {}).get("targets", {})
    known = set(concepts["index"]) | set(targets)
    from .semantics import selection
    from .model import build

    data = build(document)

    def error(code, identity):
        errors.append({"code": code, "item": identity})

    def source_refs(refs, identity, kinds=None):
        if not refs or any(
            ref not in sources or (kinds and sources[ref]["kind"] not in kinds) for ref in refs
        ):
            error("routing_source", identity)

    preference = document.get("participation")
    if preference:
        source_refs(preference["source_refs"], "participation", {"user", "project_rule"})
    for identity, decision in decisions.items():
        route = decision.get("routing")
        if route is None:
            continue
        authority = route["authority"]
        source_refs(
            authority["source_refs"],
            identity,
            {
                "user": {"user"},
                "project_rule": {"project_rule"},
                "delegated": {"user", "project_rule"},
                "engineering": {"user", "project_rule", "assistant", "inference"},
            }[authority["kind"]],
        )
        if set(route["obligation_refs"]) - obligations - set(targets):
            error("unknown_modeling_obligation", identity)
        if set(authority["scope_refs"]) - known:
            error("unknown_authority_scope", identity)
        else:
            # Authority is granted for exact affected concepts or their declared
            # construction placement, never inferred from a respondent's title.
            canonical = [ref for ref in authority["scope_refs"] if ref not in targets]
            coverage = set(selection(data, canonical)) if canonical else set()
            if any(
                ref not in authority["scope_refs"]
                and (
                    (ref in targets and not targets[ref]["scope_refs"])
                    or not affects_scope(ref, concepts["index"], targets, coverage)
                )
                for ref in decision["affects"]
            ):
                error("authority_scope_mismatch", identity)
        if route["kind"] == "business_intent":
            if route["stage"] == "before_analysis":
                error("intent_cannot_wait_for_optional_analysis", identity)
            if authority["kind"] == "engineering" or (
                route["owner"] != "human" and authority["kind"] != "delegated"
            ):
                error("business_intent_authority", identity)
            if "conversation_answer" not in route["evidence_required"]:
                error("missing_intent_evidence", identity)
        if route["kind"] in {"implementation_fact", "verification_gap"}:
            if route["owner"] == "human":
                error("implementation_fact_is_agent_work", identity)
            if not set(route["evidence_required"]) - {"conversation_answer"}:
                error("missing_implementation_evidence", identity)
        if route["owner"] == "checker" and not route.get("checker"):
            error("missing_checker_identity", identity)
        for condition in route.get("when", []):
            upstream = decisions.get(condition["decision"], {})
            if condition["decision"] not in decision.get("depends_on", []) or condition[
                "choice"
            ] not in {v["id"] for v in upstream.get("options", [])}:
                error("invalid_question_condition", identity)
        answers = decision.get("answers", [])
        if len({a["id"] for a in answers}) != len(answers):
            error("duplicate_answer_fragment", identity)
        for answer in answers:
            source_refs(answer["source_refs"], identity, {"user", "project_rule"})
            if not set(answer["affects"]) <= set(decision["affects"]):
                error("answer_outside_question", identity)
            if answer.get("reply_to") and answer["reply_to"] not in decision.get("asked_in", []):
                error("answer_without_prompt", identity)
        if decision["status"] in {"partial", "contradicted"} and not answers:
            error("missing_answer_fragment", identity)
        resolution = decision.get("resolution", {})
        if decision["status"] != "resolved":
            continue
        if resolution.get("choice") and resolution["choice"] not in {
            v["id"] for v in decision.get("options", [])
        }:
            error("unknown_answer_choice", identity)
        if route["kind"] in {"implementation_fact", "verification_gap"}:
            if resolution.get("kind") not in {"source_observation", "checker_result"}:
                error("implementation_fact_needs_evidence", identity)
        if resolution.get("kind") in {"source_observation", "checker_result"}:
            if (
                route["kind"] not in {"implementation_fact", "verification_gap", "technical_choice"}
                or route["owner"] == "human"
            ):
                error("evidence_is_not_intent_confirmation", identity)
            evidence = resolution.get("evidence", [])
            if set(route["evidence_required"]) - {item["kind"] for item in evidence}:
                error("missing_resolution_evidence", identity)
            for item in evidence:
                path = PurePosixPath(item["path"])
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in item["path"]
                    or ":" in item["path"]
                ):
                    error("invalid_evidence_path", identity)
                if not set(decision["affects"]) <= set(item["scope_refs"]):
                    error("evidence_scope_mismatch", identity)
    if previous:
        old = {item["id"]: item for item in previous.get("decisions", [])}
        for identity, original in old.items():
            current = decisions.get(identity, {})
            original_answers = original.get("answers", [])
            if current.get("answers", [])[: len(original_answers)] != original_answers:
                error("answer_history_changed", identity)
            if original.get("routing") != current.get("routing"):
                # Changing wording is presentation-only. Ownership, semantics or
                # conditions changing require the existing exact history record.
                before = {k: v for k, v in original.get("routing", {}).items() if k != "wording"}
                after = {k: v for k, v in current.get("routing", {}).items() if k != "wording"}
                if (
                    before
                    and before != after
                    and not any(
                        c.get("decision") == identity and c.get("previous") == original
                        for c in document.get("changes", [])
                    )
                ):
                    error("routing_changed_without_history", identity)
        # New records can extend the inventory, but old source-backed obligations
        # cannot disappear simply because nobody wrote a question about them.
        old_obligations = {
            item["id"]: item for item in previous.get("construction", {}).get("obligations", [])
        }
        new_obligations = {item["id"]: item for item in document["construction"]["obligations"]}
        for identity, original in old_obligations.items():
            if new_obligations.get(identity) != original:
                change = next(
                    (
                        item
                        for item in document.get("changes", [])
                        if item.get("obligation") == identity and item.get("previous") == original
                    ),
                    None,
                )
                if (
                    not change
                    or not isinstance(change.get("reason"), str)
                    or not change["reason"].strip()
                ):
                    error("modeling_obligation_changed", identity)
                else:
                    source_refs(change.get("source_refs", []), identity, {"user", "project_rule"})
    return errors
