/** Short, evidence-backed timeline details. The caller creates text nodes, not HTML. */
import { t } from "./i18n.js";
import { displayName } from "./layout.js";
import { lifecycleCaption } from "./node-lifecycle.js";

const relationNames = {
  call: "Call",
  return: "Return",
  data: "Value transfer",
  control: "Control transfer",
  transition: "State transition",
  activation: "Lifecycle start",
  completion: "Lifecycle end",
  trigger: "Trigger",
  recheck: "Recheck",
  observation: "Observed in",
};

export function traceDescription(hit, index, all, preferences, timeLabel) {
  const name = (id) => {
    const node = all.get(id);
    return node ? displayName(node, preferences || {}) : id;
  };
  if (hit.kind === "density")
    return {
      title: hit.label || name(hit.row),
      lines: [t("{0} short intervals", hit.count), t("Zoom to inspect individual intervals")],
    };
  if (hit.kind === "flow") {
    const flow = hit.flow,
      from = index.items[flow.from],
      to = index.items[flow.to];
    return {
      title: `${name(flow.fromNode || from.node)} → ${name(flow.toNode || to.node)}`,
      lines: [
        t(relationNames[flow.type] || flow.type),
        flow.outlivesParent ? t("Child ends outside the observed parent interval") : "",
      ].filter(Boolean),
      identity: `${from.id} → ${to.id}`,
    };
  }
  const event = hit.contextEvent || index.items[hit.stage?.raw ?? hit.raw];
  const row = index.rows.get(hit.row);
  const slice = hit.slice;
  const stage = slice?.stages?.findLast((item) => item.raw <= hit.raw);
  const state = hit.stage || slice?.terminal || stage;
  const label =
    lifecycleCaption(state, preferences?.nameMode === "source") ||
    (state?.phase === "waiting"
      ? "Waiting"
      : state?.phase === "running"
        ? "Running"
        : slice?.role === "residency"
          ? "State residence"
          : event.phase || "Observation");
  const duration = hit.stage
    ? timeLabel(hit.stage.end - hit.stage.start)
    : slice?.duration != null
      ? `${slice.clippedStart ? "≥ " : ""}${timeLabel(slice.duration)}`
      : slice?.unfinished
        ? t("End not observed")
        : "";
  return {
    title: name(slice?.node || row?.id || event.node),
    lines: [
      [t(label), duration].filter(Boolean).join(" · "),
      hit.contextEvent ? t("Before recording") : "",
      event.context_only ? t("Execution boundary") : "",
      event.exception?.type ? `${t("Exception")}: ${event.exception.type}` : "",
      event.provenance?.workflow_id ? `${t("Workflow")}: ${event.provenance.workflow_id}` : "",
      event.trace
        ? `${t("Trace")}: ${event.trace.trace_id} · ${t("Span")}: ${event.trace.span_id}`
        : "",
      ...Object.entries(event.outputs || {})
        .slice(0, 3)
        .map(([key, value]) => `${key}: ${JSON.stringify(value)}`),
      event.observed_at,
    ].filter(Boolean),
  };
}
