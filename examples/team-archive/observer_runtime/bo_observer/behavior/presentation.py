"""Project behavior definitions into on-demand details, never into runtime facts.

Records and graph identities are separate: several concepts may refer to one
native declaration. This index adds no node, route, lifetime or execution result.
Both renderers and recorded contexts consume the same detached representation.
"""

from collections import defaultdict
from copy import deepcopy

from ..concepts.common import canonical_id
from ..concepts.model import build
from .contract import assess
from .dependencies import expression_refs


def _sites(binding, kind):
    """Read only declared observation sites, not arbitrary strings in payloads."""
    if not binding:
        return set()
    if kind == "variable":
        return {binding["observation"]["node"]}
    if kind == "action":
        return {
            binding["entry"]["node"],
            binding["completion"]["node"],
            *(item["site"]["node"] for item in binding.get("exits", [])),
            *(item["observation"]["node"] for item in binding.get("parameters", {}).values()),
        }
    return {item["site"]["node"] for item in binding.get("witnesses", [])}


def project(contract, discovery, model):
    """Derive inspectable definitions from one already pinned project bundle.

    Definitions are validated here too so source-free use has the same semantics.
    Native bindings remain declarations; the existing source/runtime gates establish
    their evidence. Exact expressions stay available for detailed inspection.
    """
    definition = assess(contract, discovery)
    if not definition["valid"]:
        raise ValueError("Invalid behavior details: " + str(definition["errors"]))
    concepts = build(discovery)
    networks = concepts["graph"]["networks"]
    members = {item["id"]: set(item["nodes"]) for item in networks}
    binding = model.get("behavior_bindings", {})
    domains = {item["id"]: item for item in contract["domains"]}
    records, locations = {}, defaultdict(set)

    def attach(key, refs, *, spread=True):
        for ref in refs:
            locations[ref].add(key)
            if spread:
                for member in members.get(canonical_id("network", ref), ()):
                    locations[member].add(key)

    for variable in contract["variables"]:
        key = "variable/" + variable["id"]
        native = binding.get("variables", {}).get(variable["id"])
        records[key] = {
            **deepcopy(variable),
            "kind": "variable",
            "domain": deepcopy(domains[variable["domain"]]),
            "binding": deepcopy(native),
        }
        attach(key, {variable["owner"], variable["concept_ref"]})
        attach(key, _sites(native, "variable"), spread=False)
    for action in contract["actions"]:
        key = "action/" + action["id"]
        native = binding.get("actions", {}).get(action["id"])
        records[key] = {
            **deepcopy(action),
            "kind": "action",
            "binding": deepcopy(native),
            "transition": deepcopy(
                definition["action_definitions"][action["id"]]["canonical_transition"]
            ),
            "properties": [
                item["id"]
                for item in contract["properties"]
                if action["id"] in item.get("action_refs", [])
            ],
        }
        attach(key, action["model_refs"])
        attach(key, _sites(native, "action"), spread=False)
        if action.get("transition_ref"):
            attach(key, {action["transition_ref"]}, spread=False)
        # Explicit cross-model links locate the user operation requesting this
        # event. Shared containment alone never establishes a business route.
        transition = records[key]["transition"]
        if transition:
            event = next(
                (
                    edge["from"]
                    for edge in concepts["graph"]["edges"]
                    if edge["to"] == action["transition_ref"]
                    and edge["type"] == "requests_transition"
                ),
                None,
            )
            attach(
                key,
                {
                    edge["from"]
                    for edge in concepts["graph"]["edges"]
                    if event and edge["to"] == event and edge["type"] == "action_requests_event"
                },
                spread=False,
            )
    for item in contract.get("interactions", []):
        key = "interaction/" + item["id"]
        native = binding.get("interactions", {}).get(item["id"])
        records[key] = {**deepcopy(item), "binding": deepcopy(native)}
        attach(key, item["model_refs"])
        attach(key, _sites(native, "interaction"), spread=False)
    for prop in contract["properties"]:
        key = "property/" + prop["id"]
        records[key] = deepcopy(prop)
        refs = expression_refs(prop.get("expression"))
        refs.update(expression_refs(prop.get("trigger")))
        refs.update("action/" + ident for ident in prop.get("action_refs", []))
        # Use a copy: adding a property must not mutate a collection mid-iteration.
        for node, attached in list(locations.items()):
            if attached & refs:
                locations[node].add(key)
    return {
        "schema": "bo-behavior-details/v1",
        "definition_sha256": definition["definition_sha256"],
        "models": deepcopy(contract["scope"]["model_refs"]),
        "records": records,
        "nodes": {key: sorted(values) for key, values in sorted(locations.items())},
        "unresolved": deepcopy(contract["scope"]["unresolved"]),
        "exclusions": deepcopy(contract["scope"]["exclusions"]),
        "assumptions": deepcopy(contract.get("assumptions", [])),
        "origin": "definition",
        "execution_authority": False,
    }
