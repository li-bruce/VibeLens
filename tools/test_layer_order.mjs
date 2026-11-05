/** Concern order, source facets and personal layout survive taxonomy migration. */
import assert from "node:assert/strict";
import { layerContent } from "../docs/site/layer-content.mjs";
import {
  layers,
  cleanLayers,
  layerHeights,
  cleanLayerVisibility,
  visibilityForView,
  savedLayerVisibility,
  expandLayerIds,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { LayerRuler } from "../skills/vibelens/assets/stategraph-viewer/layer-ruler.js";
const expected = ["business", "state", "rules", "entry", "structure", "symbols", "unknown", "data"];
const legacyVisibility = {
  visible: ["business", "state", "rules", "api"],
  gap: 420,
};
const viewSettings = {
  layers: cleanLayers(legacyVisibility),
  layerVisibility: cleanLayerVisibility(undefined, legacyVisibility),
};
assert.deepEqual(visibilityForView(viewSettings, "overview"), legacyVisibility.visible);
assert.ok(visibilityForView(viewSettings, "project").includes("structure"));
assert.ok(visibilityForView(viewSettings, "database").includes("data"));
viewSettings.layerVisibility.project = ["project"];
viewSettings.layerVisibility["custom-empty"] = [];
assert.deepEqual(visibilityForView(viewSettings, "project"), ["project"]);
assert.deepEqual(visibilityForView(viewSettings, "custom-empty"), []);
assert.deepEqual(visibilityForView(viewSettings, "overview"), legacyVisibility.visible);
assert.equal(viewSettings.layers.gap, 420);
const restored = cleanLayerVisibility(
  JSON.parse(JSON.stringify(viewSettings.layerVisibility)),
  legacyVisibility,
);
assert.deepEqual(restored.project, ["project"]);
assert.deepEqual(restored["custom-empty"], []);
const legacy = [
  "api",
  "business",
  "state",
  "rules",
  "operations",
  "execution",
  "data",
  "project",
  "code",
];
const withoutProject = cleanLayers({
  visible: legacy.filter((id) => id !== "project"),
});
assert.ok(!withoutProject.facets.includes("project"), "An old hidden project facet stays hidden");
assert.ok(withoutProject.facets.includes("code"));
assert.deepEqual(
  layers.map((layer) => layer.id),
  expected,
);
assert.equal(layerHeights({}).get("data"), 0);
assert.ok(layerHeights({}).get("symbols") > layerHeights({}).get("data"));
assert.deepEqual(
  layerContent.map((layer) => layer.id),
  expected.filter((id) => id !== "unknown"),
  "Product explanation and actual concern planes stay aligned",
);
for (const item of layerContent)
  assert.equal(item.color, layers.find((layer) => layer.id === item.id).color);
assert.ok(
  layers.some((layer) => layer.id === "unknown"),
  "Diagnostics retain a real selectable plane",
);
for (const prior of [
  undefined,
  {},
  { order: legacy, schema: 2 },
  { order: legacy.filter((id) => id !== "project") },
]) {
  const result = cleanLayers(prior);
  assert.deepEqual(result.order, expected);
  assert.equal(result.orderMode, "default");
  assert.deepEqual(cleanLayers(result), result);
}
for (const order of [legacy, [...expected].reverse(), ["rules", "api", "business"]]) {
  const result = cleanLayers({
    schema: 2,
    order,
    orderMode: "custom",
    visible: ["rules", "api"],
    gap: 420,
  });
  const mapped = expandLayerIds(order);
  assert.deepEqual(
    result.order.slice(0, mapped.length),
    mapped,
    "Custom relative order survives collapsed facets",
  );
  assert.equal(result.orderMode, "custom");
  assert.deepEqual(result.visible, ["rules", "entry"]);
  assert.deepEqual(result.facets, ["api"]);
  assert.equal(result.gap, 420);
  assert.deepEqual(cleanLayers(result), result);
  assert.deepEqual(savedLayerVisibility(result), ["rules", "api"]);
}
const custom = cleanLayers({ order: ["rules", "state", "api"] });
assert.deepEqual(custom.order.slice(0, 3), ["rules", "state", "entry"]);
assert.equal(custom.orderMode, "custom");
assert.deepEqual(
  [...layerHeights({ visible: ["business", "api", "code"] })],
  [
    ["symbols", 0],
    ["entry", 260],
    ["business", 520],
  ],
);
const changes = [];
const ruler = {
  config: cleanLayers({}),
  change: (config) => changes.push(config),
};
LayerRuler.prototype.reorder.call(ruler, "rules", -1);
assert.equal(changes.at(-1).orderMode, "custom");
assert.deepEqual(cleanLayers(changes.at(-1)).order.slice(0, 3), ["business", "rules", "state"]);
console.log(
  "PASS: concern/site parity, optional diagnostics, legacy facets, custom order, narrow visibility and compact heights.",
);
