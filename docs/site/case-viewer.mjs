/** Read-only Pages transport for a real, exported VibeLens execution.
 * Renderer modules remain canonical. This adapter serves captured artifacts;
 * it never executes the sample application's requests or synthesizes events.
 */
const params = new URLSearchParams(location.search);
const version = params.get("case") === "2" ? 2 : 1;
const nativeFetch = window.fetch.bind(window);
const artifact = await (
  await nativeFetch(new URL(`./case-data/v${version}.json`, import.meta.url))
).json();
let view = structuredClone(artifact.view);
let preferences = { schema: 1, project_id: view.layout_id, revision: 0, entries: {} };
const preferenceKey = `vibelens.case.afterlight.${params.get("lang") || "en"}`;
try {
  preferences = JSON.parse(localStorage.getItem(preferenceKey)) || preferences;
} catch {
  /* Optional browser preferences. */
}
const reply = (value, status = 200) =>
  new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });

/** Serve only known, immutable case endpoints; unknown requests fail visibly. */
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
      ? reply(artifact.codeFocus[focus])
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

// Load after installing the transport: localization and preferences also use it.
const { mergeGraph } = await import("./viewer/graph-links.js");
view.model = mergeGraph(view.model, artifact.codeFocus.publish);
artifact.recording.context.model = mergeGraph(
  artifact.recording.context.model,
  artifact.codeFocus.publish,
);
await import("./viewer/viewer.js");
const { timeline } = await import("./viewer/recording.js");
let commandEpoch = 0;

/** Apply a narrated location through the same controls used in the full viewer. */
async function command(message) {
  const epoch = ++commandEpoch;
  const control = (id, value) => {
    const element = document.getElementById(id);
    if (!element) return;
    if (value !== undefined) element.value = value;
    element.dispatchEvent(new Event("change", { bubbles: true }));
  };
  if (message.view) control("analysis-view", message.view);
  if (message.mode && (window.graphDebug.layers.enabled ? "3d" : "2d") !== message.mode)
    document.getElementById("layered-toggle").click();
  if (message.expand) document.getElementById("expand").click();
  if (message.node) {
    const target = [...document.querySelectorAll("#semantic [data-node-id]")].find(
      (node) => node.dataset.nodeId === message.node,
    );
    target?.click();
  }
  if (message.inspectMismatch) {
    control("record-list", artifact.recording.id);
    for (let attempt = 0; attempt < 100 && document.getElementById("replay").hidden; attempt++)
      await new Promise((resolve) => setTimeout(resolve, 25));
    if (epoch !== commandEpoch) return;
    control("replay-grain", "events");
    const entered = artifact.recording.events.find(
      (event) =>
        event.node === "review-policy" &&
        event.inputs.current_version === 2 &&
        event.inputs.reviewed_version === 1,
    );
    const returned = artifact.recording.events.find(
      (event) => event.call_id === entered.call_id && event.phase === "return",
    );
    const index = timeline(artifact.recording).findIndex((event) => event.id === returned.id);
    control("replay-events", String(index));
    document.getElementById("expand").click();
    await new Promise((resolve) => setTimeout(resolve, 100));
    if (epoch !== commandEpoch) return;
    const target = [...document.querySelectorAll("#semantic [data-node-id]")].find(
      (node) => node.dataset.nodeId === "review-policy",
    );
    target?.click();
    document.getElementById("node-expand").click();
    document
      .getElementById("viewport")
      .dispatchEvent(new KeyboardEvent("keydown", { key: "f", bubbles: true }));
  }
}
window.addEventListener("message", (event) => {
  if (
    event.source === parent &&
    event.origin === location.origin &&
    event.data?.type === "vibelens-case"
  )
    command(event.data);
});
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
new MutationObserver(labelFinalState).observe(recordingChoice, { childList: true });
labelFinalState();
for (let attempt = 0; attempt < 250 && !window.graphDebug.graph; attempt++)
  await new Promise((resolve) => setTimeout(resolve, 40));
if (window.graphDebug.graph)
  parent.postMessage({ type: "vibelens-case-ready", version }, location.origin);
