/** Adapt declared concept containment into the viewer's display tree.
 * The original edge remains authoritative and typed. Display ancestry is local
 * to this inventory; it never changes source ownership or runtime span parents.
 */
export function applyConceptContainment(all, edges) {
  const claims = new Map();
  for (const edge of edges) {
    if (edge.origin !== "concept-design" || edge.type !== "contains") continue;
    const parent = all.get(edge.from),
      child = all.get(edge.to);
    if (!parent || !child || parent.id === child.id) continue;
    // Older confirmed views predate containment_kind. Their declared concept
    // types still distinguish state membership from unrelated containment.
    const kind =
      edge.containment_kind ||
      (["state_model", "state"].includes(parent.concept_kind) && child.concept_kind === "state"
        ? "state_hierarchy"
        : null);
    if (kind !== "state_hierarchy") continue;
    if (!claims.has(child.id)) claims.set(child.id, []);
    claims.get(child.id).push({ parent: parent.id, edge: edge.id, kind });
  }
  const proposed = new Map();
  for (const [id, values] of claims) {
    // Conflicting owners are graph relations, not a guessed display hierarchy.
    if (new Set(values.map((value) => value.parent)).size !== 1 || all.get(id).parent) continue;
    proposed.set(id, values[0]);
  }
  for (const [id, value] of proposed) {
    const seen = new Set([id]);
    let parent = value.parent,
      cyclic = false;
    while (parent && all.has(parent)) {
      if (seen.has(parent)) {
        cyclic = true;
        break;
      }
      seen.add(parent);
      parent = all.get(parent).parent || proposed.get(parent)?.parent;
    }
    if (!cyclic)
      all.set(id, {
        ...all.get(id),
        parent: value.parent,
        display_parent_kind: value.kind,
        display_parent_edge: value.edge,
      });
  }
}
