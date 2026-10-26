import { Delaunay, createGraph, aGreedy, RBush } from "./routing-tools.vendor.js";
import { ObstacleIndex, simpleRoute, distance, cleanPoints } from "./routing-geometry.js";

/** One reusable free-space channel graph per plane. Delaunay limits candidate
 * neighbors; ngraph A* searches validated channels, without all-pairs edge work.
 * Scope circles are checked by the caller, since their interiors are meaningful.
 */
export class Navigation {
  constructor(index, scope = null) {
    this.index = new ObstacleIndex(
      index.items
        .filter((o) => (scope ? !index.excluded(o, scope) : o.kind === "glyph"))
        .map((o) => ({ ...o, kind: "glyph" })),
    );
    this.graph = createGraph();
    this.points = [];
    const context = {
      from: "",
      to: "",
      a: { x: Infinity, y: Infinity },
      b: { x: Infinity, y: Infinity },
    };
    for (const o of this.index.items)
      for (let k = 0; k < 8; k++) {
        const angle = (k * Math.PI) / 4,
          p = { x: o.x + Math.cos(angle) * (o.r + 12), y: o.y + Math.sin(angle) * (o.r + 12) };
        if (this.index.free(p, context)) this.points.push(p);
      }
    this.tree = new RBush().load(
      this.points.map((p, id) => ({ ...p, id, minX: p.x, maxX: p.x, minY: p.y, maxY: p.y })),
    );
    this.triangulation = Delaunay.from(
      this.points,
      (p) => p.x,
      (p) => p.y,
    );
    this.points.forEach((p, id) => this.graph.addNode(id, p));
    for (let i = 0; i < this.points.length; i++)
      for (const j of this.triangulation.neighbors(i))
        if (j > i) {
          const path = simpleRoute(this.points[i], this.points[j], this.index, context);
          if (path)
            this.graph.addLink(i, j, {
              path,
              weight: path.slice(1).reduce((n, p, k) => n + distance(p, path[k]), 0),
            });
        }
    this.paths = new Map();
    this.finder = aGreedy(this.graph, {
      distance: (_, __, link) => link.data.weight,
      heuristic: (a, b) => Math.abs(a.data.x - b.data.x) + Math.abs(a.data.y - b.data.y),
    });
  }
  find(a, b, edge, globalIndex) {
    const key = JSON.stringify([a.x, a.y, b.x, b.y, edge.from, edge.to]);
    if (this.paths.has(key)) return this.paths.get(key);
    const connect = (id, p) => {
      this.graph.addNode(id, p);
      let candidates = [];
      for (let radius = 80; radius <= 5120 && candidates.length < 4; radius *= 2)
        candidates = this.tree.search({
          minX: p.x - radius,
          minY: p.y - radius,
          maxX: p.x + radius,
          maxY: p.y + radius,
        });
      let count = 0;
      for (const q of candidates.sort((x, y) => distance(x, p) - distance(y, p)).slice(0, 32)) {
        const path = simpleRoute(p, q, globalIndex, edge);
        if (!path) continue;
        this.graph.addLink(id, q.id, {
          path,
          weight: path.slice(1).reduce((n, p, k) => n + distance(p, path[k]), 0),
        });
        if (++count >= 6) break;
      }
    };
    try {
      connect("@start", a);
      connect("@end", b);
      const nodes = this.finder.find("@start", "@end").reverse();
      if (nodes.length < 2) return null;
      const path = [];
      for (let i = 1; i < nodes.length; i++) {
        const link =
          this.graph.getLink(nodes[i - 1].id, nodes[i].id) ||
          this.graph.getLink(nodes[i].id, nodes[i - 1].id);
        const segment =
          link.fromId === nodes[i - 1].id ? link.data.path : [...link.data.path].reverse();
        path.push(...segment);
      }
      const raw = cleanPoints(path),
        result = [raw[0]];
      // Remove triangulation zigzags with certified shortcuts before sending
      // routes to the main thread. This also bounds GPU and worker-copy costs.
      for (let i = 0; i < raw.length - 1; ) {
        let next = i + 1,
          shortcut;
        const candidates = [
          ...new Set([
            raw.length - 1,
            ...[64, 32, 16, 8, 4, 2, 1].map((n) => Math.min(raw.length - 1, i + n)),
          ]),
        ];
        for (const j of candidates) {
          shortcut = simpleRoute(raw[i], raw[j], globalIndex, edge);
          if (shortcut) {
            next = j;
            break;
          }
        }
        if (!shortcut) return null;
        result.push(...shortcut.slice(1));
        i = next;
      }
      if (!globalIndex.clear(result, edge)) return null;
      const accepted = cleanPoints(result);
      if (this.paths.size > 50000) this.paths.clear();
      this.paths.set(key, accepted);
      return accepted;
    } finally {
      this.graph.removeNode("@start");
      this.graph.removeNode("@end");
    }
  }
}
