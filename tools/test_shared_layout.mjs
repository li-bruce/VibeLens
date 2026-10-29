/** Shared planar seeds separate types without overriding existing spatial edits. */
import assert from "node:assert/strict";
import { clusterUnits } from "../skills/vibelens/assets/stategraph-viewer/cluster-layout.js";
import { planarSeeds } from "../skills/vibelens/assets/stategraph-viewer/spatial-model.js";
import { solveSpatial } from "../skills/vibelens/assets/stategraph-viewer/spatial-layout.js";

const units = Array.from({ length: 90 }, (_, i) => ({
  id: String(i),
  type: ["function", "decision", "data"][i % 3],
  radius: 40,
}));
const edges = units.slice(1).map((unit, i) => ({ from: units[i].id, to: unit.id }));
const result = clusterUnits(units, edges);
const types = [...new Set(units.map((unit) => unit.type))];
const centers = Object.fromEntries(
  types.map((type) => {
    const group = result.filter((p) => units.find((unit) => unit.id === p.id).type === type);
    return [
      type,
      {
        x: group.reduce((sum, p) => sum + p.x, 0) / group.length,
        y: group.reduce((sum, p) => sum + p.y, 0) / group.length,
      },
    ];
  }),
);
for (const p of result) {
  const type = units.find((unit) => unit.id === p.id).type;
  const own = Math.hypot(p.x - centers[type].x, p.y - centers[type].y);
  assert.ok(
    types
      .filter((other) => other !== type)
      .every((other) => own < Math.hypot(p.x - centers[other].x, p.y - centers[other].y)),
    "Even dense cross-type links retain readable type neighborhoods",
  );
}
const boxes = units.map((unit) => ({ ...unit, w: 160 }));
const positions = Object.fromEntries(result.map((p) => [p.id, p]));
const planar = planarSeeds({ boxes }, positions);
const nodes = units.map((unit, i) => ({
  ...unit,
  layer: i % 2 ? "code" : "business",
}));
const args = {
  nodes,
  edges,
  layers: [{ id: "business" }, { id: "code" }],
  gap: 260,
  planar,
};
const lifted = solveSpatial(args);
for (const node of nodes) {
  assert.equal(lifted[node.id].x, planar[node.id].x);
  assert.equal(lifted[node.id].z, planar[node.id].z);
}
const manual = {
  1: { x: 999, y: 0, z: -90, pinned: false },
  2: { x: -999, y: 260, z: 90, pinned: true },
};
const kept = solveSpatial({ ...args, positions: manual });
assert.equal(
  kept["1"].x,
  manual["1"].x,
  "Saved spatial movement takes precedence over a planar seed",
);
const arranged = solveSpatial({ ...args, positions: manual, arrange: true });
assert.equal(
  arranged["1"].x,
  planar["1"].x,
  "Arrange deliberately restores the shared solver's result",
);
assert.equal(arranged["2"].x, manual["2"].x, "Explicit spatial pins remain exact");
assert.equal(arranged["2"].z, manual["2"].z);
assert.deepEqual(planarSeeds({ boxes }, {}), {}, "No invented seed for an unpositioned node");
console.log("PASS: dense type clusters, exact planar/spatial coordinates, saved edits and pins.");
