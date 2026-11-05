/** Edge hue follows display layers without losing relation meaning or identity. */
import assert from "node:assert/strict";
import {
  edgeColor,
  crossLayerColor,
  layerConnectionColor,
} from "../skills/vibelens/assets/stategraph-viewer/edge-color.js";
import { layerPalette } from "../skills/vibelens/assets/stategraph-viewer/layer-style.js";
import {
  relationStyle,
  relationStyles,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";

const declarations = {
  business: { layer: "business", kind: "action" },
  state: { kind: "state" },
  rules: { kind: "decision" },
  entry: { code_role: "endpoint", layer: "api" },
  structure: { code_role: "file", layer: "project" },
  symbols: { code_role: "function", layer: "code" },
  data: { data_role: "dataset" },
  unknown: { kind: "unrecognized" },
};
const nodes = new Map(
  Object.entries(declarations).flatMap(([layer, declaration]) =>
    ["a", "b"].map((suffix) => {
      const id = `${layer}.${suffix}`;
      return [id, { id, ...declaration }];
    }),
  ),
);
const boxes = new Map([...nodes].map(([id, node]) => [id, { id, node }]));
let checked = 0;
// All layer pairs, all relation patterns, both model and renderer inputs. A new
// relation type must not introduce a second color vocabulary or change IDs.
for (const source of Object.keys(declarations)) {
  for (const target of Object.keys(declarations)) {
    for (const type of Object.keys(relationStyles)) {
      const edge = Object.freeze({
        id: `${source}:${type}:${target}`,
        from: `${source}.a`,
        to: `${target}.b`,
        type,
      });
      const expected = source === target ? layerPalette[source] : crossLayerColor;
      assert.equal(layerConnectionColor(source, target), expected, "Timeline row color");
      const before = JSON.stringify(edge);
      for (const index of [nodes, boxes]) {
        const style = relationStyle(edge, index);
        assert.equal(style.color, expected, edge.id);
        assert.deepEqual(style.dash, relationStyles[type].dash);
        assert.equal(style.arrow, relationStyles[type].arrow);
      }
      assert.equal(JSON.stringify(edge), before);
      checked++;
    }
  }
}

// Folded paths have displayed endpoints and retain original members as evidence.
const members = Object.freeze([
  Object.freeze({ id: "source-a", from: "business.a", to: "symbols.a", type: "call" }),
  Object.freeze({ id: "source-b", from: "symbols.a", to: "data.a", type: "reads" }),
]);
const projected = { id: "path", from: "business.a", to: "data.a", type: "indirect", members };
assert.equal(edgeColor(projected, boxes), crossLayerColor);
assert.equal(relationStyle(projected, boxes).arrow, "open");
assert.ok(relationStyle(projected, boxes).dash.length);
assert.equal(edgeColor({ ...projected, to: "business.b" }, boxes), layerPalette.business);
assert.equal(projected.members, members);

const capture = {
  id: "capture",
  from: "symbols.a",
  to: "symbols.b",
  type: "data",
  members: [{ origin: "capture-field", label: "Recorded input" }],
};
assert.equal(relationStyle(capture, boxes).color, layerPalette.symbols);
assert.equal(relationStyle(capture, boxes).label, "Recorded input");
assert.deepEqual(relationStyle(capture, boxes).dash, [3, 5]);
assert.deepEqual(
  relationStyle({ ...capture, members: [{ evidence_kind: "conceptual" }] }, boxes).dash,
  [4, 4],
);

// A state-valued observation belongs to the state plane even when its raw kind
// is a value. Reversing a recorded transfer does not change its layer hue.
nodes.set("phase", { id: "phase", kind: "data", semantic_role: "state_parameter" });
assert.equal(edgeColor({ from: "phase", to: "state.a" }, nodes), layerPalette.state);
assert.equal(edgeColor({ from: "state.a", to: "phase", reverse: true }, nodes), layerPalette.state);
assert.equal(edgeColor({ from: "absent", to: "phase" }, nodes), crossLayerColor);
assert.equal(
  edgeColor({ from: "business.a", to: "business.a", guide: true }, nodes),
  crossLayerColor,
);
assert.equal(edgeColor({ from: "business.a", to: "business.a" }, nodes), layerPalette.business);
assert.equal(
  relationStyle({ type: "call" }).color,
  crossLayerColor,
  "Legend has no endpoint context",
);
assert.equal(relationStyle({ type: "call" }).dash.length, 0);
assert.ok(relationStyle({ type: "guard" }).dash.length);
assert.equal(relationStyle({ type: "contains" }).arrow, "none");
console.log(
  `PASS: ${checked} layer/relation combinations; projection, reversal, missing endpoints and stable identities.`,
);
