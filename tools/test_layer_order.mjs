/** Recommended reading order is shared by the introduction and native controls. */
import assert from "node:assert/strict";
import { layerContent } from "../docs/site/layer-content.mjs";
import {
  layers,
  cleanLayers,
  layerHeights,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { LayerRuler } from "../skills/vibelens/assets/stategraph-viewer/layer-ruler.js";

const expected = [
  "business",
  "state",
  "rules",
  "api",
  "execution",
  "operations",
  "project",
  "code",
  "data",
];
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
assert.deepEqual(
  layers.map((layer) => layer.id),
  expected,
);
assert.equal(layerHeights({}).get("data"), 0, "Physical storage is the bottom plane");
assert.ok(layerHeights({}).get("project") > layerHeights({}).get("code"));
assert.ok(layerHeights({}).get("code") > layerHeights({}).get("data"));
assert.deepEqual(
  layerContent.map((layer) => layer.id),
  expected,
  "The site cannot drift from native planes",
);
for (const item of layerContent) {
  assert.equal(item.color, layers.find((layer) => layer.id === item.id).color);
}
for (const previous of [
  undefined,
  {},
  { order: legacy, schema: 2 },
  { order: legacy.filter((id) => id !== "project") },
]) {
  const result = cleanLayers(previous);
  assert.deepEqual(result.order, expected);
  assert.equal(result.orderMode, "default");
  assert.deepEqual(cleanLayers(result), result, "Migration is idempotent");
}

for (const order of [legacy, [...expected].reverse(), ["rules", "api", "business"]]) {
  const result = cleanLayers({
    schema: 2,
    order,
    orderMode: "custom",
    visible: ["rules", "api"],
    gap: 420,
  });
  assert.deepEqual(
    result.order.slice(0, order.length),
    order,
    "Explicit custom order survives upgrades",
  );
  assert.equal(result.orderMode, "custom");
  assert.deepEqual(result.visible, ["rules", "api"]);
  assert.equal(result.gap, 420);
  assert.deepEqual(cleanLayers(result), result);
}
const unmarkedCustom = cleanLayers({ order: ["rules", "state", "api"] });
assert.deepEqual(unmarkedCustom.order.slice(0, 3), ["rules", "state", "api"]);
assert.equal(
  unmarkedCustom.orderMode,
  "custom",
  "Older custom orders need no new metadata to survive",
);
const sparse = cleanLayers({ order: ["rules", "code"], visible: ["rules", "code"] });
assert.ok(sparse.order.indexOf("project") < sparse.order.indexOf("code"));
assert.deepEqual(
  sparse.visible,
  ["rules", "code"],
  "A narrow old view gains no unwanted visible layer",
);
assert.deepEqual(
  [...layerHeights({ visible: ["business", "api", "code"] })],
  [
    ["code", 0],
    ["api", 260],
    ["business", 520],
  ],
);

const changes = [];
const ruler = { config: cleanLayers({}), change: (config) => changes.push(config) };
LayerRuler.prototype.reorder.call(ruler, "rules", -1);
assert.equal(changes.at(-1).orderMode, "custom", "Reorder gestures mark user ownership");
assert.deepEqual(cleanLayers(changes.at(-1)).order.slice(0, 3), ["business", "rules", "state"]);
console.log(
  "PASS: shared nine-layer order, old-default migration, custom orders, narrow visibility, compact heights and keyboard ownership.",
);
