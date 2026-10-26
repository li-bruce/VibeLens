/** Certified routes: R-tree broad phase, bounded local libavoid, typed D3 bundles. */
import {
  ObstacleIndex,
  simpleRoute,
  freePortal,
  smoothRoute,
  cleanPoints,
  distance,
} from "./routing-geometry.js";
import { stratify } from "./routing-tools.vendor.js";
import { shapedPath } from "./route-shapes.js";
import { Navigation } from "./routing-navigation.js";
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

function wasmRoute(a, b, index, edge, A, stats) {
  let hits = index.collisions([a, b], edge, 5);
  for (let round = 0; round < 5 && hits.length <= 96; round++) {
    const router = new A.Router(A.OrthogonalRouting),
      owned = [];
    const point = (p) => {
      const value = new A.Point(p.x, p.y);
      owned.push(value);
      return value;
    };
    let output;
    try {
      for (const name of [
        "nudgeSharedPathsWithCommonEndPoint",
        "nudgeOrthogonalSegmentsConnectedToShapes",
        "performUnifyingNudgingPreprocessingStep",
        "nudgeOrthogonalTouchingColinearSegments",
      ])
        router.setRoutingOption(A[name], false);
      router.setRoutingParameter(A.shapeBufferDistance, 1);
      router.setRoutingParameter(A.segmentPenalty, 12);
      for (const o of hits) {
        // Circumscribed polygons follow the actual circles. A bounding square
        // would incorrectly swallow nearby endpoints outside a round region.
        const polygon = new A.Polygon(16),
          radius = o.r / Math.cos(Math.PI / 16);
        for (let i = 0; i < 16; i++)
          polygon.setPoint(
            i,
            point({
              x: o.x + Math.cos((i * Math.PI) / 8) * radius,
              y: o.y + Math.sin((i * Math.PI) / 8) * radius,
            }),
          );
        new A.ShapeRef(router, polygon);
        owned.push(polygon);
      }
      const from = new A.ConnEnd(point(a)),
        to = new A.ConnEnd(point(b));
      owned.push(from, to);
      const connector = new A.ConnRef(router, from, to);
      router.processTransaction();
      stats.wasm++;
      const path = connector.displayRoute();
      output = Array.from({ length: path.size() }, (_, i) => {
        const p = path.get_ps(i);
        return { x: p.x, y: p.y };
      });
    } finally {
      A.destroy(router);
      // Router owns its ShapeRefs/ConnRefs, but not these temporary WebIDL values.
      for (const value of owned.reverse()) A.destroy(value);
    }
    if (!output?.length || distance(output[0], a) > 0.1 || distance(output.at(-1), b) > 0.1)
      return null;
    const extra = index.collisions(output, edge, 1);
    if (!extra.length) return cleanPoints(output);
    const merged = new Map([...hits, ...extra].map((o) => [o.key, o]));
    if (merged.size === hits.length) return null;
    hits = [...merged.values()];
  }
  return null;
}

/** Actual parent paths group compatible edges; a spatial cell handles flat source graphs. */
function bundleKeys(scene) {
  const records = [
    { id: "__routing_root__", parent: null },
    ...scene.parents.map((n) => ({ id: n.id, parent: n.parent || "__routing_root__" })),
  ];
  let owners = new Map();
  try {
    const tree = stratify()
      .id((n) => n.id)
      .parentId((n) => n.parent)(records);
    owners = new Map(tree.descendants().map((n) => [n.id, n.parent?.id]));
  } catch {
    /* Incomplete presentation parents use spatial cells, without repairing model facts. */
  }
  const cell = (id, p) =>
    owners.get(id) && owners.get(id) !== "__routing_root__"
      ? owners.get(id)
      : `${Math.floor(p.x / 320)},${Math.floor(p.y / 320)}`;
  return (e) => `${e.type}|${e.a.level}:${cell(e.from, e.a)}>${e.b.level}:${cell(e.to, e.b)}`;
}

