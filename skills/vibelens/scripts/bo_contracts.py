"""Shared, application-independent model and value contracts.

The project checker, standalone module and exports use these same rules.
Runtime violations are diagnostics; callers must preserve the actual facts.
"""

import hashlib
import math
import json


def source_declaration_id(source):
    """Identify an exact source declaration using portable JSON and SHA-256.

    This contract belongs to the standalone model module. The observer and AST
    adapters reuse it; loading an enriched model never imports those adapters.
    """
    key = source["path"] + "::" + source["symbol"]
    raw = json.dumps(key, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "code:symbol:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def validate_source_references(model):
    """Reject forged or dangling physical references without merging observation nodes.

    Legacy graphs without this metadata retain their established validation. A
    registered reference must resolve to one exact declaration in this graph;
    sharing source never makes two business operations or runtime calls equal.
    """
    nodes = {node["id"]: node for node in model.get("nodes", [])}
    for node in nodes.values():
        target = node.get("declaration_id")
        role = node.get("representation_role")
        if target is None and role not in {"declaration", "source-reference"}:
            continue
        source = node.get("source")
        if (
            not isinstance(source, dict)
            or not all(
                isinstance(source.get(key), str) and source[key] for key in ("path", "symbol")
            )
            or target != source_declaration_id(source)
        ):
            raise ValueError("source declaration identity differs: " + node["id"])
        declared = nodes.get(target)
        if (
            not declared
            or declared.get("representation_role") != "declaration"
            or declared.get("code_role") not in {"function", "class"}
            or declared.get("source") != source
            or declared.get("declaration_id") != target
        ):
            raise ValueError("missing exact source declaration: " + node["id"])
        if role == "declaration" and node["id"] != target:
            raise ValueError("physical declaration has a second identity: " + node["id"])
        if role == "declaration" and node.get("declaration_scope", "mapped") not in {
            "mapped",
            "lexical-owner",
        }:
            raise ValueError("unsupported source declaration scope: " + node["id"])
        if role == "source-reference" and (
            node["id"] == target or node.get("code_role") != "reference"
        ):
            raise ValueError("source context must be a distinct reference: " + node["id"])


def value_errors(value, spec, name):
    kind = spec.get("type")
    matches = {
        "integer": type(value) is int,
        "number": type(value) in (int, float) and math.isfinite(value),
        "boolean": type(value) is bool,
        "string": isinstance(value, str),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
        "enum": any(type(value) is type(item) and value == item for item in spec.get("values", [])),
    }
    if not matches.get(kind, False):
        return [f"{name}: expected {kind}"]
    errors = []
    if kind in ("integer", "number"):
        if "min" in spec and value < spec["min"]:
            errors.append(f"{name}: below min")
        if "max" in spec and value > spec["max"]:
            errors.append(f"{name}: above max")
    if kind == "array" and spec.get("items"):
        for i, item in enumerate(value):
            errors.extend(value_errors(item, spec["items"], f"{name}[{i}]"))
    if kind == "object":
        for key in spec.get("required", []):
            if key not in value:
                errors.append(f"{name}.{key}: missing")
        for key, item in spec.get("properties", {}).items():
            if key in value:
                errors.extend(value_errors(value[key], item, f"{name}.{key}"))
    return errors


def state_tree(chart):
    """Return actual engine names and ancestry; underscores are not split heuristically."""
    states, parents = {}, {}
    separator = chart.get("separator", "_")
    if separator != "_":
        raise ValueError("unsupported state separator: " + str(separator))

    def descend(items, parent=None):
        if not isinstance(items, list) or not items:
            raise ValueError("states must be a nonempty list")
        for item in items:
            data = {"name": item} if isinstance(item, str) else item
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("name"), str)
                or not data["name"]
            ):
                raise ValueError("state needs a nonempty name")
            unsupported = set(data) - {"name", "initial", "children", "parallel"}
            if unsupported:
                raise ValueError("unsupported state semantics: " + ", ".join(sorted(unsupported)))
            if "parallel" in data and ("children" in data or "initial" in data):
                raise ValueError("parallel state cannot also declare children or initial")
            name = (parent + separator if parent else "") + data["name"]
            if name in states:
                raise ValueError("duplicate state name")
            if data.get("history"):
                raise ValueError("history states require a supported engine adapter")
            states[name], parents[name] = data, parent
            nested = data.get("parallel", data.get("children"))
            if nested is not None:
                descend(nested, name)

    descend(chart["states"])
    for name, data in states.items():
        if "initial" in data:
            initial = data["initial"]
            if not isinstance(initial, str) or name + separator + initial not in states:
                raise ValueError("unknown compound initial state: " + name)
    return states, parents


