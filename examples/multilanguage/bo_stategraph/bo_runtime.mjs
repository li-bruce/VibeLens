// Native application adapter. No Python imports or observer-dependent decisions.
// Only the declared flat bo.fsm/1 subset executes here; other engines need adapters.
/** Reject unsupported machine semantics and missing guards before an executor is created. */
export function bo_validateMachine(machine, guards = {}) {
  if (machine.engine !== "bo.fsm" || machine.version !== "1")
    throw Error("Unsupported native machine engine/version");
  if (machine.execution || machine.states.some((s) => typeof s !== "string"))
    throw Error("bo.fsm/1 is flat; hierarchy/activity needs an explicit engine adapter");
  const allowed = new Set([
    "engine",
    "version",
    "states",
    "values",
    "initial",
    "state_type",
    "transitions",
    "events",
    "context",
    "guards",
    "labels",
  ]);
  if (Object.keys(machine).some((k) => !allowed.has(k)))
    throw Error("Unsupported machine semantics");
  if (
    !machine.states.length ||
    machine.states.some((s) => !s.trim()) ||
    new Set(machine.states).size !== machine.states.length ||
    !machine.states.includes(machine.initial)
  )
    throw Error("Invalid initial/states");
  if (
    machine.state_type !== "enum" ||
    machine.values?.length !== machine.states.length ||
    new Set(machine.values).size !== machine.values.length ||
    machine.values.some((s) => !machine.states.includes(s))
  )
    throw Error("Invalid state values");
  if (
    ["context", "events", "guards"].some(
      (k) => machine[k] === null || typeof machine[k] !== "object" || Array.isArray(machine[k]),
    )
  )
    throw Error("Expected context, events and guards objects");
  const names = Object.keys(machine.guards || {});
  if (names.some((n) => !Object.hasOwn(guards, n) || typeof guards[n] !== "function"))
    throw Error("Missing guard implementation");
  for (const t of machine.transitions) {
    if (
      Object.keys(t).some((k) => !["source", "dest", "trigger", "conditions", "unless"].includes(k))
    )
      throw Error("Unsupported transition semantics");
    const sources = Array.isArray(t.source) ? t.source : [t.source];
    if (
      !sources.length ||
      sources.some((s) => s !== "*" && !machine.states.includes(s)) ||
      (t.dest !== null && !machine.states.includes(t.dest)) ||
      !Object.hasOwn(machine.events, t.trigger)
    )
      throw Error("Dangling transition");
    for (const key of ["conditions", "unless"])
      for (const guard of bo_list(t[key]))
        if (!names.includes(guard)) throw Error("Undeclared guard");
  }
  for (const spec of Object.values(machine.context || {})) bo_spec(spec);
  for (const event of Object.values(machine.events || {})) {
    if (!event?.payload || typeof event.payload !== "object") throw Error("Event payload required");
    for (const spec of Object.values(event.payload)) bo_spec(spec);
  }
}
const bo_list = (v) => (v === undefined ? [] : Array.isArray(v) ? v : [v]);
/** Report standard error categories only; custom names/messages may carry data. */
function bo_error_type(error) {
  try {
    return [
      "Error",
      "TypeError",
      "ReferenceError",
      "RangeError",
      "SyntaxError",
      "URIError",
      "EvalError",
      "AbortError",
      "TimeoutError",
    ].includes(error?.name)
      ? error.name
      : "Error";
  } catch {
    return "Error";
  }
}
function bo_spec(spec) {
  if (!["integer", "number", "boolean", "string", "enum", "object", "array"].includes(spec?.type))
    throw Error("Unknown value type");
  if (spec.type === "enum" && (!Array.isArray(spec.values) || !spec.values.length))
    throw Error("Enum requires values");
  if (
    (spec.min !== undefined && !Number.isFinite(spec.min)) ||
    (spec.max !== undefined && !Number.isFinite(spec.max)) ||
    spec.min > spec.max
  )
    throw Error("Invalid value bounds");
  if (spec.items) bo_spec(spec.items);
  for (const child of Object.values(spec.properties || {})) bo_spec(child);
}
/** Validate a context or payload value recursively against the declared JSON type. */
export function bo_value(value, spec) {
  bo_spec(spec);
  const type = spec.type;
  const valid = {
    integer: Number.isSafeInteger(value),
    number: typeof value === "number" && Number.isFinite(value),
    boolean: typeof value === "boolean",
    string: typeof value === "string",
    enum: spec.values?.some(
      (v) => typeof v === typeof value && JSON.stringify(v) === JSON.stringify(value),
    ),
    object: value !== null && typeof value === "object" && !Array.isArray(value),
    array: Array.isArray(value),
  }[type];
  if (!valid) throw Error(`Expected ${type}`);
  if (
    ["integer", "number"].includes(type) &&
    ((spec.min !== undefined && value < spec.min) || (spec.max !== undefined && value > spec.max))
  )
    throw Error("Value outside bounds");
  if (type === "array" && spec.items) for (const v of value) bo_value(v, spec.items);
  if (type === "object") {
    for (const k of spec.required || [])
      if (!Object.hasOwn(value, k)) throw Error("Missing property");
    for (const [k, s] of Object.entries(spec.properties || {}))
      if (Object.hasOwn(value, k)) bo_value(value[k], s);
  }
}
export class BOExecutor {
  constructor(machine, guards = {}) {
    bo_validateMachine(machine, guards);
    this.bo_definition = structuredClone(machine);
    this.bo_guards = guards;
  }
  /** Return one destination and its guard results; the application commits the effects. */
  step(state, event, context, payload = {}) {
    const m = this.bo_definition;
    if (!m.states.includes(state) || !Object.hasOwn(m.events, event))
      throw Error("Unknown state/event");
    if (Object.keys(context).some((k) => !Object.hasOwn(m.context, k)))
      throw Error("Unknown context field");
    for (const [k, s] of Object.entries(m.context)) {
      if (!Object.hasOwn(context, k)) throw Error("Missing context");
      bo_value(context[k], s);
    }
    const fields = m.events[event].payload;
    if (Object.keys(payload).some((k) => !Object.hasOwn(fields, k)))
      throw Error("Unknown payload field");
    for (const [k, s] of Object.entries(fields)) {
      if (!Object.hasOwn(payload, k)) throw Error("Missing payload");
      bo_value(payload[k], s);
    }
    const evaluated = {};
    const guard = (name) => {
      if (!Object.hasOwn(evaluated, name)) {
        const v = this.bo_guards[name](structuredClone(context), structuredClone(payload));
        if (typeof v !== "boolean") throw Error("Guard must return boolean synchronously");
        evaluated[name] = v;
      }
      return evaluated[name];
    };
    for (const t of m.transitions)
      if (
        t.trigger === event &&
        (bo_list(t.source).includes(state) || bo_list(t.source).includes("*"))
      ) {
        if (bo_list(t.conditions).every(guard) && bo_list(t.unless).every((n) => !guard(n)))
          return {
            state: t.dest ?? state,
            guards: evaluated,
            event,
            payload: structuredClone(payload),
          };
      }
    throw Error("No enabled transition");
  }
}

