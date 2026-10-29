/** Read-only Pages transport for a real, exported VibeLens execution.
 * Renderer modules remain canonical. This adapter serves captured artifacts;
 * it never executes the sample application's requests or synthesizes events.
 */
const params = new URLSearchParams(location.search);
const version = params.get("case") === "2" ? 2 : 1;
const controlMode = params.get("controls") === "1";
const { expandCodeSlice } = await import("./case-code.mjs?rev=files-1");
const { presentCase } = await import("./case-copy.mjs?rev=files-1");
const nativeFetch = window.fetch.bind(window);
const captured = await (
  await nativeFetch(new URL(`./case-data/v${version}.json`, import.meta.url))
).json();
// Only display summaries change. The exported record and source files stay original.
const artifact = presentCase(captured);
let view = structuredClone(artifact.view);
// A nonzero revision keeps the canonical viewer from migrating unrelated local
// project layouts into this separately namespaced, bilingual demonstration.
let preferences = {
  schema: 1,
  project_id: view.layout_id,
  revision: 1,
  entries: {},
};
const preferenceKey = `vibelens.case.${controlMode ? "controls-1" : "files-story-clusters-2"}.${params.get("lang") || "en"}`;
const controlPlans = controlMode
  ? (await (await nativeFetch(new URL("./control-plans.json", import.meta.url))).json()).locales[
      params.get("lang") || "en"
    ]
  : null;
const controlSession = {
  active: true,
  session: params.get("vl_session"),
  revision: 0,
  plan: null,
  result: null,
};
let controlPreset = "business";
try {
  preferences = JSON.parse(localStorage.getItem(preferenceKey)) || preferences;
} catch {
  /* Optional browser preferences. */
}
const reply = (value, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });

/** Serve only known, immutable case endpoints; unknown requests fail visibly. */
window.fetch = async (input, init = {}) => {
  const url = new URL(typeof input === "string" ? input : input.url || input.href, location.href);
  if (url.origin !== location.origin || !url.pathname.startsWith("/api/"))
    return nativeFetch(input, init);
  const route = url.pathname;
  if (route === "/api/vibelens/control" && controlMode) {
    if (init.method === "POST") {
      const result = JSON.parse(init.body);
      if (result.revision !== controlSession.revision)
        return reply({ error: "Stale preview control" }, 409);
      controlSession.result = result;
      parent.postMessage(
        {
          type: "vibelens-controls-applied",
          locale: params.get("lang") || "en",
          preset: controlPreset,
          result,
          recording: controlSession.plan?.recording,
        },
        location.origin,
      );
      if (
        result.status === "applied" &&
        controlPreset === "replay" &&
        !matchMedia("(prefers-reduced-motion: reduce)").matches
      )
        document.getElementById("replay-play")?.click();
    }
    return reply(controlSession);
  }
  if (route === "/api/view") return reply(view);
  if (route === "/api/design") return reply({ available: false });
  if (route === "/api/versions") return reply([]);
  if (route === "/api/preferences") {
    if (init.method === "POST") {
      preferences = {
        ...JSON.parse(init.body),
        revision: preferences.revision + 1,
      };
      try {
        localStorage.setItem(preferenceKey, JSON.stringify(preferences));
      } catch {
        /* No server writes in Pages. */
      }
    }
    return reply(preferences);
  }
  if (["/api/source", "/api/code/source"].includes(route)) {
    if (route === "/api/code/source" && url.searchParams.get("revision") !== artifact.code.revision)
      return reply({ error: "Source revision differs from this recorded build" }, 409);
    if (
      url.searchParams.has("recording") &&
      url.searchParams.get("recording") !== artifact.recording.id
    )
      return reply({ error: "Recording is outside this case" }, 404);
    const source = artifact.sources[url.searchParams.get("path")];
    return source === undefined
      ? reply({ error: "File is outside this recorded case" }, 404)
      : reply({
          source,
          build_id: artifact.provenance.build_id,
          code_revision: artifact.code.revision,
        });
  }
  if (route === "/api/code/graph") {
    const focus = url.searchParams.get("focus");
    if (!focus) return reply(artifact.code);
    return artifact.codeFocus[focus]
      ? reply(expandCodeSlice(artifact.code, artifact.codeFocus[focus]))
      : reply(
          {
            error:
              "This neighborhood was not exported. Open Code structure to inspect the complete recorded index.",
          },
          404,
        );
  }
  if (route === "/api/recordings") return reply(artifact.catalog);
  if (route === "/api/recordings/" + artifact.recording.id) return reply(artifact.recording);
  return reply(
    {
      error:
        "This published case replays recorded operations. Run the project locally to record new ones.",
    },
    409,
  );
};

