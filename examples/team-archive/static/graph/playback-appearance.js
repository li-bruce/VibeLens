/** Presentation of actual observations, shared by planar and spatial playback. */
import { conceptActivityIds } from "./concept-observation.js";
import { observesNode } from "./api-observation.js";
export const transferDuration = 1100;

/**
 * Advance a visual transfer without skipping its entire path on a slow frame.
 * Normal playback keeps its duration; software rendering gets at least eight
 * visible increments. This clock never changes recorded times or event order.
 */
export function createTransferClock() {
  let previous = null,
    elapsed = 0;
  return {
    advance(now) {
      if (previous !== null)
        elapsed = Math.min(
          transferDuration,
          elapsed + Math.max(0, Math.min(now - previous, transferDuration / 8)),
        );
      previous = now;
      return elapsed / transferDuration;
    },
    get done() {
      return elapsed >= transferDuration;
    },
  };
}

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