/** Copy declared capture fields only, with bounded values and JSON-safe numbers. */
export function bo_selected(value, spec, depth = 0) {
  if (depth > 6) throw Error("Capture depth exceeded");
  if (Array.isArray(spec)) {
    if (!Array.isArray(value) || spec.length !== 1 || value.length > 64)
      throw Error("Bounded array required");
    return value.map((v) => bo_selected(v, spec[0], depth + 1));
  }
  if (spec && typeof spec === "object") {
    if (value === null || typeof value !== "object" || Array.isArray(value))
      throw Error("Expected selected object");
    return Object.fromEntries(
      Object.entries(spec)
        .filter(([k]) => Object.hasOwn(value, k))
        .map(([k, s]) => [k, bo_selected(value[k], s, depth + 1)]),
    );
  }
  if (value === null) return null;
  if (
    ["number", "scalar"].includes(spec) &&
    typeof value === "number" &&
    Number.isFinite(value) &&
    (!Number.isInteger(value) || Number.isSafeInteger(value))
  )
    return value;
  if (["boolean", "scalar"].includes(spec) && typeof value === "boolean") return value;
  if (["string", "scalar"].includes(spec) && typeof value === "string" && value.length <= 256)
    return value;
  throw Error("Unapproved capture type");
}

let bo_invocation_store = null;

