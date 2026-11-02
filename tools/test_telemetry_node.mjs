/** Real SDK context, async boundaries and native probe compatibility, using Node 20+. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { BOProbe } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs";
import { BOOpenTelemetry, BOOpenTelemetryProcessor } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_otel.mjs";

const require = createRequire(new URL("../skills/vibelens/scripts/bo_observer/adapters/javascript/package.json", import.meta.url));
const { context, trace } = await import(pathToFileURL(require.resolve("@opentelemetry/api")));
const { AsyncLocalStorageContextManager } = await import(pathToFileURL(require.resolve("@opentelemetry/context-async-hooks")));
const { TracerProvider, SimpleSpanProcessor, InMemorySpanExporter } = await import(pathToFileURL(require.resolve("@opentelemetry/sdk-trace")));
context.setGlobalContextManager(new AsyncLocalStorageContextManager().enable());
const project = { project_id: "fixture", model: { revision: "1", nodes: [
  { id: "advance", layer: "business", capture: { in: {}, out: { state: "string" } } },
  { id: "point", kind: "parameter", capture: { out: { value: "boolean" } } },
  { id: "api", source: { path: "server.mjs", symbol: "request" }, capture: { out: { status: "number" } } },
] } };
const events = [], exporter = new InMemorySpanExporter();
let bridge;
const provider = new TracerProvider({ spanProcessors: [new SimpleSpanProcessor({ exporter }), {
  onStart: (...args) => bridge?.onStart(...args), onEnd: (...args) => bridge?.onEnd(...args),
  forceFlush: async () => {}, shutdown: async () => {},
}] });
const tracer = provider.getTracer("vibelens.tests");
const probe = new BOProbe({ project, buildId: "build", sink: (body) => events.push(body) });
const backend = probe.bo_bind_tracing(new BOOpenTelemetry(tracer));

if (process.argv.includes("--receive")) {
  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  const carrier = JSON.parse(input);
  let outgoing;
  await backend.receive(carrier, () => probe.span("advance", async () => {
    outgoing = backend.inject();
  }), { trusted: true });
  await probe.flush();
  console.log(JSON.stringify({ events, carrier: outgoing, health: probe.bo_health() }));
  await provider.shutdown();
  process.exit(0);
}

await probe.span("advance", async () => {
  probe.record("point", "read", () => ({ outputs: { value: true } }));
});
assert.equal(events[0].trace.span_id, events[1].trace.span_id);
assert.equal(events[1].parent_event_id, events[0].id);
await provider.forceFlush();
assert.equal(exporter.getFinishedSpans().length, 1);

let release, child;
const ready = new Promise((resolve) => { release = resolve; });
await probe.span("advance", async () => {
  child = (async () => {
    await ready;
    await probe.span("advance", async () => {
      probe.record("point", "read", () => ({ outputs: { value: false } }));
    }, { entity: "job" });
  })();
});
release();
await child;
await probe.flush();
const tail = events.slice(-5);
assert.deepEqual(tail.map((event) => event.phase), ["enter", "return", "enter", "read", "return"]);
assert.equal(tail[2].parent_event_id, tail[0].id);
assert.equal(tail[2].trace.parent_span_id, tail[0].trace.span_id);

let carrier;
await probe.span("advance", async () => { carrier = backend.inject(); }, {
  provenance: { workflow_id: "share-1", objects: [{ id: "file-1", type: "File", role: "input" }],
    actor: { id: "alice", kind: "user" } },
});
assert.ok(carrier.traceparent.match(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/));
assert.ok(!carrier["vibelens-context"].includes('"actor"'));
await backend.receive(carrier, () => probe.span("advance", async () => {}), { trusted: true, link: true });
await probe.flush();
const source = events.at(-4), linked = events.at(-2);
assert.notEqual(linked.trace.trace_id, source.trace.trace_id);
assert.equal(linked.trace.links[0].span_id, source.trace.span_id);
assert.equal(linked.parent_event_id, null);

bridge = new BOOpenTelemetryProcessor(backend, { protocol: "bo-telemetry/v1", backend: "opentelemetry", registrations: [
  { node: "api", source: project.model.nodes[2].source, match: { name: "GET /files" },
    capture: { out: { status: "http.response.status_code" } } },
] });
const before = events.length;
const span = tracer.startSpan("GET /files");
await probe.flush();
assert.equal(events.length, before + 1, "live entry is available before the SDK span ends");
span.setAttribute("http.response.status_code", 401);
span.end();
await probe.flush();
assert.deepEqual(events.at(-1).outputs, { status: 401 });
assert.equal(bridge.errors, 0);
const metadataStart = events.length;
const nativeActor = { id: "verified-user", kind: "user" };
await probe.span("advance", async (observed) => {
  observed.result(() => ({ outputs: { state: "done" }, provenance: { actor: nativeActor,
    objects: [{ type: "File", id: "created-file", role: "output" }] } }));
}, { provenance: { actor: null } });
await probe.flush();
assert.equal(events[metadataStart].provenance.actor, null);
assert.deepEqual(events.at(-1).provenance.actor, nativeActor);
assert.equal(events.at(-1).provenance.objects[0].id, "created-file");
await assert.rejects(probe.span("advance", async () => { throw new TypeError("private message"); }), TypeError);
await probe.flush();
assert.deepEqual(events.at(-1).exception, { type: "TypeError" });
assert.deepEqual(events.at(-1).outputs, {});
assert.ok(!JSON.stringify(events).includes("private message"));
assert.equal(exporter.getFinishedSpans().at(-1).attributes["error.type"], "TypeError");
assert.equal(exporter.getFinishedSpans().at(-1).events.length, 0);
const technicalError = tracer.startSpan("GET /files");
technicalError.recordException(new RangeError("not copied to VibeLens"));
technicalError.setAttribute("http.response.status_code", 500);
technicalError.end();
await probe.flush();
assert.deepEqual(events.at(-1).exception, { type: "RangeError" });
assert.equal(events.at(-1).outputs.status, 500);
assert.ok(!JSON.stringify(events).includes("not copied to VibeLens"));
const nativeEvents = [];
const native = new BOProbe({ project, buildId: "build", sink: (event) => nativeEvents.push(event) });
await assert.rejects(native.span("advance", async () => { throw new Error("not recorded"); }), Error);
await native.flush();
assert.deepEqual(nativeEvents.at(-1).exception, { type: "Error" });
assert.ok(!nativeEvents.at(-1).trace);

// Span IDs are only scoped by their trace. Two legitimate independent roots
// must not overwrite each other's observed call or current parent reference.
const repeated = new BOOpenTelemetryProcessor(backend, { protocol: "bo-telemetry/v1", backend: "opentelemetry", registrations: [
  { node: "api", source: project.model.nodes[2].source, match: { name: "GET /files" },
    capture: { out: { status: "http.response.status_code" } } },
] });
let traceNumber = 1;
const collisionProvider = new TracerProvider({ idGenerator: {
  generateTraceId: () => (++traceNumber).toString(16).padStart(32, "0"),
  generateSpanId: () => "0000000000000007",
}, spanProcessors: [repeated] });
const collisionTracer = collisionProvider.getTracer("separate-traces");
const offset = events.length;
const first = collisionTracer.startSpan("GET /files"), second = collisionTracer.startSpan("GET /files");
await probe.flush();
assert.equal(events[offset].trace.span_id, events[offset + 1].trace.span_id);
assert.notEqual(events[offset].call_id, events[offset + 1].call_id);
for (const [span, owner] of [[first, events[offset]], [second, events[offset + 1]]]) {
  context.with(trace.setSpan(context.active(), span), () => {
    assert.equal(probe.bo_current_context().parentEventId, owner.id);
    probe.record("point", "read", () => ({ outputs: { value: true } }));
  });
  span.setAttribute("http.response.status_code", 200);
  span.end();
}
await collisionProvider.shutdown();

const old = new BOProbe({ project, buildId: "previous-build", sink: () => {} });
const oldBackend = old.bo_bind_tracing(new BOOpenTelemetry(tracer));
let queued;
await old.span("advance", async () => { queued = oldBackend.inject(); }, {
  entity: "old-entity", provenance: { workflow_id: "old-process" },
});
const migrated = events.length;
await backend.receive(queued, () => probe.span("advance", async () => {}, { entity: "current-job" }), { trusted: true });
await probe.flush();
assert.equal(events[migrated].parent_event_id, null);
assert.equal(events[migrated].parent_call_id, null);
assert.ok(!events[migrated].provenance);
assert.equal(events[migrated].trace.links[0].source_build_id, "previous-build");
assert.equal(backend.health().external_build_contexts, 1);
assert.equal(probe.bo_health().errors, 0);
for (const identity of [{ provenance: { actor: null } }, { scope: "" }, { provenance: { objects: "invalid" } }]) {
  const invalid = JSON.parse(queued["vibelens-context"]);
  invalid.identity = identity;
  assert.throws(() => backend.receiveContext({ ...queued, "vibelens-context": JSON.stringify(invalid) }, { trusted: true, strict: true }));
}
assert.equal(backend.spans.size, 0);
assert.ok(events.every((event) => event.trace.trace_id.length === 32));
const sdkSpans = exporter.getFinishedSpans().length;
await provider.shutdown();
context.disable();
console.log(JSON.stringify({ valid: true, events: events.length, sdk_spans: sdkSpans,
  checks: ["SDK identity", "detached async", "W3C carrier", "linked job", "qualified objects", "live registered span"] }));
