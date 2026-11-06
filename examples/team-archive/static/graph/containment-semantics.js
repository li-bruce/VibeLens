/** Containment is a relationship meaning, independent of scanner and renderer.
 * A region replaces its owner. Keep a center glyph only when a visible internal
 * relation actually uses that owner, rather than merely declaring its children.
 */
export function containmentRelation(edge) {
  return (
    ["contains", "code-contains", "code-defines"].includes(edge.type) ||
    ["contains", "defines"].includes(edge.code_relation)
  );
}

export function selfRelationOwners(graph, accepts = () => true) {
  const visible = graph.byId || graph.all;
  const owners = new Set(),
    chains = new Map();
  const ancestors = (id) => {
    if (chains.has(id)) return chains.get(id);
    const chain = new Set([id]);
    let parent = graph.all.get(id)?.parent;
    while (parent && !chain.has(parent)) {
      chain.add(parent);
      parent = graph.all.get(parent)?.parent;
    }
    chains.set(id, chain);
    return chain;
  };
  const representative = (id) => [...ancestors(id)].find((key) => visible.has(key));
  for (const projected of graph.rawEdges || graph.edges || []) {
    if (!accepts(projected)) continue;
    for (const edge of projected.members || [projected]) {
      if (graph.acceptsRelation && !graph.acceptsRelation(edge)) continue;
      if (containmentRelation(edge)) continue;
      for (const [owner, child] of [
        [edge.from, edge.to],
        [edge.to, edge.from],
      ]) {
        // A folded child-to-child link is not an internal call to the owner.
        if (!visible.has(owner) || !ancestors(child).has(owner)) continue;
        if (owner === child || representative(child) !== owner) owners.add(owner);
      }
    }
  }
  return owners;
}