// Seed readable captions and the native semantic cluster layout. These are private
// presentation preferences; the exported model, sources and events stay intact.
const { emptyLayout, layoutKey } = await import("./viewer/layout.js");
const { profileFor } = await import("./viewer/analysis.js");
const chinese = params.get("lang") === "zh-CN";
const captions = artifact.story.captions;
const baseKey = layoutKey(view.model, preferences.project_id);
if (controlMode) {
  // Separate the layers in this preview; the native viewer keeps its own controls.
  const key = baseKey + ":analysis";
  const analysis = JSON.parse(preferences.entries[key] || "{}");
  analysis.layers = { ...analysis.layers, camera: "angled", gap: 180 };
  preferences.entries[key] = JSON.stringify(analysis);
}
for (const id of [
  "overview",
  "business",
  "states",
  "permission",
  "functions",
  "data-operations",
  "database",
  "code",
  "api",
]) {
  const key = baseKey + (id === "overview" ? "" : ":view:" + id);
  if (!preferences.entries[key]) {
    const layout = emptyLayout();
    layout.algorithm = "cluster";
    layout.filters = profileFor(id);
    preferences.entries[key] = JSON.stringify(layout);
  }
}
for (const [key, raw] of Object.entries(preferences.entries)) {
  const state = JSON.parse(raw);
  if (!state.annotations && state.schema !== 2) continue;
  state.annotations ||= {};
  for (const [id, pair] of Object.entries(captions)) {
    const existing = state.annotations[id];
    if (!existing?.label || id === artifact.story.inspection_node)
      state.annotations[id] = { ...existing, label: pair[chinese ? 1 : 0] };
  }
  preferences.entries[key] = JSON.stringify(state);
}
document.body.dataset.policyComparison = String(artifact.business.passed);

// Load after installing the transport: localization and preferences also use it.
const { mergeGraph } = await import("./viewer/graph-links.js");
if (!controlMode) {
  const sourceRegion = expandCodeSlice(
    artifact.code,
    artifact.codeFocus[artifact.story.source_focus],
  );
  view.model = mergeGraph(view.model, sourceRegion);
  artifact.recording.context.model = mergeGraph(artifact.recording.context.model, sourceRegion);
}
await import("./viewer/viewer.js?rev=files-1");
const { scenePlayer } = await import("./case-scene-player.mjs?rev=files-1");
const runtimeView = structuredClone(view);
const designView = {
  ...structuredClone(artifact.recording.context),
  layout_id: runtimeView.layout_id,
  stage: "design",
  instances: [],
  runtime_frames: { schema: "stategraph-runtime-frames/v1", frames: [] },
  program_url: null,
  database_status: null,
};
for (const node of designView.model.nodes) node.summary = "";
const post = (value) =>
  parent.postMessage({ ...value, version, locale: params.get("lang") || "en" }, location.origin);
const player = scenePlayer({
  artifact,
  locale: params.get("lang") || "en",
  post,
  setDesign: (enabled) => {
    view = enabled ? designView : runtimeView;
  },
});
window.addEventListener("message", (event) => {
  if (event.source !== parent || event.origin !== location.origin) return;
  if (controlMode) {
    if (
      event.data?.type === "vibelens-controls-select" &&
      Object.hasOwn(controlPlans, event.data.preset)
    ) {
      controlPreset = event.data.preset;
      controlSession.revision++;
      controlSession.plan = structuredClone(controlPlans[controlPreset]);
      controlSession.result = null;
    }
    if (event.data?.type === "vibelens-controls-mode" && ["2d", "3d"].includes(event.data.mode)) {
      const enabled = window.graphDebug.layers.enabled;
      if (enabled !== (event.data.mode === "3d")) document.getElementById("layered-toggle").click();
    }
    if (event.data?.type === "vibelens-controls-fit")
      requestAnimationFrame(() =>
        requestAnimationFrame(() => document.getElementById("fit").click()),
      );
    if (event.data?.type === "vibelens-controls-visibility" && !event.data.visible) {
      const play = document.getElementById("replay-play");
      if (/Pause|暂停/.test(play?.getAttribute("aria-label"))) play.click();
    }
    return;
  }
  if (
    event.source === parent &&
    event.origin === location.origin &&
    event.data?.type === "vibelens-case"
  )
    player
      .scene(event.data)
      .catch((error) => post({ type: "vibelens-case-error", error: error.message }));
});
const style = document.createElement("link");
style.rel = "stylesheet";
style.href = new URL("./case-canvas.css?rev=files-1", import.meta.url).href;
document.head.append(style);
document.body.dataset.caseCompact = "true";
// Keep the captured provenance visible; recording and project-write controls are
// unavailable on a static host. Inspection, routing, filtering and replay remain.
document.querySelector("header").hidden = true;
for (const id of ["capture-mode", "record-start", "record-stop", "record-clear", "replay-export"])
  document.getElementById(id)?.setAttribute("hidden", "");
document.body.dataset.recordedCase = String(version);
// Browser-local view preferences must not be described as writes to a project.
document.getElementById("layout-status").hidden = true;
const recordedLabel = params.get("lang") === "zh-CN" ? "记录结束时的状态" : "Recorded final state";
const recordingChoice = document.getElementById("record-list");
function labelFinalState() {
  const final = recordingChoice.querySelector('option[value=""]');
  if (final && final.textContent !== recordedLabel) final.textContent = recordedLabel;
}
new MutationObserver(labelFinalState).observe(recordingChoice, {
  childList: true,
});
labelFinalState();
for (let attempt = 0; attempt < 250 && !window.graphDebug.graph; attempt++)
  await new Promise((resolve) => setTimeout(resolve, 40));
if (window.graphDebug.graph)
  parent.postMessage(
    {
      type: controlMode ? "vibelens-controls-ready" : "vibelens-case-ready",
      version,
      locale: params.get("lang") || "en",
    },
    location.origin,
  );
