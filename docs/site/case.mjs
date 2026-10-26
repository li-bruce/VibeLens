/** A scroll-led story: one actual viewer, progressively chosen native views. */
import { initialize, t, locale, onLanguageChange } from "./site-ui.mjs?rev=story-2";
import { messages, chapters } from "./case-messages.mjs?rev=story-2";
import { scrollStory } from "./scroll-story.mjs?rev=story-2";

const $ = (id) => document.getElementById(id);
const copy = (pair) => pair[locale() === "en" ? 0 : 1];
let chapter = 0,
  mode = "2d",
  loaded = "",
  ready = false,
  pending = null,
  story;
let interacting = false,
  tools = false;
let options = { versions: true, effects: true, states: false };
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
  setInteraction(false);
  const version = index >= 4 ? 2 : 1;
  const message = {
    scene: chapters[index].id,
    mode,
    compact: !tools,
    options: index === 2 ? { versions: true, effects: false, states: false } : options,
    name: $("watch-name")?.value || t("case.viewName"),
  };
  const key = version + ":" + locale();
  $("case-view-name").textContent = t(
    index === 0 || index === 1
      ? "case.graph"
      : index === 3 || index >= 4
        ? "case.viewName"
        : "case.core",
  );
  $("case-telemetry").replaceChildren();
  if (loaded !== key) {
    ready = false;
    pending = message;
    loaded = key;
    $("case-graph").removeAttribute("data-ready");
    $("case-graph").src = `viewer/index.html?case=${version}&lang=${locale()}&rev=story-2`;
  } else send(message);
  document.body.dataset.chapter = String(index);
}

