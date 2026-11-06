/** Shared display planes; semantic concerns and capture selection stay distinct. */
import { layerPalette } from "./layer-style.js";
import { classifyNode, implementationFacets } from "./graph-classification.js";
import {
  displayLayerOf,
  displayLayerId,
  expandLayerIds,
  implementationPlanes,
} from "./implementation-planes.js";
import { projectHiddenPaths } from "./hidden-paths.js";
export { implementationFacet, implementationFacets } from "./graph-classification.js";
export { expandLayerIds } from "./implementation-planes.js";
export const canonicalLayer = displayLayerId;
export const concernOf = (node) => classifyNode(node).layer;
export const layers = [
  { id: "business", label: "Business" },
  { id: "state", label: "States" },
  { id: "rules", label: "Rules" },
  { id: "entry", label: "Entry points" },
  { id: "structure", label: "Project structure" },
  { id: "symbols", label: "Code execution" },
  { id: "unknown", label: "Unclassified" },
  { id: "data", label: "Data structure" },
].map((layer) => ({ ...layer, color: layerPalette[layer.id] }));
export const layerOf = displayLayerOf;
export const layerColor = (node) => layerPalette[layerOf(node)];
const ids = layers.map((layer) => layer.id);
const mapped = (values) => expandLayerIds(values).filter((id) => ids.includes(id));
const sliceCache = new WeakMap();
const oldDefaults = [
  ["business", "state", "rules", "implementation", "unknown", "data"],
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
  const only =
    value?.only === "implementation"
      ? "all"
      : ids.includes(canonicalLayer(value?.only))
        ? canonicalLayer(value.only)
        : "all";
  const priorOrder = Array.isArray(value?.order) ? mapped(value.order) : [];
  const same = (a, b) => a.length === b.length && a.every((id, i) => id === b[i]);
  const defaultOrder =
    value?.orderMode === "default" ||
    (value?.orderMode !== "custom" &&
      (!value?.order?.length || [ids, ...oldDefaults].some((order) => same(value.order, order))));
  const order = defaultOrder ? [...ids] : [...new Set([...priorOrder, ...ids])];
  return {
    schema: 4,
    enabled: value?.enabled === true,
    drawer: value?.drawer === true,
    compact: value?.compact === true,
    camera: ["angled", "front", "side", "top"].includes(value?.camera) ? value.camera : "top",
    gap: Number.isFinite(value?.gap) ? Math.max(80, Math.min(600, value.gap)) : 260,
    order,
    orderMode: defaultOrder ? "default" : "custom",
    only,
    visible: oldVisible
      ? mapped(oldVisible)
      : value?.only === "implementation"
        ? [...implementationPlanes]
        : ids.filter((id) => only === "all" || only === id),
    facets,
    projections: value?.projections !== false,
  };
}

/** Encode narrow legacy facets in per-view lists without changing old view IDs. */
export function savedLayerVisibility(value) {
  const config = cleanLayers(value);
  return config.visible.some((id) => implementationPlanes.includes(id)) &&
    config.facets.length < implementationFacets.length
    ? [
        ...config.visible.filter((id) => !implementationPlanes.includes(id)),
        ...config.facets.filter((facet) => config.visible.includes(displayLayerId(facet))),
      ]
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
    implementation: [...implementationPlanes],
    functions: ["symbols"],
    code: ["symbols"],
    api: ["entry"],
    project: ["structure"],
    database: ["data"],
    "data-access": ["symbols", "data"],
    "data-operations": ["symbols", "data"],
    resources: [...ids],
    data: [...ids],
    runtime: [...ids],
    blocked: [...ids],
    shared: [...ids],
  };
  // Built-in views are stable templates. Per-view visibility belongs to custom
  // views only; otherwise a prior manual edit can make a preset appear empty.
  return presets[id] || (Array.isArray(visible) ? [...visible] : [...ids]);
}
/** Only occupied, visible display layers reserve a plane. */
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
    (concernOf(node) !== "implementation" || config.facets.includes(classifyNode(node).facet));
  const boxes = graph.boxes.filter((box) => accepts(box.node));
  if (
    boxes.length === graph.boxes.length &&
    (!graph.all || ![...graph.all.values()].some((node) => !accepts(node)))
  )
    return graph;
  // Static previews can supply boxes without the runtime inventory indexes.
  // Build their declaration lookup once; never infer a missing folded endpoint.
  const declarations = graph.all || new Map(graph.boxes.map((box) => [box.id, box.node]));
  const visibleIds = new Set(boxes.map((box) => box.id));
  // A folded endpoint keeps its original layer. A call to a hidden function
  // must not become a direct call to the enclosing business action.
  const acceptsRelation = (edge) =>
    [edge.from, edge.to].every((id) => {
      const node = declarations.get(id);
      return node && accepts(node);
    });
  const directEdges = graph.edges
    .filter((edge) => visibleIds.has(edge.from) && visibleIds.has(edge.to))
    .flatMap((edge) => {
      const members = (edge.members || [edge]).filter(acceptsRelation);
      return members.length
        ? [
            {
              ...edge,
              members,
              labels: new Set(members.map((member) => member.label).filter(Boolean)),
              observed: members.some((member) => member.observed),
              current: members.some((member) => member.current),
            },
          ]
        : [];
    });
  // Counts and expansion controls describe children available in this view,
  // including a visible descendant beneath an intermediate hidden plane.
  const eligible = new Set(
    [...declarations]
      .filter(
        ([id, node]) =>
          accepts(node) &&
          (!graph.eligibleIds || graph.eligibleIds.has(id)) &&
          (!exclusions.nodeAllowed || exclusions.nodeAllowed(node)),
      )
      .map(([id]) => id),
  );
  const expansionChildren = new Map();
  for (const id of eligible) {
    const seen = new Set([id]);
    let parent = declarations.get(id)?.parent;
    while (parent && !seen.has(parent) && !eligible.has(parent)) {
      seen.add(parent);
      parent = declarations.get(parent)?.parent;
    }
    if (!parent || seen.has(parent)) continue;
    if (!expansionChildren.has(parent)) expansionChildren.set(parent, []);
    expansionChildren.get(parent).push(id);
  }
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
    edges: [...directEdges, ...projection.edges],
    acceptsRelation,
    expansionChildren,
    projection,
  };
  if (exclusions.cacheKey !== undefined) sliceCache.set(graph, { key, value });
  return value;
}

/** Shared 2D/3D expansion affordance; hidden-layer children stay in the inventory. */
export function displayChildren(graph, id) {
  return graph?.expansionChildren
    ? graph.expansionChildren.get(id) || []
    : (graph?.byId?.get(id) || graph?.boxes?.find((box) => box.id === id))?.kids || [];
}
