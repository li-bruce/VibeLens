/** Binding evidence is a view of a native observation, never a new invocation.
 * Actions may show each bound call's own interval. Other logical concepts show
 * activity marks; state residency still requires actual machine snapshots.
 */
import { conceptBindings } from "./concept-bindings.js";

export function annotateConcepts(view, declarations) {
  const native = new Map(view.model.nodes.map((node) => [node.id, node])),
    sources = new Map();
  for (const edge of conceptBindings(view)) {
    if (!sources.has(edge.from)) sources.set(edge.from, []);
    sources.get(edge.from).push({ node: edge.to, binding: edge.id });
  }
  return declarations.map((node) => {
    if (node.origin !== "concept-design" || native.has(node.id)) return node;
    const kind = node.concept_kind,
      rule = kind?.startsWith("rule_") || kind === "guard",
      interval = kind === "action" || kind === "activity",
      bound = sources.get(node.id) || [],
      owner = bound.length === 1 ? native.get(bound[0].node) : null;
    return {
      ...node,
      concept_observation: {
        kind: interval ? "call" : rule ? "rule" : kind === "state" ? "state" : "activity",
        sources: bound,
      },
      ...(rule && owner?.policy_node ? { capture_owner_policy: owner.policy_node } : {}),
    };
  });
}

export const conceptActivityIds = (node) =>
  (node?.concept_observation?.sources || []).map((source) => source.node);

/** Only call and decision views may reuse a native call's parameter rows. */
export const conceptRuntimeIds = (node) =>
  ["call", "rule"].includes(node?.concept_observation?.kind) ? conceptActivityIds(node) : [];

/** Resource and join facts are addressed by the native machine's exact identity. */
export function conceptFrameOwner(node, view) {
  if (!["resource", "join"].includes(node.concept_kind)) return null;
  const sources = conceptActivityIds(node);
  if (sources.length !== 1) return null;
  const native = view.model.nodes.find((item) => item.id === sources[0]);
  return native?.execution_role === node.concept_kind ? native : null;
}

export function projectConceptIntervals(slices, nodes) {
  const targets = new Map();
  for (const node of nodes) {
    if (node.concept_observation?.kind !== "call") continue;
    for (const source of node.concept_observation.sources) {
      if (!targets.has(source.node)) targets.set(source.node, []);
      targets.get(source.node).push({ node, source });
    }
  }
  return slices.flatMap((slice) =>
    slice.source_node
      ? []
      : (targets.get(slice.node) || []).map(({ node, source }) => ({
          ...slice,
          node: node.id,
          source_node: slice.node,
          role: "concept-observation",
          observation_basis: {
            kind: "concept-binding",
            source_node: slice.node,
            binding: source.binding,
          },
        })),
  );
}
