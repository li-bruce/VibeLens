/** One display taxonomy for graph, spatial layout, filters and timeline.
 * Planes describe concerns. Implementation facets describe source granularity or
 * observation roles; neither changes a definition, a call or an event identity.
 */
export const implementationFacets = ["execution", "code", "project", "api", "operations"];
export const legacyLayers = Object.freeze(
  Object.fromEntries(implementationFacets.map((id) => [id, "implementation"])),
);
export const canonicalLayer = (id) => legacyLayers[id] || id;
const codeRoles = new Set([
  "directory",
  "file",
  "endpoint",
  "class",
  "function",
  "parameter",
  "unresolved",
  "reference",
]);
export const dataRoles = [
  "store",
  "dataset",
  "column",
  "query",
  "write",
  "transaction",
  "transform",
];

export function visualType(node) {
  // Concept roles use the same glyph vocabulary while retaining their explicit
  // concern and concept_kind. A transition is never presented as a function.
  if (node.origin === "concept-design") {
    if (node.layer === "business") return "business";
    if (node.concept_kind === "fact") return "data";
    if (node.concept_kind?.startsWith("rule_") || node.concept_kind === "guard") return "decision";
    if (["event", "logical_effect"].includes(node.concept_kind)) return "effect";
    if (["state", "state_model", "transition"].includes(node.concept_kind)) return "state";
  }
  if (node.code_role) return codeRoles.has(node.code_role) ? "code-" + node.code_role : "unknown";
  if (node.data_role) return dataRoles.includes(node.data_role) ? node.data_role : "unknown";
  if (node.layer === "business") return "business";
  if (node.kind === "state") return "state";
  if (node.kind === "resource" || node.execution_role === "resource") return "resource";
  if (node.kind === "decision" || node.execution_role === "join") return "decision";
  if (["data", "effect", "wait"].includes(node.kind)) return node.kind;
  if (["function", "action"].includes(node.kind)) return "function";
  return "unknown";
}

/** Retain old facet identities so saved exclusions can migrate without widening. */
export function implementationFacet(node) {
  if (
    ["query", "write", "transaction", "transform"].includes(
      node.data_role || node.capture_owner_role,
    )
  )
    return "operations";
  if (node.api_role === "capture" || node.capture_owner_api_role === "capture") return "execution";
  if (node.layer === "api" || node.code_role === "endpoint") return "api";
  if (["directory", "file"].includes(node.code_role) || node.reference_scope === "project")
    return "project";
  if (node.code_role || ["python-ast", "source-ast"].includes(node.origin)) return "code";
  return "execution";
}

export function classifyNode(node) {
  const type = visualType(node);
  if (node.origin === "concept-design") {
    if (["business", "state", "rules"].includes(node.layer))
      return { layer: node.layer, facet: null };
    if (
      node.layer === "predicate" ||
      node.concept_kind?.startsWith("rule_") ||
      node.concept_kind === "fact"
    )
      return { layer: "rules", facet: null };
    if (node.concept_kind === "object") return { layer: "business", facet: null };
  }
  if (type === "unknown") return { layer: "unknown", facet: null, diagnostic: "Unclassified node" };
  if (
    node.code_role ||
    node.api_role === "capture" ||
    node.capture_owner_api_role === "capture" ||
    ["query", "write", "transaction", "transform"].includes(
      node.data_role || node.capture_owner_role,
    )
  )
    return { layer: "implementation", facet: implementationFacet(node) };
  if (type === "business") return { layer: "business", facet: null };
  if (node.origin === "policy-definition" || node.policy_node || node.capture_owner_policy)
    return { layer: "rules", facet: null };
  if (
    node.semantic_role === "state_parameter" ||
    ["state", "wait", "resource"].includes(type) ||
    (["resource", "join"].includes(node.execution_role) && node.origin !== "policy-definition")
  )
    return { layer: "state", facet: null };
  if (type === "decision") return { layer: "rules", facet: null };
  if (["store", "dataset", "column"].includes(type)) return { layer: "data", facet: null };
  return { layer: "implementation", facet: implementationFacet(node) };
}
