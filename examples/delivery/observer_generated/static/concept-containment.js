/** Adapt declared concept containment into the viewer's display tree.
 * The original edge remains authoritative and typed. Display ancestry is local
 * to this inventory; it never changes source ownership or runtime span parents.
 */
export function applyConceptContainment(all, edges) {
  const claims = new Map();
  const claim = (child, parent, kind, edge) => {
    if (!claims.has(child)) claims.set(child, []);
    claims.get(child).push({ parent, edge, kind });
  };
  for (const edge of edges) {
    if (edge.origin !== "concept-design") continue;
    const parent = all.get(edge.from),
      child = all.get(edge.to);
    if (!parent || !child || parent.id === child.id) continue;
    // Older confirmed views predate containment_kind. Their declared concept
    // types still distinguish state membership from unrelated containment.
    if (edge.type === "contains") {
      const kind =
        edge.containment_kind ||
        (["state_model", "state"].includes(parent.concept_kind) && child.concept_kind === "state"
          ? "state_hierarchy"
          : null);
      if (kind === "state_hierarchy") claim(child.id, parent.id, kind, edge.id);
    } else if (
      parent.concept_kind === "state_model" &&
      { declares_event: "event", declares_guard: "guard", declares_effect: "logical_effect" }[
        edge.type
      ] === child.concept_kind
    ) {
      claim(child.id, parent.id, "state_model_membership", edge.id);
    }
  }
  // Transition declarations belong to the model declaring their trigger. A
  // guard's use by other transitions is not ownership and never reparents it.
  for (const edge of edges) {
    if (edge.origin !== "concept-design" || edge.type !== "requests_transition") continue;
    if (
      all.get(edge.from)?.concept_kind !== "event" ||
      all.get(edge.to)?.concept_kind !== "transition"
    )
      continue;
    for (const owner of claims.get(edge.from) || [])
      if (all.get(owner.parent)?.concept_kind === "state_model")
        claim(edge.to, owner.parent, "state_model_membership", edge.id);
  }
  // Native state declarations stay distinct from conceptual occurrences. Their
  // explicit registered model identity supplies a display group only: it adds
  // no semantic edge, execution parent, runtime interval or equivalence claim.
  const models = new Map();
  for (const node of all.values()) {
    if (node.concept_kind !== "state_model" || !node.state_model_id) continue;
    if (!models.has(node.state_model_id)) models.set(node.state_model_id, []);
    models.get(node.state_model_id).push(node.id);
  }
  for (const node of all.values()) {
    if (!node.machine_state || node.layer !== "state" || node.parent || claims.has(node.id))
      continue;
    for (const owner of models.get(node.state_model_id) || [])
      claim(node.id, owner, "state_model_membership");
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
