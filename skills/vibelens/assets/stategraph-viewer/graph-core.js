import { codeRelations } from "./code-layer.js";
import { typeColor } from "./layer-style.js";
import { visualType as nodeType } from "./graph-classification.js";
import { activationFor } from "./graph-activation.js";
import { lifecycleCaption } from "./node-lifecycle.js";
import { activeMachineStates } from "./machine-projection.js";
import { graphInventory } from "./graph-inventory.js";
import { originalRelations, relationExcluded } from "./edge-identities.js";
import { conceptRelations, conceptRelationTypes } from "./concept-relations.js";
export { stateNodeId } from "./graph-inventory.js";
import { capturedValue } from "./capture-fields.js";
import { explainedName } from "./graph-names.js";
import { apiObservationIds, observesNode } from "./api-observation.js";
import { conceptActivityIds, conceptRuntimeIds, conceptFrameOwner } from "./concept-observation.js";
import { t as boTranslate } from "./i18n.js";
import {
  dataRoles,
  dataRelations,
  dataLines,
  observedDataTransfer,
  dataStatusClass,
} from "./data-layer.js";
// Business groups, internal activity states and local source share one graph.
export const colors = {
  ink: 0x30454d,
  muted: 0x7d8e96,
  line: 0xb6c7cc,
  green: 0x208b73,
  orange: 0xbc8739,
  blue: 0x477b9c,
  white: 0xffffff,
};
export const stateLabels = {
  pending: boTranslate("Not started"),
  waiting: boTranslate("Waiting for capacity"),
  running: boTranslate("Running"),
  succeeded: boTranslate("Passed"),
  rejected: boTranslate("Rejected"),
  failed: boTranslate("Failed"),
  cancelled: boTranslate("Cancelled"),
};
export function phaseLabel(model, value) {
  if (Array.isArray(value)) return value.map((state) => phaseLabel(model, state)).join(" · ");
  const labels = model?.machine?.labels;
  return labels && Object.hasOwn(labels, value) ? labels[value] : String(value);
}
export function compact(v) {
  if (v === undefined) return "—";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}
