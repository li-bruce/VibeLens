import assert from "node:assert/strict";
import {
  ObstacleIndex,
  cleanPoints,
  smoothRoute,
} from "../skills/vibelens/assets/stategraph-viewer/routing-geometry.js";
import { Navigation } from "../skills/vibelens/assets/stategraph-viewer/routing-navigation.js";
import { pickRoutes } from "../skills/vibelens/assets/stategraph-viewer/route-picking.js";
import { dataLines } from "../skills/vibelens/assets/stategraph-viewer/data-layer.js";
import { cleanLayers } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
const edge = { from: "source", to: "target", a: { x: 0, y: 0 }, b: { x: 500, y: 0 } };
const index = new ObstacleIndex([{ id: "wall", key: "wall", kind: "glyph", x: 250, y: 0, r: 60 }]);
assert.equal(index.clear([edge.a, edge.b], edge), false);
const path = new Navigation(index).find(edge.a, edge.b, edge, index);
assert.ok(path && index.clear(path, edge), "Shared navigation finds a certified channel");
assert.ok(
  index.clear(smoothRoute(path, index, edge), edge),
  "Actual smoothed segments remain clear",
);
assert.deepEqual(
  cleanPoints([
    { x: 0, y: 0 },
    { x: 1, y: 0 },
    { x: 2, y: 0 },
  ]),
  [
    { x: 0, y: 0 },
    { x: 2, y: 0 },
  ],
);
const edges = [{ id: "one" }, { id: "two" }];
assert.deepEqual(
  pickRoutes(
    edges,
    () => [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
    ],
    { x: 50, y: 1 },
    5,
  ).map((e) => e.id),
  ["one", "two"],
);
const node = {
  data_role: "column",
  data_metadata: {
    native_type: "INTEGER",
    primary_key: true,
    required: true,
    nullable: false,
    constraints: [{ kind: "unique" }],
  },
};
const compact = dataLines(node)
    .map((r) => r.text)
    .join(" "),
  detail = dataLines(node, {}, {}, false, true)
    .map((r) => r.text)
    .join(" ");
assert.equal(compact, "INTEGER");
assert.ok(
  detail.includes("Primary key") && detail.includes("Required") && detail.includes("unique"),
);
assert.equal(cleanLayers({ compact: true }).compact, true);
console.log(
  "PASS: collision certificates, navigation, smoothing, shared-trunk picking, concise field labels and saved narrow ruler.",
);
