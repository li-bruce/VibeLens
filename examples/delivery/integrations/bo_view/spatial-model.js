import { layerOf, layers, layerColor } from "./graph-layers.js";
import { enclosingCircle, REGION_PADDING, SPATIAL_GLYPH_RADIUS } from "./containment-geometry.js";
import { selfRelationOwners } from "./containment-semantics.js";

/** Lift planar node centers into X/Z without changing either saved layout.
 * Box coordinates use a top-left origin; spatial objects use their center.
 * Only known planar identities qualify, so newly exposed children can still settle.
 */
export function planarSeeds(graph, positions = {}) {
  return Object.fromEntries(
    graph.boxes
      .filter((box) => positions[box.id])
      .map((box) => {
        const p = positions[box.id];
        return [box.id, { x: p.x + box.w / 2, z: p.y + 31 }];
      }),
  );
}

/** Hierarchy uses containment on the plane; it never changes semantic elevation. */
export function nodeElevation(_node, _byId, base, _gap) {
  return base;
}

/** Compute containment membership without running a hidden planar packing pass.
 * Real 3D coordinates belong to the worker. Saved 2D positions are read only.
 */
export function prepareSpatialHierarchy(graph, preferences) {
  const self = selfRelationOwners(graph);
  for (const box of graph.boxes) {
    const saved = preferences.positions[box.id];
    if (saved) Object.assign(box, saved);
  }
  graph.regions = graph.boxes
    .filter((box) => box.open && box.kids.some((id) => graph.byId.has(id)))
    .map((box) => ({
      id: box.id,
      self: self.has(box.id),
      cx: box.x + box.w / 2,
      cy: box.y + 31,
      x: box.x,
      y: box.y,
      w: box.w,
      h: box.h,
      radius: 40,
    }));
  return graph;
}

/** Renderer-neutral scene input. Coordinates, camera and GPU objects never become graph facts. */
export function spatialModel(graph, presentation) {
  const visible = new Set([...presentation.glyphs, ...presentation.regions]);
  const visibleParent = (node) => {
    const seen = new Set([node.id]);
    let parent = node.parent;
    while (parent && !visible.has(parent) && !seen.has(parent)) {
      seen.add(parent);
      parent = graph.all.get(parent)?.parent;
    }
    return parent && visible.has(parent) && !seen.has(parent) ? parent : null;
  };
  const nodes = graph.boxes
    .filter((box) => visible.has(box.id))
    .map((box) => ({
      id: box.id,
      parent: visibleParent(box.node),
      layer: layerOf(box.node),
      type: box.type,
      color: layerColor(box.node),
      open: !!box.open,
      glyph: presentation.glyphs.has(box.id),
      region: presentation.regions.has(box.id),
      label: box.node.label || box.id,
      source: box.node.source,
      source_name: box.node.source_name,
      signature: box.node.signature,
      state: box.state,
      rows: box.rows || box.lines || [],
    }));
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const edges = presentation.edges.filter((edge) => byId.has(edge.from) && byId.has(edge.to));
  // Parent facts remain available even where a compound edge has been folded.
  // A containment guide has a different identity from a call or data transfer.
  const containment = nodes
    .filter((node) => node.parent)
    .map((node) => ({
      id: `spatial-parent:${node.parent}:${node.id}`,
      from: node.parent,
      to: node.id,
      type: "contains",
      guide: true,
      members: [],
    }));
  return {
    nodes,
    byId,
    edges,
    containment,
    // Empty planes do not reserve invisible height slots.
    layers: layers.filter((layer) => nodes.some((node) => node.layer === layer.id)),
  };
}

/** Descendant lookup has a cycle guard because presentation must survive invalid drafts. */
export function descendants(model, id) {
  const result = new Set([id]),
    children = new Map();
  for (const node of model.nodes) {
    if (!children.has(node.parent)) children.set(node.parent, []);
    children.get(node.parent).push(node.id);
  }
  const queue = [id];
  for (let i = 0; i < queue.length; i++)
    for (const child of children.get(queue[i]) || [])
      if (!result.has(child)) {
        result.add(child);
        queue.push(child);
      }
  return result;
}

/** Fit visible bodies bottom-up on each semantic plane.
 * Region-only owners have no physical center glyph, so their saved coordinates
 * cannot enlarge an enclosure. Child regions contribute their full disks,
 * including cross-layer projections, instead of only a stale owner point.
 */
export function containmentVolumes(model, positions, _gap) {
  const volumes = [],
    children = new Map(),
    byId = new Map(model.nodes.map((node) => [node.id, node]));
  for (const node of model.nodes) {
    if (!children.has(node.parent)) children.set(node.parent, []);
    children.get(node.parent).push(node.id);
  }
  for (const layer of model.layers) {
    const memo = new Map(),
      visiting = new Set();
    function fit(id) {
      if (memo.has(id)) return memo.get(id);
      // Invalid draft parent cycles must not hang a presentation calculation.
      if (visiting.has(id)) return { disks: [], members: [] };
      visiting.add(id);
      const node = byId.get(id),
        position = positions[id],
        disks = [],
        members = [];
      if (
        node.glyph &&
        node.layer === layer.id &&
        [position?.x, position?.y, position?.z].every(Number.isFinite)
      ) {
        disks.push({
          x: position.x,
          y: position.z,
          radius: SPATIAL_GLYPH_RADIUS,
        });
        members.push(id);
      }
      for (const child of children.get(id) || []) {
        const result = fit(child);
        disks.push(...result.disks);
        members.push(...result.members);
      }
      const circle = node.region && enclosingCircle(disks, REGION_PADDING);
      if (circle) {
        const plane = members.map((member) => positions[member]).find(Boolean);
        volumes.push({
          id,
          layer: layer.id,
          center: { x: circle.x, y: plane.y, z: circle.y },
          radius: circle.radius,
          height: 0,
          projection: layer.id !== node.layer,
          members,
        });
      }
      const result = { disks: circle ? [circle] : disks, members };
      visiting.delete(id);
      memo.set(id, result);
      return result;
    }
    for (const node of model.nodes) fit(node.id);
  }
  return volumes;
}