/** Native adapters install task-local storage; browser callers retain explicit child scopes. */
export function bo_use_context_store(store) {
  if (typeof store?.run !== "function" || typeof store?.getStore !== "function")
    throw Error("Invocation context requires run and getStore");
  bo_invocation_store ||= store;
  return bo_invocation_store;
}

/** Queue observations separately from business decisions; delivery failures stay local. */
export class BOProbe {
  bo_boundary_events = true;
  bo_current_context({ allowEnded = false } = {}) {
    const parent = this.bo_tracing ? this.bo_tracing.current() : bo_invocation_store?.getStore();
    if (!parent || parent.probe !== this || (!parent.active && !allowEnded)) return {};
    return {
      ...Object.fromEntries(
        ["entity", "attempt", "scope", "basis", "provenance"]
          .filter((key) => Object.hasOwn(parent.identity, key))
          .map((key) => [key, parent.identity[key]]),
      ),
      parentCallId: parent.callId,
      parentEventId: parent.entryId || null,
    };
  }

  /** Bind an optional SDK context backend; state execution and graph identity stay native. */
  bo_bind_tracing(backend) {
    if (this.bo_tracing) throw Error("Tracing backend already bound");
    backend.bind(this);
    this.bo_tracing = backend;
    return backend;
  }

  /** Keep explicit entity identities while inheriting actual enclosing call ownership. */
  bo_context_options(identity = {}, { allowEnded = false } = {}) {
    const current = this.bo_current_context({ allowEnded });
    if (Object.hasOwn(identity, "parentCallId") && identity.parentCallId !== current.parentCallId)
      delete current.parentEventId;
    if (
      Object.hasOwn(identity, "parentEventId") &&
      identity.parentEventId !== current.parentEventId
    )
      delete current.parentCallId;
    return { ...current, ...identity };
  }

  /** Adopt an already-emitted native call; synchronous return identity stays untouched. */
  bo_call_context(node, callId, identity, callback) {
    if (!bo_invocation_store && !this.bo_tracing) return callback();
    const state = { probe: this, node, callId, identity, entryId: identity.entryId, active: true };
    const run = this.bo_tracing ? this.bo_tracing : bo_invocation_store;
    return run.run(state, () => {
      try {
        return callback();
      } finally {
        state.active = false;
      }
    });
  }

  async bo_call_context_async(node, callId, identity, callback) {
    if (!bo_invocation_store && !this.bo_tracing) return await callback();
    const state = { probe: this, node, callId, identity, entryId: identity.entryId, active: true };
    const run = this.bo_tracing ? this.bo_tracing : bo_invocation_store;
    return await run.run(state, async () => {
      try {
        return await callback();
      } finally {
        state.active = false;
      }
    });
  }

  /** Physical constructor identity is distinct from a configured business outcome. */
  bo_exception(error) {
    let type = "ThrownValue";
    try {
      if (error instanceof Error) type = error.constructor?.name || "Error";
    } catch {
      type = "Error";
    }
    return this.bo_exception_metadata({ type });
  }

  bo_exception_metadata(value) {
    if (
      !value ||
      typeof value !== "object" ||
      Array.isArray(value) ||
      Object.keys(value).length !== 1 ||
      typeof value.type !== "string" ||
      !value.type.length ||
      value.type.length > 256 ||
      !value.type.split(".").every((part) => /^[\p{L}_$][\p{L}\p{N}\p{M}_$]*$/u.test(part))
    )
      throw Error("Invalid exception class metadata");
    return { type: value.type };
  }

