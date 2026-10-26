/** Renderer adapters normalize geometry; routes never change the model's edges. */
import { edgePorts } from "./layout.js";
import { regionPort } from "./edge-routing.js";
export function planarScene(graph, presentation, style, scale) {
  const obstacles = [];
  for (const id of presentation.glyphs) {
    const b = graph.byId.get(id);
    if (b)
      obstacles.push({
        key: "n:" + id,
        id,
        kind: "glyph",
        x: b.x + b.w / 2,
        y: b.y + 31,
        r: Math.max(33, 15 / scale),
        level: 0,
      });
  }
  for (const r of graph.regions || [])
    if (presentation.regions.has(r.id))
      obstacles.push({
        key: "r:" + r.id,
        id: r.id,
        kind: "region",
        x: r.cx,
        y: r.cy,
        r: r.radius,
        level: 0,
      });
  const edges = presentation.edges.map((e) => {
    const { start, end } = edgePorts(graph, e, Math.max(33, 15 / scale));
    return {
      id: e.id,
      from: e.from,
      to: e.to,
      type: e.type,
      a: { ...start, level: 0 },
      b: { ...end, level: 0 },
      allowed: [],
    };
  });
  return {
    style,
    spatial: false,
    obstacles,
    edges,
    parents: graph.boxes.map((b) => ({ id: b.id, parent: b.node.parent || null })),
  };
}
export function spatialScene(model, positions, volumes, style) {
  const flat = (p) => ({ x: p.x, y: p.z, level: p.y });
  const obstacles = model.nodes
    .filter((n) => n.glyph && positions[n.id])
    .map((n) => ({ key: "n:" + n.id, id: n.id, kind: "glyph", ...flat(positions[n.id]), r: 32 }));
  for (const v of volumes)
    obstacles.push({
      key: `r:${v.id}:${v.layer}`,
      id: v.id,
      kind: "region",
      ...flat(v.center),
      r: v.radius,
    });
  const edges = model.edges.flatMap((e) => {
    let a = positions[e.from],
      b = positions[e.to];
    if (!a || !b) return [];
    const from = volumes.find((v) => v.id === e.from && !v.projection)?.center || a;
    const to = volumes.find((v) => v.id === e.to && !v.projection)?.center || b;
    if (e.sourceRegion) a = regionPort(e.from, e.to, to, positions, volumes);
    if (e.targetRegion) b = regionPort(e.to, e.from, from, positions, volumes);
    // Ordinary glyphs use a radial port; region ports are already clipped.
    const port = (p, q, region) => {
      if (region || e.from === e.to) return p;
      const length = Math.hypot(q.x - p.x, q.z - p.z);
      return length > 64
        ? { x: p.x + ((q.x - p.x) * 32) / length, y: p.y, z: p.z + ((q.z - p.z) * 32) / length }
        : p;
    };
    return [
      {
        id: e.id,
        from: e.from,
        to: e.to,
        type: e.type,
        a: flat(port(a, b, e.sourceRegion)),
        b: flat(port(b, a, e.targetRegion)),
        allowed: [],
      },
    ];
  });
  return {
    style,
    spatial: true,
    obstacles,
    edges,
    parents: model.nodes.map((n) => ({ id: n.id, parent: n.parent || null })),
  };
}
