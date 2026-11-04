/** Check the actual served API snapshot through the unexpanded graph pipeline. */
import { writeFile } from "node:fs/promises";
import { withCodeGraph } from "../../../skills/vibelens/assets/stategraph-viewer/code-layer.js";
import { layoutGraph } from "../../../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { presentationGraph } from "../../../skills/vibelens/assets/stategraph-viewer/layout.js";

const view = await (await fetch("http://127.0.0.1:50958/api/view")).json();
const merged = withCodeGraph(view, null);
const graph = layoutGraph(merged);
const display = presentationGraph(graph);
const report = {
  project: view.model.project_id,
  build: view.manifest.build_id,
  binding: view.binding_status.status,
  optionalCodeLoaded: false,
  expandedNodes: [],
  endpoints: view.api_structure.nodes.map((node) => ({
    id: node.id,
    path: node.api.path,
    parent: node.parent,
    box: graph.byId.has(node.id),
    glyph: display.glyphs.has(node.id),
    observationSources: node.observation_sources.map((source) => source.node),
  })),
};
report.passed = report.endpoints.every((node) => node.box && node.glyph);
await writeFile(new URL("./api-initial-visibility.json", import.meta.url), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));
process.exitCode = report.passed ? 0 : 1;
