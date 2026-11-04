/** Source locality is a bounded, deterministic layout hint, never a graph edge. */
import assert from "node:assert/strict";
import { performance } from "node:perf_hooks";
import { mkdir, writeFile } from "node:fs/promises";
import {
  proximityOrder,
  proximitySeeds,
  proximityNeighbors,
} from "../skills/vibelens/assets/stategraph-viewer/proximity-layout.js";
import { clusterUnits } from "../skills/vibelens/assets/stategraph-viewer/cluster-layout.js";
import { solveSpatial } from "../skills/vibelens/assets/stategraph-viewer/spatial-layout.js";

const source = [
  { id: "a", source: { path: "app/files.py", line: 10 } },
  { id: "b", source: { path: "app/users.py", line: 1 } },
  { id: "c", source: { path: "app/files.py", line: 14 } },
  { id: "d", source: { path: "app/files.py", line: 200 } },
];
assert.deepEqual(
  proximityOrder(source).map((item) => item.id),
  ["a", "c", "d", "b"],
);
assert.equal(
  proximityOrder(source, [{ from: "a", to: "b" }])[1].id,
  "b",
  "Real relations take precedence over a source hint",
);
assert.deepEqual(
  proximityOrder(source.slice().reverse()),
  proximityOrder(source),
  "Input enumeration does not change the hint",
);
const lexical = [
  { id: "a", source_name: "uploadFile", label: "Membership" },
  { id: "b", source_name: "revokeMembership", label: "Files" },
  { id: "c", source_name: "downloadFile", label: "Users" },
];
assert.equal(proximityOrder(lexical)[1].id, "c");
assert.deepEqual(
  proximitySeeds(lexical),
  proximitySeeds(
    lexical.map((node) => ({ ...node, label: "Another AI alias", explained_name: "Changed" })),
  ),
  "AI display aliases cannot alter the physical ordering",
);
assert.deepEqual(proximitySeeds([]), new Map());
const generic = Array.from({ length: 150 }, (_, i) => ({ id: String(i), source_name: "readFile" }));
const hub = proximityNeighbors(generic.slice(1).map((item) => ({ from: "0", to: item.id })));
assert.equal(hub.get("0").length, 32, "A hub has bounded local candidates");

const units = Array.from({ length: 96 }, (_, i) => ({
  id: "n" + String(i).padStart(3, "0"),
  type: "code-function",
  layer: "code",
  radius: 25,
  source: { path: `app/${i % 4}.py`, line: Math.floor(i / 4) * 10 },
}));
const original = structuredClone(units);
const hinted = clusterUnits(units, []).sort((a, b) => a.id.localeCompare(b.id));
const baseline = clusterUnits(
  units.map(({ source, ...node }) => node),
  [],
).sort((a, b) => a.id.localeCompare(b.id));
function fileDistance(points) {
  let distance = 0,
    count = 0;
  for (let i = 0; i < units.length; i++)
    for (let j = i + 1; j < units.length; j++)
      if (units[i].source.path === units[j].source.path) {
        distance += Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y);
        count++;
      }
  return distance / count;
}
const meanHinted = fileDistance(hinted),
  meanBaseline = fileDistance(baseline);
assert.ok(
  meanHinted < meanBaseline * 0.85,
  "The solved cluster retains measurable source neighborhoods",
);
assert.deepEqual(units, original, "Neither graph objects nor source metadata are rewritten");
const pin = { x: 301, y: -900 };
assert.deepEqual(
  clusterUnits([{ ...units[0], pin }, ...units.slice(1)], []).find(
    (point) => point.id === units[0].id,
  ),
  { id: units[0].id, ...pin },
);
const planar = Object.fromEntries(hinted.map((point) => [point.id, { x: point.x, z: point.y }]));
const spatial = solveSpatial({
  nodes: units,
  edges: [],
  layers: [{ id: "code" }],
  gap: 260,
  planar,
});
for (const node of units) {
  assert.equal(spatial[node.id].x, planar[node.id].x);
  assert.equal(spatial[node.id].z, planar[node.id].z);
}

const timings = [];
for (const count of [1000, 4000, 10000]) {
  const nodes = Array.from({ length: count }, (_, i) => ({
    id: `method:${i}`,
    source_name: `handle${i % 12}File`,
    ...(i % 3 ? { source: { path: `src/service-${i % 80}.py`, line: i } } : {}),
  }));
  const edges = nodes.slice(1).map((node, i) => ({ from: nodes[i].id, to: node.id }));
  const started = performance.now(),
    result = proximitySeeds(nodes, edges, 1000);
  const elapsedMs = performance.now() - started;
  assert.equal(result.size, count);
  assert.ok(
    [...result.values()].every((point) => Number.isFinite(point.x) && Number.isFinite(point.y)),
  );
  assert.ok(elapsedMs < 5000, "Bounded hint preparation must remain practical for a large graph");
  timings.push({ nodes: count, edges: edges.length, elapsed_ms: +elapsedMs.toFixed(2) });
}
const evidence = {
  passed: true,
  source_cluster_mean_distance: +meanHinted.toFixed(2),
  baseline_mean_distance: +meanBaseline.toFixed(2),
  improvement_percent: +((1 - meanHinted / meanBaseline) * 100).toFixed(2),
  hint_preparation: timings,
};
const output = process.env.BO_LAYOUT_EVIDENCE;
if (output) {
  await mkdir(output, { recursive: true });
  await writeFile(output + "/proximity-results.json", JSON.stringify(evidence, null, 2) + "\n");
}
console.log(JSON.stringify(evidence, null, 2));
