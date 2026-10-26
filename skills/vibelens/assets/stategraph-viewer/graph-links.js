/** Source mappings connect layers by declared identities, never by display labels.
 * Static declarations remain static. These links locate the observed owner; they
 * do not assert that every function or parameter in a source file was executed.
 */
export function runtimeOwners(model, id) {
  const nodes = new Map(model.nodes.map((node) => [node.id, node]));
  const mapped = new Map();
  const handlers = new Map();
  for (const edge of model.edges || []) {
    if (edge.code_relation === "maps") {
      if (!mapped.has(edge.to)) mapped.set(edge.to, []);
      mapped.get(edge.to).push(edge.from);
    }
    if (edge.code_relation === "handles") {
      if (!handlers.has(edge.from)) handlers.set(edge.from, []);
      handlers.get(edge.from).push(edge.to);
    }
  }
  const pending = [id],
    seen = new Set(),
    result = new Set();
  for (let i = 0; i < pending.length; i++) {
    const key = pending[i];
    if (seen.has(key)) continue;
    seen.add(key);
    const node = nodes.get(key);
    if (!node) continue;
    if (!node.code_role) {
      result.add(node.event_node || node.referenceOf || node.id);
      continue;
    }
    pending.push(...(mapped.get(key) || []), ...(handlers.get(key) || []));
    // A parameter belongs to its exact declaration, not to every call in a file.
    if (node.code_role === "parameter" && node.parent) pending.push(node.parent);
  }
  return [...result].sort();
}

/** Merge one optional index slice without duplicated identities or stale endpoint links. */
export function mergeGraph(model, slice) {
  const nodes = new Map(model.nodes.map((node) => [node.id, node]));
  for (const node of slice.nodes) if (!nodes.has(node.id)) nodes.set(node.id, node);
  const edges = new Map((model.edges || []).map((edge) => [edge.id, edge]));
  for (const edge of slice.edges)
    if (nodes.has(edge.from) && nodes.has(edge.to) && !edges.has(edge.id)) edges.set(edge.id, edge);
  return {
    ...model,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    graph_roots: [
      ...new Set([
        ...(model.graph_roots || []),
        ...slice.nodes.filter((node) => !node.parent).map((node) => node.id),
      ]),
    ],
  };
}
