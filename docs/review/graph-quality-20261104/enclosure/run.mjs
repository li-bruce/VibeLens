/** Reproduce the saved-coordinate failure at the parent revision, then run repairs. */
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const directory = new URL("./", import.meta.url);
const root = new URL("../../../../", directory);
const cwd = fileURLToPath(root);
const revision = "7f7907d247beb76f1eae7995664155022d12a890";
const relative = "skills/vibelens/assets/stategraph-viewer/spatial-model.js";
const baseline = spawnSync("git", ["show", `${revision}:${relative}`], { cwd, encoding: "utf8" });
assert.equal(baseline.status, 0, baseline.stderr);
const original = await import(
  "data:text/javascript;base64," +
    Buffer.from(
      baseline.stdout.replace(
        '"./graph-layers.js"',
        JSON.stringify(
          new URL("skills/vibelens/assets/stategraph-viewer/graph-layers.js", root).href,
        ),
      ),
    ).toString("base64")
);
const coordinates = [
  [775.9554625135406, 304.35607515164065],
  [1387.3589613317151, 1446.2843874483915],
  [649.986203644909, 633.6382749044187],
  [1090.368751344015, 447.29042284012303],
  [342.97792196033197, 1297.817136616637],
  [1420.8540084617428, 439.0520013662572],
];
const nodes = [
  { id: "database", layer: "data", region: true, glyph: false },
  ...coordinates.map((_, i) => ({
    id: `table:${i}`,
    parent: "database",
    layer: "data",
    glyph: true,
  })),
];
const positions = Object.fromEntries([
  ["database", { x: 341.3830285726158, y: 0, z: -4104.077195213446, pinned: true }],
  ...coordinates.map(([x, z], i) => [`table:${i}`, { x, y: 0, z }]),
]);
const old = original.containmentVolumes({ nodes, layers: [{ id: "data" }] }, positions, 260)[0];
let failure;
try {
  assert.ok(old.radius < 850, "A hidden owner must not create the old 2882-radius circle");
} catch (error) {
  failure = { name: error.name, message: error.message, actual_radius: old.radius };
}
assert.ok(failure, "The historical source must reproduce the reported geometry failure");
writeFileSync(
  new URL("before.json", directory),
  JSON.stringify(
    {
      revision,
      source: relative,
      owner_visible: false,
      expected_failure: true,
      failure,
    },
    null,
    2,
  ) + "\n",
);

const tests = [
  "test_containment_bounds",
  "test_layered_view",
  "test_shared_layout",
  "test_ruler_controls",
  "test_edge_centres",
  "test_spatial_workspace",
  "test_spatial_planes",
  "test_viewer_semantics",
];
const checks = tests.map((name) => {
  const started = Date.now();
  const result = spawnSync(process.execPath, [`tools/${name}.mjs`], { cwd, encoding: "utf8" });
  return {
    command: `node tools/${name}.mjs`,
    exit_code: result.status,
    elapsed_ms: Date.now() - started,
    output: result.stdout + result.stderr,
  };
});
const valid = checks.every((check) => check.exit_code === 0);
writeFileSync(
  new URL("after.json", directory),
  JSON.stringify(
    {
      recorded_at: new Date().toISOString(),
      valid,
      checks,
    },
    null,
    2,
  ) + "\n",
);
assert.ok(valid, "All geometry regression checks pass");
console.log(
  JSON.stringify(
    { historical_failure_reproduced: true, current_checks_passed: checks.length },
    null,
    2,
  ),
);
