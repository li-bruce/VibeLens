import { layerOf, layers } from "./graph-layers.js";

/** Hierarchy uses containment on the plane; it never changes semantic elevation. */
export function nodeElevation(_node, _byId, base, _gap) {
  return base;
}

/** Compute containment membership without running a hidden planar packing pass.
 * Real 3D coordinates belong to the worker. Saved 2D positions are read only.
 */
export function prepareSpatialHierarchy(graph, preferences) {
  const ancestors = new Map();
  for (const node of graph.all.values()) {
    const chain = new Set(),
      seen = new Set([node.id]);
    let parent = node.parent;
    while (parent && !seen.has(parent)) {
      seen.add(parent);
      chain.add(parent);
      parent = graph.all.get(parent)?.parent;
    }
    ancestors.set(node.id, chain);
  }
  const self = new Set();
  for (const edge of graph.rawEdges) {
    if (edge.type === "contains") continue;
    if (ancestors.get(edge.to)?.has(edge.from)) self.add(edge.from);
    if (ancestors.get(edge.from)?.has(edge.to)) self.add(edge.to);
  }
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
  const nodes = graph.boxes
    .filter((box) => visible.has(box.id))
    .map((box) => ({
      id: box.id,
      parent: visible.has(box.node.parent) ? box.node.parent : null,
      layer: layerOf(box.node),
      type: box.type,
      open: !!box.open,
      glyph: presentation.glyphs.has(box.id),
      region: presentation.regions.has(box.id),
      label: box.node.label || box.id,
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
    // Keep a layer's elevation stable when other layers are hidden.
    layers,
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

/** One owner may enclose descendants on several layers. Every projection keeps its owner ID. */
export function containmentVolumes(model, positions, gap) {
  const volumes = [];
  for (const owner of model.nodes.filter((node) => node.region)) {
    const ids = descendants(model, owner.id);
    for (const layer of model.layers) {
      const members = model.nodes.filter((node) => ids.has(node.id) && node.layer === layer.id);
      if (!members.length) continue;
      const points = members.map((node) => positions[node.id]).filter(Boolean);
      if (!points.length) continue;
      const min = ["x", "y", "z"].map((key) => Math.min(...points.map((p) => p[key])));
      const max = ["x", "y", "z"].map((key) => Math.max(...points.map((p) => p[key])));
      const center = Object.fromEntries(
        ["x", "y", "z"].map((key, i) => [key, (min[i] + max[i]) / 2]),
      );
      const radius = Math.max(65, Math.hypot(max[0] - min[0], max[2] - min[2]) / 2 + 55);
      volumes.push({
        id: owner.id,
        layer: layer.id,
        center,
        radius,
        height: 0,
        projection: layer.id !== owner.layer,
        members: members.map((node) => node.id),
      });
    }
  }
  return volumes;
}
