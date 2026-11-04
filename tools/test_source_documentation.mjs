/** Source comments describe physical nodes without changing observed identities. */
import assert from "node:assert/strict";
import { nameNode, namedView } from "../skills/vibelens/assets/stategraph-viewer/graph-names.js";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import {
  layerOf,
  implementationFacet,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { nodeExplanation } from "../skills/vibelens/assets/stategraph-viewer/capture-fields.js";

const source = { path: "app/web.py", symbol: "create_app.api_entry" },
  node = {
    id: "api_get",
    kind: "function",
    layer: "api",
    label: "GET API",
    source,
    capture: { in: { path: "string" }, out: { status: "number" } },
  },
  documentation = {
    status: "documented",
    format: "python-docstring",
    summary: "Open a shared file",
    source: { ...source, line: 22, end_line: 23, file_sha256: "f".repeat(64) },
  },
  bindings = {
    api_get: {
      ...source,
      line: 21,
      end_line: 25,
      api_role: "capture",
      telemetry_match: { name: "GET /api/<path:operation>" },
      documentation,
    },
  },
  model = {
    nodes: [node],
    edges: [],
    machine: { values: [], events: {}, transitions: [] },
  },
  before = JSON.stringify({ node, model, bindings }),
  explained = nameNode(node, model, bindings);
assert.equal(explained.label, "Open a shared file");
assert.equal(explained.id, "api_get");
assert.equal(explained.source.line, 21);
assert.equal(explained.source_name, "GET /api/<path:operation>");
assert.equal(explained.api_role, "capture");
assert.equal(layerOf(explained), "implementation");
assert.equal(
  implementationFacet(explained),
  "execution",
  "Native capture keeps its observation role",
);
const view = { model, manifest: { bindings } },
  inventory = graphInventory(view),
  field = inventory.all.get("field:api_get:out:status");
assert.equal(layerOf(field), "implementation");
assert.equal(
  implementationFacet(field),
  "execution",
  "Captured status keeps its actual owner role",
);
assert.equal(
  field.documentation,
  undefined,
  "A captured HTTP status is not a documented source parameter",
);
assert.equal(field.event_node, "api_get");
assert.equal(inventory.all.get("api_get").source.line, 21);
assert.equal(
  JSON.stringify({ node, model, bindings }),
  before,
  "View naming never changes declaration or evidence",
);
assert.equal(namedView(view, false).model.nodes[0].label, "GET /api/<path:operation>");
const missing = nameNode(node, model, {
  api_get: { ...bindings.api_get, documentation: undefined },
});
assert.equal(
  missing.label,
  "GET /api/<path:operation>",
  "Missing prose falls back to the exact selector, not GET API",
);
const endpoint = {
  id: "route",
  kind: "function",
  code_role: "endpoint",
  api_role: "endpoint",
  api: { path: "/files/<file_id>", methods: ["GET"] },
  documentation,
};
assert.equal(layerOf(endpoint), "implementation");
assert.equal(
  implementationFacet(endpoint),
  "api",
  "Registration and capture remain separate facets",
);
assert.equal(nameNode(endpoint, model).source_name, "GET /files/<file_id>");
const middleware = {
  ...endpoint,
  label: "GET /files",
  api: {
    path: "/files",
    methods: ["GET"],
    registration_ids: ["auth", "files"],
    registration_bindings: {
      auth: {
        symbol: "authenticate",
        documentation: { summary: "Require a session" },
      },
      files: {
        symbol: "files",
        documentation: { summary: "Read shared files" },
      },
    },
  },
  documentation: { ...documentation, summary: "Require a session" },
};
assert.equal(nameNode(middleware, model).label, "GET /files");
assert(nodeExplanation(middleware, inventory.all).includes("files: Read shared files"));
assert(nodeExplanation(explained, inventory.all).includes("Open a shared file"));
assert(nodeExplanation(explained, inventory.all).includes("HTTP observation anchor"));

const action = { ...node, id: "share", layer: "business", label: "Share file" };
const actionBindings = { share: { ...bindings.api_get, api_role: undefined } };
assert.equal(nameNode(action, model, actionBindings).label, "Share file");
const conceptAction = { ...action, concept_label: "Share with colleague" };
assert.equal(nameNode(conceptAction, model, actionBindings).label, "Share with colleague");
assert.equal(
  nameNode(
    conceptAction,
    {
      ...model,
      presentation: { names: { nodes: { share: "Grant file access" } } },
    },
    actionBindings,
  ).label,
  "Grant file access",
);
const actionView = {
  model: { ...model, nodes: [conceptAction] },
  manifest: { bindings: actionBindings },
};
const actionBefore = JSON.stringify(actionView);
const sourceView = namedView(actionView, false);
assert.equal(sourceView.model.nodes[0].label, "create_app.api_entry");
assert.equal(namedView(sourceView, true).model.nodes[0].label, "Share with colleague");
assert.equal(
  JSON.stringify(actionView),
  actionBefore,
  "Naming cannot mutate source or recording definitions",
);
assert.equal(
  nameNode({ ...node, origin: "concept-design", label: "May share" }, model, bindings).label,
  "May share",
);
console.log("Source documentation and API observation roles passed");
