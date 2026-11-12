/** Model namespaces shared by 2D, 3D, replay and node inspection.
 * A layer may contain many independent networks. Empty selection never chooses
 * an arbitrary machine merely because its state names happen to match.
 */
const emptyMachine = Object.freeze({
  values: [],
  states: [],
  events: {},
  context: {},
  transitions: [],
});

export function machinesOf(model) {
  return model?.machines || (model?.machine ? { default: model.machine } : {});
}
export const modelValueKey = (model, modelId, value) =>
  model.machines ? JSON.stringify([modelId, value]) : value;

export function machineIdOf(model, member) {
  if (!model?.machines) return "default";
  if (typeof member === "string" && Object.hasOwn(model.machines, member)) return member;
  const node =
    typeof member === "string" ? model.nodes?.find((item) => item.id === member) : member;
  if (node?.state_model_id && Object.hasOwn(model.machines, node.state_model_id))
    return node.state_model_id;
  const owners = Object.entries(model.machines).filter(([, machine]) => {
    const execution = machine.execution;
    return (
      execution &&
      [
        execution.parent,
        execution.join?.id,
        ...(execution.activities || []).map((item) => item.id),
        ...(execution.resources || []).map((item) => item.id),
      ].includes(node?.id)
    );
  });
  return owners.length === 1 ? owners[0][0] : null;
}

export function machineFor(model, member) {
  return machinesOf(model)[machineIdOf(model, member)] || emptyMachine;
}

export function sameStateModel(node, change) {
  return (node.state_model_id || null) === (change.state_model_id || null);
}

/** Select witnessed state for this model; overlapping local instance names stay separate. */
export function configurationFor(view, node, fallback, choice = "latest") {
  if (!view.model?.machines) return fallback;
  const id = machineIdOf(view.model, node);
  if (!id) return null;
  if (fallback?.state_model_id === id) return fallback;
  const candidates = (view.machine?.configurations || []).filter(
    (cfg) =>
      cfg.state_model_id === id &&
      (choice === "latest" || [cfg.snapshot_instance, cfg.attempt].includes(choice)),
  );
  return (
    candidates.find((cfg) => cfg.snapshot_instance === view.machine.current_instance) ||
    (candidates.length === 1 ? candidates[0] : null)
  );
}

/** Authored subnet memberships coexist with ordinary containment and source trees. */
export function networkMemberships(view, all) {
  const networks = networkCatalog(view);
  const membership = new Map();
  for (const network of networks)
    for (const id of network.nodes || []) {
      if (!all.has(id)) continue;
      if (!membership.has(id)) membership.set(id, new Set());
      membership.get(id).add(network.id);
    }
  for (const [id, keys] of membership) all.set(id, { ...all.get(id), network_ids: [...keys] });
  return networks;
}

/** A catalog is metadata, not a second containment tree or execution authority. */
export function networkCatalog(view) {
  const networks = [...(view.model.networks || []), ...(view.concept_structure?.networks || [])];
  for (const id of Object.keys(view.model.machines || {})) {
    if (networks.some((network) => network.state_model_id === id)) continue;
    networks.push({
      id: `machine:${id}`,
      label: id,
      layer: "state",
      state_model_id: id,
      nodes: view.model.nodes.filter((node) => node.state_model_id === id).map((node) => node.id),
    });
  }
  return networks;
}

export const networkViewId = (network) =>
  "network-" +
  [...new TextEncoder().encode(network.id)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