def entered_states(chart, target):
    """Resolve compound initial descendants and every parallel region."""
    states, parents = state_tree(chart)
    if target not in states:
        raise ValueError("unknown transition target")

    def enter(name):
        data = states[name]
        if data.get("parallel"):
            return [
                leaf for child, parent in parents.items() if parent == name for leaf in enter(child)
            ]
        if data.get("initial"):
            return enter(name + "_" + data["initial"])
        return [name]

    return enter(target)


def transition_states(chart, previous, transitions):
    """Expected configuration for the supported declarative subset, never facts.

    This checks only supplied guard results. It does not call business callbacks.
    Independent parallel region transitions compose; cross-region transitions
    are rejected when the declaration is loaded.
    """
    states, parents = state_tree(chart)
    before = active_states(chart, previous)
    leaves = {
        s for s in before if not any(p == s and child in before for child, p in parents.items())
    }

    def chain(name):
        result = []
        while name is not None:
            result.append(name)
            name = parents[name]
        return result

    removed, added = set(), set()
    for transition in transitions:
        target = transition["dest"]
        if target is None:
            continue
        sources = transition["source"]
        sources = sources if isinstance(sources, list) else [sources]
        if "*" in sources:
            sources = [s for s, p in parents.items() if p is None]
        for source in set(sources) & before:
            ancestors = chain(source)
            common = next((p for p in ancestors if p in chain(target)), None)
            exit_root = source
            while parents[exit_root] is not None and parents[exit_root] != common:
                exit_root = parents[exit_root]
            if common == source:
                exit_root = source
            removed.update(s for s in leaves if exit_root in chain(s))
            added.update(entered_states(chart, target))
    return active_states(chart, sorted((leaves - removed) | added))


def validate_value_spec(spec, name):
    if not isinstance(spec, dict) or spec.get("type") not in {
        "integer",
        "number",
        "boolean",
        "string",
        "enum",
        "array",
        "object",
    }:
        raise ValueError("unknown value type: " + name)
    if spec["type"] == "enum" and (not isinstance(spec.get("values"), list) or not spec["values"]):
        raise ValueError("enum needs values: " + name)
    for bound in ("min", "max"):
        if bound in spec and (
            type(spec[bound]) not in (int, float) or not math.isfinite(spec[bound])
        ):
            raise ValueError("invalid bound: " + name)
    if "min" in spec and "max" in spec and spec["min"] > spec["max"]:
        raise ValueError("invalid bounds")
    if spec.get("items") is not None:
        validate_value_spec(spec["items"], name + "[]")
    for key, child in spec.get("properties", {}).items():
        validate_value_spec(child, name + "." + key)


