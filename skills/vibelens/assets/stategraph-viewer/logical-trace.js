/** Logical model exploration has its own axis and provenance.
 * These helpers are shared by graph highlighting and the analysis Timeline.
 * They never enter the runtime replay/lifecycle reducers or fabricate duration.
 */
import { layerOf, layers } from "./graph-layers.js";

function assertTrace(trace) {
  if (
    trace?.schema !== "bo-analysis-trace/v1" ||
    trace.origin !== "model_analysis" ||
    trace.subject !== "design_model" ||
    trace.axis !== "logical_step" ||
    !Array.isArray(trace.states) ||
    !Array.isArray(trace.projected_steps) ||
    trace.projected_steps.length !== trace.states.length - 1
  )
    throw new Error("Expected a projected logical model trace");
}

/** Select original conceptual identities; hidden references remain explicit. */
export function logicalStep(trace, index, all, edges) {
  assertTrace(trace);
  if (!Number.isInteger(index) || index < 0 || index >= trace.states.length)
    throw new Error("Logical step is outside this trace");
  const step = index ? trace.projected_steps[index - 1] : null;
  const nodes = step?.nodes || [],
    edgeIds = new Set(step?.edges || []);
  return {
    origin: "model_analysis",
    index,
    action: step?.action ?? null,
    values: structuredClone(trace.states[index]),
    changes: structuredClone(step?.changes || []),
    nodes: nodes.filter((id) => all.has(id)),
    hidden: nodes.filter((id) => !all.has(id)),
    edges: edges.filter((edge) => edgeIds.has(edge.id)),
    loopBack: index === trace.states.length - 1 ? trace.loop_back : null,
  };
}

/** One row per visible graph layer; links retain original conceptual edges. */
export function logicalTimeline(trace, all, edges, order = layers.map((layer) => layer.id)) {
  assertTrace(trace);
  const rows = new Map(order.map((layer) => [layer, { layer, marks: [] }])),
    links = [];
  for (let index = 1; index < trace.states.length; index++) {
    const step = logicalStep(trace, index, all, edges);
    for (const node of step.nodes) {
      const row = rows.get(layerOf(all.get(node)));
      if (row) row.marks.push({ index, node, action: step.action, changes: step.changes });
    }
    for (const edge of step.edges) {
      if (all.has(edge.from) && all.has(edge.to))
        links.push({ index, edge: edge.id, from: edge.from, to: edge.to, origin: "definition" });
    }
  }
  return {
    origin: "model_analysis",
    axis: "logical_step",
    start: 0,
    end: trace.states.length - 1,
    rows: [...rows.values()],
    links,
    loopBack: trace.loop_back,
    analysisId: trace.analysis_id,
    definition: trace.definition_sha256,
  };
}
