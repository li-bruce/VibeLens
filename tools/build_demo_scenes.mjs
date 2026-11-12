/** Compile presentation-sized graphs once. Browsers never lay out the full archive.
 * Concepts come from the same confirmation function used by the dialogue. Every
 * runtime highlight keeps its original event and relationship witnesses.
 */
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { confirmationModel } from "../docs/site/case-confirmation-model.mjs";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const site = new URL("../docs/site/", import.meta.url);
const colors = {
  business: "#318878",
  state: "#9862ae",
  rule: "#b08030",
  function: "#4b80a8",
  data: "#a97454",
  source: "#777996",
};
const kinds = {
  business: "business",
  state: "state",
  rule: "decision",
  function: "function",
  data: "dataset",
  source: "code-function",
};
const digest = (value) => createHash("sha256").update(value).digest("hex");
const write = (name, data) =>
  fs.writeFileSync(new URL(`case-preview/${name}`, site), JSON.stringify(data));

export function compileScenes(artifact) {
  const { model } = artifact.view;
  const index = new Map([...model.nodes, ...artifact.code.nodes].map((n) => [n.id, n]));
  const sourceEdges = [...model.edges, ...artifact.code.edges];
  const byEdge = new Map(sourceEdges.map((e) => [e.id, e]));
  const labels = artifact.story.captions;
  const scenes = {};
  const concepts = {};
  for (const tab of ["business", "states", "rules"]) {
    const en = confirmationModel(artifact, tab, "en"),
      zh = confirmationModel(artifact, tab, "zh-CN");
    const layer = { business: "business", states: "state", rules: "rule" }[tab];
    concepts[tab] = { en, "zh-CN": zh };
    scenes[tab] = {
      nodes: en.nodes.map((n, i) => ({
        ...n,
        labels: [n.label, zh.nodes[i].label],
        layer,
        kind: kinds[layer],
        color: colors[layer],
      })),
      edges: en.edges.map((e, i) => ({
        ...e,
        id: `concept:${tab}:${i}`,
        labels: [e.label, zh.edges[i].label],
        type: tab === "states" ? "transition" : tab === "rules" ? "guard" : "flow",
        color: colors[layer],
      })),
    };
  }
  const merge = (...graphs) => ({
    nodes: [...new Map(graphs.flatMap((g) => g.nodes).map((n) => [n.id, n])).values()],
    edges: [...new Map(graphs.flatMap((g) => g.edges).map((e) => [e.id, e])).values()],
  });
  const move = (graph, dx, dy) => ({
    ...graph,
    nodes: graph.nodes.map((n) => ({ ...n, x: n.x + dx, y: n.y + dy })),
  });
  scenes.overview = merge(scenes.business, move(scenes.states, 0, 250));
  // Event-to-transition references are explicit model mappings, not additional
  // calls. Retain them as cross-layer links and animate only recorded changes.
  for (const [i, transition] of model.machine.transitions.entries()) {
    const target = scenes.states.nodes.find((n) => n.value === transition.dest);
    if (!scenes.business.nodes.some((n) => n.id === transition.trigger)) continue;
    const id = `model-event:${i}`;
    scenes.overview.edges.push({
      id,
      from: transition.trigger,
      to: target.id,
      type: "mapping",
      labels: [
        transition.trigger,
        { upload: "上传", share: "共享", revoke: "取消共享" }[transition.trigger],
      ],
      witnesses: [`machine.transitions[${i}]`],
      color: "#8b96a1",
      event: transition.trigger,
    });
  }
  scenes.operation = {
    nodes: scenes.overview.nodes.filter(
      (n) => ["revoke", "download"].includes(n.id) || n.layer === "state",
    ),
    edges: scenes.overview.edges.filter(
      (e) =>
        ["revoke", "download", ...scenes.states.nodes.map((n) => n.id)].includes(e.from) &&
        ["revoke", "download", ...scenes.states.nodes.map((n) => n.id)].includes(e.to),
    ),
  };
  const positions = {
    revoke: [305, 160],
    download: [540, 160],
    state_empty: [70, 20],
    state_private: [305, 20],
    state_shared: [540, 20],
    db_delete_share: [305, 330],
    "field:revoke:in:actor": [65, 160],
    "field:revoke:in:recipient_id": [65, 260],
    "field:db_delete_share:out:rows": [540, 330],
  };
  const detailNode = (id, layer, position, kind) => {
    const original = index.get(id);
    if (!original) throw Error(`Missing compiled node ${id}`);
    const [x, y] = position;
    return {
      id,
      x,
      y,
      layer,
      color: colors[layer],
      kind: kind || kinds[layer],
      labels: labels[id] || [original.label, original.label],
    };
  };
  const inputs = artifact.story.focus.inputs.map((id) => {
    const [, owner, direction, field] = id.split(":");
    if (
      !artifact.recording.events.some(
        (e) =>
          e.node === owner &&
          Object.hasOwn(e[direction === "in" ? "inputs" : "outputs"] || {}, field),
      )
    )
      throw Error(`Missing captured field ${id}`);
    const node = {
      id,
      x: positions[id][0],
      y: positions[id][1],
      labels: labels[id],
      layer: "function",
      color: colors.function,
      kind: "data",
      field,
      owner,
      direction,
    };
    index.set(id, { ...node, referenceOf: owner });
    return node;
  });
  const query = detailNode("db_delete_share", "data", positions.db_delete_share, "query");
  const fieldEdges = inputs.map((n) => ({
    id: `capture:${n.id}`,
    from: n.direction === "in" ? n.id : n.owner,
    to: n.direction === "in" ? n.owner : n.id,
    type: "data",
    labels: [n.field, n.field],
    witnesses: [`capture-field:${n.id}`],
    color: n.direction === "in" ? "#8b96a1" : colors.data,
    field: n.field,
    owner: n.owner,
    direction: n.direction,
  }));
  const queryLink = sourceEdges.find(
    (e) => e.from === "revoke" && e.to === query.id && e.type === "contains",
  );
  if (!queryLink) throw Error("Missing business-to-query containment");
  const relationLabels = {
    writes: ["Writes", "写入"],
    defines: ["Defines", "定义"],
    maps: ["Source binding", "源码映射"],
    contains: ["Includes", "包含"],
  };
  const asEdge = (e) => ({
    id: e.id,
    from: e.from,
    to: e.to,
    type: e.type,
    relation: e.code_relation || e.data_relation || e.type,
    witnesses: [e.id],
    labels: relationLabels[e.code_relation || e.data_relation || e.type] || [e.label, e.label],
    color: "#8b96a1",
  });
  scenes.inputs = merge(scenes.operation, {
    nodes: [query, ...inputs],
    edges: [...fieldEdges, asEdge(queryLink)],
  });
  const tableId = artifact.story.focus.effects.find((id) => id.startsWith("db:"));
  const fnId = artifact.story.focus.effects.find((id) => id.startsWith("code:symbol:"));
  const fn = index.get(fnId),
    cls = index.get(fn.parent),
    file = index.get(cls.parent);
  const extra = [
    detailNode(tableId, "data", [760, 330]),
    detailNode(fnId, "source", [760, 160]),
    detailNode(cls.id, "source", [760, 60], "code-class"),
    detailNode(file.id, "source", [760, -40], "code-file"),
  ];
  extra.find((n) => n.id === file.id).labels = [
    file.source.path.split("/").at(-1),
    file.source.path.split("/").at(-1),
  ];
  const dataIds = new Set([...scenes.inputs.nodes, ...extra].map((n) => n.id));
  const detailEdges = sourceEdges
    .filter(
      (e) =>
        dataIds.has(e.from) &&
        dataIds.has(e.to) &&
        (e.data_relation === "writes" || ["maps", "defines"].includes(e.code_relation)),
    )
    .map(asEdge);
  scenes.data = merge(scenes.inputs, { nodes: extra, edges: detailEdges });
  for (const name of ["operation", "inputs", "data"]) {
    scenes[name].nodes = scenes[name].nodes.map((n) =>
      positions[n.id] ? { ...n, x: positions[n.id][0], y: positions[n.id][1] } : n,
    );
  }
  scenes.implementation = scenes.data;
  scenes.all = merge(move(scenes.business, 0, -280), scenes.data, move(scenes.rules, 900, 40));
  // Compile event paths once using the same evidence checker as the full tool.
  const events = artifact.recording.events;
  const visibleIds = new Set(Object.values(scenes).flatMap((g) => g.nodes.map((n) => n.id)));
  const first = Math.min(
    ...artifact.story.actions.flatMap((a) =>
      a.event_ids.map((id) => events.findIndex((e) => e.id === id)),
    ),
  );
  const last = Math.max(
    ...artifact.story.actions.flatMap((a) =>
      a.event_ids.map((id) => events.findIndex((e) => e.id === id)),
    ),
  );
  const edgeList = [
    ...new Map(
      Object.values(scenes)
        .flatMap((g) => g.edges)
        .map((e) => [e.id, e]),
    ).values(),
  ];
  const actionIds = new Set(artifact.story.actions.flatMap((action) => action.event_ids));
  let state = "empty";
  const samples = {};
  const steps = [];
  for (let i = 0; i <= last; i++) {
    const event = events[i],
      previous = state;
    if (event.outputs?.state && model.machine.states.includes(event.outputs.state))
      state = event.outputs.state;
    // Carry the last captured value with its evidence ID. Returning from the
    // business action must not erase a query result recorded inside that action.
    for (const field of inputs) {
      const values = event[field.direction === "in" ? "inputs" : "outputs"] || {};
      if (event.node === field.owner && Object.hasOwn(values, field.field))
        samples[field.id] = { value: values[field.field], eventId: event.id };
    }
    if (i < first || (!visibleIds.has(event.node) && !actionIds.has(event.id))) continue;
    const witnessed = new Set(transferEdges(event, events, sourceEdges, index));
    const transfers = edgeList
      .filter((e) => {
        if (e.owner === event.node)
          return Object.hasOwn(event[e.direction === "in" ? "inputs" : "outputs"] || {}, e.field);
        if (e.type === "transition")
          return (
            e.event === event.node &&
            e.from === `state_${previous}` &&
            e.to === `state_${state}` &&
            Object.hasOwn(event.outputs || {}, "state")
          );
        if (e.id.startsWith("model-event:"))
          return (
            e.event === event.node &&
            e.to === `state_${state}` &&
            Object.hasOwn(event.outputs || {}, "state")
          );
        return e.witnesses.length === 1 && witnessed.has(e.witnesses[0]);
      })
      .map((e) => e.id);
    steps.push({
      id: event.id,
      node: event.node,
      phase: event.phase,
      inputs: event.inputs,
      outputs: event.outputs,
      state,
      previous,
      transfers,
      samples: structuredClone(samples),
    });
  }
  for (const id of artifact.story.actions.flatMap((a) => a.event_ids))
    if (!steps.some((e) => e.id === id)) throw Error(`Missing demonstration action ${id}`);
  for (const graph of Object.values(scenes)) {
    const nodes = new Set(graph.nodes.map((n) => n.id));
    for (const edge of graph.edges) {
      if (!nodes.has(edge.from) || !nodes.has(edge.to))
        throw Error(`Dangling prepared edge ${edge.id}`);
      for (const witness of edge.witnesses)
        if (
          !byEdge.has(witness) &&
          !witness.startsWith("machine.transitions[") &&
          !witness.startsWith("capture-field:")
        )
          throw Error(`Missing witness ${witness}`);
    }
  }
  const source = artifact.sources[fn.source.path];
  const lines = source.split(/\r?\n/);
  const highlight = lines.findIndex((line) => line.includes(artifact.story.source_excerpt)) + 1;
  if (!highlight) throw Error("Source evidence has no matching highlighted line");
  return {
    version: artifact.version,
    build_id: artifact.provenance.build_id,
    concepts,
    scenes,
    steps,
    inspection: artifact.story.inspection_event,
    actions: artifact.story.actions,
    source: {
      path: fn.source.path,
      highlight,
      sha256: digest(source),
      url: `case-preview/source-v${artifact.version}.json`,
    },
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const versions = [1, 2].map((version) => {
    const artifact = JSON.parse(fs.readFileSync(new URL(`case-data/v${version}.json`, site)));
    const compiled = compileScenes(artifact);
    write(`source-v${version}.json`, {
      path: compiled.source.path,
      source: artifact.sources[compiled.source.path],
      sha256: compiled.source.sha256,
    });
    return compiled;
  });
  const payload = { schema: "vibelens-prepared-scenes/v1", versions };
  write("prepared.json", payload);
  console.log(
    `Prepared ${versions.reduce((n, v) => n + Object.keys(v.scenes).length, 0)} scene graphs: ${JSON.stringify(payload).length} characters`,
  );
}
