/** Standard tracing behind BOProbe. The application owns its provider and business state. */
import { context, trace, ROOT_CONTEXT, SpanStatusCode } from "@opentelemetry/api";
import { W3CTraceContextPropagator, suppressTracing } from "@opentelemetry/core";

const activationKey = Symbol.for("vibelens.otel.activation");
const linksKey = Symbol.for("vibelens.otel.links");
const carrierKey = "vibelens-context";

/** Configuration stays closed: unsupported options cannot silently disable capture. */
function bo_fields(value, allowed) {
  return (
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.keys(value).every((key) => allowed.includes(key))
  );
}

/** Validate private references even when an old build's identity will be discarded. */
function bo_context_provenance(value) {
  if (!bo_fields(value, ["workflow_id", "objects"])) throw Error("Invalid internal provenance");
  const valid = (item) => typeof item === "string" && item.trim().length > 0 && item.length <= 256;
  if (Object.hasOwn(value, "workflow_id") && !valid(value.workflow_id))
    throw Error("Invalid internal workflow identity");
  const objects = Object.hasOwn(value, "objects") ? value.objects : [];
  if (!Array.isArray(objects) || objects.length > 64) throw Error("Invalid internal objects");
  const seen = new Set();
  for (const item of objects) {
    if (
      !bo_fields(item, ["id", "type", "role", "version"]) ||
      ![item.id, item.type, item.role].every(valid) ||
      (Object.hasOwn(item, "version") && !valid(item.version))
    )
      throw Error("Invalid internal object reference");
    const key = JSON.stringify([item.type, item.id, item.version ?? null, item.role]);
    if (seen.has(key)) throw Error("Duplicate internal object reference");
    seen.add(key);
  }
}

/** Copy SDK identity; no payload, trace status or headers become business authority. */
export function bo_span_metadata(span, parent = span.parentSpanContext, links = span.links || []) {
  const sc = span.spanContext();
  if (!sc?.traceId || /^0+$/.test(sc.traceId)) return null;
  return {
    trace_id: sc.traceId,
    span_id: sc.spanId,
    trace_flags: sc.traceFlags,
    parent_span_id: parent?.spanId || null,
    tracestate: sc.traceState?.serialize() || "",
    links: links.map((link) => ({
      trace_id: link.context.traceId,
      span_id: link.context.spanId,
      relation: link.attributes?.["vibelens.relation"] || "trigger",
      ...(link.attributes?.["vibelens.source_build_id"]
        ? { source_build_id: link.attributes["vibelens.source_build_id"] }
        : {}),
    })),
  };
}

