/** Verify recorded facts, immutable source, native neighborhoods and real transfers. */
import assert from "node:assert/strict";
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { expandCodeSlice } from "../docs/site/case-code.mjs";

const digest = (value) => createHash("sha256").update(value).digest("hex");
const site = new URL("../docs/site/", import.meta.url);
const localPython = fileURLToPath(
  new URL(
    process.platform === "win32" ? "../.venv/Scripts/python.exe" : "../.venv/bin/python",
    import.meta.url,
  ),
);
const python = process.env.BO_PYTHON || (fs.existsSync(localPython) ? localPython : "python");
execFileSync(
  python,
  ["-B", "-X", "utf8", fileURLToPath(new URL("./check_case_sources.py", import.meta.url))],
  { stdio: "inherit" },
);
const artifacts = [1, 2].map((version) =>
  JSON.parse(fs.readFileSync(new URL(`case-data/v${version}.json`, site))),
);
function sorted(value) {
  if (Array.isArray(value)) return value.map(sorted);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, sorted(value[key])]),
    );
  return value;
}
for (const artifact of artifacts) {
  const { view, recording, story } = artifact;
  assert.equal(artifact.provenance.kind, "real-local-execution");
  assert.equal(view.health.errors, 0);
  assert.equal(view.binding_status.status, "current");
  assert.deepEqual(recording.gaps, []);
  assert.deepEqual(recording.events, view.events);
  assert.deepEqual(artifact.code.errors, []);
  assert.equal(artifact.code.omitted_nodes, 0);
  assert.equal(recording.build_id, view.manifest.build_id);
  assert.equal(recording.build_id, artifact.provenance.build_id);
  assert.equal(artifact.business.passed, artifact.version === 2);
  assert.equal(artifact.provenance.teaching_defect, artifact.version === 1);
  for (const [name, text] of Object.entries(artifact.sources)) {
    const normalized = text.replaceAll("\r\n", "\n");
    assert.ok(
      [text, normalized, normalized.replaceAll("\n", "\r\n")].some(
        (value) => digest(value) === view.manifest.files[name],
      ) ||
        (artifact.source_checks[name].archive_sha256 === view.manifest.files[name] &&
          artifact.source_checks[name].recorded_sha256 === digest(text)),
      "Recorded source differs from its build: " + name,
    );
  }
  for (const [id, slice] of Object.entries(artifact.codeFocus)) {
    const restored = expandCodeSlice(artifact.code, slice);
    assert.equal(
      digest(JSON.stringify(sorted(restored))),
      slice.projection_sha256,
      "Native source neighborhood changed: " + id,
    );
  }
  const eventIds = new Set(recording.events.map((event) => event.id));
  const all = new Map([...view.model.nodes, ...artifact.code.nodes].map((node) => [node.id, node]));
  for (const id of [...story.business, ...story.states, ...story.focus.core, story.source_focus])
    assert.ok(all.has(id), "Missing selected identity: " + id);
  const inspection = recording.events.find((event) => event.id === story.inspection_event);
  assert.equal(inspection.node, story.inspection_node);
  for (const action of story.actions)
    assert.ok(
      recording.events.some((event) => event.node === action.node && event.phase === action.phase),
    );
  assert.ok(artifact.application_frames.length >= (artifact.version === 1 ? 3 : 6));
  for (const frame of artifact.application_frames) {
    assert.ok(eventIds.has(frame.event_id));
    for (const file of Object.values(frame.images)) {
      const bytes = fs.readFileSync(new URL(file, site));
      assert.equal(digest(bytes), frame.sha256);
      assert.equal(bytes.subarray(1, 4).toString(), "PNG");
    }
  }
  const edges = view.model.edges.map((edge) => ({ ...edge, members: [edge] }));
  const witnessed = recording.events.flatMap((event) =>
    transferEdges(event, recording.events, edges, all),
  );
  assert.ok(witnessed.length > 0, "The recording needs real, connected transfers");
  const logicalEdges = edges.filter(
    (edge) =>
      edge.origin === "policy-definition" &&
      edge.type === "guard" &&
      ["all", "any", "not"].includes(all.get(edge.to)?.operator),
  );
  assert.ok(
    recording.events.some(
      (event) => transferEdges(event, recording.events, logicalEdges, all).length > 0,
    ),
    "Actual recorded Boolean child results must animate their logical composition",
  );
  for (const event of recording.events)
    assert.deepEqual(
      transferEdges(
        { ...event, depends: [], parent_call_id: null, inputs: {}, outputs: {} },
        recording.events,
        edges,
        all,
      ),
      [],
      "A declaration alone cannot animate a transfer",
    );
}
assert.notEqual(artifacts[0].view.manifest.build_id, artifacts[1].view.manifest.build_id);
for (const id of artifacts[0].story.focus.core)
  assert.ok(
    artifacts[1].story.focus.core.includes(id),
    "The investigation keeps its core identities through repair",
  );
const source = artifacts[1].view.model.nodes.find(
  (node) => node.id === artifacts[1].story.source_focus,
).source;
assert.notEqual(
  artifacts[0].sources[source.path],
  artifacts[1].sources[source.path],
  "The demonstrated repair must change actual bound source",
);
for (const name of artifacts[1].story.maintained_sources) {
  const originalBytes = fs.readFileSync(new URL("../examples/file-sharing/" + name, import.meta.url));
  assert.equal(digest(originalBytes), artifacts[1].source_checks[name].archive_sha256, "Runnable core bytes differ from the accepted archive: " + name);
  const maintained = fs
    .readFileSync(new URL("../examples/file-sharing/" + name, import.meta.url), "utf8")
    .replaceAll("\r\n", "\n");
  assert.equal(
    artifacts[1].sources[name].replaceAll("\r\n", "\n"),
    maintained,
    "The runnable example differs from the repaired case: " + name,
  );
}
const captures = JSON.parse(fs.readFileSync(new URL("images/capture-proof.json", site)));
assert.equal(captures.captures.length, 2);
for (const capture of captures.captures) {
  assert.equal(capture.evidence.build, artifacts[0].view.manifest.build_id);
  assert.ok(capture.evidence.nodes.includes(artifacts[0].story.inspection_node));
  assert.equal(capture.files.length, 2);
  for (const file of capture.files) {
    const bytes = fs.readFileSync(new URL("../" + file.file, import.meta.url));
    assert.equal(digest(bytes), file.sha256);
    assert.equal(bytes.readUInt32BE(16), 1650);
    assert.equal(bytes.readUInt32BE(20), 840);
  }
}
console.log(
  "PASS: recorded red/green cases, exact sources and neighborhoods, causal transfers, stable investigation and real screenshots.",
);
