import { filterNode, hierarchyOf, hierarchyRegions } from "./layout.js";

/** Camera bounds follow visible geometry, independently of cached topology.
 * Layer projections retain references to movable node boxes. Their scalar
 * extents can therefore predate Arrange or dragging. Recompute these extents
 * without including hidden owner anchors or changing saved positions.
 */
function visibleBounds(graph, glyphs, regions) {
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity;
  const include = (box) => {
    minX = Math.min(minX, box.x);
    minY = Math.min(minY, box.y);
    maxX = Math.max(maxX, box.x + box.w);
    maxY = Math.max(maxY, box.y + box.h);
  };
  for (const box of graph.boxes) if (glyphs.has(box.id)) include(box);
  for (const region of regions) include(region);
  if (!Number.isFinite(minX)) return { minX: 0, minY: 0, width: 210, height: 210 };
  // Keep the existing fit margin for captions and region outlines.
  const padding = 55;
  return {
    minX: minX - padding,
    minY: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  };
}

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
    graph: { ...graph, regions: bounds, ...visibleBounds(graph, glyphs, bounds) },
    presentation: { ...presentation, glyphs, regions: visibleRegions, edges },
  };
}