export function typeName(t) {
  if (Array.isArray(t)) return `list[${typeName(t[0])}]`;
  if (typeof t === "object") return "record";
  return { number: "number", string: "str", boolean: "bool" }[t] || t;
}
export function configurations(view) {
  return view.machine.configurations || view.authority.parameters.executions || [];
}
export function executionIds(view) {
  const runs = configurations(view);
  return runs.length
    ? runs.map((x) => x.attempt)
    : [...new Set(view.events.filter((e) => e.node === "read").map((e) => e.attempt))];
}
export function currentAttempt(view, choice) {
  return choice === "latest"
    ? view.authority.parameters.attempt || executionIds(view).at(-1)
    : choice;
}
export function selectedConfiguration(view, choice = "latest", step = "latest") {
  const run = configurations(view).find((r) => r.attempt === currentAttempt(view, choice));
  if (!run) return null;
  if (step === "latest") return run;
  const entry = run.journal.find((e) => String(e.seq) === String(step));
  // Historical frames contain recorded state only, never the run's later
  // results, disposition or current qualification.
  return entry
    ? {
        attempt: run.attempt,
        param_version: run.param_version,
        ...entry.after,
        phase: entry.after.phase ?? entry.phase ?? null,
        revision: entry.seq,
        selectedFrame: entry,
      }
    : null;
}
export function selectedEvents(view, choice, step = "latest") {
  const id = currentAttempt(view, choice);
  let events = view.events.filter(
    (e) =>
      e.attempt === id ||
      e.scope === "application" ||
      (e.scope === "entity" && e.entity === view.authority.entity),
  );
  if (step !== "latest") {
    // A later reevaluation may reuse an activity revision. Only its first exact
    // recorded boundary belongs to this frame; absent boundaries stay unknown.
    const parent = view.model.machine.execution?.parent;
    const frame = events.find((e) => e.node === parent && e.outputs?.revision === Number(step));
    events = frame ? events.filter((e) => e.seq <= frame.seq) : [];
  }
  return events;
}
export function sourceBinding(view, all, id) {
  if (view?.stage === "design") return undefined;
  const direct = view?.manifest.bindings[id];
  if (direct) return direct;
  const node = all?.get(id);
  if (node?.referenceOf)
    return view?.manifest.bindings[node.referenceOf] || view?.manifest.bindings[node.event_node];
  if (!node?.field) return undefined;
  const owner = view?.manifest.bindings[node.event_node || node.parent];
  // An event JSON path is not a lexical symbol. Show the owner's full file as
  // context, but never highlight it as the definition of an adapter field.
  return owner ? { ...owner, selection: undefined, provenance: "capture-owner" } : undefined;
}
export function nodeEvents(node, events) {
  const policy = node.policy_node || node.capture_owner_policy;
  // A condition skipped in the selected check must not inherit an earlier
  // request's result. Prefix replay arrays naturally select the earlier check.
  const check = policy ? events.findLast((event) => event.inputs?.bo_check)?.inputs.bo_check : null;
  return events.filter(
    (e) => observesNode(node, e.node) && (!policy || e.inputs?.bo_check === check),
  );
}
export function callValues(node, events) {
  const calls = nodeEvents(node, events),
    last = calls.at(-1);
  if (!last) return { inputs: {}, outputs: {} };
  const keys = ["node", "call_id", "run_id", "attempt", "entity", "build_id", "model_revision"];
  // Old probes used attempt:node for every call. That is not enough identity
  // to merge values; keep the last event until the caller supplies a call ID.
  const identified =
    keys.every((k) => typeof last[k] === "string" && last[k]) &&
    last.call_id !== `${last.attempt}:${last.node}`;
  const same = identified
    ? calls.filter(
        (e) =>
          keys.every((k) => e[k] === last[k]) &&
          e.basis?.param_version === last.basis?.param_version,
      )
    : [last];
  return same.reduce(
    (values, e) => ({
      inputs: { ...values.inputs, ...e.inputs },
      outputs: { ...values.outputs, ...e.outputs },
    }),
    { inputs: {}, outputs: {} },
  );
}
function activityName(view, id) {
  return view.model.nodes.find((n) => n.id === id)?.label || id;
}
function activityLabel(view, state) {
  return view.model.presentation?.name_mode === "source" ? state : stateLabels[state] || state;
}
function activityColor(state) {
  return (
    {
      running: "active",
      waiting: "blocked",
      rejected: "blocked",
      failed: "blocked",
      succeeded: "ok",
      cancelled: "historical",
    }[state] || "declared"
  );
}
function resourceOf(node, view, configuration) {
  return view.machine.shared_resources?.[node.id] || configuration?.resources?.[node.id];
}
function phaseValue(view, configuration, choice) {
  return configuration?.selectedFrame
    ? configuration.phase
    : choice === "latest"
      ? view.machine.current
      : configuration?.phase;
}
export function parameterSummary(view, _configuration = null, step = "latest") {
  if (step !== "latest") return "";
  const parameters = view.authority?.parameters || {},
    fields = view.model.presentation?.context_fields || [];
  return fields
    .filter((f) => parameters[f.key] !== undefined)
    .map(
      (f) =>
        (view.historical ? f.saved_label || f.label : f.label) +
        " " +
        compact(parameters[f.key]) +
        (f.unit ? " " + f.unit : ""),
    )
    .join(" · ");
}
function staleBasis(node, view, last) {
  const ownerId = [...apiObservationIds(node), ...conceptRuntimeIds(node)].includes(last.node)
    ? last.node
    : node.event_node || node.id;
  const owner = view.model.nodes.find((n) => n.id === ownerId) || node;
  const fields = owner.basis_fields || ["param_version"];
  return fields.some((key) => last.basis?.[key] !== view.authority.basis?.[key]);
}
export function status(node, view, events, choice, configuration = null) {
  if (node.code_role && !activationFor(node, view, events)) return "declared";
  if (view.stage === "design") return "declared";
  if (node.origin === "concept-design") {
    const sources = conceptActivityIds(node);
    if (!sources.length) return "declared";
    const nativeFrame = conceptFrameOwner(node, view);
    if (nativeFrame) return status(nativeFrame, view, events, choice, configuration);
    if (node.concept_observation?.kind === "activity")
      return events.some((event) => sources.includes(event.node)) ? "historical" : "declared";
  }
  if (node.referenceOf) node = { ...node, id: node.referenceOf };
  const ongoing = activationFor(node, view, events);
  if (ongoing?.explicit && ["running", "waiting"].includes(ongoing.phase)) {
    const last = nodeEvents(node, events).at(-1);
    if (
      view.binding_status.status !== "current" ||
      choice !== "latest" ||
      (last && staleBasis(node, view, last))
    )
      return "historical";
    return ongoing.phase === "waiting" ? "blocked" : "active";
  }
  if (["query", "write", "transaction", "transform"].includes(node.data_role)) {
    const last = nodeEvents(node, events).at(-1);
    const state = dataStatusClass(last?.outputs?.status);
    if (state) return state;
  }
  if (
    configuration?.disposition === "interrupted" &&
    (node.execution_role || node.id === view.model.machine.execution?.parent)
  )
    return "historical";
  if (node.execution_role === "activity")
    return activityColor(configuration?.activities?.[node.id]);
  if (node.execution_role === "resource") {
    const r = resourceOf(node, view, configuration);
    return typeof r?.available === "number" ? (r.available === 0 ? "blocked" : "ok") : "declared";
  }
  if (node.execution_role === "join")
    return (
      {
        waiting: "blocked",
        enabled: "active",
        passed: "ok",
        rejected: "blocked",
      }[configuration?.join?.state] || "declared"
    );
  if (node.id === view.model.machine.execution?.parent && configuration)
    return Object.values(configuration.activities || {}).includes("running")
      ? "active"
      : configuration.join?.state === "passed"
        ? "ok"
        : "blocked";
  if (node.layer === "state")
    return activeMachineStates(view.model.machine, phaseValue(view, configuration, choice)).has(
      node.value,
    )
      ? "active"
      : "declared";
  if (node.field) {
    const values = callValues(node, events)[node.direction === "in" ? "inputs" : "outputs"];
    if (!capturedValue(node, values).present) return "declared";
  }
  if (node.layer === "business") {
    const states = view.model.nodes
      .filter((n) => n.parent === node.id && n.layer !== "state")
      .map((n) => status(n, view, events, choice, configuration));
    if (!nodeEvents(node, events).length)
      return (
        ["active", "blocked", "ok", "historical"].find((s) => states.includes(s)) || "declared"
      );
  }
  const last = nodeEvents(node, events).at(-1);
  if (!last) return "declared";
  if (
    view.binding_status.status !== "current" ||
    choice !== "latest" ||
    staleBasis(node, view, last)
  )
    return "historical";
  const life = activationFor(node, view, events);
  if (life)
    return {
      running: "active",
      waiting: "blocked",
      exception: "blocked",
      returned: "historical",
      committed: "historical",
      transformed: "historical",
      ended: "historical",
      boundary: "historical",
      unknown: "declared",
    }[life.phase];
  if (
    last.phase === "wait" ||
    last.phase === "error" ||
    last.outputs.allowed === false ||
    last.outputs.safe === false
  )
    return "blocked";
  if ((node.policy_node || node.capture_owner_policy) && !node.field) {
    if (last.outputs.status === "error" || last.outputs.value === false) return "blocked";
    if (last.outputs.status === "unknown" || last.outputs.value === null) return "declared";
  }

  return last.phase === "enter" ? "active" : "ok";
}
export function lines(node, view, events, choice, configuration = null) {
  const content = baseLines(
    conceptFrameOwner(node, view) || node,
    view,
    events,
    choice,
    configuration,
  );
  const life = activationFor(node, view, events);
  const bound = conceptActivityIds(node),
    observed = events.findLast((event) => bound.includes(event.node));
  const bindingNote = observed
    ? [{ text: boTranslate("Bound observation: {0}", observed.node), role: "value" }]
    : [];
  if (!life) return [...bindingNote, ...content];
  const names = {
    running: "Running",
    waiting: "Waiting",
    returned: "Returned",
    exception: "Exception exit",
    ended: "Ended",
    boundary: "Observed boundary",
    unknown: "Unknown lifecycle",
  };
  return [
    ...bindingNote,
    {
      text:
        boTranslate(
          life.registered
            ? lifecycleCaption(life, view.model.presentation?.name_mode === "source")
            : names[life.phase] || lifecycleCaption(life) || names.unknown,
        ) + (life.activeCount > 1 ? " · " + life.activeCount : ""),
      role: life.phase === "exception" ? "bad" : "value",
    },
    ...content,
  ];
}
function baseLines(node, view, events, choice, configuration = null) {
  if (node.filter_context)
    return [
      {
        text: boTranslate("Filter boundary \u00B7 ") + nodeTypes[nodeType(node)].label,
        role: "muted",
      },
      { text: node.source?.symbol || node.summary, role: "symbol" },
    ];
  if (node.referenceOf) node = { ...node, id: node.referenceOf };
  if (dataRoles.includes(node.data_role)) {
    const values = callValues(node, events);
    return dataLines(node, values.inputs, values.outputs, nodeEvents(node, events).length > 0);
  }
  if (
    node.code_role === "endpoint" &&
    apiObservationIds(node).length &&
    nodeEvents(node, events).length
  ) {
    const values = callValues(node, events);
    return [
      ...Object.entries(values.inputs)
        .slice(0, 3)
        .map(([key, value]) => ({
          text: `${key}: ${compact(value)}`,
          role: "value",
        })),
      ...Object.entries(values.outputs)
        .slice(0, 3)
        .map(([key, value]) => ({
          text: `${key}: ${compact(value)}`,
          role: "value",
        })),
    ];
  }
  if (node.code_role)
    return [
      { text: node.summary || node.source?.path || "", role: "symbol" },
      ...(node.code_boundary
        ? [{ text: boTranslate("Outside loaded code region"), role: "muted" }]
        : []),
    ];
  if (view.stage === "design") return node.summary ? [{ text: node.summary, role: "muted" }] : [];
  if (node.policy_node && !node.field) {
    const last = nodeEvents(node, events).at(-1);
    return [
      {
        text: !last
          ? boTranslate("Not evaluated")
          : last.outputs.status === "error"
            ? boTranslate("Evaluation error")
            : last.outputs.value === null
              ? boTranslate("Unknown")
              : compact(last.outputs.value),
        role:
          !last || last.outputs.value === null
            ? "muted"
            : last.outputs.value === false
              ? "bad"
              : "value",
      },
    ];
  }
  if (node.field) {
    const values = callValues(node, events)[node.direction === "in" ? "inputs" : "outputs"];
    return [
      {
        text: [node.field, ...(node.field_path || [])].join(".") + ": " + typeName(node.fieldType),
        role: "symbol",
      },
      {
        text: capturedValue(node, values).present
          ? compact(capturedValue(node, values).value)
          : boTranslate("Not captured in this run"),
        role: capturedValue(node, values).present ? "value" : "muted",
      },
    ];
  }
  const last = nodeEvents(node, events).at(-1),
    result = [
      {
        text: node.signature || node.source?.symbol || node.summary,
        role: "symbol",
      },
    ];
  if (node.execution_role === "resource") {
    const r = resourceOf(node, view, configuration);
    if (!r) {
      result.push({
        text: boTranslate("No resource state recorded at this boundary"),
        role: "muted",
      });
      return result;
    }
    for (const [field, value] of Object.entries(r))
      result.push({
        text: `${node.field_labels?.[field] || field}：${compact(value)}`,
        role: field === "available" && value === 0 ? "bad" : "value",
      });
    return result;
  }
  if (node.execution_role) {
    if (!configuration) {
      result.push({
        text: boTranslate("No internal state recorded for this run"),
        role: "muted",
      });
      return result;
    }
    if (node.execution_role === "activity") {
      const state = configuration.activities?.[node.id];
      result.push({
        text: activityLabel(view, state) || boTranslate("Not recorded"),
        role: state === "waiting" || state === "failed" || state === "rejected" ? "bad" : "good",
      });
      if (configuration.disposition === "interrupted")
        result[result.length - 1] = {
          text:
            boTranslate("Execution interrupted; last recorded state: \u201C") +
            activityLabel(view, state) +
            "」",
          role: "muted",
        };
      result.push({
        text: `state: ${view.model.machine.execution?.activity_state_type || "str"} = ${state ?? boTranslate("Not recorded")}`,
        role: "value",
      });
      if (node.summary) result.push({ text: node.summary, role: "muted" });
    } else {
      const j = configuration.join;
      if (!j) {
        result.push({
          text: boTranslate("No join state recorded at this boundary"),
          role: "muted",
        });
        return result;
      }
      result.push({
        text:
          view.model.presentation?.name_mode === "source"
            ? j.state
            : {
                waiting: boTranslate("Some activities are unfinished"),
                enabled: boTranslate("Activities finished; checking results"),
                passed: boTranslate("All activities passed"),
                rejected: boTranslate("Some activities did not pass"),
              }[j.state] || j.state,
        role: j.state === "passed" ? "good" : "bad",
      });
      if (j.pending?.length)
        result.push({
          text:
            boTranslate("Still waiting for: ") +
            j.pending.map((x) => activityName(view, x)).join("、"),
          role: "muted",
        });
      if (node.summary) result.push({ text: node.summary, role: "muted" });
      return result;
    }
  } else if (node.layer === "state") {
    // State models, events and effects share this plane but have no state value.
    // Their declared summary and actual binding marks are sufficient.
    if (node.value === undefined) return result;
    const active = activeMachineStates(
      view.model.machine,
      phaseValue(view, configuration, choice),
    ).has(node.value);
    result.push({ text: `phase: Phase = ${node.value}`, role: "value", definition: true });
    result.push({
      text: active ? boTranslate("Flow state for this run") : boTranslate("Declared state"),
      role: "muted",
      definition: !active,
    });
    if (node.value === view.model.machine.execution?.within && configuration) {
      for (const [id, state] of Object.entries(configuration.activities || {}))
        result.push({
          text: activityName(view, id) + "：" + activityLabel(view, state),
          role: state === "waiting" ? "bad" : "value",
        });
    }
    return result;
  } else if (node.layer === "business") {
    result.push({ text: node.summary, role: "muted" });
    if (node.id === view.model.machine.execution?.parent) {
      if (configuration) {
        if (configuration.disposition === "interrupted")
          result.push({
            text: boTranslate("This run was interrupted; showing its last recorded state"),
            role: "bad",
          });
        for (const [id, state] of Object.entries(configuration.activities || {}))
          result.push({
            text: activityName(view, id) + "：" + activityLabel(view, state),
            role: state === "waiting" || state === "failed" ? "bad" : "value",
          });
        for (const r of Object.values(configuration.resources || {}))
          result.push({
            text: boTranslate("Available capacity: {0} / {1}", r.available, r.capacity),
            role: "value",
          });
      } else
        result.push({
          text: boTranslate("Checks have not started"),
          role: "muted",
        });
    } else {
      const names = {
        allowed: boTranslate("Allowed"),
        version_ok: boTranslate("Parameter version remains valid"),
        param_version: boTranslate("Parameter version"),
        length: boTranslate("Text length"),
        version: boTranslate("Committed version"),
        reason: boTranslate("Reason execution cannot continue"),
      };
      const reasons = {
        no_current_authorization: boTranslate("No valid authorization"),
        check_rejected: boTranslate("Some checks did not pass"),
        authorization_or_version_changed: boTranslate("Authorization or parameter version changed"),
        worker_error: boTranslate("A check function failed"),
        process_restarted: boTranslate("Process restarted; previous checks were interrupted"),
      };
      const ids = view.model.nodes
        .filter((n) => n.parent === node.id && n.layer !== "state")
        .map((n) => n.id);
      for (const id of ids) {
        const e = events.filter((e) => e.node === id).at(-1),
          child = view.model.nodes.find((n) => n.id === id);
        if (e)
          for (const [k, v] of Object.entries(e.outputs).slice(0, 2))
            result.push({
              text: `${child?.field_labels?.[k] || names[k] || k}：${v === true ? boTranslate("Yes") : v === false ? boTranslate("No") : k === "reason" ? reasons[v] || v : compact(v)}`,
              role: v === false ? "bad" : "value",
            });
      }
    }
    if (!Object.keys(node.capture || {}).length) return result;
  }
  if (last && staleBasis(node, view, last))
    result.push({
      text: boTranslate("Historical decision/read: evidence changed; awaiting reevaluation"),
      role: "muted",
    });
  for (const [direction, spec] of Object.entries(node.capture || {})) {
    const vals = callValues(node, events)[direction === "in" ? "inputs" : "outputs"];
    for (const [key, t] of Object.entries(spec)) {
      if (!(key in vals) || key === "state") continue;
      result.push({
        text: `${direction === "in" ? boTranslate("Input") : boTranslate("Output")} ${key}: ${typeName(t)} = ${compact(vals[key])}`,
        role: vals[key] === false ? "bad" : "value",
      });
    }
  }
  if (!last && !node.execution_role)
    result.push({
      text: boTranslate("No call recorded; expand to inspect source"),
      role: "muted",
    });
  return result;
}
export function wrapText(text, width = 47) {
  const out = [];
  let row = "",
    units = 0;
  for (const c of text) {
    const size = c.charCodeAt(0) > 255 ? 1.8 : 1;
    if (c === "\n" || units + size > width) {
      out.push(row);
      row = "";
      units = 0;
      if (c === "\n") continue;
    }
    row += c;
    units += size;
  }
  if (row || !out.length) out.push(row);
  return out;
}
export const nodeTypes = {
  "code-directory": {
    label: boTranslate("Directory"),
    glyph: "D",
    color: typeColor("code-directory"),
  },
  "code-endpoint": {
    label: boTranslate("API endpoint"),
    glyph: "API",
    color: typeColor("code-endpoint"),
  },
  "code-file": {
    label: boTranslate("Source file"),
    glyph: "F",
    color: typeColor("code-file"),
  },
  "code-class": {
    label: boTranslate("Class"),
    glyph: "C",
    color: typeColor("code-class"),
  },
  "code-function": {
    label: boTranslate("Code function"),
    glyph: "ƒ",
    color: typeColor("code-function"),
  },
  "code-parameter": {
    label: boTranslate("Code parameter"),
    glyph: "x",
    color: typeColor("code-parameter"),
  },
  "code-unresolved": {
    label: boTranslate("Unresolved reference"),
    glyph: "?",
    color: typeColor("code-unresolved"),
  },
  "code-reference": {
    label: boTranslate("Source reference"),
    glyph: "↗",
    color: typeColor("code-reference"),
  },
  unknown: {
    label: boTranslate("Unclassified"),
    glyph: "?",
    color: typeColor("unknown"),
  },
  business: {
    label: boTranslate("Business"),
    glyph: "B",
    color: typeColor("business"),
  },
  function: {
    label: boTranslate("Function"),
    glyph: "ƒ",
    color: typeColor("function"),
  },
  state: { label: boTranslate("State"), glyph: "S", color: typeColor("state") },
  decision: {
    label: boTranslate("Decision"),
    glyph: "?",
    color: typeColor("decision"),
  },
  resource: {
    label: boTranslate("Resource"),
    glyph: "R",
    color: typeColor("resource"),
  },
  data: { label: boTranslate("Value"), glyph: "x", color: typeColor("data") },
  effect: {
    label: boTranslate("Effect"),
    glyph: "✓",
    color: typeColor("effect"),
  },
  wait: { label: boTranslate("Wait"), glyph: "…", color: typeColor("wait") },
  store: {
    label: boTranslate("Database"),
    glyph: "DB",
    color: typeColor("store"),
  },
  dataset: {
    label: boTranslate("Table or collection"),
    glyph: "T",
    color: typeColor("dataset"),
  },
  column: {
    label: boTranslate("Data field"),
    glyph: ":",
    color: typeColor("column"),
  },
  query: {
    label: boTranslate("Database operation"),
    glyph: "Q",
    color: typeColor("query"),
  },
  write: {
    label: boTranslate("Database write"),
    glyph: "W",
    color: typeColor("write"),
  },
  transaction: {
    label: boTranslate("Transaction"),
    glyph: "TX",
    color: typeColor("transaction"),
  },
  transform: {
    label: boTranslate("Data processing"),
    glyph: "Δ",
    color: typeColor("transform"),
  },
};
export { nodeType };
// A business action can also implement a function. View membership is not its
// visual type; selecting a view must not erase that function's values or calls.
export function viewTypes(n) {
  if (n.code_role) return ["code-" + n.code_role];
  if (dataRoles.includes(n.data_role)) return [n.data_role];
  return [
    ...new Set([
      nodeType(n),
      ...(n.semantic_roles?.includes("business") ? ["business"] : []),
      ...(n.semantic_role === "state_parameter" ? ["state"] : []),
      ...(n.source && n.kind !== "state" && !n.field ? ["function"] : []),
    ]),
  ];
}
export function relationType(e) {
  if (conceptRelationTypes.includes(e.type)) return e.type;
  if (codeRelations.includes(e.type)) return e.type;
  if (codeRelations.includes("code-" + e.code_relation)) return "code-" + e.code_relation;
  if (e.type === "data" && dataRelations.includes(e.data_relation)) return e.data_relation;
  if (dataRelations.includes(e.type)) return e.type;
  return ["python-ast", "source-ast"].includes(e.origin) && e.type === "flow"
    ? "call"
    : [
          "indirect",
          "call",
          "flow",
          "transition",
          "guard",
          "data",
          "resource",
          "join",
          "shared",
          "contains",
        ].includes(e.type)
      ? e.type
      : "other";
}
// One typed graph. Folding changes visible nodes, never their identities or facts.
// The old layoutGraph name remains for integrations; coordinates are assigned by layout.js.
export function layoutGraph(
  view,
  expanded = new Set(),
  _sourceOpen = new Set(),
  _fullSources = new Map(),
  choice = "latest",
  step = "latest",
  options = {},
) {
  const configuration = selectedConfiguration(view, choice, step),
    events = selectedEvents(view, choice, step);
  const { all, rawEdges } = graphInventory(view, {
    attempt: currentAttempt(view, choice),
    choice,
    step,
    memberships: options.memberships,
  });
  const children = new Map();
  const explicitlyHidden = new Set(options.hiddenNodes || []);
  const excludedIds = new Set();
  for (const [id, node] of all) {
    let current = node;
    const seen = new Set();
    while (current && !seen.has(current.id)) {
      seen.add(current.id);
      if (explicitlyHidden.has(current.id) || explicitlyHidden.has(current.referenceOf)) {
        excludedIds.add(id);
        break;
      }
      current = all.get(current.parent);
    }
  }
  let matched = null;
  if (options.match) {
    for (const [id, n] of all) {
      let depth = 0,
        p = n.parent;
      const seen = new Set([id]);
      while (p && !seen.has(p)) {
        seen.add(p);
        depth++;
        p = all.get(p)?.parent;
      }
      all.set(id, { ...n, projection_depth: depth });
    }
    matched = options.match(
      all,
      events,
      (n) => status(n, view, events, choice, configuration),
      rawEdges,
    );
    for (const id of excludedIds) matched.delete(id);
    for (const id of matched.contextIds || [])
      all.set(id, { ...all.get(id), filter_context: true, parent: undefined });
    for (const id of matched) {
      const node = all.get(id),
        seen = new Set([id]);
      let parent = node.parent;
      while (
        parent &&
        (!matched.has(parent) || matched.contextIds?.has(parent)) &&
        !seen.has(parent)
      ) {
        seen.add(parent);
        parent = all.get(parent)?.parent;
      }
      all.set(id, {
        ...node,
        parent: parent && matched.has(parent) ? parent : undefined,
      });
    }
  }
  for (const n of all.values())
    if (n.parent) {
      if (!children.has(n.parent)) children.set(n.parent, []);
      children.get(n.parent).push(n.id);
    }
  const visibleIds = matched
    ? new Set([...matched].filter((id) => !all.get(id).parent))
    : new Set([
        ...(view.model.graph_roots || view.model.overview?.map((x) => x.node) || []),
        ...[...all.values()].filter((n) => !n.parent).map((n) => n.id),
      ]);
  // State nodes follow the same containment and expansion rules as functions.
  // Folding affects visibility only; all states and facts remain in `all`.
  function reveal(id, seen = new Set()) {
    if (seen.has(id)) return;
    seen.add(id);
    if (expanded.has(id) && !all.get(id)?.filter_context)
      for (const child of children.get(id) || [])
        if (!matched || matched.has(child)) {
          visibleIds.add(child);
          reveal(child, seen);
        }
  }
  for (const id of [...visibleIds]) reveal(id);
  const eligibleIds = new Set(
    [...all.keys()].filter(
      (id) =>
        !excludedIds.has(id) &&
        (!matched || matched.has(id)) &&
        (!options.include || options.include(all.get(id))),
    ),
  );
  const boxes = [...visibleIds]
    .filter((id) => eligibleIds.has(id))
    .map((id, i) => {
      const node = all.get(id),
        type = nodeType(node),
        rows = lines(node, view, events, choice, configuration);
      return {
        id,
        node,
        type,
        rows,
        open: expanded.has(id) && !node.filter_context,
        kids: node.filter_context
          ? []
          : (children.get(id) || []).filter((id) => eligibleIds.has(id)),
        state: status(node, view, events, choice, configuration),
        activation: activationFor(node, view, events),
        x: 80 + (i % 5) * 230,
        y: 70 + Math.floor(i / 5) * 180,
        w: 190,
        h:
          type === "state"
            ? 105
            : ["query", "write", "transaction", "transform"].includes(type)
              ? 172
              : 135,
      };
    });
  const byId = new Map(boxes.map((b) => [b.id, b]));
  function visible(id) {
    const seen = new Set();
    let n = all.get(id);
    while (n && !byId.has(n.id)) {
      if (seen.has(n.id)) return null;
      seen.add(n.id);
      n = all.get(n.parent);
    }
    return n?.id;
  }
  const edgeMap = new Map();
  for (const e of rawEdges) {
    if (
      !eligibleIds.has(e.from) ||
      !eligibleIds.has(e.to) ||
      relationExcluded(e, options.hiddenEdges)
    )
      continue;
    const from = visible(e.from),
      to = visible(e.to);
    if (!from || !to || (from === to && e.from !== e.to)) continue;
    // Project every cross-group relation onto its enclosing groups. Original
    // endpoints remain in members; folding must not erase static call edges.
    const source = all.get(e.from),
      target = all.get(e.to);
    if (!source || !target) continue;
    const sourceEvents = nodeEvents(source, events),
      targetEvents = nodeEvents(target, events),
      ids = new Set(sourceEvents.map((x) => x.id));
    let observed =
      e.type === "transition"
        ? e.observed
        : !["python-ast", "source-ast", "capture-field"].includes(e.origin) &&
          !["contains", "shared"].includes(e.type) &&
          targetEvents.some((x) =>
            (x.depends || []).some(
              (d) =>
                ids.has(d.event) &&
                (originalRelations(e).some((original) => d.type === original.type) ||
                  (e.type === "flow" && d.type === "control")),
            ),
          );
    if (["reads", "writes"].includes(e.data_relation))
      observed = events.some((event) => observedDataTransfer(e, event, all));
    let label =
      e.type === "contains"
        ? target.kind === "state"
          ? boTranslate("State membership")
          : boTranslate("Contains")
        : e.origin === "code-index"
          ? boTranslate(
              e.code_relation === "imports" && e.label === "Imports"
                ? "Import"
                : e.label || e.code_relation || e.type,
            )
          : e.origin === "concept-design"
            ? boTranslate(
                !e.label || e.label === e.type ? conceptRelations[e.type] || e.type : e.label,
              )
            : e.label;
    if (configuration && e.type === "resource") {
      const state = configuration.activities?.[e.to];
      observed = !!state && state !== "pending";
      label =
        state === "running"
          ? boTranslate("Occupies {0} slots", e.units)
          : state === "waiting"
            ? boTranslate("Capacity exhausted; waiting")
            : ["succeeded", "failed", "rejected"].includes(state)
              ? boTranslate("Capacity released")
              : e.label;
    }
    if (configuration && e.type === "join") {
      const state = configuration.activities?.[e.from];
      observed = ["succeeded", "failed", "rejected"].includes(state);
      label =
        state === "succeeded"
          ? boTranslate("This check passed")
          : state === "failed"
            ? boTranslate("Check failed")
            : state === "rejected"
              ? boTranslate("Check rejected")
              : boTranslate("Waiting for this check");
    }
    const current =
      choice === "latest" &&
      view.binding_status.status === "current" &&
      (!sourceEvents.length ||
        sourceEvents.at(-1)?.basis.param_version === view.authority.basis.param_version);
    // Different relation types sharing endpoints remain separate edges.
    if (view.model.presentation?.name_mode === "source")
      label = e.event || e.code_relation || e.data_relation || e.type;
    else label = explainedName(view.model.presentation?.names?.edges?.[e.id]) || label;
    // Opposite guards may share folded endpoints, but they remain distinct
    // conditions. Preserve polarity even when aggregating display relations.
    if (e.type === "guarded_by" && typeof e.negated === "boolean")
      label =
        view.model.presentation?.name_mode === "source"
          ? e.negated
            ? "unless"
            : "conditions"
          : boTranslate(e.negated ? "Requires false" : "Requires true");
    const key =
      from +
      ">" +
      to +
      ":" +
      relationType(e) +
      ":" +
      (e.origin || "model") +
      (typeof e.negated === "boolean" ? ":" + e.negated : "");
    const member = { ...e, label, observed, current };
    if (edgeMap.has(key)) {
      const found = edgeMap.get(key);
      found.labels.add(label);
      found.observed ||= observed;
      found.members.push(member);
    } else
      edgeMap.set(key, {
        ...e,
        from,
        to,
        labels: new Set([label]),
        members: [member],
        observed,
        current,
      });
  }
  const graph = {
    boxes,
    byId,
    edges: [...edgeMap.values()],
    rawEdges,
    events,
    configuration,
    children,
    all,
    eligibleIds,
  };
  return graphBounds(graph);
}
export function graphBounds(graph) {
  const boxes = graph.boxes;
  graph.minX = boxes.length ? Math.min(...boxes.map((b) => b.x)) - 55 : 0;
  graph.minY = boxes.length ? Math.min(...boxes.map((b) => b.y)) - 55 : 0;
  graph.width = (boxes.length ? Math.max(...boxes.map((b) => b.x + b.w)) : 100) - graph.minX + 55;
  graph.height = (boxes.length ? Math.max(...boxes.map((b) => b.y + b.h)) : 100) - graph.minY + 55;
  return graph;
}
