/** Real native file callbacks exercise causal context; this is not DB-server acceptance. */
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { BOProbe } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs";
import { BODataRuntime } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_data.mjs";
import { buildTraceIndex } from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { boStepPlan } from "../skills/vibelens/assets/stategraph-viewer/replay-steps.js";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { parentEvent } from "../skills/vibelens/assets/stategraph-viewer/trace-evidence.js";

const nodes = [
  { id: "request", kind: "action", layer: "business" },
  { id: "callback", kind: "function" },
  { id: "point", kind: "decision" },
  ...["query", "transaction"].map((id) => ({
    id,
    kind: "function",
    data_role: "query",
    action: id === "query" ? "read" : "transaction",
  })),
].map((node) => ({ ...node, capture: { in: {}, out: { status: "string", value: "boolean" } } }));
const config = {
  operations: [
    { id: "query", action: "read" },
    { id: "transaction", action: "transaction" },
  ],
};
const events = [];
const probe = new BOProbe({
  project: { project_id: "context-test", model: { revision: "1", nodes } },
  buildId: "native-parent",
  capacity: 1024,
  sink: async (event) => events.push(event),
});
const data = new BODataRuntime(probe, config);
const directory = await mkdtemp(join(tmpdir(), "vibelens-context-"));
const file = join(directory, "data.txt");
await writeFile(file, "native contents");
const all = new Map(nodes.map((node) => [node.id, node]));

async function factsSince(offset) {
  assert.equal(await probe.flush(), true);
  const facts = events.slice(offset);
  const record = {
    id: "native-context",
    status: "stopped",
    started_at: facts[0].observed_at,
    ended_at: facts.at(-1).observed_at,
    events: facts,
    commands: [],
    gaps: [],
    context: { events: [], model: { nodes, machine: {} }, machine: {} },
    final: { machine: {} },
  };
  return { facts, record, index: buildTraceIndex(record, timeline(record), all) };
}

