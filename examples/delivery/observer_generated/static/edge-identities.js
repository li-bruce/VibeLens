/** Original assertions behind one proven-equivalent conceptual effect relation.
 * This is an identity lookup, not graph inference: endpoints alone never merge
 * calls, guards, transitions or arbitrary relations. Recorded facts stay intact.
 */
const assertionFields = new Set([
  "id",
  "from",
  "to",
  "type",
  "label",
  "origin",
  "evidence_kind",
  "source_refs",
]);

/** Reject conflicting/extended aliases before runtime display fields are added. */
export function validateEquivalentRelations(edges) {
  const identities = new Set(edges.map((edge) => edge.id));
  for (const edge of edges) {
    if (edge.equivalent_relations === undefined) continue;
    if (!Array.isArray(edge.equivalent_relations))
      throw Error("Invalid equivalent effect relations");
    if (!edge.equivalent_relations.length) continue;
    const conceptual = (item) =>
      item.origin === "concept-design" && item.evidence_kind === "conceptual";
    if (
      edge.type !== "has_effect" ||
      !conceptual(edge) ||
      Object.keys(edge).some((key) => key !== "equivalent_relations" && !assertionFields.has(key))
    )
      throw Error("Only unchanged conceptual effect associations may share a display relation");
    for (const original of edge.equivalent_relations) {
      if (
        !original ||
        typeof original.id !== "string" ||
        !original.id ||
        identities.has(original.id) ||
        original.type !== "transition_has_effect" ||
        original.from !== edge.from ||
        original.to !== edge.to ||
        !conceptual(original) ||
        Object.keys(original).some((key) => !assertionFields.has(key))
      )
        throw Error("Ambiguous or non-equivalent effect relation identity");
      identities.add(original.id);
    }
  }
}

/** One display member may retain several original declaration identities. */
export function originalRelations(edge) {
  return (edge.members || [edge]).flatMap((member) => [
    member,
    ...(member.equivalent_relations || []),
  ]);
}

export function relationIds(edge) {
  return [...new Set([edge.id, ...originalRelations(edge).map((member) => member.id)])];
}

export function hasRelationId(edge, id) {
  return (
    edge.id === id ||
    (edge.members || [edge]).some(
      (member) =>
        member.id === id || member.equivalent_relations?.some((original) => original.id === id),
    )
  );
}

/** Hiding either name hides the same assertion, without rewriting preferences. */
export function relationExcluded(edge, hidden) {
  if (!hidden?.size && !hidden?.length) return false;
  const has = (id) => (hidden instanceof Set ? hidden.has(id) : hidden.includes(id));
  return (
    has(edge.id) ||
    (edge.members || [edge]).some(
      (member) =>
        has(member.id) || member.equivalent_relations?.some((original) => has(original.id)),
    )
  );
}

export function relationTypeAllowed(edge, allowed, classify) {
  return originalRelations(edge).some((member) => {
    const type = classify(member);
    return allowed instanceof Set ? allowed.has(type) : allowed.includes(type);
  });
}
