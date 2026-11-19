/** Isolated test wiring: never copied into the application's business functions. */
import { AsyncLocalStorage } from "node:async_hooks";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import * as app from "./application.mjs";

const config = JSON.parse(await readFile(process.argv[2], "utf8"));
const { BOProbe, bo_use_context_store } = await import(config.adapter);
bo_use_context_store(new AsyncLocalStorage());

async function run(allowed, mode) {
  const path = resolve(config.root, `store-${allowed}-${mode}.json`);
  await writeFile(path, JSON.stringify({ grant: "inactive", archive: "inactive" }));
  const events = [], native_values = {};
  const callId = "share-invocation", owner = "state-model:grant";
  const provenance = (model) => ({ objects: [{ type: model, id: "1", role: "state_owner" }] });
  const row = (model, values) => ({ model, instance: "1", invocation: callId,
    attempt: "first", build: config.build, ...values });
  const probe = new BOProbe({ project: config.project, buildId: config.build,
    enabled: mode !== "off", capacity: mode === "limited" ? 1 : 256,
    sink: async (event, kind) => {
      if (mode === "fault") throw Error("Observer transport unavailable");
      if (mode === "limited") await new Promise((resolve) => setTimeout(resolve, 40));
      if (kind === "events") events.push(event);
    } });
  native_values.share = [row(owner, { allowed })];
  try {
    await probe.span("share", async () => {
      await app.share(path, allowed);
      await app.commit(path);
      const committed = await app.read_commit(path);
      probe.record("commit", "commit", () => ({ outputs: { transaction_id: committed } }));
      native_values.commit = [row(owner, { transaction_id: await app.read_commit(path) })];
      for (const [name, state] of Object.entries(await app.read_native(path))) {
        const model = "state-model:" + name;
        probe.record(name, "read", () => ({ outputs: { state } }), { callId, provenance: provenance(model) });
        native_values[name] = [row(model, { state: (await app.read_native(path))[name] })];
      }
    }, { callId, entity: "1", attempt: "first", scope: "attempt", provenance: provenance(owner),
      inputs: () => ({ owner, allowed }) });
  } catch (error) {
    native_values.share[0].exception_type = error.constructor.name;
  }
  await probe.flush();
  return { case: allowed ? "share" : "error", mode, events, native_values,
    native_state: await app.read_native(path), health: probe.bo_health() };
}

const runs = [];
for (const mode of ["on", "off", "fault", "limited"])
  for (const allowed of [true, false]) runs.push(await run(allowed, mode));
console.log(JSON.stringify({ build_id: config.build, runs }));
