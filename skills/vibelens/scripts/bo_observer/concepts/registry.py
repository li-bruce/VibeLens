"""Typed concept registry shared by the independent peer-model projectors."""

from .common import canonical_id as cid, without_display

# Labels are presentation only. Stable relation names remain protocol identities.
RELATION_LABELS = {
    "contains": "Contains",
    "describes_fact": "Describes",
    "state_subject": "State of",
    "declares_event": "Event",
    "declares_guard": "Condition",
    "declares_effect": "Effect",
    "requests_transition": "Triggers",
    "guarded_by": "Requires",
    "has_effect": "Runs",
    "declares_target": "Enters",
    "guard": "Requires",
    "data": "Input",
    "decision_result": "Result",
    "guard_resolves_decision": "Evaluates",
    "action_requests_event": "Triggers",
    "transition_guarded_by": "Requires",
    "decision_reads_fact": "Reads",
    "transition_has_effect": "Runs",
    "reads_state": "Reads state",
    "changes_state": "Changes state",
    "requires_decision": "Requires",
    "resource": "Uses capacity",
    "join": "Completes",
    "enables_event": "Enables",
}


class ConceptGraph:
    """Keep unique identities, display nodes and semantic dependencies together."""

    def __init__(self):
        self.nodes, self.edges = [], []
        self.records, self.dependencies, self.index = {}, {}, {}

    def add(
        self,
        ident,
        kind,
        semantic_value,
        *,
        label=None,
        layer="design",
        aliases=(),
        deps=(),
        **display,
    ):
        if ident in self.index:
            raise ValueError("duplicate concept identity: " + ident)
        self.index[ident] = {"kind": kind, "aliases": sorted(set([ident, *aliases]))}
        self.records[ident] = {"kind": kind, **without_display(semantic_value)}
        self.dependencies[ident] = list(dict.fromkeys(deps))
        node_kind = (
            "state"
            if kind in {"state", "state_model"}
            else (
                "decision"
                if kind.startswith("rule_") or kind == "guard"
                else "data" if kind in {"object", "fact", "event", "logical_effect"} else "action"
            )
        )
        self.nodes.append(
            {
                "id": ident,
                "kind": node_kind,
                "label": label or ident,
                "summary": label or ident,
                "layer": layer,
                "concept_kind": kind,
                "concept_definition": without_display(semantic_value),
                "origin": "concept-design",
                "capture": {},
                **display,
            }
        )

    def relation(
        self, ident, source, target, kind, *, value=None, label=None, containment_kind=None
    ):
        """Retain semantic edge fields in the view, with protected graph identities.

        Guard polarity and transition event metadata are needed when a user
        confirms the diagram. They must not live only in the semantic snapshot.
        """
        if ident in self.index:
            raise ValueError("duplicate concept relation identity: " + ident)
        self.index[ident] = {"kind": "relation", "aliases": [ident]}
        self.records[ident] = {
            "kind": "relation",
            "from": source,
            "to": target,
            "relation": kind,
            **without_display(value or {}),
        }
        self.dependencies[ident] = [source, target]
        caption = label or RELATION_LABELS.get(kind, kind.replace("_", " ").capitalize())
        if not label and kind == "guarded_by" and isinstance((value or {}).get("negated"), bool):
            caption = "Requires false" if value["negated"] else "Requires true"
        self.edges.append(
            {
                **without_display(value or {}),
                "id": ident,
                "from": source,
                "to": target,
                "type": kind,
                "label": caption,
                "origin": "concept-design",
                "evidence_kind": "conceptual",
                # Renderer ancestry is derived from the already typed concepts;
                # adding this hint does not revise a confirmed semantic record.
                **({"containment_kind": containment_kind} if containment_kind else {}),
            }
        )

    def resolve(self, reference):
        """Resolve exact IDs first; aliases must have exactly one candidate."""
        if reference in self.index:
            return reference
        matches = [key for key, item in self.index.items() if reference in item["aliases"]]
        if len(matches) != 1:
            raise ValueError("unknown or ambiguous concept reference: " + str(reference))
        return matches[0]

    def resolve_dependencies(self):
        """Connect guards after all peer model identities have been registered."""
        for ident, item in list(self.records.items()):
            self.dependencies[ident] = [self.resolve(value) for value in self.dependencies[ident]]
            if item["kind"] == "guard" and item.get("decision"):
                target = self.resolve(item["decision"])
                if self.index[target]["kind"] not in {"rule_operation", "rule_expression"}:
                    raise ValueError("state guard must reference a Boolean decision")
                decision = self.records[target]
                if (
                    decision.get("op") in {"input", "constant"}
                    and decision.get("input_type", decision.get("type")) != "boolean"
                ):
                    raise ValueError("state guard must reference a Boolean decision")
                item["decision"] = target
                self.relation(
                    cid("guard-decision", ident), ident, target, "guard_resolves_decision"
                )

    def result(self, sources):
        """Export detached registry containers after checking every dependency."""
        if any(key not in self.index for values in self.dependencies.values() for key in values):
            raise ValueError("dangling conceptual dependency")
        roots = [
            node["id"]
            for node in self.nodes
            if node["concept_kind"] in {"business_network", "state_model", "rule_operation"}
        ]
        graph = {
            "nodes": self.nodes,
            "edges": self.edges,
            "graph_roots": roots,
            "machine": {"values": [], "transitions": [], "labels": {}},
        }
        return {
            "graph": graph,
            "index": self.index,
            "records": self.records,
            "dependencies": self.dependencies,
            "sources": sources,
        }
