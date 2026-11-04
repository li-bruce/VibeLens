/** Shared concern planes. Source granularity and capture selection are facets. */
import { layerPalette } from "./layer-style.js";
import { classifyNode, canonicalLayer, implementationFacets } from "./graph-classification.js";
import { projectHiddenPaths } from "./hidden-paths.js";
export {
  canonicalLayer,
  implementationFacet,
  implementationFacets,
} from "./graph-classification.js";
export const layers = [
  { id: "business", label: "Business" },
  { id: "state", label: "States" },
  { id: "rules", label: "Rules" },
  { id: "implementation", label: "Implementation" },
  { id: "unknown", label: "Unclassified" },
  { id: "data", label: "Data structure" },
].map((layer) => ({ ...layer, color: layerPalette[layer.id] }));
export const layerOf = (node) => classifyNode(node).layer;
export const layerColor = (node) => layerPalette[layerOf(node)];
const ids = layers.map((layer) => layer.id);
const mapped = (values) =>
  [...new Set(values.map(canonicalLayer))].filter((id) => ids.includes(id));
const sliceCache = new WeakMap();
const oldDefaults = [
  ["business", "state", "rules", "api", "execution", "project", "code", "operations", "data"],
  ["business", "state", "rules", "api", "execution", "operations", "project", "code", "data"],
  ["api", "business", "state", "rules", "operations", "execution", "data", "project", "code"],
  ["api", "business", "state", "rules", "operations", "execution", "data", "code"],
];

/** Preserve custom order, facet exclusions, coordinates and identities on upgrade. */
export function cleanLayers(value) {
  const oldVisible = Array.isArray(value?.visible) ? value.visible : null;
  const legacyFacetSelection = oldVisible?.some((id) => implementationFacets.includes(id));
  const facets = legacyFacetSelection
    ? implementationFacets.filter((id) => oldVisible.includes(id))
    : Array.isArray(value?.facets)
      ? implementationFacets.filter((id) => value.facets.includes(id))
      : implementationFacets.includes(value?.only)
        ? [value.only]
        : [...implementationFacets];
  const only = ids.includes(canonicalLayer(value?.only)) ? canonicalLayer(value.only) : "all";
  const priorOrder = Array.isArray(value?.order) ? mapped(value.order) : [];
  const same = (a, b) => a.length === b.length && a.every((id, i) => id === b[i]);
  const defaultOrder =
    value?.orderMode === "default" ||
    (value?.orderMode !== "custom" &&
      (!value?.order?.length || [ids, ...oldDefaults].some((order) => same(value.order, order))));
  const order = defaultOrder ? [...ids] : [...new Set([...priorOrder, ...ids])];
  return {
    schema: 3,
    enabled: value?.enabled === true,
    drawer: value?.drawer === true,
    compact: value?.compact === true,
    camera: ["angled", "front", "side", "top"].includes(value?.camera) ? value.camera : "top",
    gap: Number.isFinite(value?.gap) ? Math.max(80, Math.min(600, value.gap)) : 260,
    order,
    orderMode: defaultOrder ? "default" : "custom",
    only,
    visible: oldVisible ? mapped(oldVisible) : ids.filter((id) => only === "all" || only === id),
    facets,
    projections: value?.projections !== false,
  };
}

/** Encode narrow legacy facets in per-view lists without changing old view IDs. */
export function savedLayerVisibility(value) {
  const config = cleanLayers(value);
  return config.visible.includes("implementation") &&
    config.facets.length < implementationFacets.length
    ? [...config.visible.filter((id) => id !== "implementation"), ...config.facets]
    : [...config.visible];
}
export function cleanLayerVisibility(value, legacy) {
  const result = Object.create(null);
  if (value && typeof value === "object" && !Array.isArray(value))
    for (const [id, visible] of Object.entries(value).slice(0, 40))
      if (/^[a-z][a-z0-9-]{0,79}$/.test(id) && Array.isArray(visible))
        result[id] = savedLayerVisibility({ visible });
  if (!Object.hasOwn(result, "overview"))
    result.overview = legacy ? savedLayerVisibility(legacy) : ["business", "state", "rules"];
  return result;
}
export function visibilityForView(settings, id) {
  const visible = settings.layerVisibility?.[id];
  const presets = {
    overview: ["business", "state", "rules"],
    business: ["business"],
    states: ["state"],
    rules: ["rules"],
    permission: ["business", "state", "rules"],
    implementation: ["implementation"],
    functions: ["implementation"],
    code: ["implementation"],
    api: ["implementation"],
    project: ["implementation"],
    database: ["data"],
    "data-access": ["implementation", "data"],
    "data-operations": ["implementation", "data"],
  };
  return Array.isArray(visible) ? [...visible] : presets[id] || [...ids];
}
/** Only occupied, visible concerns reserve a plane. */
export function layerHeights(settings, scope = layers) {
  const config = cleanLayers(settings),
    result = new Map();
  const order = config.order.filter(
    (id) => config.visible.includes(id) && scope.some((layer) => layer.id === id),
  );
  for (let i = order.length - 1; i >= 0; i--)
    result.set(order[i], (order.length - 1 - i) * config.gap);
  return result;
}

/** Abstract hidden planes, retaining original facts and inspectable typed paths. */
export function layerSlice(graph, settings, exclusions = {}) {
  const config = cleanLayers(settings);
  const key = JSON.stringify([
    config.visible,
    config.facets,
    config.projections,
    exclusions.cacheKey,
  ]);
  const cached = sliceCache.get(graph);
  if (cached?.key === key) return cached.value;
  const accepts = (node) =>
    config.visible.includes(layerOf(node)) &&
    (layerOf(node) !== "implementation" || config.facets.includes(classifyNode(node).facet));
  const boxes = graph.boxes.filter((box) => accepts(box.node));
  if (
    boxes.length === graph.boxes.length &&
    (!graph.all || ![...graph.all.values()].some((node) => !accepts(node)))
  )
    return graph;
  const visibleIds = new Set(boxes.map((box) => box.id));
  const projection = !config.projections
    ? {
        edges: [],
        search_complete: true,
        witnesses_complete: true,
        disabled: true,
      }
    : graph.all && graph.rawEdges
      ? projectHiddenPaths(graph, { visibleIds, accepts, ...exclusions })
      : {
          edges: [],
          search_complete: false,
          witnesses_complete: false,
          unavailable: "Full inventory unavailable",
        };
  const value = {
    ...graph,
    boxes,
    byId: new Map(boxes.map((box) => [box.id, box])),
    regions: (graph.regions || []).filter((region) => visibleIds.has(region.id)),
    edges: [
      ...graph.edges.filter((edge) => visibleIds.has(edge.from) && visibleIds.has(edge.to)),
      ...projection.edges,
    ],
    projection,
  };
  if (exclusions.cacheKey !== undefined) sliceCache.set(graph, { key, value });
  return value;
}
