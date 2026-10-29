/** A scroll-led story: one actual viewer, progressively chosen native views. */
import { initialize, t, locale, onLanguageChange } from "./site-ui.mjs?rev=files-1";
import { messages, chapters } from "./case-messages.mjs?rev=files-1";
import { scrollStory } from "./scroll-story.mjs?rev=files-1";
import { companion } from "./case-companion.mjs?rev=files-1";

import { mountConversationTour } from "./conversation-tour.mjs?rev=files-1";

const $ = (id) => document.getElementById(id);
const copy = (pair) => pair[locale() === "en" ? 0 : 1];
let chapter = 0,
  mode = "2d",
  loaded = "",
  ready = false,
  pending = null,
  story,
  context;
let interacting = false,
  tools = false;
let options = { inputs: true, effects: false, states: false };
const values = await Promise.all(
  [1, 2].map(async (version) => (await fetch(`case-data/v${version}.json`)).json()),
);

function send(value) {
  if (ready)
    $("case-graph").contentWindow.postMessage({ type: "vibelens-case", ...value }, location.origin);
  else pending = { ...pending, ...value };
}
function setInteraction(enabled) {
  interacting = enabled;
  document.querySelector(".case-visual").classList.toggle("is-interacting", enabled);
  $("case-graph").tabIndex = enabled ? 0 : -1;
  $("case-interact").setAttribute("aria-pressed", String(enabled));
  $("case-interact").textContent = t(enabled ? "case.browse" : "case.explore");
}
function stage(index) {
  chapter = index;
  delete document.body.dataset.sceneReady;
  // Camera gestures work immediately in 3D. 2D keeps normal story scrolling.
  setInteraction(mode === "3d" || tools);
  context?.stage(index);
  const current = chapters[index];
  $("save-watch").disabled = true;
  document.querySelector(".case-playback").hidden = !["run", "verify"].includes(current.id);
  const lens = ["foundation", "run"].includes(current.id) ? "business" : "implementation";
  document
    .querySelectorAll("[data-case-lens]")
    .forEach((button) =>
      button.setAttribute("aria-pressed", String(button.dataset.caseLens === lens)),
    );
  const version = current.version;
  const message = {
    scene: chapters[index].id,
    mode,
    compact: !tools,
    options,
    name: $("watch-name")?.value || t("case.viewName"),
  };
  const key = version + ":" + locale();
  $("case-view-name").textContent = t(
    ["foundation", "run"].includes(current.id)
      ? "case.graph"
      : ["drill", "iterate", "verify"].includes(current.id)
        ? "case.viewName"
        : "case.core",
  );
  $("case-telemetry").replaceChildren();
  if (loaded !== key) {
    ready = false;
    pending = message;
    loaded = key;
    $("case-graph").removeAttribute("data-ready");
    $("case-graph").src = `viewer/index.html?case=${version}&lang=${locale()}&rev=files-1`;
  } else send(message);
  document.body.dataset.chapter = String(index);
}

