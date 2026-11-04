import { nodeElevation } from "./spatial-model.js";
import { layerHeights } from "./graph-layers.js";
import { proximityOrder, proximitySeeds, proximityNeighbors } from "./proximity-layout.js";
import {
  forceSimulation,
  forceManyBody,
  forceLink,
  forceCollide,
  forceX,
  forceY,
  forceZ,
} from "./spatial-force.vendor.js";

function seed(id) {
  let h = 2166136261;
  for (const c of id) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return (h >>> 0) / 4294967296;
}

/** A deterministic 3D force layout, constrained by semantic layer and parent cluster.
 * Run it in a worker: no simulation ticks occupy the browser's interaction thread.
 * Existing positions are fixed during incremental changes; an explicit arrange releases them.
 */
export function solveSpatial({
  nodes,
  edges,
  layers,
  gap,
  settings,
  positions = {},
  planar = {},
  arrange = false,
}) {
  const layerY = layerHeights(settings || { gap }, layers);
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const rootOf = (node) => {
    let current = node,
      seen = new Set();
    while (byId.has(current.parent) && !seen.has(current.id)) {
      seen.add(current.id);
      current = byId.get(current.parent);
    }
    return current.id;
  };
  const rootIds = new Set(nodes.map(rootOf));
  const neighbors = proximityNeighbors(edges);
  const roots = proximityOrder(
    nodes.filter((node) => rootIds.has(node.id)),
    neighbors,
  ).map((node) => node.id);
  const siblings = new Map();
  for (const node of nodes) {
    const key = JSON.stringify([node.parent || "", node.layer, node.type]);
    if (!siblings.has(key)) siblings.set(key, []);
    siblings.get(key).push(node);
  }
  const local = new Map();
  for (const group of siblings.values())
    for (const [id, point] of proximitySeeds(group, neighbors, 300)) local.set(id, point);
  // Spiral area already grows with node count; scaling spacing by sqrt(count)
  // again would spread a large graph beyond the camera's useful range.
  const spacing = 220;
  const centers = new Map(
    roots.map((id, i) => {
      const angle = i * 2.399963229728653,
        radius = spacing * Math.sqrt(i + 1);
      return [
        id,
        positions[id] || {
          x: Math.cos(angle) * radius,
          z: Math.sin(angle) * radius,
        },
      ];
    }),
  );
  const work = nodes.map((node) => {
    const center = centers.get(rootOf(node)),
      saved = positions[node.id],
      shared = planar[node.id];
    const angle = seed(node.id) * Math.PI * 2,
      radius = node.parent ? 90 + seed(node.id + "r") * 150 : 0,
      hint = node.parent && local.get(node.id),
      dx = hint?.x ?? Math.cos(angle) * radius,
      dz = hint?.y ?? Math.sin(angle) * radius;
    const y = nodeElevation(node, byId, layerY.get(node.layer), gap);
    return {
      ...node,
      x: saved?.x ?? shared?.x ?? center.x + dx,
      y: y,
      z: saved?.z ?? shared?.z ?? center.z + dz,
      tx: center.x + dx,
      ty: y,
      tz: center.z + dz,
      ...(saved && (!arrange || saved.pinned) ? { fx: saved.x, fz: saved.z } : {}),
      // A shared planar result is already collision-tested. Preserve its exact
      // X/Z coordinates instead of pulling connected layers back into one knot.
      ...((!saved || (arrange && !saved.pinned)) && shared ? { fx: shared.x, fz: shared.z } : {}),
      fy: y,
    };
  });
  const ids = new Set(work.map((node) => node.id));
  const links = [
    ...edges,
    ...nodes.filter((n) => n.parent).map((n) => ({ from: n.parent, to: n.id, type: "contains" })),
  ]
    .filter((edge) => ids.has(edge.from) && ids.has(edge.to) && edge.from !== edge.to)
    .map((edge) => ({ source: edge.from, target: edge.to, type: edge.type }));
  const simulation = forceSimulation(work, 3)
    .stop()
    .alphaDecay(0.045)
    .force("charge", forceManyBody().strength(-700).distanceMax(1000).theta(0.9))
    .force(
      "links",
      forceLink(links)
        .id((n) => n.id)
        .distance((e) => (e.type === "contains" ? 150 : 230))
        .strength(0.04),
    )
    .force("collision", forceCollide(54).iterations(2))
    .force("clusterX", forceX((n) => n.tx).strength(0.08))
    .force("layer", forceY((n) => n.ty).strength(0.8))
    .force("clusterZ", forceZ((n) => n.tz).strength(0.08));
  simulation.tick(Math.min(160, 70 + Math.ceil(Math.sqrt(nodes.length))));
  simulation.stop();
  return Object.fromEntries(
    work.map((node) => [
      node.id,
      { x: node.x, y: node.y, z: node.z, pinned: !!positions[node.id]?.pinned },
    ]),
  );
}