/** Yield between small solves so a newer drag/expansion can cancel this epoch. */
export async function routeScene(
  scene,
  A,
  cache = new Map(),
  emit = () => {},
  cancelled = () => false,
) {
  const started = performance.now(),
    result = new Map(),
    stats = { wasm: 0, cached: 0, bundles: 0, routed: 0, unresolved: 0, total: scene.edges.length };
  const levels = [
    ...new Set(
      scene.obstacles
        .map((o) => o.level)
        .concat(scene.edges.flatMap((e) => [e.a.level, e.b.level])),
    ),
  ];
  const indices = new Map(
    levels.map((level) => [
      level,
      new ObstacleIndex(scene.obstacles.filter((o) => o.level === level)),
    ]),
  );
  const columns = new Map();
  const signature = JSON.stringify(scene.obstacles);
  if (cache.navigationSignature !== signature) {
    cache.navigationSignature = signature;
    cache.navigation = new Map();
  }
  const navigation = cache.navigation;
  const columnIndex = (a, b) => {
    const lo = Math.min(a, b),
      hi = Math.max(a, b),
      key = `${lo}:${hi}`;
    if (!columns.has(key))
      columns.set(
        key,
        new ObstacleIndex(scene.obstacles.filter((o) => o.level >= lo && o.level <= hi)),
      );
    return columns.get(key);
  };
  const solve = (a, b, index, edge, smooth = scene.style === "curve") => {
    if (!index.free(a, edge) || !index.free(b, edge)) return null;
    let points = simpleRoute(a, b, index, edge, scene.style !== "straight");
    if (!points && index.items.length > 80) {
      const level = index.items[0]?.level;
      if (!navigation.has(level)) navigation.set(level, new Navigation(index));
      points = navigation.get(level).find(a, b, edge, index);
      if (points) stats.navigation = (stats.navigation || 0) + 1;
    }
    if (!points) points = wasmRoute(a, b, index, edge, A, stats);
    if (!points && index.items.length <= 80) {
      points = new Navigation(index, edge).find(a, b, edge, index);
      if (points) stats.navigation = (stats.navigation || 0) + 1;
    }
    return points && (smooth ? smoothRoute(points, index, edge) : points);
  };
  const groups = new Map(),
    keyFor = bundleKeys(scene);
  for (const e of scene.edges) {
    const key = scene.style === "bus" ? keyFor(e) : e.id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(e);
  }
  let lastYield = performance.now(),
    chunk = new Map();
  for (const group of groups.values()) {
    if (cancelled()) return null;
    let trunk = null,
      portals,
      column;
    if (group.length > 1 && scene.style === "bus" && group[0].a.level === group[0].b.level) {
      const index = indices.get(group[0].a.level),
        average = (side) => ({
          x: group.reduce((n, e) => n + e[side].x, 0) / group.length,
          y: group.reduce((n, e) => n + e[side].y, 0) / group.length,
        });
      const source = average("a"),
        target = average("b"),
        common = { from: "", to: "", a: source, b: target, allowed: [] };
      // Shared trunks exclude no member glyph. Each branch still retains its own edge identity.
      const p = freePortal(
        { x: source.x * 0.7 + target.x * 0.3, y: source.y * 0.7 + target.y * 0.3 },
        index,
        common,
      );
      const q = freePortal(
        { x: source.x * 0.3 + target.x * 0.7, y: source.y * 0.3 + target.y * 0.7 },
        index,
        common,
      );
      if (p && q) {
        trunk = solve(p, q, index, common, false);
        portals = [p, q];
      }
      if (trunk) stats.bundles++;
    }
    if (group.length > 1 && scene.style === "bus" && group[0].a.level !== group[0].b.level) {
      const edge = group[0],
        combined = columnIndex(edge.a.level, edge.b.level);
      const a = {
        x: group.reduce((n, e) => n + e.a.x, 0) / group.length,
        y: group.reduce((n, e) => n + e.a.y, 0) / group.length,
      };
      const b = {
        x: group.reduce((n, e) => n + e.b.x, 0) / group.length,
        y: group.reduce((n, e) => n + e.b.y, 0) / group.length,
      };
      column = freePortal({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, combined, {
        from: "",
        to: "",
        a,
        b,
      });
      if (column) stats.bundles++;
    }
    for (const edge of group) {
      const aIndex = indices.get(edge.a.level),
        bIndex = indices.get(edge.b.level);
      const key = JSON.stringify([scene.style, edge, portals, column]),
        saved = cache.get(key);
      let points;
      // Cached paths are checked against the NEW global obstacle index. Moving an
      // unrelated node therefore invalidates paths as well as incident edges.
      if (["straight", "curve"].includes(scene.style)) {
        // Shape is a user choice. Avoidance may bend a curve, never a straight
        // edge. A geometric intersection is reported separately, not omitted.
        points = shapedPath(edge, scene.style, 1, scene.edges.length > 5000 ? 12 : 24);
        const clear = (path) => {
          if (edge.a.level === edge.b.level) return aIndex.clear(path, edge);
          // Test the actual crossing point at each occupied semantic plane.
          return levels
            .filter(
              (n) =>
                n >= Math.min(edge.a.level, edge.b.level) &&
                n <= Math.max(edge.a.level, edge.b.level),
            )
            .every((n) => {
              const i = Math.max(
                1,
                path.findIndex((p) => (edge.a.level < edge.b.level ? p.level >= n : p.level <= n)),
              );
              const a = path[i - 1],
                b = path[i],
                t = (n - a.level) / (b.level - a.level || 1);
              return indices
                .get(n)
                .free({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }, edge);
            });
        };
        if (scene.style === "curve" && !clear(points)) {
          for (const bend of [-1, 2, -2, 4, -4]) {
            const candidate = shapedPath(edge, "curve", bend, scene.edges.length > 5000 ? 12 : 24);
            if (clear(candidate)) {
              points = candidate;
              break;
            }
          }
        }
        if (!clear(points)) stats.intersections = (stats.intersections || 0) + 1;
      } else if (
        saved &&
        saved.every(
          (p, i) =>
            !i ||
            (p.level === saved[i - 1].level
              ? indices.get(p.level).clear([saved[i - 1], p], edge)
              : levels
                  .filter(
                    (n) =>
                      n >= Math.min(p.level, saved[i - 1].level) &&
                      n <= Math.max(p.level, saved[i - 1].level),
                  )
                  .every((n) => indices.get(n).free(p, { ...edge, from: "", to: "" }))),
        )
      ) {
        points = saved;
        stats.cached++;
      } else if (edge.a.level === edge.b.level) {
        let path;
        if (edge.from === edge.to && distance(edge.a, edge.b) < 1) {
          const p = edge.a;
          path = [
            p,
            { x: p.x + 70, y: p.y },
            { x: p.x + 70, y: p.y - 80 },
            { x: p.x - 70, y: p.y - 80 },
            { x: p.x - 70, y: p.y },
            p,
          ];
          if (!aIndex.clear(path, edge)) path = null;
        } else if (trunk) {
          const first = solve(edge.a, portals[0], aIndex, edge, false),
            last = solve(portals[1], edge.b, aIndex, edge, false);
          if (first && last) path = cleanPoints([...first, ...trunk, ...last]);
          if (path && !aIndex.clear(path, edge)) path = null;
        }
        path ||= solve(edge.a, edge.b, aIndex, edge);
        points = path?.map((p) => ({ ...p, level: edge.a.level }));
      } else {
        const combined = columnIndex(edge.a.level, edge.b.level);
        const portal =
          column ||
          freePortal({ x: (edge.a.x + edge.b.x) / 2, y: (edge.a.y + edge.b.y) / 2 }, combined, {
            ...edge,
            from: "",
            to: "",
          });
        if (portal) {
          const first = solve(edge.a, portal, aIndex, edge),
            last = solve(portal, edge.b, bIndex, edge);
          if (first && last)
            points = [
              ...first.map((p) => ({ ...p, level: edge.a.level })),
              ...last.map((p) => ({ ...p, level: edge.b.level })),
            ];
        }
      }
      if (points?.length >= 2) {
        cache.set(key, points);
        result.set(edge.id, points);
        chunk.set(edge.id, points);
        stats.routed++;
      } else {
        stats.unresolved++;
        if ((stats.failures ||= []).length < 20) stats.failures.push(edge.id);
      }
      if (performance.now() - lastYield > 24) {
        emit(chunk, { ...stats, elapsed: performance.now() - started, busy: true });
        chunk = new Map();
        await tick();
        lastYield = performance.now();
        if (cancelled()) return null;
      }
    }
  }
  // Bound cache memory over repeated edits; current scene paths remain reusable.
  if (cache.size > Math.max(1000, scene.edges.length * 3)) cache.clear();
  emit(chunk, { ...stats, elapsed: performance.now() - started, busy: false });
  return { routes: result, stats };
}
