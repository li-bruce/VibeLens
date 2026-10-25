/** Semantic layers are shared by renderers, filters and the spatial layout worker. */
import { nodeType } from "./graph-core.js";
export const layers = [
  { id: "api", label: "API", color: 0x986345 },
  { id: "business", label: "Business", color: 0x208b73 },
  { id: "state", label: "States", color: 0x8c57ad },
  { id: "rules", label: "Rules", color: 0xaf731c },
  { id: "operations", label: "Data operations", color: 0x3b839c },
  { id: "execution", label: "Functions and values", color: 0x477b9c },
  { id: "data", label: "Data structure", color: 0x638b98 },
  { id: "code", label: "Source code", color: 0x8172a3 },
];

/** Classify facts by their declared role, never by an AI-generated display name. */
export function layerOf(node) {
  const type = nodeType(node);
  if (["query", "transform"].includes(node.data_role || node.capture_owner_role))
    return "operations";
  if (node.code_role === "endpoint") return "api";
  if (node.code_role || ["python-ast", "source-ast"].includes(node.origin)) return "code";
  if (type === "business") return "business";
  if (["state", "wait"].includes(type)) return "state";
  if (["decision", "resource"].includes(type)) return "rules";
  if (["store", "dataset", "column"].includes(type)) return "data";
  return "execution";
}

export function cleanLayers(value) {
  const only = layers.some((layer) => layer.id === value?.only) ? value.only : "all";
  const ids = layers.map((layer) => layer.id);
  const order = [...new Set([...(Array.isArray(value?.order) ? value.order : []), ...ids])].filter(
    (id) => ids.includes(id),
  );
  return {
    enabled: value?.enabled === true,
    drawer: value?.drawer === true,
    compact: value?.compact === true,
    camera: ["angled", "front", "side", "top"].includes(value?.camera) ? value.camera : "top",
    gap: Number.isFinite(value?.gap) ? Math.max(80, Math.min(600, value.gap)) : 260,
    order,
    gaps: Object.fromEntries(
      ids
        .filter((id) => Number.isFinite(value?.gaps?.[id]))
        .map((id) => [id, Math.max(80, Math.min(600, value.gaps[id]))]),
    ),
    only,
    visible: Array.isArray(value?.visible)
      ? layers.filter((layer) => value.visible.includes(layer.id)).map((layer) => layer.id)
      : layers.filter((layer) => only === "all" || only === layer.id).map((layer) => layer.id),
    projections: value?.projections !== false,
  };
}

/** A hidden layer keeps its slot. Gaps belong to the layer immediately above them. */
export function layerHeights(settings, scope = layers) {
  const config = cleanLayers(settings),
    result = new Map();
  config.order = config.order.filter((id) => scope.some((layer) => layer.id === id));
  let height = 0;
  for (let i = config.order.length - 1; i >= 0; i--) {
    const id = config.order[i];
    if (i < config.order.length - 1) height += config.gaps[id] ?? config.gap;
    result.set(id, height);
  }
  return result;
}

/** A layer filter keeps endpoints together; it never manufactures a direct relation. */
export function layerSlice(graph, settings) {
  const visible = cleanLayers(settings).visible;
  if (visible.length === layers.length) return graph;
  const boxes = graph.boxes.filter((box) => visible.includes(layerOf(box.node)));
  const ids = new Set(boxes.map((box) => box.id));
  return {
    ...graph,
    boxes,
    byId: new Map(boxes.map((box) => [box.id, box])),
    regions: (graph.regions || []).filter((region) => ids.has(region.id)),
    edges: graph.edges.filter((edge) => ids.has(edge.from) && ids.has(edge.to)),
  };
}
