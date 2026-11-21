/** Read-only transport for an accepted multi-network recording.
 * The application and provider are absent on Pages. The canonical viewer reads
 * the archived graph, events and source; only browser-local preferences change.
 */
import { loadForestRecord } from "./forest-data.mjs";
import { graphInventory } from "./viewer/graph-inventory.js";
const params = new URLSearchParams(location.search);
const epoch = params.get("forest") === "updated" ? "updated" : "initial";
const nativeFetch = window.fetch.bind(window);
const manifest = await (
  await nativeFetch(new URL("./forest-data/manifest.json", import.meta.url))
).json();
const record = await loadForestRecord(
  new URL(`./forest-data/${epoch}.json.gz`, import.meta.url),
  manifest.epochs[epoch].raw_sha256,
  nativeFetch,
);
const view = {
  ...record.context,
  ...record.final,
  model: record.context.model,
  events: record.events,
  instances: [],
  runtime_frames: record.runtime_frames,
  manifest: record.context.manifest,
  historical: true,
  busy: false,
  layout_id: "forest-demo:" + record.build_id,
  program_url: null,
  database_status: null,
};
const preferenceKey = `vibelens.forest.${epoch}.${params.get("lang") || "en"}`;
let preferences = { schema: 1, revision: 1, project_id: view.layout_id, entries: {} };
try {
  preferences = JSON.parse(localStorage.getItem(preferenceKey)) || preferences;
} catch {
  /* Optional browser-local view state. */
}
const inventory = graphInventory(record.context);
const code = {
  revision: record.build_id,
  nodes: [...inventory.all.values()],
  edges: inventory.rawEdges,
  evidence: "Recorded declaration inventory",
  build_id: record.build_id,
};
const reply = (value, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
window.fetch = async (input, init = {}) => {
  const url = new URL(typeof input === "string" ? input : input.url || input.href, location.href);
  if (url.origin !== location.origin || !url.pathname.startsWith("/api/"))
    return nativeFetch(input, init);
  const route = url.pathname;
  if (route === "/api/view") return reply(view);
  if (route === "/api/design") return reply({ available: false });
  if (route === "/api/versions") return reply([]);
  if (route === "/api/preferences") {
    if (init.method === "POST") {
      preferences = { ...JSON.parse(init.body), revision: preferences.revision + 1 };
      try {
        localStorage.setItem(preferenceKey, JSON.stringify(preferences));
      } catch {
        /* Browser storage may be unavailable; the current view still works. */
      }
    }
    return reply(preferences);
  }
  if (route === "/api/recordings")
    return reply({
      active: null,
      archival_replay_only: true,
      recordings: [
        {
          id: record.id,
          label: record.label,
          status: record.status,
          started_at: record.started_at,
          ended_at: record.ended_at,
          events: record.events.length,
          gaps: record.gaps,
          capture: record.capture,
        },
      ],
    });
  if (route === "/api/recordings/" + record.id) return reply(record);
  if (["/api/source", "/api/code/source"].includes(route)) {
    const requested = url.searchParams.get("recording");
    if (requested && requested !== record.id) return reply({ error: "Unknown recording" }, 404);
    if (
      route === "/api/code/source" &&
      url.searchParams.has("revision") &&
      url.searchParams.get("revision") !== record.build_id
    )
      return reply({ error: "Source revision differs from this recorded build" }, 409);
    const source = record.sources[url.searchParams.get("path")];
    return typeof source === "string"
      ? reply({ source, build_id: record.build_id, code_revision: record.build_id })
      : reply({ error: "Source is outside the recorded build" }, 404);
  }
  if (route === "/api/code/graph") {
    const focus = url.searchParams.get("focus");
    if (!focus) return reply(code);
    const edges = code.edges.filter((edge) => edge.from === focus || edge.to === focus);
    const ids = new Set([focus, ...edges.flatMap((edge) => [edge.from, edge.to])]);
    return reply({ ...code, nodes: code.nodes.filter((node) => ids.has(node.id)), edges });
  }
  return reply({ error: "Open the project locally to record new operations" }, 409);
};
await import("./viewer/viewer.js");
for (const id of ["capture-mode", "record-start", "record-stop", "record-clear"])
  document.getElementById(id)?.setAttribute("hidden", "");
document.getElementById("layout-status").hidden = true;
document.body.dataset.forestRecording = record.id;
