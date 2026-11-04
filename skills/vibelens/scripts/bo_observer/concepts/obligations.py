"""Cross-model semantics, feature applicability and independent expected outcomes."""

from .common import canonical_id as cid, fields, records, references, text, without_display

LINKS = {
    "action_requests_event": ({"action", "effect"}, {"event"}),
    "transition_guarded_by": ({"transition"}, {"rule_operation", "rule_expression"}),
    "decision_reads_fact": ({"rule_operation", "rule_expression"}, {"fact"}),
    "transition_has_effect": ({"transition"}, {"logical_effect"}),
}


def add_crosslinks(graph, doc, sources):
    """Reject conceptual references whose endpoint types or state guards differ."""
    resolve, relation = graph.resolve, graph.relation
    semantic, dependencies, index = graph.records, graph.dependencies, graph.index
    crosslinks = records(doc["crosslinks"], "crosslinks")
    for ident, link in crosslinks.items():
        fields(
            link,
            {"id", "from", "to", "relation", "argument", "label", "source_refs"},
            {"id", "from", "to", "relation", "source_refs"},
            "crosslink " + ident,
        )
        references(link, sources, "crosslink " + ident)
        a, b = resolve(link["from"]), resolve(link["to"])
        allowed = LINKS.get(link["relation"])
        if not allowed or index[a]["kind"] not in allowed[0] or index[b]["kind"] not in allowed[1]:
            raise ValueError("crosslink endpoint types differ: " + ident)
        if link["relation"] == "decision_reads_fact":
            left, right = semantic[a], semantic[b]
            if left.get("op") == "input" and left["input_type"] != right["type"]:
                raise ValueError("rule input and fact types differ: " + ident)
            dependencies[a].append(b)
        elif link["relation"] == "action_requests_event":
            dependencies[a].append(b)
        elif link["relation"] == "transition_guarded_by":
            guard_ids = [key for key in dependencies[a] if index[key]["kind"] == "guard"]
            if not any(semantic[key].get("decision") == b for key in guard_ids):
                raise ValueError("transition crosslink differs from its logical guard: " + ident)
            dependencies[a].append(b)
        elif link["relation"] == "transition_has_effect":
            if b not in dependencies[a]:
                raise ValueError("transition crosslink differs from its declared effects: " + ident)
        relation(
            ident,
            a,
            b,
            link["relation"],
            value={"argument": link["argument"]} if "argument" in link else {},
            label=link.get("label"),
            source_refs=link["source_refs"],
        )
    return crosslinks


def add_applicability(graph, doc, sources, business, models, policy, crosslinks):
    """Every operation explicitly changes, reads, or has no state/rule concern."""
    resolve, relation = graph.resolve, graph.relation
    semantic, dependencies, index = graph.records, graph.dependencies, graph.index
    applicability = {}
    for record in doc["applicability"]:
        operation = record.get("operation")
        if (
            operation not in business
            or business[operation]["kind"] not in {"action", "effect"}
            or operation in applicability
        ):
            raise ValueError("applicability needs one declared operation")
        references(record, sources, "applicability " + operation)
        for field, available, key in [
            ("state", models, "models"),
            ("rules", policy["operations"] if policy else {}, "operations"),
        ]:
            value = record.get(field)
            if not isinstance(value, dict) or value.get("status") not in {"applicable", "none"}:
                raise ValueError(
                    "operation needs explicit " + field + " applicability: " + operation
                )
            if value["status"] == "none":
                fields(value, {"status", "reason"}, {"status", "reason"}, "not applicable")
                if not text(value["reason"]):
                    raise ValueError("not applicable needs a reason")
            else:
                allowed_fields = {"status", key, "mode"} if field == "state" else {"status", key}
                fields(value, allowed_fields, allowed_fields, "applicability")
                if field == "state" and value["mode"] not in {"read", "change"}:
                    raise ValueError("state applicability needs read or change mode")
                ids = value.get(key)
                if (
                    not isinstance(ids, list)
                    or not ids
                    or len(set(ids)) != len(ids)
                    or any(x not in available for x in ids)
                ):
                    raise ValueError("applicability references missing " + key)
        applicability[operation] = record
        aid = cid("applicability", operation)
        deps = [operation]
        deps += [cid("state-model", m) for m in record["state"].get("models", [])]
        deps += [cid("policy-operation", op) for op in record["rules"].get("operations", [])]
        # Applicability changes an operation's meaning. Keep this dependency in
        # the semantic index as well as in the scope-selection obligations so a
        # shared rule edit reaches every previously confirmed consumer.
        dependencies[operation].extend(deps[1:])
        for mid in record["state"].get("models", []):
            relation(
                cid("operation-state", operation, mid),
                operation,
                cid("state-model", mid),
                "reads_state" if record["state"]["mode"] == "read" else "changes_state",
            )
        for op in record["rules"].get("operations", []):
            relation(
                cid("operation-rule", operation, op),
                operation,
                cid("policy-operation", op),
                "requires_decision",
            )
        # Applicability is an explicit semantic obligation, not a visual node.
        index[aid] = {"kind": "applicability", "aliases": [aid]}
        semantic[aid] = {"kind": "applicability", **without_display(record)}
        dependencies[aid] = deps
    if set(n for n, v in business.items() if v["kind"] == "action") - set(applicability):
        raise ValueError("missing explicit operation applicability")
    for link in crosslinks.values():
        if link["relation"] == "action_requests_event":
            operation = resolve(link["from"])
            if (
                operation not in applicability
                or applicability[operation]["state"].get("mode") != "change"
            ):
                raise ValueError("event request contradicts state applicability")
            declared_models = {
                cid("state-model", mid) for mid in applicability[operation]["state"]["models"]
            }
            event_models = set(dependencies[resolve(link["to"])])
            if not event_models.intersection(declared_models):
                raise ValueError("event request targets an undeclared state model: " + operation)
    for operation, item in applicability.items():
        if item["state"].get("mode") == "change" and not any(
            link["relation"] == "action_requests_event" and resolve(link["from"]) == operation
            for link in crosslinks.values()
        ):
            raise ValueError("state-changing operation lacks a typed event request: " + operation)


def add_expectations(graph, doc, sources):
    """Retain independent given/when/then assertions as semantic obligations."""
    resolve = graph.resolve
    semantic, dependencies, index = graph.records, graph.dependencies, graph.index
    for ident, expectation in records(doc["expectations"], "expectations").items():
        fields(
            expectation,
            {"id", "scope", "given", "when", "then", "source_refs", "label"},
            {"id", "scope", "given", "when", "then", "source_refs"},
            "expectation " + ident,
        )
        references(expectation, sources, "expectation " + ident)
        if (
            not isinstance(expectation["scope"], list)
            or not expectation["scope"]
            or not isinstance(expectation["then"], list)
            or not expectation["then"]
        ):
            raise ValueError("expectation needs scope and independent outcome")
        for assertion in expectation["then"]:
            fields(assertion, {"path", "equals"}, {"path", "equals"}, "expected assertion")
            if (
                not isinstance(assertion["path"], list)
                or not assertion["path"]
                or any(not text(p) and type(p) is not int for p in assertion["path"])
            ):
                raise ValueError("expected assertion needs an exact field path")
        refs = [resolve(x) for x in expectation["scope"]]
        eid = cid("expectation", ident)
        index[eid] = {"kind": "expectation", "aliases": [eid, ident]}
        semantic[eid] = {"kind": "expectation", **without_display({**expectation, "scope": refs})}
        dependencies[eid] = refs
