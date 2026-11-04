/** Visible glyphs and nested regions bound circles without moving saved anchors. */
import assert from "node:assert/strict";
import { performance } from "node:perf_hooks";
import {
  enclosingCircle,
  PLANAR_GLYPH_RADIUS,
  REGION_PADDING,
  SPATIAL_GLYPH_RADIUS,
  planarBodyCircle,
} from "../skills/vibelens/assets/stategraph-viewer/containment-geometry.js";
import {
  containmentVolumes,
  spatialModel,
  prepareSpatialHierarchy,
} from "../skills/vibelens/assets/stategraph-viewer/spatial-model.js";
import {
  hierarchyRegions,
  nodeCenter,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { regionPort } from "../skills/vibelens/assets/stategraph-viewer/edge-routing.js";
import { spatialScene } from "../skills/vibelens/assets/stategraph-viewer/routing-scene.js";
import { fitVisibleHierarchy } from "../skills/vibelens/assets/stategraph-viewer/containment-view.js";
import {
  emptyFilters,
  presentationGraph,
  refreshHierarchy,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { layerSlice } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";

let assertions = 0;
function contains(outer, inner, message) {
  assert.ok(
    Math.hypot(outer.x - inner.x, outer.y - inner.y) + inner.radius <= outer.radius + 1e-6,
    message,
  );
  assertions++;
}
function spatial(nodes, positions, layers = ["data"]) {
  return containmentVolumes({ nodes, layers: layers.map((id) => ({ id })) }, positions, 260);
}
const disk = (x, y, radius = 0) => ({ x, y, radius });
assert.equal(enclosingCircle([]), null);
assert.deepEqual(enclosingCircle([disk(7, 11, 9)]), disk(7, 11, 9));
assert.deepEqual(enclosingCircle([disk(0, 0, 2), disk(10, 0, 4)]), disk(6, 0, 8));
assert.deepEqual(enclosingCircle([disk(0, 0, 10), disk(0, 0, 2)]), disk(0, 0, 10));
const triangle = [disk(0, 0, 3), disk(12, 0, 3), disk(6, 6 * Math.sqrt(3), 3)];
const triangleCircle = enclosingCircle(triangle);
assert.ok(Math.abs(triangleCircle.radius - (12 / Math.sqrt(3) + 3)) < 1e-9);
assert.deepEqual(enclosingCircle(triangle.toReversed()), triangleCircle);
assert.deepEqual(enclosingCircle(triangle, 12), {
  ...triangleCircle,
  radius: triangleCircle.radius + 12,
});
for (const member of triangle) contains(triangleCircle, member, "Exact three-disk boundary");

// These are the actual saved coordinates from the reported six-table database.
// The invisible database owner's old Z was -4104; its tables sit around 304–1446.
const tablePositions = [
  [775.9554625135406, 304.35607515164065],
  [1387.3589613317151, 1446.2843874483915],
  [649.986203644909, 633.6382749044187],
  [1090.368751344015, 447.29042284012303],
  [342.97792196033197, 1297.817136616637],
  [1420.8540084617428, 439.0520013662572],
];
const owner = { id: "database", layer: "data", glyph: false, region: true };
const nodes = [
  owner,
  ...tablePositions.map((_, i) => ({
    id: `table:${i}`,
    parent: owner.id,
    layer: "data",
    glyph: true,
    region: false,
  })),
];
const positions = Object.fromEntries(
  nodes.map((node, i) => [
    node.id,
    i
      ? {
          x: tablePositions[i - 1][0],
          y: 0,
          z: tablePositions[i - 1][1],
          pinned: i % 2 === 0,
        }
      : { x: 341.3830285726158, y: 0, z: -4104.077195213446, pinned: true },
  ]),
);
const snapshot = JSON.stringify({ nodes, positions });
const fitted = spatial(nodes, positions).find((volume) => volume.id === owner.id);
assert.ok(fitted.radius < 850, "A hidden owner must not create the old 2882-radius circle");
const movedOwner = {
  ...positions,
  database: { x: 900000, y: 0, z: -900000, pinned: true },
};
assert.deepEqual(spatial(nodes, movedOwner), spatial(nodes, positions));
assert.deepEqual(
  fitted.members.toSorted(),
  nodes
    .slice(1)
    .map((node) => node.id)
    .toSorted(),
);
for (const node of nodes.slice(1)) {
  const p = positions[node.id];
  contains(
    disk(fitted.center.x, fitted.center.z, fitted.radius),
    disk(p.x, p.z, SPATIAL_GLYPH_RADIUS),
  );
}
assert.equal(
  JSON.stringify({ nodes, positions }),
  snapshot,
  "Fitting preserves IDs and saved coordinates",
);

const selfNodes = nodes.map((node) => (node.id === owner.id ? { ...node, glyph: true } : node));
const self = spatial(selfNodes, positions).find((volume) => volume.id === owner.id);
contains(
  disk(self.center.x, self.center.z, self.radius),
  disk(positions.database.x, positions.database.z, SPATIAL_GLYPH_RADIUS),
);
assert.ok(
  self.radius > fitted.radius * 2,
  "A real self glyph contributes its genuine occupied space",
);

const nested = [
  { id: "root", layer: "business", region: true, glyph: false },
  {
    id: "child",
    parent: "root",
    layer: "operations",
    region: true,
    glyph: false,
  },
  { id: "left", parent: "child", layer: "data", glyph: true },
  { id: "right", parent: "child", layer: "data", glyph: true },
];
const saved = {
  root: { x: -50000, y: 520, z: 90000 },
  child: { x: 60000, y: 260, z: -90000 },
  left: { x: 0, y: 0, z: 0 },
  right: { x: 100, y: 0, z: 0 },
};
const nestedVolumes = spatial(nested, saved, ["business", "operations", "data"]);
assert.equal(nestedVolumes.length, 2, "No empty owner-plane circles are invented");
const child = nestedVolumes.find((volume) => volume.id === "child"),
  root = nestedVolumes.find((volume) => volume.id === "root");
assert.ok(child.projection && root.projection);
assert.equal(root.layer, "data");
assert.equal(root.center.y, 0);
contains(
  disk(root.center.x, root.center.z, root.radius),
  disk(child.center.x, child.center.z, child.radius + REGION_PADDING),
);
assert.equal(child.radius, 50 + SPATIAL_GLYPH_RADIUS + REGION_PADDING);
assert.equal(root.radius, child.radius + REGION_PADDING);

const movedLeaf = structuredClone(saved);
movedLeaf.right.x = 300;
assert.ok(spatial(nested, movedLeaf, ["data"]).find((v) => v.id === "root").radius > root.radius);
const folded = nested
  .filter((node) => node.parent !== "child")
  .map((node) => (node.id === "child" ? { ...node, glyph: true, region: false } : node));
const foldedVolumes = spatial(folded, saved, ["business", "operations", "data"]);
assert.equal(foldedVolumes.length, 1);
assert.equal(foldedVolumes[0].layer, "operations");
assert.equal(foldedVolumes[0].radius, SPATIAL_GLYPH_RADIUS + REGION_PADDING);
assert.deepEqual(spatial(nested, saved, ["api"]), [], "Unselected planes contribute no circles");
const endpoint = { x: 300, y: 0, z: 100 };
const rim = regionPort("root", "external", endpoint, saved, nestedVolumes);
assert.equal(rim.y, 0, "A region-only owner endpoint uses its occupied projection plane");
assert.ok(Math.abs(Math.hypot(rim.x - root.center.x, rim.z - root.center.z) - root.radius) < 1e-6);
const routed = spatialScene(
  {
    nodes: nested,
    edges: [
      {
        id: "out",
        from: "root",
        to: "external",
        type: "call",
        sourceRegion: true,
      },
    ],
  },
  { ...saved, external: endpoint },
  nestedVolumes,
  "curve",
);
assert.deepEqual(routed.edges[0].a, { x: rim.x, y: rim.z, level: rim.y });
const selfVolumes = spatial(selfNodes, positions);
assert.deepEqual(
  regionPort("database", "table:0", positions["table:0"], positions, selfVolumes),
  positions.database,
  "Internal self-node edges retain their actual glyph center",
);

// Planar glyphs and their actual rendered label rectangles must both fit.
const planarNodes = [
  { id: "root", kind: "action" },
  { id: "a", parent: "root", kind: "function" },
  { id: "b", parent: "root", kind: "function" },
];
const boxes = planarNodes.map((node, i) => ({
  id: node.id,
  node,
  x: i ? (i - 1) * 100 - 500 : -10000,
  y: i ? -31 : -10000,
  w: 1000,
  h: 600,
  kids: i ? [] : ["a", "b"],
  open: !i,
}));
const graph = {
  all: new Map(planarNodes.map((node) => [node.id, node])),
  boxes,
  byId: new Map(boxes.map((box) => [box.id, box])),
  rawEdges: [],
  edges: [],
};
const planar = hierarchyRegions(graph)[0];
const leafBody = planarBodyCircle(boxes[1]);
assert.equal(planar.radius, 50 + leafBody.radius + REGION_PADDING);
assert.equal(planar.cx, 50);
for (const box of boxes.slice(1)) {
  contains(disk(planar.cx, planar.cy, planar.radius), {
    ...nodeCenter(box),
    radius: PLANAR_GLYPH_RADIUS,
  });
  for (const [x, y] of [
    [box.x, box.y],
    [box.x + box.w, box.y],
    [box.x, box.y + box.h],
    [box.x + box.w, box.y + box.h],
  ])
    contains(
      disk(planar.cx, planar.cy, planar.radius),
      disk(x, y),
      "Entire rendered node label remains enclosed",
    );
}
boxes[0].x -= 30000;
assert.deepEqual(
  hierarchyRegions(graph),
  [planar],
  "A region-only owner's planar anchor is ignored",
);
boxes[2].x = 40000;
const filtered = hierarchyRegions(graph, { glyphs: new Set(["a"]), regions: new Set(["root"]) });
assert.equal(filtered[0].radius, leafBody.radius + REGION_PADDING);
assert.equal(
  filtered[0].cx,
  nodeCenter(boxes[1]).x,
  "An excluded glyph cannot enlarge a planar circle",
);
assert.deepEqual(hierarchyRegions(graph, { glyphs: new Set(), regions: new Set(["root"]) }), []);
graph.rawEdges.push({ id: "self", from: "root", to: "a", type: "call" });
const planarSelf = hierarchyRegions(graph)[0];
assert.equal(planarSelf.self, true);
assert.equal(
  planarSelf.cx,
  nodeCenter(boxes[0]).x,
  "Real planar self glyph remains at circle center",
);
contains(disk(planarSelf.cx, planarSelf.cy, planarSelf.radius), {
  ...nodeCenter(boxes[0]),
  radius: PLANAR_GLYPH_RADIUS,
});

const source = { path: "routes/files.py", symbol: "download", line: 20 };
boxes[1].node.source = source;
boxes[1].node.source_name = "download";
boxes[1].node.signature = "download(file_id)";
const model = spatialModel(graph, {
  glyphs: new Set(["a"]),
  regions: new Set(),
  edges: [],
});
assert.deepEqual(model.nodes[0].source, source);
assert.equal(model.nodes[0].source_name, "download");
assert.equal(model.nodes[0].signature, "download(file_id)");
const contained = {
  ...graph,
  rawEdges: [{ id: "contains", from: "root", to: "a", type: "code-contains" }],
};
prepareSpatialHierarchy(contained, { positions: {} });
assert.equal(
  contained.regions[0].self,
  false,
  "Lexical containment does not create a visible self glyph",
);
const grandchild = { id: "value", kind: "data", parent: "a" };
const grandchildBox = { id: "value", node: grandchild, type: "data" };
const hierarchy = spatialModel(
  {
    ...graph,
    all: new Map([...graph.all, [grandchild.id, grandchild]]),
    boxes: [...graph.boxes, grandchildBox],
  },
  { glyphs: new Set(["value"]), regions: new Set(["root"]), edges: [] },
);
assert.equal(
  hierarchy.byId.get("value").parent,
  "root",
  "Filtering an intermediate owner preserves the nearest visible ancestor",
);

const focusNodes = [
  { id: "business", kind: "action", layer: "business" },
  { id: "handler", kind: "function", parent: "business", layer: "execution" },
  { id: "next", kind: "action", layer: "business" },
];
const focusBoxes = focusNodes.map((node, i) => ({
  id: node.id,
  node,
  type: i === 1 ? "function" : "business",
  x: i * 100,
  y: 0,
  w: 100,
  h: 100,
  kids: i ? [] : ["handler"],
  open: !i,
}));
const focusEdges = [{ id: "flow", from: "business", to: "next", type: "flow" }];
const focusGraph = {
  boxes: focusBoxes,
  all: new Map(focusNodes.map((n) => [n.id, n])),
  byId: new Map(focusBoxes.map((b) => [b.id, b])),
  edges: focusEdges,
  rawEdges: focusEdges,
};
focusGraph.regions = hierarchyRegions(focusGraph);
const shown = fitVisibleHierarchy(focusGraph, presentationGraph(focusGraph, emptyFilters()));
assert.ok(shown.presentation.regions.has("business"));
assert.equal(shown.presentation.glyphs.has("business"), false);
const businessOnly = layerSlice(focusGraph, { visible: ["business"] });
const collapsed = fitVisibleHierarchy(
  businessOnly,
  presentationGraph(businessOnly, emptyFilters()),
);
assert.equal(collapsed.presentation.regions.has("business"), false);
assert.ok(
  collapsed.presentation.glyphs.has("business"),
  "Hiding every child layer retains the business owner glyph",
);
assert.equal(collapsed.presentation.edges[0].sourceRegion, false);
assert.equal(
  collapsed.graph.boxes.find((box) => box.id === "business").open,
  true,
  "Personal expansion preference is retained",
);
const hiddenChildren = { ...emptyFilters(), hiddenNodes: ["handler"] };
const childHidden = fitVisibleHierarchy(focusGraph, presentationGraph(focusGraph, hiddenChildren));
assert.ok(
  childHidden.presentation.glyphs.has("business"),
  "Explicitly hiding the last child keeps the owner visible",
);
assert.equal(childHidden.presentation.edges.length, 1);
const collapsedModel = spatialModel(collapsed.graph, collapsed.presentation);
assert.equal(
  collapsedModel.byId.get("business").glyph,
  true,
  "3D consumes the same intentional visible owner",
);
assert.equal(collapsedModel.byId.get("business").region, false);
const restored = fitVisibleHierarchy(focusGraph, presentationGraph(focusGraph, emptyFilters()));
assert.ok(
  restored.presentation.regions.has("business"),
  "Restoring child layers restores the region",
);
assert.equal(restored.presentation.glyphs.has("business"), false);
assert.equal(focusGraph.regions.length, 1, "The complete graph's region inventory is preserved");

// A layer slice shares node coordinates but caches its old scalar extents. After
// Arrange, Fit must frame the current visible bodies rather than that snapshot.
refreshHierarchy(focusGraph);
const cacheOptions = { cacheKey: "fit-regression" };
const cachedSlice = layerSlice(focusGraph, { visible: ["business"] }, cacheOptions);
const oldBounds = { minX: cachedSlice.minX, minY: cachedSlice.minY };
for (const box of focusBoxes) {
  box.x += 5000;
  box.y -= 3000;
}
refreshHierarchy(focusGraph);
const movedSlice = layerSlice(focusGraph, { visible: ["business"] }, cacheOptions);
assert.equal(movedSlice, cachedSlice, "Layout keeps the cached topological projection");
assert.equal(movedSlice.minX, oldBounds.minX, "Cached extents reproduce the stale snapshot");
const refitted = fitVisibleHierarchy(movedSlice, presentationGraph(movedSlice, emptyFilters()));
for (const box of refitted.graph.boxes.filter((box) => refitted.presentation.glyphs.has(box.id))) {
  assert.ok(box.x >= refitted.graph.minX, "Fit includes the arranged glyph's left edge");
  assert.ok(box.y >= refitted.graph.minY, "Fit includes the arranged glyph's top edge");
  assert.ok(
    box.x + box.w <= refitted.graph.minX + refitted.graph.width,
    "Fit includes the arranged glyph's right edge",
  );
  assert.ok(
    box.y + box.h <= refitted.graph.minY + refitted.graph.height,
    "Fit includes the arranged glyph's bottom edge",
  );
}
assert.equal(cachedSlice.minX, oldBounds.minX, "Refitting does not overwrite the cached view");

// An expanded owner is a region, not a second invisible body at its saved
// anchor. A filtered-out neighbor must likewise not consume camera space.
focusGraph.byId.get("business").x = -900000;
focusGraph.byId.get("business").y = -900000;
focusGraph.byId.get("next").x = 900000;
const visibleFilters = { ...emptyFilters(), hiddenNodes: ["next"] };
const visibleBefore = JSON.stringify(focusGraph.boxes);
const regionFit = fitVisibleHierarchy(focusGraph, presentationGraph(focusGraph, visibleFilters));
const region = regionFit.graph.regions.find((item) => item.id === "business");
assert.ok(region, "The expanded visible child retains its parent region");
assert.equal(regionFit.graph.minX, region.x - 55);
assert.equal(regionFit.graph.minY, region.y - 55);
assert.ok(Math.abs(regionFit.graph.width - region.w - 110) < 1e-8);
assert.ok(Math.abs(regionFit.graph.height - region.h - 110) < 1e-8);
assert.equal(JSON.stringify(focusGraph.boxes), visibleBefore, "Fit never moves saved anchors");

const emptyView = fitVisibleHierarchy(
  focusGraph,
  presentationGraph(focusGraph, {
    ...emptyFilters(),
    hiddenNodes: focusNodes.map((node) => node.id),
  }),
);
assert.equal(emptyView.presentation.glyphs.size + emptyView.presentation.regions.size, 0);
assert.ok(
  [emptyView.graph.minX, emptyView.graph.minY, emptyView.graph.width, emptyView.graph.height].every(
    Number.isFinite,
  ),
  "Empty views retain finite camera bounds",
);

// Dense regions need bounded interactive work and must contain every body.
const dense = Array.from({ length: 10000 }, (_, i) =>
  disk(
    Math.sin(i * 2.399963229728653) * Math.sqrt(i) * 4,
    Math.cos(i * 2.399963229728653) * Math.sqrt(i) * 4,
    20 + (i % 7),
  ),
);
const start = performance.now();
const denseCircle = enclosingCircle(dense, REGION_PADDING);
const elapsed = performance.now() - start;
for (const member of dense) contains(denseCircle, member, "Dense disk remains enclosed");
assert.ok(elapsed < 1500, `10,000 disk fit took ${elapsed.toFixed(1)} ms`);
console.log(
  JSON.stringify(
    {
      passed: true,
      assertions,
      real_trial_radius: fitted.radius,
      old_trial_radius: 2882.1793051870277,
      dense_disks: dense.length,
      dense_fit_ms: elapsed,
    },
    null,
    2,
  ),
);
