/** Semantic layers are shared by renderers, filters and the spatial layout worker. */
import { nodeType } from "./graph-core.js";
export const layers = [
  { id: "api", label: "API", color: 0x986345 },
  { id: "business", label: "Business", color: 0x208b73 },
  { id: "state", label: "States", color: 0x8c57ad },
  { id: "rules", label: "Rules", color: 0xaf731c },
  { id: "execution", label: "Functions and values", color: 0x477b9c },
  { id: "data", label: "Data structure", color: 0x638b98 },
  { id: "code", label: "Source code", color: 0x8172a3 },
];

/** Classify facts by their declared role, never by an AI-generated display name. */
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
    camera: ["angled", "front", "side", "top"].includes(value?.camera) ? value.camera : "angled",
    gap: Number.isFinite(value?.gap) ? Math.max(80, Math.min(600, value.gap)) : 260,
    only: layers.some((layer) => layer.id === value?.only) ? value.only : "all",
    projections: value?.projections !== false,
  };
}

/** A layer filter keeps endpoints together; it never manufactures a direct relation. */
export function layerSlice(graph, settings) {
  if (!settings?.enabled || settings.only === "all") return graph;
  const boxes = graph.boxes.filter((box) => layerOf(box.node) === settings.only);
  const ids = new Set(boxes.map((box) => box.id));
  return {
    ...graph,
    boxes,
    byId: new Map(boxes.map((box) => [box.id, box])),
    regions: (graph.regions || []).filter((region) => ids.has(region.id)),
    edges: graph.edges.filter((edge) => ids.has(edge.from) && ids.has(edge.to)),
  };
}
