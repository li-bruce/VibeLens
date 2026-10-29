/** Circular semantic clusters built with D3's Barnes-Hut forces and collision index.
 * Units are complete containment subtrees. This solver moves them as a whole;
 * it creates no model nodes, edges or persistent synthetic type containers.
 */
import {
  forceSimulation,
  forceManyBody,
  forceLink,
  forceCollide,
  forceX,
  forceY,
} from "./spatial-force.vendor.js";
export function clusterUnits(units, edges) {
  const byId = new Map(units.map((n) => [n.id, n])),
    groups = new Map();
  for (const n of units) {
    if (!groups.has(n.type)) groups.set(n.type, []);
    groups.get(n.type).push(n);
  }
  const clusters = [...groups]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([id, members], i) => {
      const radius = Math.sqrt(members.reduce((s, n) => s + (n.radius + 20) ** 2, 0)) * 1.3 + 30;
      const angle = (i * Math.PI * 2) / groups.size;
      return {
        id,
        radius,
        x: Math.cos(angle) * radius * 2,
        y: Math.sin(angle) * radius * 2,
        members,
      };
    });
  const centers = new Map(clusters.map((n) => [n.id, n]));
  const groupEdges = new Map();
  for (const e of edges) {
    const a = byId.get(e.from),
      b = byId.get(e.to);
    if (a && b && a.type !== b.type)
      groupEdges.set([a.type, b.type].sort().join(":"), {
        source: a.type,
        target: b.type,
      });
  }
  const coarse = forceSimulation(clusters, 2)
    .stop()
    .force("charge", forceManyBody().strength(-180))
    .force(
      "links",
      forceLink([...groupEdges.values()])
        .id((n) => n.id)
        .distance((e) => e.source.radius + e.target.radius + 180)
        .strength(0.07),
    )
    .force("collision", forceCollide((n) => n.radius + 90).iterations(3))
    .force("x", forceX(0).strength(0.008))
    .force("y", forceY(0).strength(0.008));
  coarse.tick(160);
  const outside = new Map(units.map((n) => [n.id, []]));
  for (const e of edges) {
    const a = byId.get(e.from),
      b = byId.get(e.to);
    if (a && b && a.type !== b.type) {
      outside.get(a.id).push(centers.get(b.type));
      outside.get(b.id).push(centers.get(a.type));
    }
  }
  const bridgeCounts = new Map(
    clusters.map((group) => [
      group.id,
      group.members.filter((unit) => outside.get(unit.id).length).length,
    ]),
  );
  const nodes = [];
  for (const group of clusters)
    group.members
      .sort((a, b) => a.id.localeCompare(b.id))
      .forEach((unit, i) => {
        const neighbors = outside.get(unit.id),
          angle = i * 2.3999632297;
        const r = group.radius * 0.45 * Math.sqrt((i + 1) / group.members.length);
        let dx = Math.cos(angle) * r,
          dy = Math.sin(angle) * r;
        if (neighbors.length) {
          const x = neighbors.reduce((s, p) => s + p.x - group.x, 0),
            y = neighbors.reduce((s, p) => s + p.y - group.y, 0),
            length = Math.hypot(x, y) || 1;
          // Keep the packing distribution when many members share a neighbor.
          // Replacing every target with the same rim point makes collision
          // forces eject bridge nodes into another type's neighborhood.
          if (bridgeCounts.get(group.id) <= Math.max(2, group.members.length * 0.25)) {
            const rim = Math.max(0, group.radius - unit.radius - 15);
            dx = (x / length) * rim;
            dy = (y / length) * rim;
          } else {
            const bias = group.radius * 0.22;
            dx += (x / length) * bias;
            dy += (y / length) * bias;
          }
        }
        const tx = group.x + dx,
          ty = group.y + dy;
        nodes.push({
          ...unit,
          x: tx + Math.cos(angle) * 8,
          y: ty + Math.sin(angle) * 8,
          tx,
          ty,
          ...(unit.pin ? { fx: unit.pin.x, fy: unit.pin.y } : {}),
        });
      });
  const links = edges
    .filter((e) => byId.has(e.from) && byId.has(e.to))
    .map((e) => ({ source: e.from, target: e.to }));
  const fine = forceSimulation(nodes, 2)
    .stop()
    .force("charge", forceManyBody().strength(-70).distanceMax(800))
    .force(
      "links",
      forceLink(links)
        .id((n) => n.id)
        .distance((e) => e.source.radius + e.target.radius + 65)
        .strength((e) => (e.source.type === e.target.type ? 0.035 : 0.002)),
    )
    .force("collision", forceCollide((n) => n.radius + 22).iterations(3))
    .force("x", forceX((n) => n.tx).strength(0.16))
    .force("y", forceY((n) => n.ty).strength(0.16));
  fine.tick(units.length > 2000 ? 100 : 180);
  return nodes.map((n) => ({ id: n.id, x: n.x, y: n.y }));
}
