"""Validate declared relation meanings without interpreting labels or source code."""

from copy import deepcopy
import hashlib
import json

from ...protocol import schema_check

CONTEXT_FIELDS = {"scope", "revision", "basis", "bindings", "conditions"}
DEFAULT_LIMITS = {"max_work": 100_000, "max_candidates": 512}
EMPTY_RULES = {"schema": "bo-relation-rules/v1", "definitions": [], "compositions": []}
WITNESS_FIELDS = {
    "source",
    "callsite",
    "call_id",
    "trace",
    "span_id",
    "event_id",
    "event_ids",
    "witnesses",
    "observed",
}
SUMMARY_FIELDS = {
    "id",
    "from",
    "to",
    "type",
    "evidence",
    "origin",
    "semantic_relation",
    "label",
    "summary",
    "description",
    "source_refs",
    "presentation",
} | WITNESS_FIELDS


def encoded(value):
    """Use portable, type-preserving JSON for equality and revision checks."""

    def keys(item, depth=0, active=frozenset()):
        if depth > 64:
            raise ValueError("Relation JSON exceeds the supported nesting depth")
        if isinstance(item, (dict, list)):
            if id(item) in active:
                raise ValueError("Relation JSON cannot contain object cycles")
            active = active | {id(item)}
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("Relation objects require string keys")
            for child in item.values():
                keys(child, depth + 1, active)
        elif isinstance(item, list):
            for child in item:
                keys(child, depth + 1, active)
        elif item is not None and type(item) not in {str, int, float, bool}:
            raise ValueError("Relation values must use portable JSON types")
        elif type(item) is int and abs(item) > 9007199254740991:
            raise ValueError("Relation integers exceed the JSON safe range")

    keys(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def context_key(entry):
    """An omitted or unknown condition/basis cannot establish equivalence."""
    context = entry.get("context")
    if (
        not context
        or set(context) != CONTEXT_FIELDS
        or any(v is None or (isinstance(v, str) and not v.strip()) for v in context.values())
    ):
        return None
    return encoded(context)


def definition_key(entry):
    """Require explicit identity and identical non-display evidence for duplicates."""
    context = context_key(entry)
    if context is None or not entry.get("definition_key"):
        return None
    edge = {
        key: value for key, value in entry["edge"].items() if key not in {"id", "label", "summary"}
    }
    return digest(
        {
            "edge": edge,
            "context": context,
            "relation": entry.get("relation"),
            "definition_key": entry["definition_key"],
            "independent": entry.get("independent", False),
        }
    )


def independent(entry):
    """Direct runtime/source witnesses protect even an explicitly marked summary."""
    edge = entry["edge"]
    return (
        entry.get("independent", False)
        or edge.get("observed") is True
        or any(edge.get(key) is not None for key in WITNESS_FIELDS - {"observed"})
    )


class Rules:
    """A small typed composition contract, rather than untyped reachability."""

    def __init__(self, value=None):
        value = deepcopy(EMPTY_RULES if value is None else value)
        encoded(value)
        schema_check(value, "relations")
        if value.get("schema") != "bo-relation-rules/v1":
            raise ValueError("Expected relation rules")
        self.value = value
        self.definitions = {}
        self.compositions = {}
        for item in value["definitions"]:
            if not item["id"].strip():
                raise ValueError("Relation definitions require nonempty IDs")
            if item["id"] in self.definitions:
                raise ValueError("Duplicate relation definition: " + item["id"])
            if item["mode"] == "summary":
                required = {
                    "type": "maps",
                    "origin": "relation-summary",
                    "semantic_relation": item["id"],
                }
                if item["match"] != required:
                    raise ValueError("A summary must use its dedicated conceptual mapping selector")
            elif item.get("transitive", False):
                raise ValueError("Direct relations cannot be declared transitive")
            self.definitions[item["id"]] = item
        seen = set()
        dependencies = {}
        for rule in value["compositions"]:
            if not rule["id"].strip():
                raise ValueError("Composition rules require nonempty IDs")
            if rule["id"].startswith("transitive:"):
                raise ValueError("Composition IDs reserve the transitive: prefix")
            if rule["id"] in seen:
                raise ValueError("Duplicate composition rule: " + rule["id"])
            seen.add(rule["id"])
            names = [rule["result"], *rule["path"]]
            if any(name not in self.definitions for name in names):
                raise ValueError("Composition references an undefined relation")
            if self.definitions[rule["result"]]["mode"] != "summary":
                raise ValueError("Composition results must be summaries")
            self.compositions.setdefault(rule["result"], []).append(rule)
            dependencies.setdefault(rule["result"], set()).update(rule["path"])
        # Recursive relation meanings need their explicit transitive declaration.
        # Project execution cycles are valid and are handled separately by the index.
        finished = set()
        for name in self.definitions:
            pending = [(name, False)]
            active = set()
            while pending:
                key, leaving = pending.pop()
                if leaving:
                    active.remove(key)
                    finished.add(key)
                elif key not in finished:
                    if key in active:
                        raise ValueError(
                            "Cyclic composition rules; use an explicit transitive summary"
                        )
                    active.add(key)
                    pending.append((key, True))
                    pending.extend(
                        (child, False) for child in sorted(dependencies.get(key, ()), reverse=True)
                    )

    def entry(self, value, nodes):
        value = deepcopy(value)
        encoded(value)
        schema_check(value, "relations")
        if "edge" not in value:
            raise ValueError("Expected a relation registration")
        edge = value["edge"]
        if any(not edge[key].strip() for key in ("id", "from", "to", "type", "evidence")):
            raise ValueError("Relation identity, type and evidence must be nonempty")
        if edge["from"] not in nodes or edge["to"] not in nodes:
            raise ValueError("Relation endpoint does not exist: " + edge["id"])
        relation = value.get("relation")
        if relation is not None:
            if relation not in self.definitions:
                raise ValueError("Undefined relation: " + relation)
            definition = self.definitions[relation]
            if any(edge.get(key) != expected for key, expected in definition["match"].items()):
                raise ValueError("Relation does not match its registered meaning: " + edge["id"])
            if definition["mode"] == "summary" and set(edge) - SUMMARY_FIELDS:
                raise ValueError("A summary cannot carry unregistered physical or execution fields")
        return value

    def family(self, relation):
        """Include nested composition inputs when checking execution cycles."""
        pending, result = [relation], set()
        while pending:
            current = pending.pop()
            if current not in result:
                result.add(current)
                for rule in self.compositions.get(current, ()):
                    pending.extend(rule["path"])
        return result