function button(parent, key, action, css = "scene-action") {
  const node = document.createElement("button");
  node.type = "button";
  node.dataset.sceneAction = key;
  node.textContent = t(key);
  node.className = css;
  node.addEventListener("click", action);
  parent.append(node);
  return node;
}
function render() {
  context?.destroy();
  $("case-chapters").replaceChildren();
  $("case-foundation").replaceChildren();
  $("case-narrative").replaceChildren();
  chapters.forEach((current, index) => {
    const link = document.createElement("a");
    link.href = "#" + current.id;
    link.dataset.chapter = index;
    link.textContent = copy(current.label);
    $("case-chapters").append(link);
    const section = document.createElement("section");
    section.id = current.id;
    section.className = index === 0 ? "foundation-scene" : "case-scene";
    section.dataset.caseScene = current.id;
    const kicker = document.createElement("p");
    kicker.className = "eyebrow";
    kicker.textContent = `${String(index + 1).padStart(2, "0")} / ${copy(current.label)}`;
    const surface = document.createElement("span");
    surface.className = "scene-surface";
    surface.textContent = t("case.location." + current.surface);
    kicker.append(surface);
    const title = document.createElement("h2");
    title.textContent = copy(current.title);
    const body = document.createElement("p");
    body.textContent = copy(current.body);
    section.append(kicker, title, body);
    if (current.steps) {
      const steps = document.createElement("ol");
      steps.className = "scene-steps";
      for (const [location, text] of current.steps) {
        const step = document.createElement("li");
        step.dataset.location = location;
        const label = document.createElement("span");
        label.textContent = t("case.location." + location);
        const action = document.createElement("p");
        action.textContent = copy(text);
        step.append(label, action);
        steps.append(step);
      }
      section.append(steps);
    }
    const slot = document.createElement("div");
    slot.className = "scene-companion-slot";
    section.append(slot);
    const appSlot = document.createElement("div");
    appSlot.className = "scene-app-slot";
    section.append(appSlot);
    if (current.id === "run") button(section, "case.run", () => send({ action: "play" }));
    if (current.id === "drill") {
      const trace = document.createElement("div");
      trace.className = "source-trail";
      const owner = values[0].view.model.nodes.find(
        (node) => node.id === values[0].story.inspection_node,
      );
      for (const text of [owner.source.symbol + "()", owner.source.path]) {
        const item = document.createElement("span");
        item.textContent = text;
        trace.append(item);
      }
      section.append(trace);
      button(section, "case.drill", () => send({ action: "source" }));
    }
    if (current.id === "drill") {
      const editor = document.createElement("details");
      editor.className = "view-editor";
      const summary = document.createElement("summary");
      summary.textContent = t("case.customize");
      editor.append(summary);
      const fieldset = document.createElement("fieldset");
      fieldset.className = "watch-options";
      const legend = document.createElement("legend");
      legend.textContent = t("case.selected");
      fieldset.append(legend);
      for (const [key, prop] of [
        ["case.rule", null],
        ["case.inputs", "inputs"],
        ["case.effects", "effects"],
        ["case.status", "states"],
      ]) {
        const label = document.createElement("label"),
          input = document.createElement("input");
        input.type = "checkbox";
        input.checked = prop ? options[prop] : true;
        input.disabled = !prop;
        if (prop) {
          input.dataset.watch = prop;
          input.onchange = () => {
            options = { ...options, [prop]: input.checked };
            $("save-watch").textContent = t("case.save");
            $("save-watch").disabled = true;
            delete document.body.dataset.sceneReady;
            send({ action: "preview", options });
          };
        }
        label.append(input, document.createTextNode(t(key)));
        fieldset.append(label);
      }
      const name = document.createElement("input");
      name.id = "watch-name";
      name.className = "watch-name";
      name.value = t("case.viewName");
      name.maxLength = 40;
      name.setAttribute("aria-label", t("case.name"));
      editor.append(fieldset, name);
      const save = button(
        editor,
        "case.save",
        () => send({ action: "save", name: name.value }),
        "watch-save",
      );
      save.id = "save-watch";
      section.append(editor);
    }
    if (current.id === "iterate") {
      button(section, "case.repair", () => send({ action: "source" }));
    }
    if (current.id === "verify") {
      const change = document.createElement("p");
      change.className = "rule-change";
      change.textContent = t("case.change");
      section.append(change);
      const check = document.createElement("div");
      check.id = "case-check";
      check.className = "scene-check passed";
      check.textContent = t("case.check.pass");
      section.append(check);
      button(section, "case.retest", () => send({ action: "play" }));
    }
    $(index === 0 ? "case-foundation" : "case-narrative").append(section);
  });
  context = companion({
    host: $("case-context"),
    chapters,
    artifacts: values,
    send,
    begin: () => story.go(1),
  });
  story?.destroy?.();
  story = scrollStory({
    scenes: document.querySelectorAll("[data-case-scene]"),
    navigation: $("case-chapters"),
    onChange: stage,
  });
  setInteraction(interacting);
}
window.addEventListener("message", (event) => {
  if (
    event.origin !== location.origin ||
    event.source !== $("case-graph").contentWindow ||
    event.data.version !== chapters[chapter].version ||
    event.data.locale !== locale()
  )
    return;
  const data = event.data;
  if (data.scene && data.scene !== chapters[chapter].id) return;
  if (data.type === "vibelens-case-ready") {
    ready = true;
    send(pending || { scene: chapters[chapter].id, options });
    pending = null;
  }
  if (data.type === "vibelens-scene-ready") {
    $("case-graph").dataset.ready = "true";
    document.body.dataset.sceneReady = data.scene;
    $("save-watch").disabled = false;
  }
  if (data.type === "vibelens-view-saved") {
    $("save-watch").textContent = t("case.saved");
    $("case-view-name").textContent = data.name;
    document.body.dataset.savedView = data.id;
  }
  if (data.type === "vibelens-case-error") {
    $("case-step").textContent = data.error;
    console.error(data.error);
  }
  if (data.type === "vibelens-lens-ready") document.body.dataset.lensReady = data.lens;
  if (data.type === "vibelens-case-state") {
    context?.update(data.eventId);
    document.querySelector(".case-playback").hidden =
      !data.playing && !["run", "verify"].includes(chapters[chapter].id);
    $("case-position").value = data.progress || 0;
    $("case-play").innerHTML = data.playing
      ? '<span aria-hidden="true">Ⅱ</span>'
      : '<span aria-hidden="true">▶</span>';
    $("case-play").setAttribute("aria-label", t(data.playing ? "case.pause" : "case.paused"));
    const model = values[chapters[chapter].version - 1].view.model;
    $("case-step").textContent = data.node
      ? model.nodes.find((node) => node.id === data.node)?.label || data.node
      : "";
    $("case-graph").dataset.visibleNodes = data.nodes;
    document.body.dataset.nativeView = data.viewId;
    if (
      ["drill", "iterate", "verify"].includes(chapters[chapter].id) &&
      data.viewId?.startsWith("custom-")
    )
      $("case-view-name").textContent = data.viewName;
    if (["drill", "iterate"].includes(chapters[chapter].id)) {
      const currentStory = values[chapters[chapter].version - 1].story,
        host = $("case-telemetry");
      host.replaceChildren();
      for (const field of currentStory.telemetry || []) {
        const value = data[field.direction]?.[field.field];
        if (data.node !== currentStory.inspection_node || value === undefined) continue;
        const span = document.createElement("span");
        span.textContent = copy(field.label);
        const strong = document.createElement("strong");
        strong.textContent = value;
        span.append(strong);
        host.append(span);
      }
    }
  }
});
for (const dimension of ["2d", "3d"])
  $("case-" + dimension).onclick = () => {
    mode = dimension;
    for (const value of ["2d", "3d"])
      $("case-" + value).setAttribute("aria-pressed", String(value === mode));
    setInteraction(mode === "3d" || tools);
    $("case-gestures").hidden = mode !== "3d";
    send({ mode });
  };
$("case-tools").onclick = () => {
  tools = !tools;
  $("case-tools").setAttribute("aria-pressed", String(tools));
  setInteraction(tools || mode === "3d");
  send({ compact: !tools });
};
$("case-interact").onclick = () => setInteraction(!interacting);
$("case-play").onclick = () => send({ action: "toggle-play" });
$("case-position").oninput = (event) =>
  send({ action: "seek", progress: Number(event.target.value) });
document.querySelectorAll("[data-case-lens]").forEach((button) => {
  button.onclick = () => {
    delete document.body.dataset.lensReady;
    document
      .querySelectorAll("[data-case-lens]")
      .forEach((other) => other.setAttribute("aria-pressed", String(other === button)));
    send({ action: button.dataset.caseLens });
    if (button.dataset.caseLens === "all") $("case-view-name").textContent = t("case.layered");
  };
});
onLanguageChange(render);
initialize(messages);
mountConversationTour();
// Story sections are created after HTML parsing; restore direct links afterward.
if (location.hash === "#conversation-controls")
  requestAnimationFrame(() =>
    document.getElementById("conversation-controls").scrollIntoView({ behavior: "instant" }),
  );