def validate_runtime_definition(
    chart, *, loaded_engine=None, loaded_version=None, guard_names=None
):
    """Fail before creating an executor when its declared semantics are unsupported."""
    if not isinstance(chart, dict):
        raise ValueError("statechart must be an object")
    unsupported = set(chart) & {
        "queued",
        "auto_transitions",
        "ignore_invalid_triggers",
        "send_event",
        "ordered_transitions",
        "model_override",
        "before_state_change",
        "after_state_change",
        "prepare_event",
        "finalize_event",
        "on_exception",
    }
    if unsupported:
        raise ValueError("unsupported engine options: " + ", ".join(sorted(unsupported)))
    engine = chart.get("engine")
    if engine not in (
        None,
        "transitions.Machine",
        "transitions.HierarchicalMachine",
        "transitions.extensions.HierarchicalMachine",
        "adapter-selected",
        "python.explicit",
        "bo.fsm",
    ):
        raise ValueError("unsupported execution engine: " + str(engine))
    if loaded_engine is not None and engine not in (None, "adapter-selected", loaded_engine):
        raise ValueError("loaded engine differs from declaration")
    if (
        loaded_version is not None
        and engine != "adapter-selected"
        and chart.get("version") != loaded_version
    ):
        raise ValueError("loaded engine version differs from declaration")
    if guard_names is not None and set(chart.get("guards", {})) - set(guard_names):
        raise ValueError("declared guard is missing from loaded executor")
    states, parents = state_tree(chart)
    if (
        engine != "bo.fsm"
        and "values" in chart
        and (
            not isinstance(chart["values"], list)
            or len(chart["values"]) != len(states)
            or set(chart["values"]) != set(states)
        )
    ):
        raise ValueError("state values must exactly cover executable states")
    if engine == "bo.fsm":
        if (
            chart.get("version") != "1"
            or any(p is not None for p in parents.values())
            or chart.get("execution")
        ):
            raise ValueError(
                "bo.fsm/1 supports flat states; hierarchy and activities need an explicit engine adapter"
            )
        if set(chart) - {
            "engine",
            "version",
            "states",
            "values",
            "initial",
            "state_type",
            "transitions",
            "events",
            "context",
            "guards",
            "labels",
        }:
            raise ValueError("unsupported bo.fsm semantics")
        if (
            chart.get("state_type") != "enum"
            or not isinstance(chart.get("values"), list)
            or len(chart["values"]) != len(states)
            or set(chart["values"]) != set(states)
        ):
            raise ValueError("bo.fsm values must exactly cover its states")
        if not all(isinstance(chart.get(k), dict) for k in ("context", "events", "guards")):
            raise ValueError("bo.fsm requires context, events and guards objects")
    if chart.get("initial") not in states:
        raise ValueError("unknown initial state")
    active_states(chart, entered_states(chart, chart["initial"]))
    if engine == "transitions.Machine" and any(p is not None for p in parents.values()):
        raise ValueError("flat engine cannot load hierarchical states")
    for name, spec in chart.get("context", {}).items():
        validate_value_spec(spec, name)
    for event, data in chart.get("events", {}).items():
        if not isinstance(data, dict) or not isinstance(data.get("payload"), dict):
            raise ValueError("event needs payload declaration: " + event)
        for name, spec in data["payload"].items():
            validate_value_spec(spec, event + "." + name)
    for transition in chart["transitions"]:
        if set(transition) - {"source", "dest", "trigger", "conditions", "unless"}:
            raise ValueError("unsupported transition callback or semantics")
        sources = transition["source"]
        sources = sources if isinstance(sources, list) else [sources]
        if not sources:
            raise ValueError("transition needs a source")
        if any(s != "*" and s not in states for s in sources) or transition["dest"] not in {
            None,
            *states,
        }:
            raise ValueError("dangling transition")
        if transition["trigger"] not in chart.get("events", {}):
            raise ValueError("unknown transition event")
        for field in ("conditions", "unless"):
            refs = transition.get(field, [])
            refs = refs if isinstance(refs, list) else [refs]
            if set(refs) - set(chart.get("guards", {})):
                raise ValueError("undefined guard")
        # Explicitly bound the supported HSM subset instead of silently applying
        # sequential rules to cross-region transitions.
        for source in sources:
            if source == "*" or transition["dest"] is None:
                continue
            branch = source
            while parents[branch] is not None:
                parent = parents[branch]
                if states[parent].get("parallel") and not (
                    transition["dest"] == branch or transition["dest"].startswith(branch + "_")
                ):
                    raise ValueError("cross-region transition requires a supported engine adapter")
                branch = parent


