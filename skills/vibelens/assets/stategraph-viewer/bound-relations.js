/** Reconcile two declarations of the same bound relation at the view boundary.
 * Endpoint similarity is insufficient. The server must identify an original ID
 * collision, and every non-provenance field must match before drawing it once.
 * Neither the executable model nor its confirmed concept projection is edited.
 */
import { declaredEdges } from "./graph-names.js";

const metadata = new Set(["id", "label", "origin", "evidence", "evidence_kind", "source_refs"]);
const ordered = (value) =>
  Array.isArray(value)
    ? value.map(ordered)
    : value && typeof value === "object"
      ? Object.fromEntries(
          Object.keys(value)
            .sort()
            .map((key) => [key, ordered(value[key])]),
        )
      : value;
const meaning = (edge) =>
  ordered(Object.fromEntries(Object.entries(edge).filter(([key]) => !metadata.has(key))));

/** Unknown fields, call sites, guards, arguments and scopes participate in equality. */
export function sameBoundRelation(concept, native) {
  return (
    !!concept &&
    !!native &&
    concept.origin === "concept-design" &&
    concept.evidence_kind === "conceptual" &&
    (!native.origin || native.origin === "model") &&
    !concept.equivalent_relations &&
    !native.equivalent_relations &&
    JSON.stringify(meaning(concept)) === JSON.stringify(meaning(native))
  );
}

export function boundRelations(view) {
  const concepts = new Map((view.concept_structure?.edges || []).map((edge) => [edge.id, edge]));
  const declarations = new Map(declaredEdges(view.model).map((edge) => [edge.id, edge]));
  const aliases = new Map();
  if (view.concept_structure?.stage === "bound") {
    for (const [nativeId, occurrenceId] of Object.entries(
      view.concept_structure.relation_occurrences || {},
    )) {
      const concept = concepts.get(occurrenceId),
        native = declarations.get(nativeId);
      if (!sameBoundRelation(concept, native)) continue;
      aliases.set(nativeId, [concept]);
      concepts.delete(occurrenceId);
    }
  }
  return [
    ...new Map(
      [
        ...concepts.values(),
        ...view.model.edges.map((edge) =>
          aliases.has(edge.id) ? { ...edge, definition_aliases: aliases.get(edge.id) } : edge,
        ),
      ].map((edge) => [edge.id, edge]),
    ).values(),
  ];
}
