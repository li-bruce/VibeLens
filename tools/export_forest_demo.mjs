/** Export small prepared scenes plus lossless, lazily loaded recording archives.
 * Usage: node tools/export_forest_demo.mjs <reviewed-spec.json> <output-folder>
 * Inputs must already have accepted native evidence. Exporting proves identity
 * and layout consistency; it does not promote a failed recording to acceptance.
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createHash } from "node:crypto";
import { gzipSync } from "node:zlib";
import { compileForest } from "./forest_preview.mjs";

const [specPath, outputPath] = process.argv.slice(2);
if (!specPath || !outputPath) throw Error("Expected reviewed spec and output folder");
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const output = path.resolve(outputPath);
fs.mkdirSync(output, { recursive: true });
const sandbox = { module: { exports: {} }, console, setTimeout, clearTimeout };
sandbox.exports = sandbox.module.exports;
vm.createContext(sandbox);
vm.runInContext("global = this;", sandbox);
vm.runInContext(
  fs.readFileSync(
    new URL("../skills/vibelens/assets/stategraph-viewer/elk.bundled.js", import.meta.url),
    "utf8",
  ),
  sandbox,
);
vm.runInContext("elk = new module.exports();", sandbox);
const elk = {
  layout(value) {
    sandbox.input = JSON.stringify(value);
    return vm.runInContext("elk.layout(JSON.parse(input))", sandbox);
  },
};
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const epochs = {};
for (const [name, input] of Object.entries(spec.epochs)) {
  if (!/^[a-z][a-z-]*$/.test(name)) throw Error("Invalid epoch name");
  const raw = fs.readFileSync(input.recording);
  const record = JSON.parse(raw);
  if (record.build_id !== input.build_id || record.id !== input.recording_id)
    throw Error("Reviewed recording/build identity differs: " + name);
  const preview = await compileForest(record, elk);
  const compressed = gzipSync(raw);
  fs.writeFileSync(path.join(output, name + ".json"), JSON.stringify(preview));
  fs.writeFileSync(path.join(output, name + ".json.gz"), compressed);
  epochs[name] = {
    build_id: record.build_id,
    recording_id: record.id,
    raw_sha256: hash(raw),
    compressed_sha256: hash(compressed),
    compressed_bytes: compressed.length,
    preview_bytes: Buffer.byteLength(JSON.stringify(preview)),
    states: Object.fromEntries(
      Object.entries(preview.networks.states).map(([id, graph]) => [
        id,
        graph.nodes.map((node) => node.id),
      ]),
    ),
    acceptance: input.acceptance,
  };
}
fs.writeFileSync(
  path.join(output, "manifest.json"),
  JSON.stringify(
    {
      schema: "vibelens-forest-story/v1",
      epochs,
      dialogue: spec.dialogue,
    },
    null,
    2,
  ) + "\n",
);
console.log(JSON.stringify({ valid: true, epochs }, null, 2));
