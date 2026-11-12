/** A scroll-led story: one actual viewer, progressively chosen native views. */
import { initialize, t, locale, onLanguageChange } from "./site-ui.mjs?rev=files-1";
import { messages, chapters } from "./case-messages.mjs?rev=guided-1";
import { loadJson } from "./case-data.mjs?rev=pages-20261112";
import { scrollStory } from "./scroll-story.mjs?rev=0.14.0";
import { companion } from "./case-companion.mjs?rev=guided-1";
import { walkthroughGuide } from "./case-guide.mjs?rev=guided-1";

const $ = (id) => document.getElementById(id);
const copy = (pair) => pair[locale() === "en" ? 0 : 1];
let chapter = 0,
  mode = "2d",
  loaded = "",
  ready = false,
  pending = null,
  story,
  context,
  guide;
let interacting = false,
  tools = false;
let options = { inputs: true, effects: false, states: false };
let values = null,
  loadingTimer;

/** Keep the current canvas visible during in-place work; cover only a new document. */
function loading(phase, blocking = false) {
  clearTimeout(loadingTimer);
  const host = $("case-loading");
  host.hidden = !phase;
  host.classList.toggle("is-compact", !blocking);
  host.dataset.phase = phase || "ready";
  $("case-loading-text").textContent = t("case.loading." + (phase || "graph"));
  $("case-retry").hidden = phase !== "error";
  document.querySelector(".case-canvas").setAttribute("aria-busy", String(!!phase));
  if (phase && phase !== "error")
    loadingTimer = setTimeout(() => {
      $("case-loading-text").textContent = t("case.loading.slow");
      $("case-retry").hidden = false;
    }, 20000);
}

