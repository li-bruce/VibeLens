/** Keep the published story honest when its source or exported evidence changes. */
import assert from "node:assert/strict";
import fs from "node:fs";
import {transferEdges} from "../skills/vibelens/assets/stategraph-viewer/recording.js";
const base = new URL("../docs/site/case-data/", import.meta.url);
const artifacts = [1, 2].map((version) =>
  JSON.parse(fs.readFileSync(new URL(`v${version}.json`, base))),
);
for (const artifact of artifacts) {
  assert.equal(artifact.provenance.kind, "real-local-execution");
  assert.equal(artifact.view.health.errors, 0);
  assert.equal(artifact.view.binding_status.status, "current");
  assert.deepEqual(artifact.recording.gaps, []);
  assert.deepEqual(artifact.recording.events, artifact.view.events);
  assert.deepEqual(artifact.code.errors, []);
  assert.equal(artifact.code.omitted_nodes, 0);
  assert.equal(artifact.recording.build_id, artifact.view.manifest.build_id);
  for (const name of [
    "app.py",
    "domain.py",
    "repository.py",
    "web/app.js",
    ...(artifact.version === 2 ? ["policy.py"] : []),
  ]) {
    const maintained = fs
      .readFileSync(new URL("../examples/exhibition-review/" + name, import.meta.url), "utf8")
      .replaceAll("\r\n", "\n");
    assert.equal(artifact.sources[name], maintained, "Published case source is stale: " + name);
  }
  assert.ok(
    artifact.view.events.some(
      (event) => event.node === "version-selection" && event.outputs.result?.selected === 2,
    ),
  );
  const request = artifact.view.events.find(
    (event) =>
      event.node === "review-policy" &&
      event.inputs.reviewed_version === 1 &&
      event.inputs.current_version === 2,
  );
  const result = artifact.view.events.find(
    (event) => event.call_id === request.call_id && event.phase === "return",
  );
  assert.equal(result.outputs.verdict, artifact.version === 1 ? "allowed" : "stale_review");
  assert.equal(artifact.business.passed, artifact.version === 2);
  assert.equal(artifact.provenance.teaching_defect, artifact.version === 1);
  const all = new Map(artifact.view.model.nodes.map(node=>[node.id,node]));
  const workflow = artifact.view.model.edges.filter(edge=>['upload:review:flow','review:publish:flow','publish:exhibit:flow'].includes(edge.id)).map(edge=>({...edge,members:[edge]}));
  for (const edge of workflow) {
    const transfer = artifact.recording.events.find(event=>event.node===edge.to && event.depends.some(dependency=>dependency.type==='control' && artifact.recording.events.some(prior=>prior.id===dependency.event && prior.node===edge.from)));
    assert.ok(transfer, 'Missing witnessed workflow transfer: '+edge.id);
    assert.ok(transferEdges(transfer, artifact.recording.events,workflow,all).includes(edge.id));
    assert.deepEqual(transferEdges({...transfer,depends:[]},artifact.recording.events,workflow,all),[], 'Declared workflow alone must not animate');
  }
}
assert.notEqual(artifacts[0].view.manifest.build_id, artifacts[1].view.manifest.build_id);
assert.deepEqual(
  artifacts[0].view.model.nodes.map((node) => node.id).sort(),
  artifacts[1].view.model.nodes.map((node) => node.id).sort(),
  "The repair must retain graph identities",
);
console.log(
  "PASS: actual mismatch, red/green outcomes, recorded transformations, source freshness, separate builds and stable graph IDs.",
);
