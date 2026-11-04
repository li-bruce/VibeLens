/** Qualify one-way implementation maps supplied by a validated bound contract. */
export function conceptBindingId(from, to) {
  const encode = (value) =>
    encodeURIComponent(value).replace(
      /[!'()*]/g,
      (character) => "%" + character.charCodeAt(0).toString(16).toUpperCase(),
    );
  return "concept-implements:" + encode(from) + ":" + encode(to);
}

export function conceptBindings(view) {
  const projection = view.concept_structure;
  if (projection?.schema !== "bo-concept-projection/v1" || projection.stage !== "bound") return [];
  const concepts = new Set(
      projection.nodes.filter((node) => node.origin === "concept-design").map((node) => node.id),
    ),
    native = new Set(view.model.nodes.map((node) => node.id));
  return (projection.edges || []).filter(
    (edge) =>
      concepts.has(edge.from) &&
      native.has(edge.to) &&
      edge.from !== edge.to &&
      edge.id === conceptBindingId(edge.from, edge.to) &&
      edge.type === "maps" &&
      edge.code_relation === "maps" &&
      edge.mapping_role === "implements" &&
      edge.origin === "concept-binding" &&
      edge.evidence_kind === "binding" &&
      edge.observed === false,
  );
}