async function loadStory() {
  $("story-status").hidden = false;
  $("story-status-text").textContent = t("case.loading.story");
  $("story-retry").hidden = true;
  try {
    const summary = await loadJson("case-preview/story.json?rev=guided-1");
    if (summary.schema !== "vibelens-story-summary/v1") throw Error("Unsupported story summary");
    values = summary.versions;
    $("story-status").hidden = true;
    render();
    // Direct chapter links are restored only after their translated DOM exists.
    if (chapters.some((item) => "#" + item.id === location.hash))
      requestAnimationFrame(() =>
        document.querySelector(location.hash).scrollIntoView({ behavior: "instant" }),
      );
  } catch {
    $("story-status-text").textContent = t("case.loading.error");
    $("story-retry").hidden = false;
  }
}

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
  guide?.stage(current.id);
  $("save-watch").disabled = true;
  document.querySelector(".case-playback").hidden = !guide?.replayEnabled;
  const lens = ["foundation", "build", "run", "verify"].includes(current.id)
    ? "overview"
    : "implementation";
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
    editing: !!$("view-editor")?.open,
    options,
    name: $("watch-name")?.value || t("case.viewName"),
  };
  const key = version + ":" + locale();
  $("case-view-name").textContent = t(
    ["foundation", "build", "run", "verify"].includes(current.id)
      ? "case.graph"
      : ["drill", "iterate", "verify"].includes(current.id)
        ? "case.viewName"
        : "case.core",
  );
  $("case-telemetry").replaceChildren();
  const explanations = {
    foundation: ["Business · States · Rules", "业务 · 状态 · 规则"],
    build: [
      "Business + file states · open a node to follow its implementation",
      "业务与文件状态 · 展开节点可以继续追到实现",
    ],
    run: [
      "A pulse marks activity · moving arrows follow the recorded path · values show the result",
      "节点闪烁表示响应 · 箭头沿记录中的关系流动 · 数值显示实际结果",
    ],
    drill: ["Business → State → Function → Storage", "业务 → 状态 → 函数 → 存储"],
    iterate: [
      "Updated implementation · the confirmed requirement stays the same",
      "实现已更新 · 继续核对同一条已确认的业务要求",
    ],
    verify: [
      "Replay the same actions · compare the state and storage effects",
      "重放同样的操作 · 对照状态与数据变化",
    ],
  };
  $("case-scope").textContent = copy(explanations[current.id]);
  if (loaded !== key) {
    ready = false;
    pending = message;
    loaded = key;
    $("case-graph").removeAttribute("data-ready");
    loading("data", true);
    $("case-graph").src = `viewer/index.html?case=${version}&lang=${locale()}&rev=guided-1`;
  } else {
    loading("layout", !$("case-graph").hasAttribute("data-ready"));
    send(message);
  }
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
  if (!values) return;
  // Translation replaces chapter elements. Preserve the selected chapter, then
  // anchor its translated content after companions have their new height.
  // Focusing the sticky language button can itself change scroll position, so
  // restoring that pixel offset would incorrectly select an adjacent chapter.
  const previousChapter = story ? chapter : null;
  story?.destroy();
  context?.destroy();
  guide?.destroy();
  guide = walkthroughGuide({
    send,
    onDepthChange: (depth) => {
      options = { inputs: depth !== "operation", effects: depth === "data", states: true };
      for (const [key, value] of Object.entries(options)) {
        const input = document.querySelector(`[data-watch="${key}"]`);
        if (input) input.checked = value;
      }
    },
    onCaptureChange: ({ enabled, replay, phase }) => {
      context?.enableActions(enabled);
      document.querySelector(".case-playback").hidden = !replay;
      document.body.dataset.capturePhase = phase;
      $("case-capture-state").textContent =
        phase === "recording"
          ? copy(["● Recording demo", "● 演示录制中"])
          : phase === "recorded"
            ? copy(["Recorded sequence", "已录制的操作"])
            : "";
    },
  });
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
    if (index === 0) {
      const introduction = document.createElement("div");
      introduction.className = "scene-copy";
      introduction.append(kicker, title, body);
      section.append(introduction);
      const models = document.createElement("div");
      models.className = "scene-model-slot";
      section.append(models);
    } else section.append(kicker, title, body);
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
    guide.mount(section, current);
    if (current.id === "build") {
      const next = button(section, "case.run", () => story.go(2));
      next.textContent = copy(["Try the app and observe →", "开始操作，观察运行 →"]);
    }
    if (current.id === "drill") {
      const source = button(section, "case.drill", () => send({ action: "source" }));
      source.textContent = copy(["Open the mapped source ↗", "按需查看对应源码 ↗"]);
    }
    if (current.id === "drill") {
      // Keep editing outside document flow. Preview acknowledgements can resize
      // the graph and move focus; a native dialog keeps the form usable without
      // changing the narrative's height or advancing to the next chapter.
      const editor = document.createElement("dialog");
      editor.className = "view-editor";
      editor.id = "view-editor";
      editor.setAttribute("aria-labelledby", "view-editor-title");
      const heading = document.createElement("h2");
      heading.id = "view-editor-title";
      heading.textContent = t("case.customize");
      const close = button(editor, "case.closeView", () => editor.close(), "view-editor-close");
      close.textContent = "×";
      close.setAttribute("aria-label", t("case.closeView"));
      editor.append(heading);
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
            send({ action: "preview", options, guided: true });
          };
        }
        const labelText =
          prop === "inputs"
            ? copy(["Inputs & return values", "参数与返回值"])
            : prop === "effects"
              ? copy(["Storage & source", "数据与源码"])
              : t(key);
        label.append(input, document.createTextNode(labelText));
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
      const trigger = button(
        section,
        "case.customize",
        () => {
          editor.showModal();
          send({ editing: true });
          name.focus({ preventScroll: true });
        },
        "view-editor-trigger scene-action",
      );
      trigger.setAttribute("aria-haspopup", "dialog");
      trigger.setAttribute("aria-controls", editor.id);
      editor.addEventListener("close", () => {
        send({ editing: false });
        trigger.focus({ preventScroll: true });
        story?.refresh();
      });
      section.append(editor);
    }
    if (current.id === "verify") {
      const change = document.createElement("p");
      change.className = "rule-change";
      change.textContent = t("case.change");
      section.append(change);
      const check = button(section, "case.retest", () => send({ action: "restore-watch" }));
      check.textContent = copy(["Reopen my focused view", "再看保存的局部视图"]);
      const note = document.createElement("p");
      note.className = "iteration-note";
      note.textContent = copy([
        "One grant removed, state Private, recipient denied. The owner still has access. Repeat this observe–refine cycle for each new feature.",
        "这次删除 1 条授权，状态变为仅自己可见，接收者访问被拒绝，所有者仍可下载。之后每次新增功能，都可以继续这样观察与迭代。",
      ]);
      section.append(note);
    }
    $(index === 0 ? "case-foundation" : "case-narrative").append(section);
  });
  context = companion({
    host: $("case-context"),
    chapters,
    artifacts: values,
    send,
    onAction: (action) => guide.application(action),
    begin: () => story.go(1),
  });
  if (previousChapter !== null) {
    context.stage(previousChapter);
    $(chapters[previousChapter].id).scrollIntoView({
      behavior: "instant",
      block: "start",
    });
  }
  story = scrollStory({
    scenes: document.querySelectorAll("[data-case-scene]"),
    navigation: $("case-chapters"),
    onChange: stage,
    interactionSelector:
      ".view-editor, .case-visual, .case-conversation, .capture-guide, .case-application, .depth-controls",
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
  guide?.update(data);
  if (data.type === "vibelens-case-loading") loading(data.phase, true);
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
    loading(null);
  }
  if (data.type === "vibelens-view-saved") {
    $("save-watch").textContent = t("case.saved");
    $("case-view-name").textContent = data.name;
    document.body.dataset.savedView = data.id;
    $("view-editor").close();
  }
  if (data.type === "vibelens-case-error") {
    loading("error", !$("case-graph").hasAttribute("data-ready"));
    console.error(data.error);
  }
  if (data.type === "vibelens-lens-ready") {
    document.body.dataset.lensReady = data.lens;
    loading(null);
  }
  if (data.type === "vibelens-case-state") {
    context?.update(data.eventId);
    document.querySelector(".case-playback").hidden = !guide?.replayEnabled;
    $("case-position").value = data.progress || 0;
    $("case-play").innerHTML = data.playing
      ? '<span aria-hidden="true">Ⅱ</span>'
      : '<span aria-hidden="true">▶</span>';
    $("case-play").setAttribute("aria-label", t(data.playing ? "case.pause" : "case.paused"));
    const model = values[chapters[chapter].version - 1].view.model;
    $("case-step").textContent = data.node
      ? values[chapters[chapter].version - 1].story.captions[data.node]
        ? copy(values[chapters[chapter].version - 1].story.captions[data.node])
        : model.nodes.find((node) => node.id === data.node)?.label || data.node
      : "";
    $("case-graph").dataset.visibleNodes = data.nodes;
    document.body.dataset.nativeView = data.viewId;
    if (
      ["drill", "iterate", "verify"].includes(chapters[chapter].id) &&
      data.viewId?.startsWith("custom-")
    )
      $("case-view-name").textContent = data.viewName;
    if (["run", "drill", "iterate", "verify"].includes(chapters[chapter].id)) {
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
    loading("layout");
    document
      .querySelectorAll("[data-case-lens]")
      .forEach((other) => other.setAttribute("aria-pressed", String(other === button)));
    send({ action: button.dataset.caseLens });
    if (button.dataset.caseLens === "all") $("case-view-name").textContent = t("case.layered");
  };
});
$("case-retry").onclick = () => {
  loaded = "";
  stage(chapter);
};
$("story-retry").onclick = loadStory;
onLanguageChange(render);
initialize(messages);
loadStory();
