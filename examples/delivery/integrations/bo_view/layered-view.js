import { t } from "./i18n.js";
import { nodeType, graphBounds } from "./graph-core.js";
import { refreshHierarchy } from "./layout.js";

// This is a projection of the same graph, not a second model or layout store.
export const layers = [
  { id: "api", label: "API", color: 0x986345 },
  { id: "business", label: "Business", color: 0x208b73 },
  { id: "state", label: "States", color: 0x8c57ad },
  { id: "rules", label: "Rules", color: 0xaf731c },
  { id: "execution", label: "Functions and values", color: 0x477b9c },
  { id: "data", label: "Data structure", color: 0x638b98 },
  { id: "code", label: "Source code", color: 0x8172a3 },
];
const cameras = {
  angled: { yaw: -0.24, pitch: 0.72 },
  front: { yaw: 0, pitch: 0.36 },
  side: { yaw: 0.65, pitch: 0.86 },
};
export function layerOf(node) {
  const type = nodeType(node);
  if (node.code_role === "endpoint") return "api";
  if (node.code_role || ["python-ast", "source-ast"].includes(node.origin)) return "code";
  if (type === "business") return "business";
  if (["state", "wait"].includes(type)) return "state";
  if (["decision", "resource"].includes(type)) return "rules";
  if (["store", "dataset", "column"].includes(type)) return "data";
  return "execution";
}
export function cleanLayers(value) {
  return {
    enabled: value?.enabled === true,
    camera: Object.hasOwn(cameras, value?.camera) ? value.camera : "angled",
    gap: Number.isFinite(value?.gap) ? Math.max(80, Math.min(600, value.gap)) : 260,
    only: layers.some((layer) => layer.id === value?.only) ? value.only : "all",
  };
}
/** Orthographic yaw/pitch projection: node labels remain screen-facing. */
export function projection(settings) {
  const { yaw, pitch } = cameras[settings.camera],
    cy = Math.cos(yaw),
    sy = Math.sin(yaw),
    cp = Math.cos(pitch),
    sp = Math.sin(pitch);
  return {
    point(x, y, z) {
      return { x: cy * x - sy * y, y: cp * (sy * x + cy * y) - sp * z };
    },
    delta(x, y) {
      return { x: cy * x + (sy * y) / cp, y: -sy * x + (cy * y) / cp };
    },
  };
}

export function projectLayers(graph, rawSettings) {
  const settings = cleanLayers(rawSettings);
  if (!settings.enabled) return graph;
  const camera = projection(settings),
    visible = graph.boxes.filter(
      (b) => settings.only === "all" || layerOf(b.node) === settings.only,
    ),
    activeLayers = layers.filter((layer) => visible.some((b) => layerOf(b.node) === layer.id)),
    depthOf = (id) =>
      (activeLayers.length - activeLayers.findIndex((layer) => layer.id === id) - 1) *
      settings.gap *
      3,
    ids = new Set(visible.map((b) => b.id)),
    all = new Map(
      [...graph.all].map(([id, node]) => {
        const parent = graph.all.get(node.parent);
        return [
          id,
          {
            ...node,
            parent: parent && layerOf(parent) === layerOf(node) ? node.parent : undefined,
          },
        ];
      }),
    ),
    boxes = visible.map((b) => {
      const layer = layerOf(b.node),
        z = depthOf(layer),
        p = camera.point(b.x + b.w / 2, b.y + 31, z);
      return { ...b, node: all.get(b.id), x: p.x - b.w / 2, y: p.y - 31, layer, z };
    });
  const result = {
    ...graph,
    all,
    boxes,
    byId: new Map(boxes.map((b) => [b.id, b])),
    layered: true,
    edges: graph.edges.filter((e) => ids.has(e.from) && ids.has(e.to)),
    regions: [],
    planes: [],
  };
  // Cross-layer containment needs a line once its common enclosure is separated.
  for (const b of visible) {
    const parent = graph.byId.get(b.node.parent);
    if (!parent || !ids.has(parent.id) || layerOf(parent.node) === layerOf(b.node)) continue;
    if (result.edges.some((e) => e.type === "contains" && e.from === parent.id && e.to === b.id))
      continue;
    result.edges.push({
      id: `layer-parent:${parent.id}:${b.id}`,
      from: parent.id,
      to: b.id,
      type: "contains",
      label: t("Contains"),
      origin: "node-parent",
    });
  }
  refreshHierarchy(result);
  const margin = 130;
  // Parallel planes use one world extent, so crossing lines retain spatial context.
  const minX = Math.min(...visible.map((b) => b.x), 0) - margin,
    minY = Math.min(...visible.map((b) => b.y), 0) - margin,
    maxX = Math.max(...visible.map((b) => b.x + b.w), 180) + margin,
    maxY = Math.max(...visible.map((b) => b.y + b.h), 150) + margin;
  for (const [index, layer] of layers.entries()) {
    if (!boxes.some((b) => b.layer === layer.id)) continue;
    const z = depthOf(layer.id);
    result.planes.push({
      ...layer,
      label: t(layer.label),
      z,
      points: [
        [minX, minY],
        [maxX, minY],
        [maxX, maxY],
        [minX, maxY],
      ].map(([x, y]) => camera.point(x, y, z)),
    });
  }
  graphBounds(result);
  const points = result.planes.flatMap((p) => p.points);
  if (points.length) {
    const right = Math.max(result.minX + result.width, ...points.map((p) => p.x)) + 30,
      bottom = Math.max(result.minY + result.height, ...points.map((p) => p.y)) + 30;
    result.minX = Math.min(result.minX, ...points.map((p) => p.x)) - 30;
    result.minY = Math.min(result.minY, ...points.map((p) => p.y)) - 45;
    result.width = right - result.minX;
    result.height = bottom - result.minY;
  }
  return result;
}

/** Convert a drag on a projected plane back into the persistent 2D layout. */
export function unprojectMove(original, displayed, x, y, settings) {
  const delta = projection(cleanLayers(settings)).delta(x - displayed.x, y - displayed.y);
  return { x: original.x + delta.x, y: original.y + delta.y };
}
