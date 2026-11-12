import { machineFor } from "./model-networks.js";
/** Resolve a selected declaration to actual capture owners.
 * Concept links are accepted only from the server's bound projection. Their
 * direction is concept -> native declaration; ordinary maps/flow edges cannot
 * authorize capture. Returned IDs always belong to the physical model.
 */
import { runtimeOwners } from "./graph-links.js";
import { visualType } from "./graph-classification.js";
import { conceptBindings } from "./concept-bindings.js";
import { apiObservationSources } from "./api-observation.js";
export { conceptBindingId } from "./concept-bindings.js";

/** Concept-to-code capture requires exact source ownership, as on the server. */
function boundOwners(model, target) {
  const nodes = new Map(model.nodes.map((node) => [node.id, node])),
    pending = [target],
    seen = new Set(),
    result = new Set(),
    sameSource = (left, right) =>
      left &&
      right &&
      Object.keys(left).length === Object.keys(right).length &&
      Object.entries(left).every(([key, value]) => right[key] === value);
  while (pending.length) {
    const id = pending.pop(),
      node = nodes.get(id);
    if (!node || seen.has(id)) continue;
    seen.add(id);
    if (!node.code_role) {
      result.add(id);
      continue;
    }
    if (node.code_role === "endpoint" && node.observation_projection === true) {
      for (const binding of apiObservationSources(node))
        if (sameSource(binding.source, nodes.get(binding.node)?.source)) result.add(binding.node);
      continue;
    }
    for (const edge of model.edges || [])
      if (
        edge.to === id &&
        edge.code_relation === "maps" &&
        sameSource(node.source, nodes.get(edge.from)?.source)
      )
        pending.push(edge.from);
    if (
      node.code_role === "reference" &&
      sameSource(node.source, nodes.get(node.declaration_id)?.source)
    )
      pending.push(node.declaration_id);
    if (
      node.code_role === "parameter" &&
      ["function", "class"].includes(nodes.get(node.parent)?.code_role)
    )
      pending.push(node.parent);
  }
  return [...result];
}

export function captureRoots(view, selected) {
  if (!selected) return [];
  const model = view.model,
    native = new Map(model.nodes.map((node) => [node.id, node])),
    id = selected.referenceOf || selected.event_node || selected.id;
  const owners = (target) => {
    const node = native.get(target);
    if (!node) return [];
    return node.code_role ? runtimeOwners(model, target) : [target];
  };
  if (native.has(id)) return owners(id);

  const projection = view.concept_structure,
    concept = projection?.nodes?.find((node) => node.id === id && node.origin === "concept-design");
  if (concept) {
    if (projection.schema !== "bo-concept-projection/v1" || projection.stage !== "bound") return [];
    const result = new Set();
    for (const edge of conceptBindings(view)) {
      if (edge.from === id)
        for (const owner of boundOwners(model, edge.to)) if (native.has(owner)) result.add(owner);
    }
    return [...result].sort();
  }
  // Generated machine-state markers retain the existing native execution owner.
  // An unbound concept must never fall through to this broad fallback.
  if (selected.origin === "concept-design") return [];
  const parent = visualType(selected) === "state" && machineFor(model, selected).execution?.parent;
  return parent && native.has(parent) ? [parent] : [];
}
