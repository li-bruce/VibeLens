/** Re-index immutable failed evidence; this does not repair or accept that run. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { timeline } from "../../../skills/vibelens/assets/stategraph-viewer/recording.js";
import { buildTraceIndex } from "../../../skills/vibelens/assets/stategraph-viewer/trace-index.js";

const file = new URL("./dialogue-06/artifacts/actual-recording-recovered.json", import.meta.url);
const bytes = await readFile(file);
const hash = (value) => createHash("sha256").update(value).digest("hex");
const recording = JSON.parse(bytes);
const nodes = new Map(recording.context.model.nodes.map((node) => [node.id, node]));
const index = buildTraceIndex(recording, timeline(recording), nodes);
const unassigned = index.executions.chains.filter((chain) => chain.kind === "observation");
assert.ok(unassigned.length > 0, "old missing ownership stays visible");
assert.ok(unassigned.every((chain) => chain.start === chain.end));
assert.equal(hash(await readFile(file)), hash(bytes));
const result = {
  passed: true,
  scope: "read-only component replay of failed trial 06, not application acceptance",
  file: fileURLToPath(file),
  sha256: hash(bytes),
  events: recording.events.length,
  invocationBands: index.executions.lanes.filter((lane) => lane.kind === "invocation").length,
  unassignedBands: index.executions.lanes.filter((lane) => lane.kind === "observation").length,
  unassignedFacts: unassigned.length,
  inventedUnassignedIntervals: unassigned.filter((chain) => chain.start !== chain.end).length,
};
await writeFile(new URL("./old-recording-ownership-replay.json", import.meta.url), JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify(result));