def active_states(chart, value):
    states, parents = state_tree(chart)
    leaves = []

    def collect(item):
        if isinstance(item, list):
            for child in item:
                collect(child)
        else:
            leaves.append(item)

    collect(value)
    if not leaves or len(set(leaves)) != len(leaves) or any(s not in states for s in leaves):
        raise ValueError("unknown or duplicate active state")
    result = set(leaves)
    for leaf in leaves:
        parent = parents[leaf]
        while parent:
            result.add(parent)
            parent = parents[parent]
    # Concurrent leaves are legal only in distinct regions of a parallel state.
    # A parent plus its active child is not a second active leaf.
    for parent in [None, *states]:
        children = [s for s, p in parents.items() if p == parent and s in result]
        parallel = parent is not None and bool(states[parent].get("parallel"))
        if parent in leaves and states[parent].get("initial") and not children:
            raise ValueError("compound configuration is missing its active descendant")
        if len(children) > 1 and not parallel:
            raise ValueError("exclusive states cannot be active together")
        if parent in result and parallel:
            declared = [s for s, p in parents.items() if p == parent]
            if set(children) != set(declared):
                raise ValueError("parallel configuration is missing an active region")
        if parent in leaves and children:
            raise ValueError("active configuration repeats an ancestor")
    return result


def validate_names(model):
    """Reject malformed names without changing IDs, source symbols or state values.

    Node keys may include generated capture fields and lazily indexed source IDs.
    Only exact IDs are looked up; names never create a node or a relationship.
    """
    names = model.get("presentation", {}).get("names", {})
    if not isinstance(names, dict) or set(names) - {"nodes", "edges", "states", "events"}:
        raise ValueError("invalid presentation.names categories")
    for category, entries in names.items():
        if not isinstance(entries, dict):
            raise ValueError("presentation.names category must be an identity map")
        for identity, value in entries.items():
            if not isinstance(identity, str) or not identity.strip():
                raise ValueError("presentation.names needs a nonempty identity")
            if isinstance(value, dict):
                if not value or set(value) - {"en", "zh-CN"}:
                    raise ValueError("presentation.names supports en and zh-CN")
                labels = value.values()
            else:
                labels = [value]
            for label in labels:
                if (
                    not isinstance(label, str)
                    or not label.strip()
                    or label != label.strip()
                    or len(label) > 60
                    or any(ord(char) < 32 or ord(char) == 127 for char in label)
                ):
                    raise ValueError(
                        "presentation.names labels need 1-60 plain, single-line characters"
                    )


def validate_lifecycle(node, capture=None):
    """Validate an optional observation vocabulary, never a second business executor.

    Bindings name facts already present in the node's probe stream. Missing bindings
    use neutral execution boundaries; labels never classify a business outcome.
    """
    if "lifecycle" not in node:
        return
    definition = node["lifecycle"]
    if not isinstance(definition, dict) or set(definition) != {"states", "bindings"}:
        raise ValueError("lifecycle requires states and bindings")
    states, bindings = definition["states"], definition["bindings"]
    if not isinstance(states, list) or not 1 <= len(states) <= 64:
        raise ValueError("lifecycle needs 1-64 named states")
    by_id = {}
    for state in states:
        if not isinstance(state, dict) or set(state) != {"id", "label", "kind"}:
            raise ValueError("lifecycle state requires id, label and kind")
        for key in ("id", "label"):
            value = state[key]
            if (
                not isinstance(value, str)
                or not 1 <= len(value) <= 60
                or value != value.strip()
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
            ):
                raise ValueError("lifecycle names need 1-60 plain single-line characters")
        if state["kind"] not in ("active", "waiting", "ended") or state["id"] in by_id:
            raise ValueError("invalid or duplicate lifecycle state")
        by_id[state["id"]] = state
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= 128:
        raise ValueError("lifecycle needs 1-128 event bindings")
    groups = {}
    for binding in bindings:
        if (
            not isinstance(binding, dict)
            or set(binding) - {"phase", "state", "boundary", "when"}
            or not {"phase", "state", "boundary"} <= set(binding)
            or binding["phase"]
            not in ("enter", "return", "read", "decision", "wait", "commit", "change", "error")
            or not isinstance(binding["state"], str)
            or binding["state"] not in by_id
            or binding["boundary"] not in ("start", "update", "end")
        ):
            raise ValueError("invalid lifecycle event binding")
        ended = by_id[binding["state"]]["kind"] == "ended"
        if ended != (binding["boundary"] == "end"):
            raise ValueError("lifecycle end boundaries require an ended state")
        if binding["phase"] in {"return", "error"} and binding["boundary"] != "end":
            raise ValueError("return/error cannot keep an observed invocation open")
        if binding["phase"] == "enter" and binding["boundary"] != "start":
            raise ValueError("entry must start its observed lifecycle")
        guard = binding.get("when")
        if guard is not None:
            if (
                not isinstance(guard, dict)
                or set(guard) != {"direction", "field", "equals"}
                or guard["direction"] not in ("in", "out")
                or not isinstance(guard["field"], str)
            ):
                raise ValueError("invalid lifecycle value selector")
            spec = (
                (capture if capture is not None else node.get("capture", {}))
                .get(guard["direction"], {})
                .get(guard["field"])
            )
            value = guard["equals"]
            if spec not in ("string", "number", "boolean", "scalar"):
                raise ValueError("lifecycle selector must reference a captured scalar field")
            if value is not None and not (
                (spec in {"string", "scalar"} and isinstance(value, str) and len(value) <= 256)
                or (spec in {"boolean", "scalar"} and type(value) is bool)
                or (
                    spec in {"number", "scalar"}
                    and type(value) in {int, float}
                    and math.isfinite(value)
                    and abs(value) <= 9007199254740991
                )
            ):
                raise ValueError("lifecycle selector value does not match its capture type")
        previous = groups.setdefault(binding["phase"], [])
        for other in previous:
            # A phase has one unconditional binding, or disjoint values of one field.
            if (
                guard is None
                or other is None
                or (guard["direction"], guard["field"]) != (other["direction"], other["field"])
                or (
                    type(guard["equals"]) is type(other["equals"])
                    and guard["equals"] == other["equals"]
                )
            ):
                raise ValueError("ambiguous lifecycle bindings for one event")
        previous.append(guard)


