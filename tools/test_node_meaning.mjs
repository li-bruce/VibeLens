/** Layer-specific meanings, exact state transitions and stale-response isolation. */
import assert from "node:assert/strict";
import { nameNode } from "../skills/vibelens/assets/stategraph-viewer/graph-names.js";
import { nodeFacts, detailRows } from "../skills/vibelens/assets/stategraph-viewer/node-facts.js";
import { createNodeExplanation } from "../skills/vibelens/assets/stategraph-viewer/node-explanation.js";
import { lines } from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";

const stateGroup = {
  id: "grant-model",
  concept_kind: "state_model",
  layer: "state",
  summary: "Recipient grant",
};
assert.deepEqual(
  lines(stateGroup, { model: { machine: { values: [] }, nodes: [stateGroup] } }, [], "latest"),
  [{ text: "Recipient grant", role: "symbol" }],
);

const model = {
  presentation: {
    names: {
      nodes: { status: "Boolean variable" },
      states: { active: "Generic active" },
      concepts: { "state:grant:active": { en: "Recipient can download", "zh-CN": "接收者可下载" } },
    },
  },
};
const business = {
    id: "concept-view:status",
    concept_id: "status",
    concept_kind: "action",
    layer: "business",
    label: "Share a file",
  },
  state = {
    id: "state:grant:active",
    kind: "state",
    value: "active",
    concept_kind: "state",
    layer: "state",
    origin: "concept-design",
    label: "Access granted",
  },
  rule = {
    id: "policy:enabled",
    concept_kind: "rule_expression",
    layer: "rules",
    label: "Has current access",
  };
assert.equal(nameNode(business, model).label, "Share a file");
assert.equal(nameNode(state, model).label, "Recipient can download");
assert.equal(nameNode(rule, model).label, "Has current access");
assert.equal(
  nameNode({ id: "status", kind: "data", label: "status" }, model).label,
  "Boolean variable",
);
assert.equal(nameNode(business, { presentation: { name_mode: "source" } }).label, "status");
assert.equal(business.id, "concept-view:status");
const businessNext = { id: "download", layer: "business", label: "Download file" },
  physicalCall = { id: "check", layer: "function", label: "Read grant" };
const businessFacts = nodeFacts(
  business,
  { model: {} },
  new Map([
    [business.id, business],
    [businessNext.id, businessNext],
    [physicalCall.id, physicalCall],
  ]),
  [
    { id: "next", from: business.id, to: businessNext.id, type: "flow", origin: "concept-design" },
    { id: "call", from: business.id, to: physicalCall.id, type: "flow" },
  ],
);
assert.deepEqual(businessFacts.find((fact) => fact.label === "Next").values, ["Download file"]);
const edges = [
    {
      id: "revoke",
      from: state.id,
      to: "private",
      type: "transition",
      trigger: "revoke",
      conditions: ["owner"],
    },
  ],
  all = new Map([
    [state.id, state],
    ["private", { id: "private", label: "Access removed" }],
  ]);
const facts = nodeFacts(state, { model: { machine: { transitions: [] } } }, all, edges);
assert.deepEqual(facts.find((f) => f.label === "Transitions").values, [
  "revoke → Access removed · owner",
]);
assert.equal(
  facts.some((f) => f.values.includes("Generic active")),
  false,
);
const nestedFacts = nodeFacts(
  { id: "state.active_reading", kind: "state", value: "active_reading" },
  {
    model: {
      machine: {
        states: [{ name: "active", children: ["reading"] }, "closed"],
        transitions: [
          { source: "active", trigger: "close", dest: "closed", conditions: ["owner"] },
        ],
      },
    },
  },
  new Map(),
);
assert.deepEqual(nestedFacts.find((fact) => fact.label === "Transitions").values, [
  "close → closed · owner",
]);
assert.deepEqual(
  detailRows(
    state,
    [
      { text: state.label },
      { text: "active" },
      { text: "phase: Phase = active", definition: true },
      { text: "Running", role: "value" },
      { text: "Running", role: "value" },
    ],
    facts,
  ),
  [{ text: "Running", role: "value" }],
);

const elements = new Map(
  ["node-explanation", "explain-node"].map((id) => [id, { dataset: {}, textContent: "" }]),
);
let current = { view: { manifest: { build_id: "one" } }, selected: "node" },
  resolve;
const ui = createNodeExplanation({ read: () => current, element: (id) => elements.get(id) });
const prior = globalThis.fetch;
try {
  globalThis.fetch = () =>
    new Promise((done) => {
      resolve = done;
    });
  const loading = ui.explain();
  current = { ...current, selected: "another" };
  ui.update();
  resolve({ ok: true, json: async () => ({ available: true, build_id: "one", revision: "r" }) });
  await loading;
  assert.equal(elements.get("node-explanation").textContent, "");
  current = { ...current, selected: "node" };
  let calls = 0;
  globalThis.fetch = async () => ({
    ok: true,
    json: async () =>
      ++calls === 1
        ? {
            available: true,
            build_id: "one",
            revision: "r",
            code_revision: null,
            concept_revision: null,
          }
        : {
            node: "node",
            revision: "r",
            language: "en",
            status: "complete",
            provider: "test-contract",
            answer: { text: "<script>Plain text only</script>" },
          },
  });
  await ui.explain();
  assert.equal(elements.get("node-explanation").textContent, "<script>Plain text only</script>");
  assert.equal(elements.get("node-explanation").innerHTML, undefined);
  current.view = { manifest: { build_id: "two" } };
  ui.update();
  assert.equal(elements.get("node-explanation").textContent, "");
  globalThis.fetch = async () => ({
    ok: false,
    json: async () => {
      throw new SyntaxError("<!DOCTYPE html>");
    },
  });
  await ui.explain();
  assert.equal(elements.get("node-explanation").dataset.status, "error");
  assert.equal(
    elements.get("node-explanation").textContent,
    "AI explanation unavailable. Check the provider and retry.",
  );
  ui.clear();
} finally {
  globalThis.fetch = prior;
}
console.log(
  "PASS: distinct layer meanings, stable IDs, actual transitions and isolated plain-text AI results.",
);