export class BOOpenTelemetry {
  constructor(tracer, { limit = 10000 } = {}) {
    this.tracer = tracer;
    this.limit = limit;
    this.probe = null;
    this.spans = new Map();
    this.automatic = new Map();
    this.processors = [];
    this.externalBuildContexts = 0;
    this.propagator = new W3CTraceContextPropagator();
  }
  bind(probe) {
    if (this.probe) throw Error("Tracing backend already bound to a producer");
    this.probe = probe;
  }
  /** Annotate an actual escaping exception; do not add deprecated span exception events. */
  exception(callId, value) {
    const span = this.spans.get(callId)?.span;
    span?.setAttribute("error.type", value.type);
    span?.setStatus({ code: SpanStatusCode.ERROR });
  }
  health() {
    return {
      backend: "opentelemetry",
      open_spans: this.spans.size,
      automatic_open: this.processors.reduce((sum, p) => sum + p.open.size, 0),
      automatic_errors: this.processors.reduce((sum, p) => sum + p.errors, 0),
      ignored: this.processors.reduce((sum, p) => sum + p.ignored, 0),
      external_build_contexts: this.externalBuildContexts,
    };
  }
  /** Suppress observer HTTP/export work through the upstream context convention. */
  internal(operation) {
    return context.with(suppressTracing(context.active()), operation);
  }
  current() {
    const sc = trace.getSpan(context.active())?.spanContext();
    return (
      this.automatic.get(`${sc?.traceId}:${sc?.spanId}`) || context.active().getValue(activationKey)
    );
  }
  /** SDK async context follows real callbacks and promises, including detached tasks. */
  run(activation, operation) {
    let ctx = context.active().setValue(activationKey, activation);
    const record = this.spans.get(activation.callId);
    if (record) ctx = trace.setSpan(ctx, record.span).deleteValue(linksKey);
    return context.with(ctx, operation);
  }
  observe(node, phase, callId, boundary) {
    let record = this.spans.get(callId);
    if (boundary === "start" && !record && callId) {
      if (this.spans.size >= this.limit) throw Error("Open telemetry span limit reached");
      const parent = trace.getSpan(context.active())?.spanContext();
      const links = context.active().getValue(linksKey) || [];
      const span = this.tracer.startSpan(node, { attributes: { "vibelens.node_id": node }, links });
      record = { span, parent, links };
      this.spans.set(callId, record);
    }
    if (record) {
      const metadata = bo_span_metadata(record.span, record.parent, record.links);
      if (!metadata) throw Error("Selected tracing backend lacks a configured SDK SpanContext");
      return metadata;
    }
    const current = trace.getSpan(context.active());
    return current ? bo_span_metadata(current) : null;
  }
  complete(callId, phase, boundary) {
    if (boundary !== "end") return;
    const record = this.spans.get(callId);
    this.spans.delete(callId);
    record?.span.end();
  }
  /** W3C propagation plus explicit project metadata for internal jobs. Actor is omitted. */
  inject() {
    const carrier = {};
    this.propagator.inject(context.active(), carrier, {
      set: (c, k, v) => {
        c[k] = v;
      },
    });
    const activation = this.current();
    if (activation?.probe === this.probe) {
      const identity = Object.fromEntries(
        ["entity", "attempt", "scope"]
          .filter((key) => Object.hasOwn(activation.identity, key))
          .map((key) => [key, activation.identity[key]]),
      );
      if (activation.identity.provenance) {
        identity.provenance = structuredClone(activation.identity.provenance);
        delete identity.provenance.actor;
      }
      carrier[carrierKey] = JSON.stringify({
        project_id: this.probe.bo_project.project_id,
        build_id: this.probe.bo_build,
        model_revision: this.probe.bo_project.model.revision,
        call_id: activation.callId,
        entry_id: activation.entryId,
        identity,
      });
    }
    return carrier;
  }
  /** Extract public trace context; opt into application-owned queue metadata explicitly. */
  receiveContext(carrier, { trusted = false, link = false, strict = false } = {}) {
    let ctx = this.propagator.extract(ROOT_CONTEXT, carrier, {
      get: (c, k) => c[k],
      keys: (c) => Object.keys(c),
    });
    const sc = trace.getSpan(ctx)?.spanContext();
    let activation, sourceBuild;
    if (trusted && Object.hasOwn(carrier, carrierKey)) {
      if (!sc?.traceId || /^0+$/.test(sc.traceId)) throw Error("Invalid W3C trace context");
      if (typeof carrier[carrierKey] !== "string" || carrier[carrierKey].length > 16384)
        throw Error("Invalid internal trace carrier");
      const value = JSON.parse(carrier[carrierKey]);
      if (
        !value ||
        Array.isArray(value) ||
        Object.keys(value).sort().join() !==
          ["project_id", "build_id", "model_revision", "call_id", "entry_id", "identity"]
            .sort()
            .join() ||
        [value.call_id, value.entry_id].some(
          (id) => typeof id !== "string" || !id || id.length > 512,
        )
      )
        throw Error("Invalid internal invocation reference");
      if (value.project_id !== this.probe.bo_project.project_id)
        throw Error("Internal trace carrier belongs to another project");
      if ([value.build_id, value.model_revision].some((item) => typeof item !== "string" || !item))
        throw Error("Invalid internal build identity");
      const changedBuild =
        value.build_id !== this.probe.bo_build ||
        value.model_revision !== this.probe.bo_project.model.revision;
      if (
        !value.identity ||
        typeof value.identity !== "object" ||
        Array.isArray(value.identity) ||
        Object.keys(value.identity).some(
          (key) => !["entity", "attempt", "scope", "provenance"].includes(key),
        ) ||
        Object.hasOwn(value.identity.provenance || {}, "actor")
      )
        throw Error("Invalid internal observation identity");
      if (
        ["entity", "attempt"].some(
          (key) =>
            Object.hasOwn(value.identity, key) &&
            (typeof value.identity[key] !== "string" ||
              !value.identity[key] ||
              value.identity[key].length > 256),
        ) ||
        (Object.hasOwn(value.identity, "scope") &&
          !["application", "entity", "attempt"].includes(value.identity.scope))
      )
        throw Error("Invalid internal business instance reference");
      if (Object.hasOwn(value.identity, "provenance"))
        bo_context_provenance(value.identity.provenance);
      activation = {
        probe: this.probe,
        identity: value.identity,
        callId: value.call_id,
        entryId: value.entry_id,
        active: false,
      };
      if (changedBuild) {
        if (strict || value.build_id.length > 256)
          throw Error("Internal trace carrier belongs to another graph build");
        sourceBuild = value.build_id;
        this.externalBuildContexts++;
        activation = undefined;
        link = true;
      }
    }
    if (link) {
      ctx = ROOT_CONTEXT.setValue(
        linksKey,
        sc
          ? [
              {
                context: sc,
                attributes: {
                  "vibelens.relation": "trigger",
                  ...(sourceBuild ? { "vibelens.source_build_id": sourceBuild } : {}),
                },
              },
            ]
          : [],
      );
      if (activation) activation = { ...activation, callId: null, entryId: null };
    }
    return ctx.setValue(activationKey, activation);
  }
  receive(carrier, operation, options = {}) {
    let ctx;
    try {
      ctx = this.receiveContext(carrier, options);
    } catch (error) {
      this.probe.bo_errors++;
      this.probe.bo_last_error = { stage: "trace_context", type: "Error" };
      if (options.strict) throw error;
      ctx = ROOT_CONTEXT;
    }
    return context.with(ctx, operation);
  }
  /** Fan-in links several causes; no actor or business instance is guessed from them. */
  linked(carriers, operation) {
    if (!Array.isArray(carriers) || !carriers.length || carriers.length > 32)
      throw Error("Linked execution requires 1 to 32 carriers");
    const links = carriers.map((carrier) => {
      const ctx = this.propagator.extract(ROOT_CONTEXT, carrier, {
        get: (c, k) => c[k],
        keys: Object.keys,
      });
      const sc = trace.getSpan(ctx)?.spanContext();
      if (!sc?.traceId || /^0+$/.test(sc.traceId)) throw Error("Invalid linked W3C context");
      return { context: sc, attributes: { "vibelens.relation": "trigger" } };
    });
    return context.with(ROOT_CONTEXT.setValue(linksKey, links), operation);
  }
}