def validate_graph(model):
    validate_names(model)
    # Only an exact, validated policy projection may contain source-free logical
    # expressions. Ordinary executable-node checks remain unchanged.
    policy_nodes, policy_edges = set(), set()
    if model.get("policy"):
        try:
            from .policy.projection import projection_errors, ORIGIN
        except ImportError:
            try:
                from .bo_observer.policy.projection import projection_errors, ORIGIN
            except ImportError:
                from bo_observer.policy.projection import projection_errors, ORIGIN
        errors = projection_errors(model)
        if errors:
            raise ValueError("; ".join(errors))
        policy_nodes = {n["id"] for n in model["nodes"] if n.get("origin") == ORIGIN}
        policy_edges = {e["id"] for e in model["edges"] if e.get("origin") == ORIGIN}
    if model.get("schema_version") == 3:
        for key in ("revision", "intent", "source_files", "nodes", "edges", "overview", "scope"):
            if not model.get(key):
                raise ValueError("missing " + key)
    elif model.get("schema_version") not in (None, "bo-model/v1"):
        raise ValueError("unsupported model schema")
    nodes = {n["id"]: n for n in model.get("nodes", [])}
    if not nodes or len(nodes) != len(model["nodes"]):
        raise ValueError("invalid node identities")
    validate_source_references(model)
    for node in nodes.values():
        if "observation_root" in node and type(node["observation_root"]) is not bool:
            raise ValueError("observation_root must be Boolean")
        if node.get("observation_root") and not node.get("source"):
            raise ValueError("external observation roots require their native source binding")
        owner = nodes.get(node.get("event_node") or node.get("referenceOf"), node)
        validate_lifecycle(node, capture=owner.get("capture", {}))
        representation = node.get("represents")
        if representation is not None:
            if (
                not isinstance(representation, dict)
                or set(representation) != {"path", "symbol", "parameter"}
                or any(not isinstance(v, str) or not v.strip() for v in representation.values())
                or representation["path"] not in model.get("source_files", [])
                or node.get("code_role")
                or node.get("kind") != "data"
            ):
                raise ValueError("semantic parameter needs one exact source parameter reference")
        if node.get("semantic_role") == "state_parameter" and representation is None:
            raise ValueError("state parameter requires an explicit representation mapping")
        seen = {node["id"]}
        parent = node.get("parent")
        while parent:
            if parent not in nodes or parent in seen:
                raise ValueError("missing parent or hierarchy cycle")
            seen.add(parent)
            parent = nodes[parent].get("parent")
        if model.get("schema_version") == 3:
            if node.get("kind") not in {
                "action",
                "function",
                "decision",
                "wait",
                "effect",
                "data",
                "state",
            }:
                raise ValueError("invalid node kind")
            if not node.get("label") or not node.get("summary"):
                raise ValueError("node lacks developer explanation")
            if (
                node["kind"] not in {"data", "state"}
                and not node.get("source")
                and node["id"] not in policy_nodes
            ):
                raise ValueError("executable node lacks source: " + node["id"])
    edges = set()
    for edge in model.get("edges", []):
        if edge["id"] in edges or edge["from"] not in nodes or edge["to"] not in nodes:
            raise ValueError("duplicate/dangling edge")
        edges.add(edge["id"])
        if model.get("schema_version") == 3 and (
            (
                edge.get("type") not in {"flow", "data", "guard", "contains", "resource", "join"}
                and not (edge["id"] in policy_edges and edge.get("type") == "maps")
            )
            or not edge.get("evidence")
        ):
            raise ValueError("edge needs type and provenance")
        if edge.get("type") in ("resource", "join") and not model.get("machine", {}).get(
            "execution"
        ):
            raise ValueError("resource and join edges need an executable activity declaration")
    for item in model.get("overview", []):
        if item["node"] not in nodes:
            raise ValueError("unknown overview node")
    return nodes