function button(parent, key, action, css = "scene-action") {
  const node = document.createElement("button");
  node.type = "button";
  node.textContent = t(key);
  node.className = css;
  node.addEventListener("click", action);
  parent.append(node);
  return node;
}
function mismatch(version) {
  const artifact = values[version - 1];
  const enter = artifact.recording.events.find(
    (event) =>
      event.node === "review-policy" &&
      event.inputs.reviewed_version === 1 &&
      event.inputs.current_version === 2,
  );
  return enter.inputs;
}
function render() {
  $("case-chapters").replaceChildren();
  $("case-narrative").replaceChildren();
  chapters.forEach((current, index) => {
    const link = document.createElement("a");
    link.href = "#" + current.id;
    link.dataset.chapter = index;
    link.textContent = copy(current.label);
    $("case-chapters").append(link);
    const section = document.createElement("section");
    section.id = current.id;
    section.className = "case-scene";
    section.dataset.scrollScene = "";
    const kicker = document.createElement("p");
    kicker.className = "eyebrow";
    kicker.textContent = `${String(index + 1).padStart(2, "0")} / ${copy(current.label)}`;
    const title = document.createElement("h2");
    title.textContent = copy(current.title);
    const body = document.createElement("p");
    body.textContent = copy(current.body);
    section.append(kicker, title, body);
    if (current.quote) {
      const quote = document.createElement("blockquote");
      quote.textContent = copy(current.quote);
      section.append(quote);
    }
    if (index === 0) {
      button(section, "case.confirm", () => story.go(1));
      button(section, "case.states", () => send({ action: "states" }));
    }
    if (index === 1) button(section, "case.run", () => send({ action: "play" }));
    if (index === 2) {
      const facts = document.createElement("div");
      facts.className = "scene-values";
      const inputs = mismatch(1);
      for (const [key, value] of [
        ["case.reviewed", inputs.reviewed_version],
        ["case.current", inputs.current_version],
      ]) {
        const item = document.createElement("div");
        item.textContent = t(key);
        const strong = document.createElement("strong");
        strong.textContent = value;
        item.append(strong);
        facts.append(item);
      }
      section.append(facts);
      const check = document.createElement("div");
      check.className = "scene-check";
      check.textContent = t("case.check.fail");
      section.append(check);
      button(section, "case.drill", () =>
        send({ scene: "drill", options: { versions: true, effects: false, states: false } }),
      );
    }
    if (index === 3) {
      const fieldset = document.createElement("fieldset");
      fieldset.className = "watch-options";
      const legend = document.createElement("legend");
      legend.textContent = t("case.selected");
      fieldset.append(legend);
      for (const [key, prop] of [
        ["case.rule", null],
        ["case.versions", "versions"],
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
      section.append(fieldset, name);
      const save = button(
        section,
        "case.save",
        () => send({ action: "save", name: name.value }),
        "watch-save",
      );
      save.id = "save-watch";
      button(section, "case.replay", () => send({ action: "play" }));
    }
    if (index === 4) {
      const code = document.createElement("pre");
      code.className = "scene-code";
      code.textContent = "reviewed_version\n       == current_version";
      section.append(code);
      button(section, "case.repair", () => send({ scene: "iterate", options }));
    }
    if (index === 5) {
      const check = document.createElement("div");
      check.id = "case-check";
      check.className = "scene-check passed";
      check.textContent = t("case.check.pass");
      section.append(check);
      button(section, "case.retest", () => send({ action: "play" }));
    }
    $("case-narrative").append(section);
  });
  story?.destroy?.();
  story = scrollStory({
    scenes: document.querySelectorAll(".case-scene"),
    navigation: $("case-chapters"),
    onChange: stage,
  });
  setInteraction(interacting);
}
window.addEventListener("message", (event) => {
  if (
    event.origin !== location.origin ||
    event.source !== $("case-graph").contentWindow ||
    event.data.version !== (chapter >= 4 ? 2 : 1) ||
    event.data.locale !== locale()
  )
    return;
  const data = event.data;
  if (data.type === "vibelens-case-ready") {
    ready = true;
    send(pending || { scene: chapters[chapter].id, options });
    pending = null;
  }
  if (data.type === "vibelens-scene-ready") {
    $("case-graph").dataset.ready = "true";
    document.body.dataset.sceneReady = data.scene;
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
  if (data.type === "vibelens-case-state") {
    $("case-position").value = data.progress || 0;
    $("case-play").innerHTML = data.playing
      ? '<span aria-hidden="true">Ⅱ</span>'
      : '<span aria-hidden="true">▶</span>';
    $("case-play").setAttribute("aria-label", t(data.playing ? "case.pause" : "case.paused"));
    const model = values[chapter >= 4 ? 1 : 0].view.model;
    $("case-step").textContent = data.node
      ? model.nodes.find((node) => node.id === data.node)?.label || data.node
      : "";
    $("case-graph").dataset.visibleNodes = data.nodes;
    document.body.dataset.nativeView = data.viewId;
    if (chapter >= 3 && data.viewId?.startsWith("custom-"))
      $("case-view-name").textContent = data.viewName;
    if ([2, 3, 4].includes(chapter)) {
      const inputs = data.inputs || {},
        host = $("case-telemetry");
      host.replaceChildren();
      for (const [key, value] of [
        ["case.reviewed", inputs.reviewed_version],
        ["case.current", inputs.current_version],
        ["case.verdict", data.outputs?.verdict],
      ]) {
        if (data.node !== "review-policy" || value === undefined) continue;
        const span = document.createElement("span");
        span.textContent = t(key);
        const strong = document.createElement("strong");
        strong.textContent = value;
        span.append(strong);
        if (key === "case.current") span.className = "mismatch";
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
    send({ mode });
  };
$("case-tools").onclick = () => {
  tools = !tools;
  $("case-tools").setAttribute("aria-pressed", String(tools));
  setInteraction(tools);
  send({ compact: !tools });
};
$("case-interact").onclick = () => setInteraction(!interacting);
$("case-play").onclick = () => send({ action: "toggle-play" });
$("case-position").oninput = (event) =>
  send({ action: "seek", progress: Number(event.target.value) });
onLanguageChange(render);
initialize(messages);
