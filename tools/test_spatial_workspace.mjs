import { activeMachineStates } from "../skills/vibelens/assets/stategraph-viewer/machine-projection.js";
import { edgeCurve } from "../skills/vibelens/assets/stategraph-viewer/spatial-paths.js";
import { regionLabelAnchor } from "../skills/vibelens/assets/stategraph-viewer/spatial-labels.js";
/** Executable declaration coverage and coplanar hierarchy are independent of rendering. */
import assert from "node:assert/strict";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { nodeElevation } from "../skills/vibelens/assets/stategraph-viewer/spatial-model.js";
import { solveSpatial } from "../skills/vibelens/assets/stategraph-viewer/spatial-layout.js";

const nodes = [
  { id: "file", layer: "code" },
  { id: "fn", parent: "file", layer: "code" },
];
assert.equal(
  nodeElevation(nodes[1], new Map(nodes.map((n) => [n.id, n])), 260, 260),
  260,
  "A nested member stays on its semantic plane",
);
const points = solveSpatial({ nodes, edges: [], layers: [{ id: "code" }], gap: 260 });
assert.equal(points.file.y, points.fn.y);
const view = {
  model: {
    nodes: [],
    edges: [],
    machine: {
      values: ["draft", "approved", "rejected"],
      states: ["draft", "approved", "rejected"],
      labels: {},
      transitions: [
        { source: "draft", dest: "approved", trigger: "review", conditions: ["allowed"] },
        { source: "draft", dest: "rejected", trigger: "review", unless: ["allowed"] },
      ],
    },
  },
  machine: { journal: [{ event: "review", source: "draft", target: "approved", attempt: "a" }] },
};
const graph = graphInventory(view, { attempt: "a" });
const transitions = graph.rawEdges.filter((e) => e.type === "transition");
assert.equal(
  new Set(transitions.map((e) => e.id)).size,
  2,
  "Parallel conditional transitions retain unique identities",
);
assert.equal(transitions.filter((e) => e.observed).length, 1);
assert.ok(
  transitions.every((e) => e.machine_transition && (e.conditions?.length || e.unless?.length)),
);
assert.deepEqual(
  [...graph.all.values()]
    .filter((n) => n.machine_state)
    .map((n) => n.value)
    .sort(),
  view.model.machine.values.slice().sort(),
);
const flat = structuredClone(view);
flat.model.machine.values = ["a", "a_b"];
flat.model.machine.states = ["a", "a_b"];
flat.model.machine.transitions = [{ source: "a", dest: "a_b", trigger: "go" }];
assert.equal(
  graphInventory(flat).rawEdges.filter((e) => e.type === "transition").length,
  1,
  "Underscores in flat names do not declare ancestry",
);
const ambiguous = structuredClone(view);
ambiguous.model.machine.transitions[1].dest = "approved";
assert.equal(
  graphInventory(ambiguous, { attempt: "a" }).rawEdges.filter((e) => e.observed).length,
  0,
  "An unrecorded guard branch remains ambiguous",
);
const hsm = structuredClone(flat);
hsm.model.machine.states = [{ name: "a", initial: "b", children: ["b"] }];
assert.equal(graphInventory(hsm).all.get("state.a_b").parent, "state.a");
for (const pair of [
  [
    { x: 0, y: 260, z: 0 },
    { x: 100, y: 260, z: 10 },
  ],
  [
    { x: 0, y: 260, z: 0 },
    { x: 0, y: 260, z: 0 },
  ],
]) {
  const points = edgeCurve(...pair).getPoints(32);
  assert.ok(points.every((p) => p.y === 260));
  if (pair[0].x === pair[1].x)
    assert.ok(
      points.some((p) => p.z > 20),
      "Self-transitions have visible curvature",
    );
}
for (const angle of [0, 0.3, 1, 2]) {
  const project = (p) => ({
    x: p.x * Math.cos(angle) + p.z * Math.sin(angle),
    y: p.z * Math.cos(angle) - p.x * Math.sin(angle),
    visible: true,
  });
  const label = regionLabelAnchor({ center: { x: 0, y: 0, z: 0 }, radius: 100 }, project);
  assert.ok(Math.abs(label.y - 107) < 0.1);
}
assert.deepEqual([...activeMachineStates(hsm.model.machine, "a_b")].sort(), ["a", "a_b"]);
assert.deepEqual([...activeMachineStates(flat.model.machine, "a_b")], ["a_b"]);
console.log("Spatial workspace checks passed");
