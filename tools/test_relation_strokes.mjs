/** Type-based strokes must preserve meaning, layer hue and original evidence. */
import assert from "node:assert/strict";
import { relationStyle } from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import {
  relationFamilies,
  differentTypeDash,
} from "../skills/vibelens/assets/stategraph-viewer/relation-appearance.js";
import {
  strokePasses,
  strokeProfile,
} from "../skills/vibelens/assets/stategraph-viewer/relation-strokes.js";
import { relationLineMaterial } from "../skills/vibelens/assets/stategraph-viewer/spatial-line-material.js";
import { crossLayerColor } from "../skills/vibelens/assets/stategraph-viewer/edge-color.js";
import { layerPalette } from "../skills/vibelens/assets/stategraph-viewer/layer-style.js";
import * as T from "../skills/vibelens/assets/stategraph-viewer/spatial-three.vendor.js";
import { SpatialRenderer } from "../skills/vibelens/assets/stategraph-viewer/spatial-renderer.js";

const nodes = new Map([
  ["state", { kind: "state" }],
  ["phase", { kind: "data", semantic_role: "state_parameter" }],
  ["value", { kind: "data" }],
]);
const edge = Object.freeze({ id: "physical", from: "phase", to: "state", type: "maps" });
// Same plane, different icons: type pairing wins over layer membership.
assert.deepEqual(relationStyle(edge, nodes).dash, differentTypeDash);
assert.equal(relationStyle(edge, nodes).color, layerPalette.state);
// Same icon on different planes: solid, but retain the cross-layer hue.
assert.deepEqual(relationStyle({ ...edge, to: "value" }, nodes).dash, []);
assert.equal(relationStyle({ ...edge, to: "value" }, nodes).color, crossLayerColor);
assert.equal(relationStyle({ ...edge, to: "missing" }, nodes).sameType, null);
assert.deepEqual(relationStyle({ ...edge, to: "missing" }, nodes).dash, differentTypeDash);
assert.deepEqual(
  relationStyle({ ...edge, to: "phase", guide: true }, nodes).dash,
  differentTypeDash,
);
assert.equal(edge.id, "physical");
const boxes = new Map([...nodes].map(([id, node]) => [id, { node }]));
assert.deepEqual(relationStyle(edge, nodes), relationStyle(edge, boxes));

const straight = [
  { x: 0, y: 0 },
  { x: 100, y: 0 },
];
const signatures = new Set();
for (const family of Object.values(relationFamilies)) {
  const style = { ...family, color: 0x397d6a };
  signatures.add(`${style.stroke}:${style.arrow}:${style.width}`);
  const passes = strokePasses(straight, style, 1);
  const profile = strokeProfile(style);
  assert.notEqual(style.stroke, "double", "Every relation uses one continuous route");
  assert.ok(
    passes.every((pass) => pass.points === straight),
    "No offset rails",
  );
  if (style.stroke === "bordered") {
    assert.equal(passes.length, 2);
    assert.ok(passes[0].width > passes[1].width);
    assert.notEqual(passes[0].color, passes[1].color);
    assert.equal(passes[0].points, passes[1].points);
  } else assert.equal(passes.length, 1);
  assert.equal(passes[0].width, style.width * profile.width);
  assert.ok(profile.width <= 1.8, "Borders must not dominate a dense graph");
}
assert.equal(signatures.size, 7);

// Exercise the bundled shader API, not a replica: fail on incompatible upgrades.
const material = relationLineMaterial({ vertexColors: true });
assert.ok(material.vertexShader.includes("offset *= linewidth * boStrokeProfile.x;"));
assert.ok(!material.fragmentShader.includes("if (stripe <"), "No transparent center gap");
assert.equal(material.worldUnits, false);
material.dispose();

// Exercise the real buffer builder at scale. This measures CPU construction,
// not browser FPS or a hardware-GPU guarantee. No per-edge mesh is permitted.
const timings = [];
for (const count of [1000, 20000]) {
  const model = { edges: [] },
    routes = new Map();
  const types = ["call", "flow", "guard", "maps", "contains", "join", "indirect"];
  const points = [
    { x: 0, y: 0, level: 0 },
    { x: 90, y: 20, level: 0 },
    { x: 180, y: 0, level: 0 },
  ];
  for (let i = 0; i < count; i++) {
    const id = String(i);
    model.edges.push({
      id,
      from: "phase",
      to: i % 2 ? "state" : "value",
      type: types[i % types.length],
    });
    routes.set(id, points);
  }
  const renderer = {
    model,
    input: { graph: { byId: nodes } },
    settings: { projections: false },
    positions: { phase: {}, state: {}, value: {} },
    curves: new Map(),
    router: { routes },
    group: new T.Group(),
    edgeColor: () => new T.Color(0x397d6a),
  };
  const started = performance.now();
  SpatialRenderer.prototype.drawEdges.call(renderer, new T.Object3D());
  const elapsed = performance.now() - started;
  const attributes = renderer.lines.geometry.attributes;
  assert.equal(attributes.boStrokeProfile.count, attributes.instanceStart.count);
  assert.equal(renderer.edgeSegments.length, count);
  assert.equal(
    renderer.group.children.length,
    2,
    "One line batch plus one filled-arrow instance batch",
  );
  assert.ok(attributes.boStrokeProfile.count <= count * 32, "Bounded segment/attribute growth");
  const modes = new Set(
    Array.from({ length: attributes.boStrokeProfile.count }, (_, i) =>
      attributes.boStrokeProfile.getY(i),
    ),
  );
  assert.deepEqual([...modes].sort(), [0, 2]);
  timings.push({
    edges: count,
    build_ms: Number(elapsed.toFixed(2)),
    segments: attributes.boStrokeProfile.count,
    batches: renderer.group.children.length,
  });
  renderer.group.traverse((item) => {
    item.geometry?.dispose();
    item.material?.dispose();
  });
}
console.log(
  JSON.stringify({
    valid: true,
    checks: "Types, layers, seven signatures, continuous centerlines and real Three.js buffers",
    timings,
  }),
);
