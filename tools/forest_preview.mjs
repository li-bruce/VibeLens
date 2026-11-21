/** Compile presentation geometry from one immutable native recording.
 * This module does not infer business routes or execute state machines. The
 * maintained inventory and machine projector supply identities and relations;
 * ELK supplies only coordinates. The compact result is safe to preload.
 */
import assert from "node:assert/strict";
import { machineProjection } from "../skills/vibelens/assets/stategraph-viewer/machine-projection.js";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { routeEdges } from "../docs/site/case-graph-geometry.mjs";
import { visualType } from "../skills/vibelens/assets/stategraph-viewer/graph-classification.js";

const colors = {
  business: "#318878",
  state: "#9862ae",
  rule: "#b08030",
  function: "#4b80a8",
  data: "#a97454",
  source: "#777996",
};
const networkNames = {
  files: ["Files and sharing", "文件与共享"],
  downloads: ["Download tasks", "下载任务"],
  announcements: ["Announcements", "公告"],
  authentication: ["Sign in and out", "登录与退出"],
  grant: ["Sharing access", "共享授权"],
  download_task: ["Download task", "下载任务"],
  announcement: ["Announcement", "公告"],
  session: ["Login session", "登录会话"],
};
const transitionNames = {
  enqueue: ["Queue", "入队"],
  start: ["Start", "开始"],
  finish: ["Finish", "完成"],
  cancel: ["Cancel", "取消"],
  share: ["Share", "共享"],
  revoke: ["Revoke", "撤销"],
  publish: ["Publish", "发布"],
  edit: ["Edit", "修改"],
  delete: ["Delete", "删除"],
  login: ["Sign in", "登录"],
  logout: ["Sign out", "退出"],
};
const operationNames = {
  upload: ["Upload a file", "上传文件"],
  manage_share: ["Manage sharing", "管理共享"],
  manage_announcement: ["Manage an announcement", "管理公告"],
};

function caption(model, node) {
  const names = model.presentation?.names || {};
  const entry = names.nodes?.[node.id] || names.concepts?.[node.id];
  return [entry?.en || node.label || node.id, entry?.["zh-CN"] || node.label || node.id];
}

function presentNode(model, node, layer) {
  return {
    id: node.id,
    kind: visualType(node),
    source_kind: node.kind,
    layer,
    color: colors[layer],
    labels: caption(model, node),
    ...(node.value === undefined ? {} : { value: node.value }),
    ...(node.state_model_id ? { state_model_id: node.state_model_id } : {}),
    ...(node.source ? { source: node.source } : {}),
  };
}

/** Keep separate edges separate, including equal endpoints with different guards. */
function presentEdge(model, edge, nodes) {
  const from = nodes.find((node) => node.id === edge.from);
  const to = nodes.find((node) => node.id === edge.to);
  assert(from && to, `Missing endpoint for ${edge.id}`);
  const names = model.presentation?.names?.edges?.[edge.id];
  // Source captions are sometimes untranslated. An empty visible edge caption
  // is preferable to inventing a business meaning; its typed detail is retained.
  const labels = edge.event
    ? transitionNames[edge.event] || [edge.event, edge.event]
    : names
      ? [names.en || "", names["zh-CN"] || ""]
      : ["", ""];
  return {
    id: edge.id,
    from: edge.from,
    to: edge.to,
    type: edge.type,
    labels,
    label: edge.event ? labels[0] : "",
    color: from.layer === to.layer ? from.color : "#7b8490",
    witnesses: [edge.id],
    ...(edge.state_model_id ? { state_model_id: edge.state_model_id } : {}),
    ...(edge.event
      ? {
          event: edge.event,
          conditions: edge.conditions,
          unless: edge.unless,
          condition: [
            ...(edge.conditions || []),
            ...(edge.unless || []).map((item) => "unless " + item),
          ].join(" · "),
        }
      : {}),
    ...(edge.machine_transition ? { machine_transition: edge.machine_transition } : {}),
  };
}

/** ELK's layered algorithm orders routes and packs disconnected components.
 * Every node reserves label space. Cycles remain genuine edges in the result.
 */
async function arrange(elk, graph) {
  if (!graph.nodes.length) return graph;
  const result = await elk.layout({
    id: "preview",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.randomSeed": "42",
      "elk.spacing.nodeNode": "50",
      "elk.spacing.componentComponent": "90",
      "elk.layered.spacing.nodeNodeBetweenLayers": "70",
      "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
    },
    children: graph.nodes.map((node) => ({ id: node.id, width: 200, height: 80 })),
    edges: graph.edges.map((edge) => ({ id: edge.id, sources: [edge.from], targets: [edge.to] })),
  });
  const byId = new Map(result.children.map((node) => [node.id, node]));
  return {
    ...graph,
    nodes: graph.nodes.map((node) => ({
      ...node,
      x: byId.get(node.id).x + 100,
      y: byId.get(node.id).y + 40,
    })),
    edges: routeEdges(graph.edges),
  };
}

function subset(model, inventory, identities, layer, includeEdge = () => true) {
  const ids = new Set(identities);
  const nodes = [...ids].map((id) => {
    assert(inventory.all.has(id), `Missing recorded node: ${id}`);
    return presentNode(model, inventory.all.get(id), layer);
  });
  const edges = [
    ...new Map(
      inventory.rawEdges
        .filter((edge) => ids.has(edge.from) && ids.has(edge.to) && includeEdge(edge))
        .map((edge) => [edge.id, edge]),
    ).values(),
  ];
  return { nodes, edges: edges.map((edge) => presentEdge(model, edge, nodes)) };
}

