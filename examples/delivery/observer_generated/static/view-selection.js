/** View templates describe content; cameras and manual positions are personal.
 * A changed selection becomes a draft instead of silently rewriting a preset.
 */
import { cleanProfile, profileFor, presets } from "./analysis.js";
import { cleanFilters } from "./layout.js";
export const draftViewId = "custom-draft";
export const isPreset = (id) => presets.some((view) => view.id === id);

export function restoredFilters(id, custom, saved) {
  return isPreset(id) ? cleanFilters(profileFor(id, custom)) : cleanFilters(saved);
}

/** A layer selection addresses whole layers. Remove the previous template's
 * narrower semantic scope, while keeping the user's individual exclusions.
 */
export function layerSelection(filters) {
  return {
    profile: { ...cleanProfile(), hierarchical: true },
    filters: cleanFilters({
      hiddenNodes: filters.hiddenNodes,
      hiddenEdges: filters.hiddenEdges,
      fields: filters.fields,
    }),
  };
}

export function needsSource(id, settings) {
  return (
    ["project", "code", "api", "implementation"].includes(id) ||
    !!settings.codeFocus ||
    (id.startsWith("custom-") &&
      settings.layers.visible.some((layer) => ["entry", "structure", "symbols"].includes(layer)))
  );
}

/** Arrange the selected contents, retaining full identity/ancestry for bindings.
 * Hidden planes must not reserve layout space or push a new preset off-screen.
 * The caller applies these coordinates to its full graph so hidden descendants
 * can follow a moved owner and recover their previous relative arrangement.
 */
export function layoutSelection(graph, presentation) {
  const visible = new Set([...presentation.glyphs, ...presentation.regions]),
    boxes = graph.boxes.filter((box) => visible.has(box.id));
  return {
    ...graph,
    boxes,
    byId: new Map(boxes.map((box) => [box.id, box])),
    edges: presentation.edges.filter((edge) => visible.has(edge.from) && visible.has(edge.to)),
    regions: graph.regions.filter((region) => visible.has(region.id)),
  };
}