def validate_chart(model, runtime_definition=None):
    validate_graph(model)
    chart = model["machine"]
    # Compact models are explicit bo-model/v1 or legacy unversioned declarations.
    fields = ("states", "values", "transitions", "events", "initial", "context")
    if model.get("schema_version") == 3:
        fields += ("engine", "version", "state_type")
    for key in fields:
        if key not in chart or chart[key] is None:
            raise ValueError("missing statechart field: " + key)
    validate_runtime_definition(chart)
    states, _ = state_tree(chart)
    values = set(chart["values"])
    if not values or len(values) != len(chart["values"]):
        raise ValueError("duplicate or missing state values")
    if not values <= states.keys():
        raise ValueError("unknown persisted state value")
    if chart["initial"] not in states:
        raise ValueError("unknown initial state")
    for name, spec in chart["context"].items():
        if spec.get("type") not in {
            "integer",
            "number",
            "boolean",
            "string",
            "enum",
            "array",
            "object",
        }:
            raise ValueError("unknown context type: " + name)
        if spec["type"] == "enum" and not spec.get("values"):
            raise ValueError("enum needs values")
        if "min" in spec and "max" in spec and spec["min"] > spec["max"]:
            raise ValueError("invalid bounds")
    for transition in chart["transitions"]:
        event = transition.get("trigger")
        if event not in chart["events"] or not isinstance(
            chart["events"][event].get("payload"), dict
        ):
            raise ValueError("transition event needs payload declaration")
        sources = transition["source"]
        sources = sources if isinstance(sources, list) else [sources]
        if any(s != "*" and s not in states for s in sources) or (
            transition["dest"] is not None and transition["dest"] not in states
        ):
            raise ValueError("dangling transition")
        for field in ("conditions", "unless"):
            refs = transition.get(field, [])
            refs = refs if isinstance(refs, list) else [refs]
            if set(refs) - set(chart.get("guards", {})):
                raise ValueError("undefined guard")
    represented = {n["value"] for n in model["nodes"] if n.get("layer") == "state"}
    if values != represented:
        raise ValueError("persisted states and graph projection differ")
    if runtime_definition is not None:
        validate_runtime_definition(runtime_definition)
        if json.dumps(chart, sort_keys=True, allow_nan=False) != json.dumps(
            runtime_definition, sort_keys=True, allow_nan=False
        ):
            raise ValueError("graph and runtime statechart declarations differ")
    try:
        from .execution_contract import validate_execution_graph
    except ImportError:
        from execution_contract import validate_execution_graph
    validate_execution_graph(model)
    return {
        "valid": True,
        "states": len(values),
        "events": len(chart["events"]),
        "runtime_definition_compared": runtime_definition is not None,
    }
