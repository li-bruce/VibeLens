"""Transactional construction-time insertion; direct facts are never rerouted."""

from copy import deepcopy

from ...protocol import schema_check
from .contract import (
    Rules,
    DEFAULT_LIMITS,
    context_key,
    definition_key,
    digest,
    encoded,
    independent,
)
from .paths import Budget, SearchLimit, adjacency, leaf_path, path, reachable


class RelationIndex:
    """Keep every registration ID while admitting a nonredundant edge structure.

    Mutations compile a detached candidate before committing. This also revisits
    earlier summaries when a new path arrives, or restores them when a path breaks.
    Neither rendering nor runtime event collection participates in this decision.
    """

    def __init__(self, nodes, rules=None, *, limits=None):
        self._nodes = self._node_ids(nodes)
        self._rules = Rules(rules)
        if limits is not None and not isinstance(limits, dict):
            raise ValueError("Expected relation search limits object")
        self._limits = {**DEFAULT_LIMITS, **(limits or {})}
        if set(self._limits) != set(DEFAULT_LIMITS) or any(
            type(v) is not int or not 0 <= v <= 10_000_000 for v in self._limits.values()
        ):
            raise ValueError("Invalid relation search limits")
        self._entries = {}
        self._decisions = {}
        self._active = set()
        self._revision = self._version(self._entries, self._nodes)

    @staticmethod
    def _node_ids(nodes):
        values = list(nodes)
        if any(not isinstance(node, str) or not node.strip() for node in values) or len(
            set(values)
        ) != len(values):
            raise ValueError("Relation nodes need unique nonempty IDs")
        return frozenset(values)

    def _version(self, entries, nodes):
        return digest(
            {
                "nodes": sorted(nodes),
                "rules": self._rules.value,
                "entries": list(entries.values()),
                "limits": self._limits,
            }
        )

    @property
    def revision(self):
        return self._revision

    @property
    def edges(self):
        return deepcopy(
            [entry["edge"] for key, entry in self._entries.items() if key in self._active]
        )

    def decision(self, ident):
        if ident not in self._decisions:
            raise ValueError("Unknown relation ID: " + ident)
        return deepcopy(self._decisions[ident])

    def insert(self, entry, *, expected_revision=None):
        return self.apply([{"op": "insert", "entry": entry}], expected_revision=expected_revision)

    def update(self, ident, entry, *, expected_revision=None):
        return self.apply(
            [{"op": "update", "id": ident, "entry": entry}], expected_revision=expected_revision
        )

    def remove(self, ident, *, expected_revision=None):
        return self.apply([{"op": "remove", "id": ident}], expected_revision=expected_revision)

    def apply(self, operations, *, nodes=None, expected_revision=None):
        """Apply one all-or-nothing batch, optionally changing its node inventory."""
        if expected_revision is not None and expected_revision != self._revision:
            raise ValueError("Relation revision conflict")
        candidate_nodes = self._nodes if nodes is None else self._node_ids(nodes)
        candidate = dict(self._entries)
        actions = []
        if not isinstance(operations, list):
            raise ValueError("Expected a list of relation operations")
        for operation in operations:
            if not isinstance(operation, dict):
                raise ValueError("Expected a relation operation object")
            kind = operation.get("op")
            fields = (
                {"op", "entry"}
                if kind == "insert"
                else {"op", "id", "entry"} if kind == "update" else {"op", "id"}
            )
            if kind not in {"insert", "update", "remove"} or set(operation) != fields:
                raise ValueError("Invalid relation operation")
            if kind == "remove":
                ident = operation["id"]
                if not isinstance(ident, str) or ident not in candidate:
                    raise ValueError("Cannot remove an unknown relation")
                del candidate[ident]
                actions.append({"edge_id": ident, "action": "removed"})
                continue
            item = self._rules.entry(operation["entry"], candidate_nodes)
            ident = item["edge"]["id"]
            if kind == "update":
                if operation["id"] != ident or ident not in candidate:
                    raise ValueError("Update requires an existing, unchanged edge ID")
            elif ident in candidate:
                if encoded(candidate[ident]) != encoded(item):
                    raise ValueError("Conflicting relation ID; use update: " + ident)
                actions.append({"edge_id": ident, "action": "idempotent"})
                continue
            candidate[ident] = item
            actions.append(
                {"edge_id": ident, "action": "updated" if kind == "update" else "inserted"}
            )
        for entry in candidate.values():
            if {entry["edge"]["from"], entry["edge"]["to"]} - candidate_nodes:
                raise ValueError("Node removal would leave a dangling relation")
        if len(candidate) > 100_000:
            raise ValueError("Relation registry exceeds its portable entry limit")
        decisions, active = self._compile(candidate)
        restored = sorted((active - self._active) & set(self._entries))
        represented = sorted(
            key
            for key in self._active - active
            if key in candidate and decisions[key]["status"] == "represented"
        )
        revision = self._version(candidate, candidate_nodes)
        self._entries, self._decisions, self._active, self._nodes = (
            candidate,
            decisions,
            active,
            candidate_nodes,
        )
        self._revision = revision
        return {
            "revision": self._revision,
            "actions": actions,
            "restored": restored,
            "represented": represented,
            "decisions": {
                row["edge_id"]: self.decision(row["edge_id"])
                for row in actions
                if row["edge_id"] in decisions
            },
        }

    def _compile(self, entries):
        decisions, signatures, active = {}, {}, set(entries)
        candidates = []
        for ident, item in entries.items():
            signature = definition_key(item)
            if signature is not None and signature in signatures:
                decisions[ident] = {
                    "status": "duplicate",
                    "reason": "same_definition",
                    "duplicate_of": signatures[signature],
                }
                active.remove(ident)
                continue
            if signature is not None:
                signatures[signature] = ident
            definition = self._rules.definitions.get(item.get("relation"))
            reason = "unknown_relation" if definition is None else "direct_fact"
            if definition and definition["mode"] == "summary":
                reason = (
                    "independent_evidence"
                    if independent(item)
                    else "unknown_context" if context_key(item) is None else "no_equivalent_path"
                )
                if reason == "no_equivalent_path":
                    candidates.append(ident)
            decisions[ident] = {"status": "retained", "reason": reason}
        # A represented claim remains a typed proof input for an upper summary.
        # Only duplicate aliases leave this inventory; final witnesses expand to
        # retained leaves before any result is committed.
        proof_inputs = {key for key in entries if decisions[key]["status"] != "duplicate"}
        budget = Budget(self._limits["max_work"])
        for ordinal, ident in enumerate(sorted(candidates)):
            item = entries[ident]
            relation, edge = item["relation"], item["edge"]
            definition = self._rules.definitions[relation]
            rules = list(self._rules.compositions.get(relation, ()))
            if definition.get("transitive", False):
                rules.append({"id": "transitive:" + relation, "result": relation, "path": None})
            if ordinal >= self._limits["max_candidates"]:
                decisions[ident]["reason"] = "search_budget"
                continue
            try:
                family = self._rules.family(relation)
                graph = adjacency(entries, proof_inputs, context_key(item), family, budget)
                if reachable(graph, edge["to"], edge["from"], budget, excluded=ident):
                    decisions[ident]["reason"] = "cyclic_relation_family"
                    continue
                for rule in sorted(rules, key=lambda value: value["id"]):
                    witness = path(
                        graph,
                        edge["from"],
                        edge["to"],
                        budget,
                        rule["path"],
                        excluded=ident,
                        repeat=relation,
                    )
                    if witness:
                        decisions[ident] = {
                            "status": "represented",
                            "reason": "registered_path",
                            "rule": rule["id"],
                            "path": witness,
                        }
                        active.remove(ident)
                        break
            except SearchLimit:
                decisions[ident]["reason"] = "search_budget"
        # Later-elided witnesses are expanded first. If expansion traverses a
        # cycle, retain the summary so earlier claims still have a valid leaf.
        for ident in reversed(sorted(candidates)):
            decision = decisions[ident]
            if decision["status"] == "represented":
                try:
                    leaves = leaf_path(ident, decisions, self._limits["max_work"])
                except SearchLimit:
                    decisions[ident] = {"status": "retained", "reason": "search_budget"}
                    active.add(ident)
                    continue
                route = [entries[leaves[0]]["edge"]["from"]]
                for key in leaves:
                    edge = entries[key]["edge"]
                    if edge["from"] != route[-1]:
                        raise ValueError("Broken relation witness continuity")
                    route.append(edge["to"])
                if len(set(route)) != len(route):
                    decisions[ident] = {"status": "retained", "reason": "cyclic_witness"}
                    active.add(ident)
                else:
                    decision["leaf_path"] = leaves
        return decisions, active

    def export(self):
        """Retain every original ID, definition and witness in portable JSON."""
        return deepcopy(
            {
                "schema": "bo-relation-index/v1",
                "nodes": sorted(self._nodes),
                "rules": self._rules.value,
                "limits": self._limits,
                "entries": list(self._entries.values()),
                "decisions": self._decisions,
                "canonical_edges": [
                    entry["edge"]["id"]
                    for key, entry in self._entries.items()
                    if key in self._active
                ],
                "revision": self._revision,
            }
        )

    @classmethod
    def restore(cls, value):
        """Reject stale or hand-edited decisions instead of trusting saved claims."""
        encoded(value)
        schema_check(value, "relations")
        if value.get("schema") != "bo-relation-index/v1":
            raise ValueError("Expected a relation index")
        result = cls(value["nodes"], value["rules"], limits=value["limits"])
        result.apply([{"op": "insert", "entry": entry} for entry in value["entries"]])
        if encoded(result.export()) != encoded(value):
            raise ValueError("Stale or altered relation decisions; rebuild through insertion")
        return result