  /** Own a real asynchronous lifetime. Explicit child scopes avoid ambient async leakage. */
  async span(node, operation, { inputs = () => ({}), outputs = () => ({}), ...options } = {}) {
    const activation = this.startSpan(node, () => ({ inputs: inputs() }), options);
    return await activation.run(async () => {
      try {
        const result = await operation(activation);
        activation.finish(() => ({ outputs: outputs(result) }));
        return result;
      } catch (error) {
        activation.fail(() => ({
          outputs: { error: error?.name || "Error" },
          exception: this.bo_exception(error),
        }));
        throw error;
      }
    });
  }

  /** Synchronous callers may finish explicitly; business results stay with the caller. */
  startSpan(node, builder = () => ({}), options = {}) {
    const context = {
      parentCallId: null,
      parentEventId: null,
      ...this.bo_context_options(options, { allowEnded: true }),
      callId: options.callId || globalThis.crypto.randomUUID(),
      lifecycle: "span",
    };
    let closed = false,
      completionBuilder = null;
    const record = (phase, values = () => ({})) => this.record(node, phase, values, context);
    const finish = (phase, values) => {
      if (closed) return null;
      closed = true;
      return record(phase, values);
    };
    const entryId = record("enter", builder);
    return {
      entryId,
      callId: context.callId,
      record,
      result: (builder) => {
        completionBuilder = builder;
      },
      finish: (values) => finish("return", completionBuilder || values),
      fail: (values) => finish("error", values),
      run: (operation) =>
        this.bo_call_context_async(node, context.callId, { ...context, entryId }, operation),
      child: (child, operation, settings = {}) =>
        this.span(child, operation, {
          ...Object.fromEntries(
            ["entity", "attempt", "scope", "basis", "provenance"]
              .filter((key) => Object.hasOwn(context, key))
              .map((key) => [key, context[key]]),
          ),
          parentCallId: context.callId,
          parentEventId: entryId,
          ...settings,
        }),
    };
  }

