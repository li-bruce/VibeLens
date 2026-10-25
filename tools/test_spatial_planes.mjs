/** Check actual rendered layer meshes without constructing a WebGL context. */
import assert from "node:assert/strict";
import * as T from "../skills/vibelens/assets/stategraph-viewer/spatial-three.vendor.js";
import { SpatialRenderer } from "../skills/vibelens/assets/stategraph-viewer/spatial-renderer.js";

globalThis.document = { createElement: () => ({}) };
const context = {
  model: {
    layers: [
      { id: "business", label: "Business", color: "#557eaf" },
      { id: "state", label: "States", color: "#995fa6" },
    ],
    nodes: [
      { id: "start", layer: "business" },
      { id: "end", layer: "business" },
    ],
  },
  positions: { start: { x: 10, y: 260, z: 0 }, end: { x: 30, y: 260, z: 20 } },
  settings: { gap: 260 },
  group: new T.Group(),
  labels: { append() {} },
  labelItems: [],
  callbacks: {},
};
SpatialRenderer.prototype.drawLayerGuides.call(context);
assert.equal(context.group.children[0].position.y, 260, "Layer mesh aligns with node plane");
assert.equal(context.group.children.length, 1, "Hidden or empty layers leave no mesh");
assert.equal(context.labelItems.length, 1);
assert.equal(context.labelItems[0].position.y, 260);
console.log("Rendered layer plane checks passed");