/** Produce independent model views and real activity steps for a single build. */
export async function compileForest(record, elk) {
  assert.equal(record.build_id, record.context.manifest.build_id, "Recording/model epoch mismatch");
  assert.equal(record.gaps.length, 0, "Incomplete capture is not a product replay");
  const model = record.context.model,
    inventory = graphInventory(record.context);
  const projected = machineProjection(model, { journal: [] });
  const networks = { business: {}, states: {}, rules: {} };
  for (const [id, definition] of Object.entries(model.machines)) {
    const declared = projected.nodes.filter((node) => node.state_model_id === id);
    assert.deepEqual(new Set(declared.map((node) => node.value)), new Set(definition.values));
    const nodes = declared.map((node) => presentNode(model, node, "state"));
    networks.states[id] = await arrange(elk, {
      labels: networkNames[id] || [id, id],
      nodes,
      edges: projected.edges
        .filter((edge) => edge.state_model_id === id)
        .map((edge) => presentEdge(model, edge, nodes)),
    });
  }
  for (const network of record.context.concept_structure.networks.filter(
    (item) => item.layer === "business",
  )) {
    const ids = network.nodes.filter((id) => model.concepts.business[id]);
    const name = decodeURIComponent(network.id).split(":").at(-1);
    const declared = new Set(network.edges);
    networks.business[network.id] = await arrange(elk, {
      labels: networkNames[name] || [network.label, network.label],
      ...subset(model, inventory, ids, "business", (edge) => declared.has(edge.id)),
    });
  }
  const policyNodes = new Map(model.policy.nodes.map((node) => [node.id, node]));
  for (const operation of model.policy.operations) {
    const selected = new Set();
    const visit = (id) => {
      if (selected.has(id)) return;
      const definition = policyNodes.get(id);
      assert(definition, `Unknown policy input: ${id}`);
      selected.add(id);
      for (const child of [
        ...(definition.inputs || []),
        ...Object.values(definition.arguments || {}),
      ])
        visit(child);
    };
    visit(operation.root);
    const concept = model.nodes.find((node) => node.id === operation.id);
    networks.rules[operation.id] = await arrange(elk, {
      labels: operationNames[operation.id] || caption(model, concept || { id: operation.id }),
      ...subset(
        model,
        inventory,
        [...selected].reverse().map((id) => "policy:" + id),
        "rule",
        (edge) => edge.origin === "policy-definition",
      ),
    });
  }
  const businessIds = new Set(Object.keys(model.concepts.business));
  const entered = new Map(),
    rawEdges = [...inventory.rawEdges, ...projected.edges];
  const callKey = (event) => JSON.stringify([event.run_id, event.producer_id, event.call_id]);
  const steps = [];
  for (const event of record.events) {
    if (event.phase === "enter") entered.set(callKey(event), event);
    const isBusiness = businessIds.has(event.node) && event.phase === "return";
    const isState =
      projected.nodes.some((node) => node.id === event.node) && event.phase === "change";
    if (!isBusiness && !isState) continue;
    const start = entered.get(callKey(event));
    const output = event.outputs || {};
    const transitions = isState
      ? projected.edges.filter(
          (edge) =>
            edge.state_model_id === output.state_model_id &&
            edge.to === event.node &&
            edge.event === output.event_name &&
            projected.nodes.find((node) => node.id === edge.from)?.value === output.before,
        )
      : [];
    steps.push({
      id: event.id,
      node: event.node,
      observed_at: event.observed_at,
      ...(start ? { started_at: start.observed_at, start_event_id: start.id } : {}),
      state_model_id: output.state_model_id,
      state: output.state,
      inputs: event.inputs,
      outputs: output,
      transfers: isState
        ? transitions.map((edge) => edge.id)
        : transferEdges(event, record.events, rawEdges, inventory.all),
    });
  }
  // A bounded inspection slice keeps real bindings. The complete recording is
  // loaded separately by the canonical viewer when the visitor asks for it.
  const roots = [
    "prepare_download",
    "request_download",
    "guard_prepare_download",
    "task_commit",
    "data_write",
    "db:application:table%3Atasks",
  ].filter((id) => inventory.all.has(id));
  const ids = new Set(roots);
  for (const id of roots) {
    const node = inventory.all.get(id);
    if (inventory.all.has(node.declaration_id)) ids.add(node.declaration_id);
  }
  if (inventory.all.has("policy:may_prepare")) ids.add("policy:may_prepare");
  if (inventory.all.has("policy:may_access")) ids.add("policy:may_access");
  const inspection = subset(model, inventory, [...ids], "function");
  for (const node of inspection.nodes) {
    const original = inventory.all.get(node.id);
    node.layer = businessIds.has(node.id)
      ? "business"
      : node.id.startsWith("policy:") || original.kind === "decision"
        ? "rule"
        : ["write", "transaction", "dataset"].includes(original.data_role)
          ? "data"
          : "function";
    node.color = colors[node.layer];
  }
  for (const edge of inspection.edges) {
    const a = inspection.nodes.find((node) => node.id === edge.from);
    const b = inspection.nodes.find((node) => node.id === edge.to);
    edge.color = a.layer === b.layer ? a.color : "#7b8490";
  }
  return {
    schema: "vibelens-forest-preview/v1",
    recording_id: record.id,
    build_id: record.build_id,
    networks,
    inspection: await arrange(elk, inspection),
    steps,
    provenance: { kind: "native_recording", event_count: record.events.length },
  };
}