  constructor({
    project,
    buildId,
    endpoint,
    token,
    runId = globalThis.crypto.randomUUID(),
    producerId = globalThis.crypto.randomUUID(),
    enabled = true,
    capacity = 256,
    timeout = 1000,
    sink = null,
  }) {
    this.bo_project = project;
    this.bo_build = buildId;
    this.bo_endpoint = endpoint;
    this.bo_token = token;
    this.bo_run = runId;
    this.bo_producer = producerId;
    this.bo_enabled = enabled;
    this.bo_tracing = null;
    this.bo_capacity = capacity;
    this.bo_timeout = timeout;
    this.bo_sink = sink;
    this.bo_queue = [];
    this.bo_submitted = this.bo_completed = this.bo_flush_target = 0;
    this.bo_seq = 0;
    this.bo_busy = false;
    this.bo_internal = false;
    this.bo_errors = 0;
    this.bo_dropped = 0;
    this.bo_suppressed = 0;
    this.bo_filtered = 0;
    this.bo_capture_nodes = null;
    this.bo_last_error = null;
    this.bo_nodes = new Map(project.model.nodes.map((n) => [n.id, n]));
    const excluded = project.model.implementation?.excluded || {};
    this.bo_excluded = new Set(
      project.model.nodes
        .filter(
          (n) =>
            n.source && excluded[`${n.source.path}::${n.source.symbol}`]?.category === "observer",
        )
        .map((n) => n.id),
    );
  }
  /** Temporarily limit capture owners without running excluded value builders. */
  bo_set_scope(nodes) {
    if (
      nodes !== null &&
      (!Array.isArray(nodes) ||
        nodes.some((id) => typeof id !== "string" || !this.bo_nodes.has(id)))
    )
      throw Error("Capture scope requires known node IDs or null");
    this.bo_capture_nodes = nodes === null ? null : new Set(nodes);
  }
  /** Read transport state; a host bridge may expose this to the Python observer. */
  bo_health() {
    return {
      enabled: this.bo_enabled,
      boundary_context: true,
      run_id: this.bo_run,
      producer_id: this.bo_producer,
      enqueued: this.bo_seq,
      pending: this.bo_queue.length + (this.bo_busy ? 1 : 0),
      queue_submitted: this.bo_submitted,
      queue_completed: this.bo_completed,
      flush_target: this.bo_flush_target,
      errors: this.bo_errors,
      dropped: this.bo_dropped,
      filtered: this.bo_filtered,
      last_error: this.bo_last_error ? { ...this.bo_last_error } : null,
      ...(this.bo_tracing ? { tracing: this.bo_tracing.health() } : {}),
    };
  }
  record(node, phase, builder, options = {}) {
    if (!this.bo_enabled) return null;
    if (this.bo_internal || this.bo_excluded.has(node)) {
      this.bo_suppressed++;
      return null;
    }
    let boundary;
    try {
      boundary =
        options?.contextBoundary ||
        (options?.lifecycle === "span"
          ? { enter: "start", return: "end", error: "end" }[phase]
          : null);
      const filtered = this.bo_capture_nodes !== null && !this.bo_capture_nodes.has(node);
      if (filtered) {
        this.bo_filtered++;
        if (!["start", "end"].includes(boundary)) return null;
      }
      this.bo_internal = true;
      const {
        entity = "application",
        attempt = "application",
        scope = "application",
        basis = {},
        callId = null,
        parentCallId = null,
        parentEventId = null,
        depends = [],
        revision = null,
        lifecycle = null,
        provenance = null,
      } = this.bo_context_options(options, { allowEnded: boundary === "start" });
      if (!this.bo_nodes.has(node)) throw Error("Unknown capture node");
      const spec = this.bo_nodes.get(node).capture || {};
      if (
        !["enter", "return", "read", "decision", "wait", "commit", "change", "error"].includes(
          phase,
        )
      )
        throw Error("Unknown phase");
      const values = filtered ? {} : builder();
      if (options.contextBoundary != null && !["start", "end"].includes(options.contextBoundary))
        throw Error("Invalid physical context boundary");
      if (lifecycle !== null && lifecycle !== "span")
        throw Error("Invalid lifecycle boundary mode");
      const seq = ++this.bo_seq,
        id = `${this.bo_run}:${this.bo_producer}:${seq}`;
      const event = {
        protocol: "bo-event/v1",
        schema_version: 3,
        project_id: this.bo_project.project_id,
        model_revision: this.bo_project.model.revision,
        build_id: this.bo_build,
        run_id: this.bo_run,
        producer_id: this.bo_producer,
        seq,
        id,
        node,
        phase,
        entity,
        attempt,
        scope,
        call_id: callId || id,
        parent_call_id: parentCallId,
        parent_event_id: parentEventId,
        basis: bo_selected(basis, { param_version: "number", epoch: "number", clock: "number" }),
        inputs: bo_selected(values.inputs || {}, spec.in || {}),
        outputs: bo_selected(values.outputs || {}, spec.out || {}),
        depends,
        observed_at: new Date().toISOString(),
      };
      if (revision !== null) {
        if (!Number.isSafeInteger(revision) || revision < 0) throw Error("Invalid state revision");
        event.revision = revision;
      }
      if (lifecycle !== null) event.lifecycle = lifecycle;
      const metadata = options.trace || this.bo_tracing?.observe(node, phase, callId, boundary);
      if (metadata) event.trace = structuredClone(metadata);
      const eventProvenance = Object.hasOwn(values, "provenance") ? values.provenance : provenance;
      if (eventProvenance && !filtered) event.provenance = structuredClone(eventProvenance);
      if (Object.hasOwn(values, "exception") && !filtered) {
        event.exception = this.bo_exception_metadata(values.exception);
        this.bo_tracing?.exception?.(callId, event.exception);
      }
      if (filtered) {
        Object.assign(event, {
          context_only: true,
          context_boundary: boundary,
          inputs: {},
          outputs: {},
          depends: [],
          basis: {},
        });
        delete event.revision;
      }
      if (new TextEncoder().encode(JSON.stringify(event)).length > 24576)
        throw Error("Event too large");
      if (this.bo_queue.length >= this.bo_capacity) {
        this.bo_dropped++;
        this.bo_last_error = { stage: "queue", type: "Full" };
        return null;
      }
      this.bo_queue.push({ kind: "events", body: event });
      this.bo_submitted++;
      queueMicrotask(() => this.bo_drain());
      return id;
    } catch (error) {
      this.bo_errors++;
      // Keep only safe diagnostic identity; messages may contain business data.
      this.bo_last_error = {
        stage: "capture",
        type: bo_error_type(error),
        node: typeof node === "string" && this.bo_nodes.has(node) ? node.slice(0, 160) : null,
        phase: [
          "enter",
          "return",
          "read",
          "decision",
          "wait",
          "commit",
          "change",
          "error",
        ].includes(phase)
          ? phase
          : null,
      };
      return null;
    } finally {
      try {
        this.bo_tracing?.complete(options.callId, phase, boundary);
      } catch {
        this.bo_errors++;
        this.bo_last_error = { stage: "tracing", type: "Error" };
      }
      this.bo_internal = false;
    }
  }
  snapshot(
    instanceId,
    state,
    context,
    revision,
    evidenceId,
    { event = null, guards = null, payload = null, configuration = null } = {},
  ) {
    if (!this.bo_enabled) return false;
    // A filtered or failed record has no evidence to attach. Preserve existing
    // health failures and let the collector validate every non-null identity.
    if (evidenceId == null) return false;
    if (this.bo_internal) {
      this.bo_suppressed++;
      return false;
    }
    try {
      if (this.bo_queue.length >= this.bo_capacity) {
        this.bo_dropped++;
        this.bo_last_error = { stage: "queue", type: "Full" };
        return false;
      }
      const body = {
        protocol: "bo-snapshot/v1",
        project_id: this.bo_project.project_id,
        model_revision: this.bo_project.model.revision,
        build_id: this.bo_build,
        run_id: this.bo_run,
        producer_id: this.bo_producer,
        instance_id: instanceId,
        state,
        context,
        revision,
        evidence_id: evidenceId,
        event,
        guards,
        payload,
        configuration,
      };
      const raw = JSON.stringify(body);
      if (new TextEncoder().encode(raw).length > 24576) throw Error("Snapshot too large");
      this.bo_queue.push({ kind: "snapshots", body: JSON.parse(raw) });
      this.bo_submitted++;
      queueMicrotask(() => this.bo_drain());
      return true;
    } catch (error) {
      this.bo_errors++;
      this.bo_last_error = { stage: "snapshot", type: bo_error_type(error) };
      return false;
    }
  }
  async bo_drain() {
    if (this.bo_busy) return;
    this.bo_busy = true;
    try {
      while (this.bo_queue.length) {
        const item = this.bo_queue.shift();
        try {
          if (this.bo_sink) {
            let pending;
            this.bo_internal = true;
            try {
              const deliverToSink = () => this.bo_sink(item.body, item.kind);
              pending = this.bo_tracing ? this.bo_tracing.internal(deliverToSink) : deliverToSink();
            } finally {
              this.bo_internal = false;
            }
            await pending;
          } else {
            for (let attempt = 0; attempt < 2; attempt++) {
              try {
                const sendRequest = () =>
                  fetch(`${this.bo_endpoint}/api/bo/${item.kind}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-BO-Token": this.bo_token },
                    body: JSON.stringify(item.body),
                    signal: AbortSignal.timeout(this.bo_timeout),
                  });
                const response = await (this.bo_tracing
                  ? this.bo_tracing.internal(sendRequest)
                  : sendRequest());
                if (!response.ok) throw Error("Collector rejected observation");
                break;
              } catch (error) {
                if (attempt === 1) throw error;
              }
            }
          }
        } catch (error) {
          this.bo_errors++;
          this.bo_last_error = { stage: "transport", type: bo_error_type(error) };
        } finally {
          this.bo_completed++;
        }
      }
    } finally {
      this.bo_busy = false;
    }
  }
  async flush(timeout = 2000) {
    // Freeze a prefix including snapshots; ongoing producers do not extend it.
    const target = this.bo_submitted;
    this.bo_flush_target = target;
    const deadline = Date.now() + timeout;
    while (this.bo_completed < target && Date.now() < deadline)
      await new Promise((r) => setTimeout(r, 5));
    return this.bo_completed >= target;
  }
}
