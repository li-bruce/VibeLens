/** Reading scales within the implementation concern.
 * These are display memberships, never new model identities or runtime spans.
 * Legacy facet filters remain separate so a saved narrow view cannot widen.
 */
import { classifyNode } from "./graph-classification.js";

export const implementationPlanes = ["entry", "structure", "symbols"];
const facetPlanes = Object.freeze({
  api: "entry",
  project: "structure",
  code: "symbols",
  execution: "symbols",
  operations: "symbols",
});

/** A single old Timeline depth resolves to the deepest implementation scale. */
export const displayLayerId = (id) => (id === "implementation" ? "symbols" : facetPlanes[id] || id);

/** A whole concern in a saved order/selection expands to all its detail planes. */
export function expandLayerIds(ids) {
  return [
    ...new Set(
      ids.flatMap((id) => (id === "implementation" ? implementationPlanes : [displayLayerId(id)])),
    ),
  ];
}

export function displayLayerOf(node) {
  const classification = classifyNode(node);
  if (classification.layer !== "implementation") return classification.layer;
  // Endpoint declarations identify entry points. Handler invocation/response
  // captures remain executions linked to that entry, rather than a second API.
  return facetPlanes[classification.facet] || "symbols";
}
