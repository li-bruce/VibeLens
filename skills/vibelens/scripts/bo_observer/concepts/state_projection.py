"""Build object-state diagrams with events, transition conditions and effects."""

from .common import canonical_id as cid, records
from .activities import add_activities, activity_semantics


def add_states(graph, doc, state_indexes):
    """Project the declared state machine without inventing runtime activation."""
    add, relation = graph.add, graph.relation
    models = records(doc["state_models"], "state_models")
    for mid, state in models.items():
        root = cid("state-model", mid)
        membership = {
            "states": state["states"],
            "events": list(state["events"]),
            "guards": list(state["guards"]),
            "effects": list(state["effects"]),
            "transitions": [t["id"] for t in state["transitions"]],
        }
        add(
            root,
            "state_model",
            {
                **{
                    k: v
                    for k, v in state.items()
                    if k
                    not in {
                        "states",
                        "events",
                        "guards",
                        "effects",
                        "transitions",
                        "source_refs",
                        "label",
                        "summary",
                    }
                },
                "members": membership,
                **(
                    {"execution": activity_semantics(state["execution"])}
                    if "execution" in state
                    else {}
                ),
            },
            label=state.get("label", mid),
            layer="state",
            aliases=[mid],
            deps=[cid("object", state["subject"]["object"])],
        )
        relation(
            cid("state-subject", mid),
            root,
            cid("object", state["subject"]["object"]),
            "state_subject",
        )
        table = state_indexes[mid]
        for name, value in table["states"].items():
            ident = cid("state", mid, name)
            add(
                ident,
                "state",
                value,
                label=value.get("label", name),
                layer="state",
                aliases=[name],
                deps=[root],
                value=name,
            )
            parent = table["parents"][name]
            relation(
                cid("state-contains", mid, name),
                cid("state", mid, parent) if parent else root,
                ident,
                "contains",
                containment_kind="state_hierarchy",
            )
        for name, value in state["events"].items():
            add(
                cid("event", mid, name),
                "event",
                value,
                label=value.get("label", name),
                layer="state",
                aliases=[name],
                deps=[root],
            )
            relation(cid("state-event", mid, name), root, cid("event", mid, name), "declares_event")
        for name, value in state["guards"].items():
            add(
                cid("guard", mid, name),
                "guard",
                value,
                label=value.get("label", name),
                layer="state",
                aliases=[name],
                deps=[root, *([value["decision"]] if value.get("decision") else [])],
            )
            relation(cid("state-guard", mid, name), root, cid("guard", mid, name), "declares_guard")
        for name, value in state["effects"].items():
            add(
                cid("effect", mid, name),
                "logical_effect",
                value,
                label=value.get("label", name),
                layer="state",
                aliases=[name],
                deps=[root],
            )
            relation(
                cid("state-effect", mid, name), root, cid("effect", mid, name), "declares_effect"
            )
        for offset, transition in enumerate(state["transitions"]):
            ident = cid("transition", mid, transition["id"])
            before = (
                transition["source"]
                if isinstance(transition["source"], list)
                else [transition["source"]]
            )
            deps = [root, cid("event", mid, transition["trigger"])]
            deps += [cid("state", mid, name) for name in before if name != "*"]
            if transition["dest"] is not None:
                deps.append(cid("state", mid, transition["dest"]))
            deps += [
                cid("guard", mid, name)
                for name in transition.get("conditions", []) + transition.get("unless", [])
            ]
            deps += [cid("effect", mid, name) for name in transition.get("effects", [])]
            add(
                ident,
                "transition",
                {**transition, "priority": offset},
                label=transition.get("label", transition["id"]),
                layer="state",
                aliases=[transition["id"]],
                deps=deps,
            )
            relation(
                cid("event-trigger", mid, transition["id"]),
                cid("event", mid, transition["trigger"]),
                ident,
                "requests_transition",
            )
            for name in transition.get("conditions", []) + transition.get("unless", []):
                relation(
                    cid("transition-guard", mid, transition["id"], name),
                    ident,
                    cid("guard", mid, name),
                    "guarded_by",
                    value={"negated": name in transition.get("unless", [])},
                )
            for name in transition.get("effects", []):
                relation(
                    cid("transition-effect", mid, transition["id"], name),
                    ident,
                    cid("effect", mid, name),
                    "has_effect",
                    source_refs=transition.get("source_refs", []),
                )
            if transition["dest"] is not None:
                relation(
                    cid("transition-target", mid, transition["id"]),
                    ident,
                    cid("state", mid, transition["dest"]),
                    "declares_target",
                )
            for name in before:
                actual = list(table["states"]) if name == "*" else [name]
                for start in actual:
                    relation(
                        cid("state-transition", mid, transition["id"], start),
                        cid("state", mid, start),
                        cid(
                            "state",
                            mid,
                            transition["dest"] if transition["dest"] is not None else start,
                        ),
                        "transition",
                        value={
                            "transition": ident,
                            "trigger": transition["trigger"],
                            "conditions": transition.get("conditions", []),
                            "unless": transition.get("unless", []),
                        },
                        label=transition["trigger"],
                    )
        add_activities(graph, mid, state)
    return models
