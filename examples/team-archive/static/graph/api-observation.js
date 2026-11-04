/** Exact HTTP observation bindings supplied by verified route registrations.
 * Names, shared handlers and arbitrary source-map paths never establish runtime
 * ownership. This overlay retains native event/call/parent IDs and raw ordinals.
 */
export function apiObservationSources(node) {
  if (node?.code_role !== "endpoint" || node.observation_projection !== true) return [];
  return (Array.isArray(node.observation_sources) ? node.observation_sources : []).filter(
    (source) =>
      typeof source.node === "string" &&
      source.node &&
      typeof source.method === "string" &&
      source.method &&
      typeof source.route === "string" &&
      source.route &&
      typeof source.source?.path === "string" &&
      source.source.path &&
      typeof source.source?.symbol === "string" &&
      source.source.symbol,
  );
}

export function apiObservationIds(node) {
  return [...new Set(apiObservationSources(node).map((source) => source.node))];
}

/** Include a physical node's own events and only its explicitly bound API events. */
export function observesNode(node, id) {
  return (
    id === (node.referenceOf || node.event_node || node.id) || apiObservationIds(node).includes(id)
  );
}

/** Reuse witnessed native intervals; an API view is not another invocation. */
export function projectAPIIntervals(slices, nodes) {
  const targets = new Map();
  for (const node of nodes)
    for (const owner of apiObservationIds(node)) {
      if (!targets.has(owner)) targets.set(owner, []);
      targets.get(owner).push(node);
    }
  return slices.flatMap((slice) => {
    if (slice.source_node) return [];
    return (targets.get(slice.node) || []).map((node) => ({
      ...slice,
      node: node.id,
      source_node: slice.node,
      role: "api-observation",
      observation_basis: {
        kind: "http-registration",
        source_node: slice.node,
        registrations: apiObservationSources(node).filter((source) => source.node === slice.node),
      },
    }));
  });
}
