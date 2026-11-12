/** Multiple models share local names, never identities or witnessed intervals. */
import assert from "node:assert/strict";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { machineProjection } from "../skills/vibelens/assets/stategraph-viewer/machine-projection.js";
import {
  configurationFor,
  modelValueKey,
} from "../skills/vibelens/assets/stategraph-viewer/model-networks.js";
import {
  selectedConfiguration,
  executionIds,
  status,
} from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { namedView } from "../skills/vibelens/assets/stategraph-viewer/graph-names.js";
import { setLocale } from "../skills/vibelens/assets/stategraph-viewer/i18n.js";
import {
  networkProfiles,
  matchingNodes,
} from "../skills/vibelens/assets/stategraph-viewer/analysis.js";
import { cleanFilters } from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { stateResidencies } from "../skills/vibelens/assets/stategraph-viewer/trace-residencies.js";
import { clusterGroups } from "../skills/vibelens/assets/stategraph-viewer/cluster-layout.js";
import { frame } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const chart = {
  states: ["idle", "ready"],
  values: ["idle", "ready"],
  events: { advance: {} },
  transitions: [{ source: "idle", dest: "ready", trigger: "advance" }],
};
const model = {
  machines: { file: structuredClone(chart), review: structuredClone(chart) },
  nodes: ["file", "review"].flatMap((id) =>
    chart.values.map((value) => ({
      id: `${id}:${value}`,
      state_model_id: id,
      value,
      layer: "state",
      kind: "state",
      label: value,
      capture: {},
    })),
  ),
  edges: [],
  networks: ["file", "review"].map((id) => ({
    id: `network:${id}`,
    layer: "state",
    state_model_id: id,
    nodes: chart.values.map((value) => `${id}:${value}`),
  })),
};
const configuration = (id, phase) => ({
  state_model_id: id,
  phase,
  attempt: "same",
  snapshot_instance: `${id}:1`,
  journal: [],
});
const view = {
  model,
  manifest: { bindings: {} },
  events: [],
  machine: {
    current_instance: "file:1",
    state_model_id: "file",
    configurations: [configuration("file", "ready"), configuration("review", "idle")],
  },
  authority: { parameters: {} },
};
const projection = machineProjection(model, view.machine);
assert.equal(projection.nodes.length, 4);
assert.equal(projection.edges.length, 2);
assert.equal(new Set(projection.edges.map((edge) => edge.id)).size, 2);
assert.ok(
  projection.edges.every(
    (edge) => edge.from.startsWith(edge.state_model_id) && edge.to.startsWith(edge.state_model_id),
  ),
);
assert.deepEqual(executionIds(view), ["file:1", "review:1"]);
assert.equal(selectedConfiguration(view, "review:1").state_model_id, "review");
assert.equal(configurationFor(view, model.nodes[2], selectedConfiguration(view)).phase, "idle");
assert.equal(status(model.nodes[3], view, [], "latest", selectedConfiguration(view)), "declared");
assert.equal(status(model.nodes[2], view, [], "latest", selectedConfiguration(view)), "active");
const { all, rawEdges, networks } = graphInventory(view);
assert.equal(networks.length, 2);
const profiles = networkProfiles(view);
assert.equal(profiles.length, 2);
const selected = matchingNodes(all, view, [], profiles[0], () => "idle", rawEdges);
assert.deepEqual([...selected].sort(), ["file:idle", "file:ready"]);
assert.deepEqual(cleanFilters(profiles[0]).networks, ["network:file"]);
assert.equal(
  clusterGroups(
    [...all.values()].map((node) => ({
      id: node.id,
      node,
      layer: node.layer,
      type: "state",
      radius: 20,
    })),
  ).length,
  2,
);

model.presentation = {
  names: {
    states: {
      [modelValueKey(model, "file", "ready")]: { en: "File available", "zh-CN": "文件可用" },
      [modelValueKey(model, "review", "ready")]: { en: "Review complete", "zh-CN": "审核完成" },
    },
  },
};
setLocale("zh-CN");
const translated = namedView(view);
assert.equal(translated.model.machines.file.labels.ready, "文件可用");
assert.equal(translated.model.nodes[3].label, "审核完成");
assert.deepEqual(namedView(translated, false).model.machines.review.values, ["idle", "ready"]);

const events = ["file", "review", "file", "review"].map((id, index) => ({
  id: `e${index}`,
  kind: "probe",
  run_id: "run",
  revision: index < 2 ? 0 : 1,
  node: `${id}:idle`,
  attempt: "same",
}));
const recording = {
  id: "recording",
  build_id: "build",
  events,
  commands: [],
  gaps: [],
  context: { ...view, events: [], machine: { configurations: [] } },
  final: { machine: view.machine },
  runtime_frames: {
    schema: "stategraph-runtime-frames/v1",
    frames: events.map((event, index) => ({
      event_id: event.id,
      run_id: "run",
      build_id: "build",
      revision: event.revision,
      machine: {
        state_revision: event.revision,
        state_model_id: index % 2 ? "review" : "file",
        configurations: [
          configuration(index % 2 ? "review" : "file", index < 2 ? "idle" : "ready"),
        ],
      },
      authority: { parameters: {} },
    })),
  },
};
const spans = stateResidencies(recording, events, [], all, {
  times: [0, 10, 20, 30],
  total: 40,
  ordered: true,
});
assert.equal(
  spans.slices.length,
  4,
  "A snapshot must not activate same-named states in another model",
);
assert.equal(spans.links.length, 2);
assert.ok(spans.links.every((edge) => edge.fromNode.split(":")[0] === edge.toNode.split(":")[0]));
assert.deepEqual(
  spans.slices.filter((slice) => !slice.unfinished).map((slice) => slice.duration),
  [20, 20],
);
const historical = frame(recording, 2, events);
assert.equal(historical.machine.state_model_id, "file");
assert.equal(historical.machine.configurations[0].phase, "ready");
console.log(
  "Multiple-model projection, names, filtering, clustering, replay and residency checks passed.",
);
