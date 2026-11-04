/** Read-only audit: actual viewer projection of emitted concept/source shapes. */
import { writeFileSync } from "node:fs";
import { layoutGraph } from "../../../../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { profileFor, matchingNodes } from "../../../../skills/vibelens/assets/stategraph-viewer/analysis.js";
import {
  refreshHierarchy,
  presentationGraph,
  hierarchyOf,
} from "../../../../skills/vibelens/assets/stategraph-viewer/layout.js";

function project(nodes, edges, preset, layered = false) {
  const view = {
    model: { nodes, edges, machine: { values: [], transitions: [] } },
    manifest: { bindings: {} },
    machine: { configurations: [], journal: [] },
    events: [],
    authority: { parameters: {}, basis: {} },
    binding_status: { status: "current" },
  };
  const profile = profileFor(preset);
  const graph = layoutGraph(
    view, new Set(nodes.map(node => node.id)), new Set(), new Map(), "latest", "latest",
    { match: (all, events, status, relations) =>
      matchingNodes(all, view, events, profile, status, relations) },
  );
  graph.layered = layered;
  refreshHierarchy(graph);
  const shown = presentationGraph(graph, profile);
  return {
    raw_edges: graph.rawEdges.map(edge => edge.id),
    glyphs: [...shown.glyphs],
    parents: [...hierarchyOf(graph).parents],
    regions: graph.regions.map(region => region.id),
    drawn_edges: shown.edges.map(edge => ({
      type: edge.type,
      members: edge.members?.map(member => member.id),
    })),
    allowed_relations: profile.edges,
  };
}

// concepts/state_projection.py emits the state parent as a contains edge only.
const states = [
  { id: "machine", kind: "state", layer: "state", concept_kind: "state_model", origin: "concept-design", label: "Machine" },
  { id: "parent", kind: "state", layer: "state", concept_kind: "state", origin: "concept-design", label: "Reviewing" },
  { id: "child", kind: "state", layer: "state", concept_kind: "state", origin: "concept-design", label: "Waiting" },
];
const containment = [
  { id: "has-parent", label: "Contains", from: "machine", to: "parent", type: "contains", origin: "concept-design" },
  { id: "has-child", label: "Contains", from: "parent", to: "child", type: "contains", origin: "concept-design" },
];
const functions = [
  { id: "f", kind: "function", code_role: "function", label: "f" },
  { id: "g", kind: "function", code_role: "function", label: "g" },
  { id: "p", kind: "data", code_role: "parameter", parent: "f", label: "p" },
];
const calls = [
  { id: "call", label: "Calls", from: "f", to: "g", type: "call", code_relation: "calls", origin: "code-index" },
  { id: "parameter", label: "Parameter", from: "f", to: "p", type: "data", code_relation: "parameter", origin: "code-index" },
];
const result = {
  audit_commit: "ce0a1fa6",
  state_2d: project(states, containment, "states"),
  state_3d: project(states, containment, "states", true),
  functions: project(functions, calls, "functions"),
  code_control: project(functions, calls, "code"),
};
writeFileSync(new URL("layer-view-repro.json", import.meta.url), JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify(result, null, 2));
