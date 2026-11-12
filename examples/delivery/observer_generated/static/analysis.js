import { machinesOf, networkCatalog, networkViewId } from "./model-networks.js";
import { t as boTranslate } from "./i18n.js";
// View selection is a projection. It cannot add permission, call or runtime facts.
import { viewTypes, relationType, stateNodeId } from "./graph-core.js";
import { dataRoles, dataRelations, migrateDataFilters } from "./data-layer.js";
import { codeTypes, codeRelations, migrateCodeFilters } from "./code-layer.js";
import { concernOf } from "./graph-layers.js";
import { conceptRelationTypes } from "./concept-relations.js";
import { relationTypeAllowed } from "./edge-identities.js";
const types = [
  "business",
  "function",
  "state",
  "decision",
  "resource",
  "data",
  "effect",
  "wait",
  "unknown",
  ...dataRoles,
  ...codeTypes,
];
const edges = [
  "indirect",
  "call",
  "flow",
  "transition",
  "guard",
  "data",
  "resource",
  "join",
  "shared",
  "other",
  "contains",
  ...dataRelations,
  ...codeRelations,
  ...conceptRelationTypes,
];
export const presets = [
  {
    id: "overview",
    label: boTranslate("Behavior"),
    group: "Behavior",
    hierarchical: true,
    nodes: types,
    edges,
  },
  {
    id: "business",
    group: "Behavior",
    label: boTranslate("Business flow"),
    nodes: ["business"],
    edges: ["flow", "guard", "data", "join"],
    scope: "business",
  },
  {
    id: "project",
    group: "Implementation",
    label: boTranslate("Project structure"),
    hierarchical: true,
    nodes: ["code-directory", "code-file", "code-unresolved"],
    edges: ["code-contains", "code-imports", "code-exports", "code-links", "code-dependency"],
    codeTypes: 4,
  },
  {
    id: "code",
    group: "Implementation",
    label: boTranslate("Code structure"),
    hierarchical: true,
    nodes: codeTypes,
    edges: codeRelations,
    codeTypes: 4,
  },
  {
    id: "api",
    group: "Implementation",
    label: boTranslate("API entries"),
    hierarchical: true,
    nodes: ["code-endpoint", "code-function", "code-parameter", "code-file"],
    edges: ["code-handles", "code-calls", "code-parameter", "code-maps"],
    codeTypes: 4,
  },
  {
    id: "states",
    group: "Behavior",
    label: boTranslate("State machine"),
    nodes: types,
    edges,
    scope: "state",
  },
  {
    id: "rules",
    group: "Behavior",
    label: boTranslate("Rule network"),
    nodes: types,
    edges,
    scope: "rules",
  },
  {
    id: "implementation",
    group: "Implementation",
    label: boTranslate("Implementation"),
    hierarchical: true,
    nodes: types,
    edges,
    scope: "implementation",
  },
  {
    id: "functions",
    group: "Implementation",
    label: boTranslate("Functions and parameters"),
    fields: "all",
    nodes: [
      "function",
      "decision",
      "data",
      "query",
      "write",
      "transaction",
      "transform",
      "code-function",
      "code-parameter",
      "code-reference",
    ],
    // Physical declarations and contextual observed functions use distinct
    // relation families. Selecting both node families must retain both links.
    edges: ["call", "data", "code-calls", "code-parameter", "code-maps", ...dataRelations],
  },
  {
    id: "permission",
    group: "Behavior",
    label: boTranslate("Authorization"),
    nodes: ["business", "decision", "function", "data", "wait"],
    edges: ["guard", "data", "call", "flow"],
    scope: "permission",
  },
  {
    id: "resources",
    group: "Behavior",
    label: boTranslate("Concurrency and resources"),
    nodes: ["function", "resource", "decision", "state", "wait", "data"],
    edges: ["resource", "join", "transition", "data"],
    scope: "execution",
  },
  {
    id: "data",
    group: "Data",
    label: boTranslate("Data dependencies"),
    fields: "all",
    nodes: ["function", "decision", "data", "effect", ...dataRoles],
    edges: ["data", "guard", "call", ...dataRelations],
  },
  {
    id: "database",
    group: "Data",
    label: boTranslate("Database structure"),
    nodes: ["store", "dataset", "column"],
    edges: ["references", "maps"],
  },
  {
    id: "data-operations",
    group: "Data",
    label: boTranslate("Queries and data processing"),
    nodes: ["query", "write", "transaction", "transform"],
    edges: ["call", "data", "reads", "writes", "transforms", "maps"],
  },
  {
    id: "data-access",
    group: "Data",
    label: boTranslate("Data access"),
    nodes: types,
    edges: [
      "call",
      "data",
      "reads",
      "writes",
      "transforms",
      "maps",
      "code-maps",
      "code-calls",
      "indirect",
    ],
  },
  {
    id: "runtime",
    group: "Analysis",
    label: boTranslate("Observed execution"),
    nodes: types,
    edges,
    scope: "observed",
  },
  {
    id: "blocked",
    group: "Analysis",
    label: boTranslate("Waiting and failures"),
    nodes: types,
    edges,
    scope: "blocked",
  },
  {
    id: "shared",
    group: "Analysis",
    label: boTranslate("Shared membership"),
    nodes: types,
    edges: ["shared"],
    scope: "shared",
  },
];
export function cleanProfile(value) {
  value = migrateCodeFilters(migrateDataFilters(value));
  if (value?.conceptTypes !== 1 && value?.edges?.includes("other"))
    value = { ...value, edges: [...value.edges, ...conceptRelationTypes] };
  const strings = (values, allowed) =>
    Array.isArray(values)
      ? [...new Set(values.filter((x) => allowed.includes(x)))]
      : allowed.slice();
  return {
    dataTypes: 2,
    conceptTypes: 1,
    codeTypes: 4,
    nodes: strings(value?.nodes, types),
    edges: strings(value?.edges, edges),
    regions: strings(value?.regions, types),
    depth: Number.isInteger(value?.depth) ? value.depth : "all",
    fields: value?.fields === "all" ? "all" : "selected",
    scope: [
      "all",
      "business",
      "permission",
      "execution",
      "observed",
      "blocked",
      "shared",
      "rules",
      "state",
      "implementation",
    ].includes(value?.scope)
      ? value.scope
      : "all",
    query: typeof value?.query === "string" ? value.query.trim().slice(0, 100) : "",
    networks: Array.isArray(value?.networks)
      ? [...new Set(value.networks.filter((id) => typeof id === "string" && id))]
      : [],
    hierarchical: value?.hierarchical === true,
  };
}
export function profileFor(id, custom = []) {
  const preset = presets.find((p) => p.id === id);
  return cleanProfile(
    preset
      ? { ...preset, dataTypes: 2, codeTypes: 4 }
      : custom.find((p) => p.id === id) || { ...presets[0], dataTypes: 2 },
  );
}
/** Each named subnetwork reuses the normal view/filter/layout pipeline. */
export function networkProfiles(view) {
  return networkCatalog(view).map((network) => ({
    ...cleanProfile(),
    id: networkViewId(network),
    group: "Networks",
    label: typeof network.label === "string" ? network.label : network.id,
    layer: network.layer,
    networks: [network.id],
    hierarchical: true,
  }));
}
export function matchingNodes(all, view, events, profile, statusOf, relations = view.model.edges) {
  const profileTypes = new Set(profile.nodes),
    selected = new Set();
  const scopeNodes = new Set(),
    raw = relations;
  if (profile.scope === "permission") {
    for (const n of all.values())
      if (n.semantic_roles?.includes("permission") || n.origin === "policy-definition")
        scopeNodes.add(n.id);
    const seeds = new Set(scopeNodes);
    for (const e of raw)
      if (["guard", "data"].includes(e.type) && (seeds.has(e.to) || seeds.has(e.from))) {
        scopeNodes.add(e.from);
        scopeNodes.add(e.to);
      }
  }
  if (profile.scope === "execution") {
    for (const n of all.values()) if (n.execution_role) scopeNodes.add(n.id);
    for (const [modelId, machine] of Object.entries(machinesOf(view.model))) {
      const execution = machine.execution || {};
      for (const n of [
        ...(execution.activities || []),
        ...(execution.resources || []),
        execution.join,
      ].filter(Boolean))
        scopeNodes.add(n.id);
      if (execution.within) scopeNodes.add(stateNodeId(view.model, execution.within, modelId));
    }
  }
  const eventIds = new Set(events.map((e) => e.node));
  for (const n of all.values()) {
    const canonical = n.referenceOf || n.id;
    let inScope = profile.scope === "all";
    // A business-flow preset displays actions, not a collapsed network root or
    // standalone object definitions. Their original containment stays in inventory.
    if (profile.scope === "business")
      inScope =
        concernOf(n) === "business" && !["business_network", "object"].includes(n.concept_kind);
    if (["rules", "state", "implementation"].includes(profile.scope))
      inScope = concernOf(n) === profile.scope;
    if (["permission", "execution"].includes(profile.scope))
      inScope =
        scopeNodes.has(canonical) || scopeNodes.has(n.event_node) || scopeNodes.has(n.parent);
    if (profile.scope === "observed") inScope = eventIds.has(n.event_node || canonical);
    if (profile.scope === "blocked") inScope = statusOf(n) === "blocked";
    if (profile.scope === "shared")
      inScope =
        !!n.referenceOf ||
        [...all.values()].some(
          (ref) => ref.referenceOf === n.id || (ref.referenceOf && ref.parent === n.id),
        );
    const query = profile.query.toLocaleLowerCase();
    const matches =
      !query ||
      [
        n.label,
        n.id,
        n.source?.symbol,
        n.summary,
        n.data_key,
        n.data_store,
        n.data_metadata?.native_type,
      ]
        .join(" ")
        .toLocaleLowerCase()
        .includes(query);
    const depthMatches = profile.depth === "all" || n.projection_depth === profile.depth;
    const inNetwork =
      !profile.networks?.length || profile.networks.some((id) => n.network_ids?.includes(id));
    if (
      viewTypes(n).some((type) => profileTypes.has(type)) &&
      inScope &&
      matches &&
      depthMatches &&
      inNetwork
    )
      selected.add(n.id);
  }
  for (const id of selected) {
    const n = all.get(id);
    if (n.referenceOf && !selected.has(n.parent)) selected.delete(id);
  }
  // Keep the real endpoint of an allowed relation as a labelled boundary. This
  // is one hop from the selection, never a transitive permission/call shortcut.
  const seeds = new Set(selected),
    context = new Set();
  for (const e of raw) {
    if (!relationTypeAllowed(e, profile.edges, relationType) || e.type === "contains") continue;
    for (const [from, to] of [
      [e.from, e.to],
      [e.to, e.from],
    ])
      if (seeds.has(from) && !seeds.has(to) && all.has(to)) {
        if (e.origin === "capture-field" && all.get(to).field) continue;
        context.add(to);
      }
  }
  for (const id of context) selected.add(id);
  selected.contextIds = context;
  return selected;
}
export function sharedMemberships(model) {
  const memberships = [...(model.presentation?.memberships || [])];
  for (const [modelId, machine] of Object.entries(machinesOf(model))) {
    const execution = machine.execution;
    if (execution?.within) {
      const group = stateNodeId(model, execution.within, modelId);
      for (const n of [
        ...(execution.activities || []),
        ...(execution.resources || []),
        execution.join,
      ].filter(Boolean))
        memberships.push({
          group,
          member: n.id,
          reason: boTranslate("Internal execution configuration for this state"),
          evidence: "machine.execution",
        });
    }
  }
  const seen = new Set();
  return memberships.filter((m) => {
    const key = m.group + "\0" + m.member;
    if (m.group === m.member || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
