/** Engineering/code projections share filters, containment, geometry and saved layout. */
import assert from "node:assert/strict";
import { nodeType, status } from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { layers, layerOf, cleanLayers } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { profileFor } from "../skills/vibelens/assets/stategraph-viewer/analysis.js";
import { emptyFilters, cleanFilters, emptyLayout, migrateNodeIds, hasSelfRelation } from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { migrateCodeFilters } from "../skills/vibelens/assets/stategraph-viewer/code-layer.js";
import { nodeGeometry } from "../skills/vibelens/assets/stategraph-viewer/spatial-geometry.js";
import { iconFor } from "../skills/vibelens/assets/stategraph-viewer/node-icons.js";

const directory = {id: "dir", label: "src", code_role: "directory", project_path: "src"};
assert.equal(nodeType(directory), "code-directory");
assert.equal(layerOf(directory), "project");
assert.equal(layerOf({code_role: "file"}), "project");
assert.equal(layerOf({code_role: "function"}), "code");
assert.equal(layerOf({code_role: "unresolved", reference_scope: "project"}), "project");
assert.equal(status(directory, {}, [], "latest"), "declared");
const child = {id: "file", parent: directory.id, code_role: "file"};
const tree = {all: new Map([[directory.id, directory], [child.id, child]]), rawEdges: [
  {from: directory.id, to: child.id, type: "data", origin: "code-index", code_relation: "contains"},
]};
assert.equal(hasSelfRelation(tree, directory.id), false, "Physical membership alone needs no central folder glyph");
tree.rawEdges.push({from: directory.id, to: child.id, type: "call"});
assert.equal(hasSelfRelation(tree, directory.id), true, "An actual self relation still keeps its node");
assert.equal(iconFor("code-directory").name, "folder");
const full = nodeGeometry("code-directory"), dense = nodeGeometry("code-directory", true);
assert.ok(full.getAttribute("position").count > dense.getAttribute("position").count);
full.dispose(); dense.dispose();
assert.deepEqual(profileFor("project").nodes, ["code-directory", "code-file", "code-unresolved"]);
assert.ok(profileFor("project").edges.includes("code-imports"));
assert.ok(!profileFor("project").nodes.includes("code-function"));

const previous = emptyFilters();
previous.codeTypes = 2;
previous.nodes = previous.nodes.filter((type) => type !== "code-directory");
previous.regions = previous.regions.filter((type) => type !== "code-directory");
previous.edges = previous.edges.filter((type) => !["code-contains", "code-exports", "code-links", "code-dependency"].includes(type));
assert.ok(cleanFilters(previous).nodes.includes("code-directory"));
assert.ok(cleanFilters(previous).edges.includes("code-contains"));
const narrow = {codeTypes: 2, nodes: ["code-file"], regions: [], edges: ["code-imports"]};
assert.deepEqual(migrateCodeFilters(narrow).nodes, narrow.nodes);
assert.deepEqual(migrateCodeFilters(narrow).regions, []);
assert.deepEqual(migrateCodeFilters(narrow).edges, narrow.edges);
const oldLayers = layers.filter((layer) => layer.id !== "project").map((layer) => layer.id);
const migrated = cleanLayers({order: oldLayers, visible: oldLayers});
assert.ok(migrated.visible.includes("project"));
assert.equal(migrated.order.indexOf("project"), migrated.order.indexOf("code") - 1);
const hidden = cleanLayers({...migrated, visible: oldLayers});
assert.ok(!hidden.visible.includes("project"), "New deliberate hiding survives reloading");

const layout = emptyLayout();
layout.positions.file = {x: 42, y: 108};
layout.annotations.file = {label: "Access", note: "Shared by routes", core: true};
layout.expanded = ["dir", "file"];
layout.filters.hiddenNodes = ["hidden-file"];
const before = JSON.stringify(layout);
migrateNodeIds(layout, {});
assert.equal(JSON.stringify(layout), before, "Adding directory parents does not reset existing file preferences");
console.log("PASS: project/code separation, directory 2D/3D icons and LOD, filter/layer migration, preserved file preferences.");