try {
  // Attribution may be installed before the enclosing request starts.
  await data.operation("query", () =>
    probe.span(
      "request",
      () =>
        data.executeAsync("query", () =>
          probe.span("callback", async () => {
            assert.equal(await readFile(file, "utf8"), "native contents");
            probe.record("point", "decision", () => ({ outputs: { value: true } }), {
              entity: "document-a",
              attempt: "evaluation-a",
              scope: "entity",
            });
          }),
        ),
      { entity: "file-a", attempt: "request-a", scope: "entity" },
    ),
  );
  const sequential = await factsSince(0);
  const entries = sequential.facts.filter((event) => event.phase === "enter");
  const [request, query, callback] = entries;
  assert.equal(query.parent_call_id, request.call_id);
  assert.equal(callback.parent_call_id, query.call_id);
  assert.equal(query.parent_event_id, request.id);
  assert.equal(callback.parent_event_id, query.id);
  const point = sequential.facts.find((event) => event.node === "point");
  assert.equal(point.parent_event_id, callback.id);
  assert.equal(point.parent_call_id, callback.call_id);
  assert.equal(point.entity, "document-a");
  assert.equal(parentEvent(point, sequential.facts).id, callback.id);
  const graphEdge = {
    id: "observed-point",
    type: "flow",
    members: [{ from: "callback", to: "point", type: "flow" }],
  };
  assert.deepEqual(transferEdges(point, sequential.facts, [graphEdge], all), [graphEdge.id]);
  assert.ok(
    sequential.index.links.some(
      (link) => link.type === "observation" && sequential.index.items[link.to].id === point.id,
    ),
  );
  assert.ok(entries.every((event) => event.entity === "file-a" && event.attempt === "request-a"));
  assert.equal(sequential.index.executions.chains.length, 1);
  assert.equal(sequential.index.executions.lanes.length, 1);
  assert.deepEqual(probe.bo_current_context(), {});

  // Exact synchronous result identity includes promises and lazy cursors.
  const promise = Promise.resolve("value");
  assert.equal(
    data.execute("query", () => promise),
    promise,
  );
  let consumed = false;
  const iterator = (function* () {
    consumed = true;
    yield "row";
  })();
  assert.equal(
    data.execute("query", () => iterator),
    iterator,
  );
  assert.equal(consumed, false);
  await probe.flush();

  // Both requests enter before either native read finishes. Their parent scopes
  // must remain independent through awaits and preserve the original exception.
  const offset = events.length;
  let entered = 0;
  let release;
  const ready = new Promise((resolve) => {
    release = resolve;
  });
  const expectedError = new RangeError("original native callback error");
  let staleContext;
  let resumeDetached;
  const detached = new Promise((resolve) => {
    resumeDetached = resolve;
  });
  await Promise.all(
    ["a", "b"].map((actor) =>
      data.operation("query", () =>
        probe.span(
          "request",
          async () => {
            entered++;
            if (entered === 2) release();
            if (actor === "a") staleContext = detached.then(() => probe.bo_current_context());
            await ready;
            try {
              await data.executeAsync("query", async () => {
                assert.equal(await readFile(file, "utf8"), "native contents");
                probe.record("point", "decision", () => ({ outputs: { value: actor === "a" } }), {
                  entity: "document-" + actor,
                  attempt: "evaluation-" + actor,
                  scope: "entity",
                });
                if (actor === "b") throw expectedError;
              });
              assert.equal(actor, "a");
            } catch (error) {
              assert.equal(actor, "b");
              assert.equal(error, expectedError);
            }
          },
          { entity: actor, attempt: actor, scope: "entity" },
        ),
      ),
    ),
  );
  resumeDetached();
  assert.deepEqual(await staleContext, {}, "finished async context must not be reused");
  const concurrent = await factsSince(offset);
  const roots = new Map(
    concurrent.facts
      .filter((event) => event.node === "request" && event.phase === "enter")
      .map((event) => [event.entity, event]),
  );
  for (const event of concurrent.facts.filter((event) => event.node === "query")) {
    assert.equal(event.parent_call_id, roots.get(event.entity).call_id);
    assert.equal(event.attempt, event.entity);
  }
  assert.equal(concurrent.index.executions.chains.length, 2);
  assert.equal(concurrent.index.executions.lanes.length, 2);
  assert.ok(concurrent.index.lifecycles.slices.every((slice) => slice.closed));

  // Transaction begin/body/acknowledgement use the same adopted native scope.
  const transactionOffset = events.length;
  const marker = join(directory, "committed.txt");
  await probe.span(
    "request",
    () =>
      data.transaction(
        "transaction",
        {
          begin: async () => file,
          commit: async () => writeFile(marker, "committed"),
          rollback: async () => assert.fail("unexpected rollback"),
        },
        async (resource) => {
          assert.equal(
            await data.executeAsync("query", () => readFile(resource, "utf8")),
            "native contents",
          );
        },
      ),
    { entity: "transaction", attempt: "transaction" },
  );
  assert.equal(await readFile(marker, "utf8"), "committed");
  const transaction = await factsSince(transactionOffset);
  const nativeEntries = transaction.facts.filter((event) => event.phase === "enter");
  assert.equal(nativeEntries[1].parent_call_id, nativeEntries[0].call_id);
  assert.equal(nativeEntries[2].parent_call_id, nativeEntries[1].call_id);
  assert.equal(transaction.index.executions.chains.length, 1);
  assert.ok(transaction.index.lifecycles.slices.every((slice) => slice.closed));

  // Explicit roots and another probe never acquire a neighbouring probe's parent.
  const otherEvents = [];
  const other = new BOProbe({
    project: { project_id: "another-project", model: { revision: "1", nodes } },
    buildId: "other-build",
    sink: async (event) => otherEvents.push(event),
  });
  const otherData = new BODataRuntime(other, config);
  const explicitOffset = events.length;
  await probe.span("request", async () => {
    await data.executeAsync("query", () => readFile(file), {
      parentCallId: null,
      entity: "explicit",
    });
    assert.deepEqual(other.bo_current_context(), {});
    await otherData.executeAsync("query", () => readFile(file));
  });
  await probe.flush();
  await other.flush();
  assert.equal(
    events.slice(explicitOffset).find((event) => event.node === "query").parent_call_id,
    null,
  );
  assert.equal(otherEvents[0].parent_call_id, null);
  assert.equal(data.bo_errors, 0);
  assert.equal(probe.bo_errors, 0);
  assert.equal(other.bo_errors, 0);
  assert.deepEqual(probe.bo_current_context(), {});
  const focusedOffset = events.length;
  probe.bo_set_scope(["point"]);
  let focusedArrived = 0,
    focusedRelease;
  const focusedReady = new Promise((resolve) => {
    focusedRelease = resolve;
  });
  await Promise.all(
    ["focused-a", "focused-b"].map((actor) =>
      probe.span(
        "request",
        async () => {
          focusedArrived++;
          if (focusedArrived === 2) focusedRelease();
          await focusedReady;
          await new Promise((resolve) => setTimeout(resolve, 5));
          const actual = await data.executeAsync("query", () => readFile(file, "utf8"), {
            summarize: () => assert.fail("Unselected native summary ran"),
          });
          assert.equal(actual, "native contents");
          probe.record("point", "decision", () => ({ outputs: { value: actual.length > 0 } }), {
            entity: "same-file",
            attempt: actor,
          });
        },
        {
          entity: actor,
          attempt: actor,
          inputs: () => assert.fail("Unselected input builder ran"),
          outputs: () => assert.fail("Unselected output builder ran"),
        },
      ),
    ),
  );
  const focused = await factsSince(focusedOffset);
  assert.equal(focused.facts.filter((event) => event.context_only).length, 4);
  assert.equal(focused.facts.filter((event) => event.node === "point").length, 2);
  assert.ok(
    focused.facts
      .filter((event) => event.context_only)
      .every(
        (event) =>
          Object.keys(event.inputs).length === 0 && Object.keys(event.outputs).length === 0,
      ),
  );
  assert.equal(focused.index.executions.lanes.length, 2);
  assert.ok(focused.index.executions.chains.every((chain) => chain.kind === "invocation"));
  assert.ok(focused.index.lifecycles.slices.every((slice) => slice.closed));
  assert.equal(
    boStepPlan(focused.record, timeline(focused.record), all, [], { mode: "events" }).length,
    4,
    "two actual value steps plus recording boundaries; metadata does not add replay steps",
  );
  assert.equal(data.bo_errors, 0);
  assert.equal(probe.bo_errors, 0);
  probe.bo_set_scope(null);
  console.log(
    JSON.stringify({
      valid: true,
      nativeCallbacks: true,
      concurrentBands: 2,
      singleRequestBands: 1,
      transactionParentage: true,
      staleAndForeignScopesRejected: true,
      focusedBoundaryOwnership: true,
    }),
  );
} finally {
  await probe.flush();
  await rm(directory, { recursive: true, force: true });
}