/** Live bridge for selected automatic spans; all other library work stays outside the graph. */
export class BOOpenTelemetryProcessor {
  constructor(backend, configuration) {
    this.backend = backend;
    this.open = new Map();
    this.errors = this.ignored = this.suppressed = 0;
    if (
      !bo_fields(configuration, ["protocol", "backend", "registrations"]) ||
      configuration.protocol !== "bo-telemetry/v1" ||
      configuration.backend !== "opentelemetry" ||
      !Array.isArray(configuration.registrations) ||
      configuration.registrations.length > 512
    )
      throw Error("Invalid telemetry configuration");
    const selectors = new Set();
    this.items = configuration.registrations;
    for (const item of this.items) {
      if (!bo_fields(item, ["node", "source", "match", "capture"]))
        throw Error("Invalid telemetry registration");
      const node = backend.probe.bo_nodes.get(item.node);
      if (
        !node?.source ||
        node.layer === "business" ||
        item.source?.path !== node.source.path ||
        item.source?.symbol !== node.source.symbol ||
        Object.keys(item.source || {}).length !== Object.keys(node.source).length ||
        Object.keys(node.source).some((key) => item.source?.[key] !== node.source[key])
      )
        throw Error("Technical span registration needs exact API/execution/data source binding");
      if (
        !bo_fields(item.match, ["name", "attributes"]) ||
        (Object.hasOwn(item.match, "name") &&
          (typeof item.match.name !== "string" || !item.match.name)) ||
        !bo_fields(item.match.attributes || {}, Object.keys(item.match.attributes || {})) ||
        Object.values(item.match.attributes || {}).some(
          (value) => !["string", "boolean"].includes(typeof value) && !Number.isSafeInteger(value),
        ) ||
        (!item.match.name && !Object.keys(item.match.attributes || {}).length)
      )
        throw Error("Empty telemetry selector");
      const key = JSON.stringify([
        item.match.name,
        Object.entries(item.match.attributes || {}).sort(),
      ]);
      if (selectors.has(key)) throw Error("Duplicate telemetry selector");
      selectors.add(key);
      if (!bo_fields(item.capture || {}, ["in", "out"]))
        throw Error("Invalid telemetry capture mapping");
      for (const [direction, fields] of Object.entries(item.capture || {}))
        if (
          !["in", "out"].includes(direction) ||
          !bo_fields(fields, Object.keys(node.capture?.[direction] || {})) ||
          Object.values(fields).some((attr) => typeof attr !== "string" || !attr) ||
          Object.keys(fields).some(
            (field) => !Object.hasOwn(node.capture?.[direction] || {}, field),
          )
        )
          throw Error("Undeclared telemetry capture field");
    }
    backend.processors.push(this);
  }
  values(item, attributes) {
    return Object.fromEntries(
      [
        ["inputs", "in"],
        ["outputs", "out"],
      ].map(([key, dir]) => [
        key,
        Object.fromEntries(
          Object.entries(item.capture?.[dir] || {})
            .filter(([, attr]) => Object.hasOwn(attributes, attr))
            .map(([field, attr]) => [field, attributes[attr]]),
        ),
      ]),
    );
  }
  onStart(span) {
    try {
      const attributes = span.attributes || {};
      if (attributes["vibelens.node_id"] || this.backend.probe.bo_internal) {
        this.suppressed++;
        return;
      }
      const matches = this.items.filter(
        (item) =>
          (!item.match.name || item.match.name === span.name) &&
          Object.entries(item.match.attributes || {}).every(
            ([key, value]) => attributes[key] === value,
          ),
      );
      if (matches.length > 1) throw Error("Ambiguous automatic span registration");
      const item = matches[0];
      if (!item) {
        this.ignored++;
        return;
      }
      if (this.open.size >= this.backend.limit)
        throw Error("Automatic telemetry span limit reached");
      const probe = this.backend.probe,
        identity = {
          parentCallId: null,
          parentEventId: null,
          ...probe.bo_context_options({}, { allowEnded: true }),
        };
      const callId = `${span.spanContext().traceId}:${span.spanContext().spanId}`,
        metadata = bo_span_metadata(span);
      const entryId = probe.record(item.node, "enter", () => this.values(item, attributes), {
        ...identity,
        callId,
        lifecycle: "span",
        trace: metadata,
      });
      this.backend.automatic.set(callId, { probe, identity, callId, entryId, active: true });
      while (this.backend.automatic.size > this.backend.limit)
        this.backend.automatic.delete(this.backend.automatic.keys().next().value);
      this.open.set(callId, { item, identity, callId, metadata });
    } catch {
      this.reportError();
    }
  }
  onEnd(span) {
    try {
      const callId = `${span.spanContext().traceId}:${span.spanContext().spanId}`,
        state = this.open.get(callId);
      this.open.delete(callId);
      if (!state) return;
      this.backend.probe.record(
        state.item.node,
        "return",
        () => {
          const value = this.values(state.item, span.attributes || {});
          const exception = [...(span.events || [])]
            .reverse()
            .find((event) => event.name === "exception" && event.attributes?.["exception.type"]);
          if (exception) value.exception = { type: exception.attributes["exception.type"] };
          return value;
        },
        { ...state.identity, callId, lifecycle: "span", trace: state.metadata },
      );
      this.backend.automatic.get(callId).active = false;
    } catch {
      this.reportError();
    }
  }
  reportError() {
    this.errors++;
    this.backend.probe.bo_errors++;
    this.backend.probe.bo_last_error = { stage: "tracing", type: "Error" };
  }
  async shutdown() {}
  async forceFlush() {
    await this.backend.probe.flush();
  }
}
