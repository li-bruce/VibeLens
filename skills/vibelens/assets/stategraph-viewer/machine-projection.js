import { t } from "./i18n.js";
/** Actual nesting determines active ancestors; names alone never do. */
export function machineParents(machine) {
  const parents = new Map();
  function descend(items, parent = null) {
    for (const item of items || []) {
      const state = typeof item === "string" ? { name: item } : item;
      const name = parent ? parent + "_" + state.name : state.name;
      parents.set(name, parent);
      descend(state.parallel || state.children, name);
    }
  }
  descend(machine.states);
  return parents;
}
export function activeMachineStates(machine, value) {
  const parents = machineParents(machine),
    active = new Set();
  for (let state of [].concat(value || [])) {
    const seen = new Set();
    while (typeof state === "string" && !seen.has(state)) {
      seen.add(state);
      if (!machine.values.includes(state)) break;
      active.add(state);
      state = parents.get(state);
    }
  }
  return active;
}

/** Project executable declarations, retaining every conditional transition.
 * This does not run a second machine. Only actual journal entries mark a path.
 */
export function machineProjection(
  model,
  snapshot,
  { attempt, choice = "latest", step = "latest" } = {},
) {
  const machine = model.machine;
  const parents = machineParents(machine);
  const childOf = (value, parent) => {
    const seen = new Set();
    while (parents.has(value) && !seen.has(value)) {
      seen.add(value);
      value = parents.get(value);
      if (value === parent) return true;
    }
    return false;
  };
  const nodes = machine.values.map((value) => {
    const authored = model.nodes.find((n) => n.kind === "state" && n.value === value);
    return {
      ...(authored || {
        id: "state." + value,
        label: machine.labels?.[value] || value,
        kind: "state",
        layer: "state",
        value,
        source: machine.source,
      }),
      machine_state: true,
      declaration: "machine.states",
    };
  });
  const ids = new Map(nodes.map((n) => [n.value, n.id]));
  const edges = [];
  for (const node of nodes) {
    const parent = parents.get(node.value);
    if (!parent) continue;
    node.machine_parent = ids.get(parent);
    node.parent = node.machine_parent;
    edges.push({
      id: `machine-contains:${node.machine_parent}:${node.id}`,
      from: node.machine_parent,
      to: node.id,
      type: "contains",
      origin: "machine-declaration",
      label: t("Nested state"),
    });
  }
  for (const [index, transition] of machine.transitions.entries()) {
    const sources = Array.isArray(transition.source) ? transition.source : [transition.source];
    for (const source of machine.values.filter((v) =>
      sources.some((s) => s === "*" || s === v || childOf(v, s)),
    )) {
      const target = transition.dest || source;
      edges.push({
        id: "transition:" + transition.trigger + ":" + source,
        from: ids.get(source),
        to: ids.get(target),
        type: "transition",
        event: transition.trigger,
        label: [
          machine.event_labels?.[transition.trigger] || transition.trigger,
          ...[].concat(transition.conditions || []).map((g) => t("when {0}", g)),
          ...[].concat(transition.unless || []).map((g) => t("unless {0}", g)),
        ].join(" · "),
        conditions: [...[].concat(transition.conditions || [])],
        unless: [...[].concat(transition.unless || [])],
        machine_transition: {
          index,
          source: transition.source,
          dest: transition.dest,
          internal: transition.dest == null,
        },
        observed:
          step === "latest" &&
          (snapshot.journal || []).some(
            (j) =>
              j.event === transition.trigger &&
              j.source === source &&
              j.target === target &&
              j.attempt === attempt,
          ),
        current: choice === "latest",
      });
    }
  }
  for (const edge of edges.filter((e) => e.observed)) {
    const candidates = edges.filter(
      (e) => e.event === edge.event && e.from === edge.from && e.to === edge.to,
    );
    if (candidates.length > 1) {
      const witness = (snapshot.journal || []).find(
        (j) =>
          j.event === edge.event &&
          j.source === nodes.find((n) => n.id === edge.from)?.value &&
          j.target === nodes.find((n) => n.id === edge.to)?.value &&
          j.attempt === attempt &&
          j.transition_index === edge.machine_transition.index,
      );
      edge.observed = !!witness;
      edge.runtime_witness = witness ? "observed" : "ambiguous";
    }
  }
  const counts = new Map();
  for (const edge of edges) counts.set(edge.id, (counts.get(edge.id) || 0) + 1);
  for (const edge of edges)
    if (counts.get(edge.id) > 1)
      edge.id +=
        ":" +
        encodeURIComponent(
          JSON.stringify([edge.to, edge.conditions, edge.unless, edge.machine_transition.internal]),
        );
  // Identical declarations are still distinct entries in the executable table.
  const repeated = new Map();
  for (const edge of edges) {
    const count = repeated.get(edge.id) || 0;
    repeated.set(edge.id, count + 1);
    if (count) edge.id += ":duplicate:" + count;
  }
  return { nodes, edges };
}
