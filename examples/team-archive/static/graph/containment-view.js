import { filterNode, hierarchyOf, hierarchyRegions } from "./layout.js";

/** Refit a filtered view without changing the complete graph or saved expansion.
 * When every visible child disappears, an expanded owner becomes a normal glyph
 * in this view. Restoring the children restores its circle with the same ID.
 */
export function fitVisibleHierarchy(graph, presentation) {
  const glyphs = new Set(presentation.glyphs),
    regions = new Set(presentation.regions),
    tree = hierarchyOf(graph);
  function visit(id) {
    let occupied = false;
    for (const child of tree.children.get(id) || []) occupied = visit(child) || occupied;
    if (regions.has(id) && !occupied) {
      regions.delete(id);
      if (filterNode(graph.all.get(id), graph.all, presentation.filters)) glyphs.add(id);
    }
    return occupied || glyphs.has(id);
  }
  tree.roots.forEach(visit);
  const bounds = hierarchyRegions(graph, { glyphs, regions });
  const occupied = new Set(bounds.map((region) => region.id));
  const visibleRegions = new Set([...regions].filter((id) => occupied.has(id)));
  const edges = presentation.edges
    .map((edge) => ({
      ...edge,
      sourceRegion: edge.sourceRegion && visibleRegions.has(edge.from),
      targetRegion: edge.targetRegion && visibleRegions.has(edge.to),
    }))
    .filter(
      (edge) =>
        (edge.sourceRegion || glyphs.has(edge.from)) && (edge.targetRegion || glyphs.has(edge.to)),
    );
  return {
    graph: { ...graph, regions: bounds },
    presentation: { ...presentation, glyphs, regions: visibleRegions, edges },
  };
}
