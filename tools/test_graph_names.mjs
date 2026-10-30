/** Verify display names cannot rename source identities, states or recorded facts. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { namedView, sourceName } from "../skills/vibelens/assets/stategraph-viewer/graph-names.js";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import {
  emptyLayout,
  displayName,
  searchNodes,
  setAnnotation,
  relationName,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { setLocale } from "../skills/vibelens/assets/stategraph-viewer/i18n.js";
import { boDisplayValue } from "../skills/vibelens/assets/stategraph-viewer/replay-steps.js";
import { phaseLabel } from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { eventLabel } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const recording = JSON.parse(
  await readFile(
    "docs/review/recording-timeline/real-project-completion/v2-recording.json",
    "utf8",
  ),
);
const view = structuredClone(recording.context);
view.model.presentation.names = {
  nodes: {
    login: { en: "Verify account", "zh-CN": "验证账号" },
    "field:login:out:allowed": { en: "May sign in", "zh-CN": "允许登录" },
  },
  edges: { login_upload: { en: "Upload after sign-in", "zh-CN": "登录后上传" } },
  states: { shared: { en: "Shared with recipients", "zh-CN": "已共享给接收者" } },
  events: { share: { en: "Grant access", "zh-CN": "授予访问权" } },
};
const original = JSON.stringify(view),
  raw = JSON.stringify(recording);
setLocale("zh-CN");
const explained = namedView(view),
  source = namedView(explained, false),
  restored = namedView(source);
assert.equal(explained.model.nodes.find((n) => n.id === "login").label, "验证账号");
assert.equal(source.model.nodes.find((n) => n.id === "login").label, "SharingService.authenticate");
assert.equal(restored.model.nodes.find((n) => n.id === "login").label, "验证账号");
assert.equal(source.model.machine.labels.shared, "shared");
assert.equal(explained.model.machine.labels.shared, "已共享给接收者");
assert.equal(explained.model.machine.event_labels.share, "授予访问权");
assert.equal(source.model.edges.find((e) => e.id === "login_upload").label, "flow");
assert.equal(
  relationName(explained.model.edges.find((e) => e.id === "login_upload")),
  "登录后上传",
);
const inventory = graphInventory(source),
  other = graphInventory(explained);
assert.equal(inventory.all.get("field:login:out:allowed").label, "allowed");
assert.equal(other.all.get("field:login:out:allowed").label, "允许登录");
assert.equal(other.all.get("state_shared").label, "已共享给接收者");
assert.equal(
  sourceName({
    id: "p",
    code_role: "parameter",
    label: "recipient_id",
    source: { symbol: "SharingService.share" },
  }),
  "recipient_id",
);
assert.equal(
  sourceName({
    id: "api",
    code_role: "endpoint",
    api: { methods: ["GET"], path: "/files" },
    source: { symbol: "get_files" },
  }),
  "GET /files",
);
assert.equal(sourceName({ id: "scope", label: "Logical scope" }), "scope");
const prefs = emptyLayout();
setAnnotation(prefs, "login", { label: "My login", note: "Check here", core: true });
assert.equal(displayName(other.all.get("login"), prefs), "My login");
prefs.nameMode = "source";
assert.equal(displayName(inventory.all.get("login"), prefs), "SharingService.authenticate");
assert.equal(prefs.annotations.login.label, "My login");
assert.equal(searchNodes(inventory.all, prefs, "验证账号")[0].node.id, "login");
assert.equal(searchNodes(other.all, prefs, "SharingService.authenticate")[0].node.id, "login");
assert.equal(boDisplayValue("shared", explained.model, { kind: "business" }), "已共享给接收者");
assert.equal(boDisplayValue("shared", source.model, { kind: "business" }), "shared");
assert.equal(boDisplayValue("shared", explained.model, { kind: "value" }), "shared");
assert.equal(phaseLabel(explained.model, ["private", "shared"]), "private · 已共享给接收者");
assert.equal(
  boDisplayValue(["private", "shared"], explained.model, { kind: "business" }),
  "private · 已共享给接收者",
);
assert.equal(
  boDisplayValue(["private", "shared"], explained.model, { kind: "value" }),
  '["private","shared"]',
);
assert.equal(
  eventLabel({ node: "login", phase: "enter" }, source.model),
  "SharingService.authenticate · enter",
);
assert.deepEqual([...inventory.all.keys()], [...other.all.keys()]);
assert.deepEqual(source.manifest.bindings, view.manifest.bindings);
for (const field of ["states", "values", "transitions", "events", "initial", "context"])
  assert.deepEqual(source.model.machine[field], explained.model.machine[field]);
assert.deepEqual(
  inventory.rawEdges.map((e) => [e.id, e.from, e.to, e.type]),
  other.rawEdges.map((e) => [e.id, e.from, e.to, e.type]),
);
assert.equal(JSON.stringify(view), original);
assert.equal(JSON.stringify(recording), raw);
const repeated = structuredClone(view);
repeated.model.presentation.names.nodes.upload = repeated.model.presentation.names.nodes.login;
const sameLabels = graphInventory(namedView(repeated));
assert.equal(sameLabels.all.get("login").label, sameLabels.all.get("upload").label);
assert.notEqual(sameLabels.all.get("login").id, sameLabels.all.get("upload").id);
assert.deepEqual([...sameLabels.all.keys()], [...other.all.keys()]);
setLocale("en");
assert.equal(namedView(view).model.nodes.find((n) => n.id === "login").label, "Verify account");
console.log(
  JSON.stringify({
    valid: true,
    nodes: inventory.all.size,
    edges: inventory.rawEdges.length,
  }),
);
