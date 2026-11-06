/** Presentation of actual observations, shared by planar and spatial playback. */
import { conceptActivityIds } from "./concept-observation.js";
import { observesNode } from "./api-observation.js";
export const transferDuration = 1100;

export function respondingNodes(event, graph, presentation, detail) {
  const result = new Set(),
    owners = new Set((detail?.rows || []).flatMap((row) => row.owners || [row.owner]));
  for (const node of graph.all.values()) {
    if (
      !owners.has(node.id) &&
      !observesNode(node, event.node) &&
      !conceptActivityIds(node).includes(event.node)
    )
      continue;
    let id = node.id;
    const visited = new Set();
    while (id && !visited.has(id)) {
      visited.add(id);
      if (presentation.glyphs.has(id) || presentation.regions.has(id)) {
        result.add(id);
        break;
      }
      id = graph.all.get(id)?.parent;
    }
  }
  return result;
}
