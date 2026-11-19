/** Real HTTP regression: early exits, async ownership and observer independence. */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { BOProbe } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs";
import { bo_observeHttp } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_http.mjs";
import { BOOpenTelemetry } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_otel.mjs";

const require = createRequire(
  new URL(
    "../skills/vibelens/scripts/bo_observer/adapters/javascript/package.json",
    import.meta.url,
  ),
);
const sdkImport = async (name) => import(pathToFileURL(require.resolve(name)));
const { context } = await sdkImport("@opentelemetry/api");
const { AsyncLocalStorageContextManager } = await sdkImport("@opentelemetry/context-async-hooks");
const { TracerProvider } = await sdkImport("@opentelemetry/sdk-trace");
context.setGlobalContextManager(new AsyncLocalStorageContextManager().enable());
const results = [];

async function checkBoundary(mode) {
  const events = [];
  const project = {
    project_id: "http-boundary",
    model: {
      revision: "1",
      nodes: [
        {
          id: "api",
          kind: "api",
          source: { path: "server.mjs", symbol: "upload" },
          capture: { out: { status: "number", completed: "boolean", duration_ms: "number" } },
        },
        { id: "work", kind: "function", capture: { in: { id: "string" } } },
        { id: "point", kind: "parameter", capture: { out: { id: "string" } } },
      ],
    },
  };
  const probe = new BOProbe({
    project,
    buildId: "build",
    enabled: mode !== "disabled",
    sink: (event) => {
      if (mode === "transport-fault") throw Error("transport offline");
      events.push(event);
    },
  });
  const provider = mode === "otel" ? new TracerProvider() : null;
  const tracing =
    provider && probe.bo_bind_tracing(new BOOpenTelemetry(provider.getTracer("http-test")));
  let nativeCalls = 0;
  const nativeError = new TypeError("native-error");
  const thrown = [];
  // A real request listener with a guard and parser before its business operation.
  // The observer wraps this whole listener; none of the branches know its identity.
  function nativeHandler(request, response) {
    assert.equal(this, server, "native listener receiver must be retained");
    if (request.url === "/unknown") {
      response.writeHead(404);
      response.end();
      return;
    }
    if (request.url === "/abort") {
      response.destroy();
      return;
    }
    if (request.url === "/throw") throw nativeError;
    if (request.headers.origin) {
      response.writeHead(403);
      response.end();
      return;
    }
    void (async () => {
      let body = "";
      for await (const chunk of request) body += chunk;
      let value;
      try {
        value = JSON.parse(body);
      } catch {
        response.writeHead(400);
        response.end();
        return;
      }
      nativeCalls++;
      // This happens after the synchronous request listener has returned.
      probe.record("point", "read", () => ({ outputs: { id: value.id } }));
      await probe.span(
        "work",
        async () => {
          await new Promise((resolve) => setTimeout(resolve, value.id === "slow" ? 20 : 1));
        },
        { inputs: () => ({ id: value.id }) },
      );
      response.writeHead(201);
      response.end(value.id);
    })();
  }
  const observed = bo_observeHttp(nativeHandler, {
    probe,
    resolve: (request) => (request.url === "/unknown" ? null : { node: "api" }),
  });
  assert.throws(() => bo_observeHttp(observed, { probe, resolve: () => null }), /already observed/);
  const server = createServer(function (request, response) {
    try {
      return observed.call(this, request, response);
    } catch (error) {
      thrown.push(error);
      response.writeHead(500);
      response.end();
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const send = async (body, headers = {}, route = "/upload") => {
    const response = await fetch(base + route, { method: "POST", body, headers });
    return { status: response.status, body: await response.text() };
  };
  try {
    const statuses = await Promise.all([
      send("{}", { origin: "https://unrelated.invalid" }),
      send("{"),
      send('{"id":"slow"}'),
      send('{"id":"fast"}'),
    ]);
    assert.deepEqual(
      statuses.map((x) => x.status),
      [403, 400, 201, 201],
    );
    assert.equal(nativeCalls, 2, "guard/parser exits must not invent business invocations");
    await probe.flush(5000);
    if (["native", "otel"].includes(mode)) {
      const entries = events.filter((e) => e.node === "api" && e.phase === "enter");
      const returns = events.filter((e) => e.node === "api" && e.phase === "return");
      assert.equal(entries.length, 4);
      assert.equal(returns.length, 4);
      assert.deepEqual(returns.map((e) => e.outputs.status).sort(), [201, 201, 400, 403]);
      assert.equal(new Set(entries.map((e) => e.call_id)).size, 4);
      for (const entry of entries) {
        const end = returns.find((e) => e.call_id === entry.call_id);
        assert.ok(end.outputs.completed && end.outputs.duration_ms >= 0);
        const points = events.filter((e) => e.node === "point" && e.parent_event_id === entry.id);
        const children = events.filter(
          (e) => e.node === "work" && e.phase === "enter" && e.parent_event_id === entry.id,
        );
        if (end.outputs.status === 201) {
          assert.equal(points.length, 1, `${mode}: async point retains request ownership`);
          assert.equal(children.length, 1, "async child belongs to its actual request");
          assert.equal(points[0].outputs.id, children[0].inputs.id);
          if (tracing) assert.equal(children[0].trace.parent_span_id, entry.trace.span_id);
        } else assert.equal(points.length + children.length, 0);
      }
      const before = events.length;
      assert.equal((await send("", {}, "/unknown")).status, 404);
      await probe.flush();
      assert.equal(events.length, before, "unmapped/observer requests remain excluded");
      await assert.rejects(send("", {}, "/abort"));
      await new Promise((resolve) => setTimeout(resolve, 20));
      await probe.flush();
      const aborted = events.at(-1);
      assert.equal(aborted.phase, "return");
      assert.equal(aborted.outputs.completed, false);
      assert.equal(
        Object.hasOwn(aborted.outputs, "status"),
        false,
        "no fabricated HTTP 200 on disconnect",
      );
      assert.equal((await send("", {}, "/throw")).status, 500);
      assert.equal(thrown.at(-1), nativeError, "escaping native error identity is unchanged");
      await probe.flush();
      assert.deepEqual(events.at(-1).exception, { type: "TypeError" });
      assert.equal(events.at(-1).phase, "error");
      assert.equal(probe.bo_health().errors, 0);
      if (tracing) assert.equal(tracing.spans.size, 0);

      const scope = probe.startSpan("work");
      const nativeResult = {};
      assert.equal(
        scope.runUntilEnd(() => nativeResult),
        nativeResult,
      );
      scope.finish();
    }
    if (mode === "disabled") assert.equal(events.length, 0);
    if (mode === "transport-fault") assert.ok(probe.bo_health().errors > 0);
    results.push({ mode, valid: true, native_calls: nativeCalls, recorded_events: events.length });
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await provider?.shutdown();
  }
}

try {
  for (const mode of ["native", "otel", "disabled", "transport-fault"]) await checkBoundary(mode);
  console.log(JSON.stringify({ valid: true, results }));
} finally {
  context.disable();
}
