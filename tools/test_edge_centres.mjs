/** Renderer adapters use the same centre anchors at every zoom and elevation. */
import assert from "node:assert/strict";
import { edgePorts, nodeCenter } from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import {
  planarScene,
  spatialScene,
} from "../skills/vibelens/assets/stategraph-viewer/routing-scene.js";
import { routeScene } from "../skills/vibelens/assets/stategraph-viewer/routing-engine.js";

const nodes = [
  { id: "a", glyph: true },
  { id: "b", glyph: true },
];
const boxes = nodes.map((node, i) => ({ id: node.id, node, x: i * 400, y: 60, w: 100, h: 90 }));
const graph = { byId: new Map(boxes.map((box) => [box.id, box])), boxes, regions: [] };
const edge = { id: "ab", from: "a", to: "b", type: "call" };
const presentation = { glyphs: new Set(["a", "b"]), regions: new Set(), edges: [edge] };
const from = nodeCenter(boxes[0]),
  to = nodeCenter(boxes[1]);
assert.deepEqual(edgePorts(graph, edge), { start: from, end: to });
const positions = { a: { x: from.x, y: 260, z: from.y }, b: { x: to.x, y: 0, z: to.y } };
let checks = 0;
for (const style of ["straight", "curve", "orthogonal", "bus"]) {
  for (const scale of [0.2, 1, 2]) {
    const flat = planarScene(graph, presentation, style, scale);
    const spatial = spatialScene({ nodes, edges: [edge] }, positions, [], style);
    for (const scene of [flat, spatial]) {
      const result = await routeScene(scene, null);
      const path = result.routes.get("ab");
      assert.ok(path?.length, `${style} has a routed relation`);
      assert.deepEqual(path[0], scene.edges[0].a);
      assert.deepEqual(path.at(-1), scene.edges[0].b);
      assert.equal(path[0].x, from.x);
      assert.equal(path.at(-1).x, to.x);
      checks++;
    }
  }
}
graph.regions = [{ id: "a", cx: 50, cy: 91, radius: 80 }];
const expanded = { ...edge, sourceRegion: true };
const rim = edgePorts(graph, expanded);
assert.equal(rim.start.x, 130);
assert.deepEqual(rim.end, to);
const scene = spatialScene(
  { nodes, edges: [expanded] },
  positions,
  [{ id: "a", projection: false, members: [], center: positions.a, radius: 80, layer: "business" }],
  "straight",
);
assert.equal(scene.edges[0].a.x, 130);
console.log(JSON.stringify({ passed: true, centreRouteChecks: checks, expandedRims: 2 }));
