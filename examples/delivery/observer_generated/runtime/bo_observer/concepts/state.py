"""Validate source-free object state designs without constructing an executor."""

from copy import deepcopy

try:
    from ...bo_contracts import state_tree, entered_states, validate_value_spec
except ImportError:
    from bo_contracts import state_tree, entered_states, validate_value_spec
from .common import fields, records, references, text
from .activities import validate_activities

SCALARS = {"string", "number", "integer", "boolean"}


def validate_objects(doc, sources):
    objects = records(doc["objects"], "objects")
    for ident, item in objects.items():
        fields(
            item,
            {"id", "identity", "fields", "label", "summary", "source_refs"},
            {"id", "identity", "source_refs"},
            "object " + ident,
        )
        references(item, sources, "object " + ident)
        identity = item["identity"]
        if (
            not isinstance(identity, dict)
            or not identity
            or any(not text(k) or v not in SCALARS for k, v in identity.items())
        ):
            raise ValueError("object identity needs typed scalar fields: " + ident)
        properties = item.get("fields", {})
        if not isinstance(properties, dict) or any(
            not text(k) or v not in SCALARS for k, v in properties.items()
        ):
            raise ValueError("invalid object fields: " + ident)
        if any(k in properties and properties[k] != v for k, v in identity.items()):
            raise ValueError("object identity type conflicts with its field: " + ident)
    return objects


def validate_states(doc, objects, sources):
    """Retain transition order, state loops, hierarchy and explicit unknown boundaries."""
    models = records(doc["state_models"], "state_models")
    indexes = {}
    for ident, item in models.items():
        fields(
            item,
            {
                "id",
                "subject",
                "states",
                "initial",
                "events",
                "context",
                "guards",
                "effects",
                "transitions",
                "execution",
                "label",
                "summary",
                "source_refs",
            },
            {
                "id",
                "subject",
                "states",
                "initial",
                "events",
                "context",
                "guards",
                "effects",
                "transitions",
                "source_refs",
            },
            "state model " + ident,
        )
        references(item, sources, "state model " + ident)
        subject = item["subject"]
        fields(subject, {"object", "identity"}, {"object", "identity"}, "state subject")
        owner = objects.get(subject["object"])
        if not owner or subject["identity"] != list(owner["identity"]):
            raise ValueError("state subject identity differs from its object: " + ident)
        states, parents = state_tree(item)
        if item["initial"] not in states:
            raise ValueError("unknown initial state: " + ident)
        entered_states(item, item["initial"])
        for field in ("context", "events", "guards", "effects"):
            if not isinstance(item[field], dict):
                raise ValueError("state " + field + " must be an object")
        for name, spec in item["context"].items():
            validate_value_spec(spec, name)
        for name, event in item["events"].items():
            fields(
                event,
                {"payload", "label", "summary", "source_refs"},
                {"payload"},
                "state event " + name,
            )
            if not text(name) or not isinstance(event["payload"], dict):
                raise ValueError("event needs typed payload fields")
            for field, spec in event["payload"].items():
                validate_value_spec(spec, name + "." + field)
        for name, guard in item["guards"].items():
            fields(
                guard,
                {"decision", "meaning", "label", "summary", "source_refs"},
                {"source_refs"},
                "logical guard " + name,
            )
            references(guard, sources, "logical guard " + name)
            if not text(name) or not (text(guard.get("decision")) or text(guard.get("meaning"))):
                raise ValueError("logical guard needs a decision or meaning")
        for name, effect in item["effects"].items():
            fields(
                effect,
                {"meaning", "completion", "label", "summary", "source_refs"},
                {"meaning", "completion", "source_refs"},
                "state effect " + name,
            )
            references(effect, sources, "state effect " + name)
            if not text(name) or not text(effect["meaning"]) or not text(effect["completion"]):
                raise ValueError("effect needs meaning and a completion boundary")
        transitions = records(item["transitions"], "state transitions")
        for tid, transition in transitions.items():
            fields(
                transition,
                {
                    "id",
                    "source",
                    "dest",
                    "trigger",
                    "conditions",
                    "unless",
                    "effects",
                    "label",
                    "summary",
                    "source_refs",
                },
                {"id", "source", "dest", "trigger", "source_refs"},
                "transition " + tid,
            )
            references(transition, sources, "transition " + tid)
            before = (
                transition["source"]
                if isinstance(transition["source"], list)
                else [transition["source"]]
            )
            if (
                not before
                or len(set(before)) != len(before)
                or any(s != "*" and s not in states for s in before)
            ):
                raise ValueError("transition source is not declared: " + tid)
            if transition["dest"] is not None and transition["dest"] not in states:
                raise ValueError("transition destination is not declared: " + tid)
            if transition["trigger"] not in item["events"]:
                raise ValueError("transition event is not declared: " + tid)
            for field, available in [
                ("conditions", item["guards"]),
                ("unless", item["guards"]),
                ("effects", item["effects"]),
            ]:
                refs = transition.get(field, [])
                if (
                    not isinstance(refs, list)
                    or len(set(refs)) != len(refs)
                    or any(r not in available for r in refs)
                ):
                    raise ValueError("transition has an undeclared " + field + ": " + tid)
        if "execution" in item:
            business_ids = {
                node["id"] for network in doc["networks"] for node in network.get("nodes", [])
            }
            validate_activities(item, states, business_ids)
        indexes[ident] = {
            "states": deepcopy(states),
            "parents": parents,
            "transitions": transitions,
        }
    return indexes


def validate_facts(doc, objects, sources):
    facts = records(doc["facts"], "facts")
    for ident, fact in facts.items():
        fields(
            fact,
            {
                "id",
                "object",
                "field",
                "type",
                "read_basis",
                "meaning",
                "label",
                "summary",
                "source_refs",
            },
            {"id", "object", "field", "type", "read_basis", "source_refs"},
            "fact " + ident,
        )
        references(fact, sources, "fact " + ident)
        owner = objects.get(fact["object"])
        available = {**owner.get("fields", {}), **owner["identity"]} if owner else {}
        if fact["field"] not in available or fact["type"] != available[fact["field"]]:
            raise ValueError("fact field/type differs from its object: " + ident)
        basis = fact["read_basis"]
        fields(basis, {"timing", "scope", "version"}, {"timing", "scope"}, "fact read basis")
        if any(not text(value) for value in basis.values()):
            raise ValueError("fact read basis needs explicit identities: " + ident)
    return facts
