/** A small native-trial story. The canonical graph renderer owns both 2D and 3D.
 * Scene changes select precomputed subsets; recordings are fetched only for the
 * full viewer or a source inspection. All runtime steps retain their event IDs.
 */
import { forestCopy, forestScenes, foundationDialogue, iterationDialogue } from "./forest-copy.mjs";
import { preparedGraph } from "./case-prepared-graph.mjs";
import { initialize, locale, onLanguageChange } from "./site-ui.mjs";
import { loadForestRecord } from "./forest-data.mjs";

const link = document.createElement("link");
link.rel = "stylesheet";
link.href = "forest.css";
document.head.append(link);
document.body.className = "forest-story";
const main = document.getElementById("main");
main.innerHTML = `<section class="forest-hero"><p>VibeLens</p><h1 id="forest-title"></h1><p id="forest-lead"></p></section>
  <nav class="forest-stages" aria-label="Development stages"></nav>
  <div class="forest-journey"><div class="forest-narrative"></div>
    <aside class="forest-workspace" aria-label="VibeLens">
      <div class="forest-toolbar"><strong>VibeLens</strong><span id="forest-epoch"></span>
        <button id="forest-2d" aria-pressed="true">2D</button><button id="forest-3d" aria-pressed="false">3D</button>
        <button id="forest-full"></button></div>
      <div class="forest-toolbar" id="forest-views"></div>
      <div class="forest-canvas"><div id="forest-graph" class="forest-graph"></div>
        <div class="forest-loading" id="forest-loading" role="status"></div>
        <div class="forest-detail" id="forest-detail" hidden></div></div>
      <div class="forest-result" id="forest-result"></div>
      <div class="forest-replay" id="forest-replay" hidden><button id="forest-play">▶</button>
        <input id="forest-position" type="range" min="0" max="0" value="0" aria-label="Recorded event"/>
        <output id="forest-time"></output></div>
      <div class="forest-note" id="forest-key"></div>
    </aside></div><footer class="forest-footer"><a href="index.html#install" data-i18n="case.install" data-local-link>Get VibeLens ↗</a></footer>`;
const $ = (id) => document.getElementById(id);
const text = (pair) => pair[locale() === "zh-CN" ? 1 : 0];
let epochData = {},
  manifest,
  scene = forestScenes[0],
  view = "business",
  network = "";
let graph,
  steps = [],
  position = 0,
  mode = "2d",
  timer = null,
  turnCount = 1;
const archivePromises = new Map();
const renderer = preparedGraph($("forest-graph"), { onInspect: inspect });
renderer.interact(false);
function stop() {
  clearInterval(timer);
  timer = null;
  $("forest-play").textContent = "▶";
  $("forest-play").setAttribute("aria-label", text(forestCopy.play));
}
function archive(epoch) {
  if (!archivePromises.has(epoch))
    archivePromises.set(
      epoch,
      loadForestRecord(`forest-data/${epoch}.json.gz`, manifest.epochs[epoch].raw_sha256).catch(
        (error) => {
          archivePromises.delete(epoch);
          throw error;
        },
      ),
    );
  return archivePromises.get(epoch);
}

/** Details display the archived declaration and source, never the live checkout. */
function inspect(node) {
  const detail = $("forest-detail");
  detail.replaceChildren();
  detail.hidden = false;
  const title = document.createElement("strong");
  title.textContent = text(node.labels);
  const identity = document.createElement("p");
  identity.textContent = node.id;
  detail.append(title, identity);
  if (node.value !== undefined) {
    const value = document.createElement("p");
    value.textContent = `${node.state_model_id} · ${node.value}`;
    detail.append(value);
  }
  const close = document.createElement("button");
  close.textContent = text(forestCopy.close);
  close.onclick = () => {
    detail.hidden = true;
  };
  detail.append(close);
  if (!node.source?.path) return;
  const source = document.createElement("button");
  source.textContent = text(forestCopy.source);
  detail.append(source);
  const epoch = scene.epoch;
  source.onclick = async () => {
    source.disabled = true;
    try {
      const record = await archive(epoch);
      const content = record.sources[node.source.path];
      if (typeof content !== "string") throw Error("Source is outside this recorded build");
      const pre = document.createElement("pre");
      const symbol = node.source.symbol?.split(".").at(-1);
      content.split("\n").forEach((line, index) => {
        const element = document.createElement(symbol && line.includes(symbol) ? "mark" : "span");
        element.textContent = `${index + 1}  ${line}\n`;
        pre.append(element);
      });
      detail.append(pre);
      // Scroll only the source pane. Moving the page would change the selected
      // story section and hide the context the visitor has just inspected.
      const mark = pre.querySelector("mark");
      if (mark)
        pre.scrollTop +=
          mark.getBoundingClientRect().top - pre.getBoundingClientRect().top - pre.clientHeight / 3;
    } catch (error) {
      source.textContent = error.message;
      source.disabled = false;
    }
  };
}

function replay() {
  const step = scene.replay ? steps[position] : null;
  renderer.render(graph, step, locale());
  $("forest-position").value = String(position);
  $("forest-position").max = String(Math.max(0, steps.length - 1));
  $("forest-time").textContent = step
    ? `${position + 1} / ${steps.length} · ${step.observed_at.slice(11, 23)}`
    : "";
  const result = $("forest-result");
  result.replaceChildren();
  if (step) {
    const label = document.createElement("span");
    label.textContent = text(forestCopy.captured);
    const value = document.createElement("span");
    value.textContent = Object.entries(step.outputs)
      .filter(([key]) => ["state", "status", "allowed", "cancel_reason"].includes(key))
      .map(([key, item]) => `${key}: ${item}`)
      .join(" · ");
    result.append(label, value);
    result.dataset.eventId = step.id;
  } else delete result.dataset.eventId;
}

function draw() {
  const data = epochData[scene.epoch];
  if (!data) return;
  const toolbar = $("forest-views");
  toolbar.replaceChildren();
  for (const id of ["business", "states", "rules", "inspection"]) {
    const button = document.createElement("button");
    button.textContent = text(forestCopy[id]);
    button.dataset.forestView = id;
    button.setAttribute("aria-pressed", String(view === id));
    button.onclick = () => {
      stop();
      view = id;
      network = "";
      position = 0;
      draw();
    };
    toolbar.append(button);
  }
  if (view === "inspection") graph = data.inspection;
  else {
    const groups = data.networks[view],
      ids = Object.keys(groups);
    if (!groups[network]) network = view === "states" ? "download_task" : ids[0];
    const select = document.createElement("select");
    select.id = "forest-network";
    select.setAttribute("aria-label", text(forestCopy.networks));
    for (const id of ids) {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = text(groups[id].labels);
      select.append(option);
    }
    select.value = network;
    select.onchange = () => {
      stop();
      network = select.value;
      position = 0;
      draw();
    };
    toolbar.append(select);
    graph = groups[network];
  }
  const ids = new Set(graph.nodes.map((node) => node.id));
  steps = data.steps.filter((step) => ids.has(step.node));
  position = Math.min(position, Math.max(0, steps.length - 1));
  $("forest-replay").hidden = !scene.replay || !steps.length;
  $("forest-epoch").textContent = text(forestCopy[scene.epoch]);
  $("forest-detail").hidden = true;
  $("forest-loading").hidden = true;
  replay();
  document.body.dataset.forestScene = scene.id;
  $("forest-graph").dataset.epoch = scene.epoch;
  $("forest-graph").dataset.network = network;
}
function choose(next) {
  if (scene.id === next.id && graph) return;
  stop();
  scene = next;
  view = next.view;
  network = next.network || "";
  position = 0;
  document
    .querySelectorAll(".forest-stages a")
    .forEach((a) => a.setAttribute("aria-current", a.hash === "#" + scene.id ? "step" : "false"));
  draw();
}
function dialogue(host, turns, count = turns.length) {
  host.replaceChildren();
  for (const turn of turns.slice(0, count)) {
    const row = document.createElement("div");
    row.className = "forest-turn";
    const label = document.createElement("b");
    label.textContent = turn.speaker === "You" && locale() === "zh-CN" ? "用户" : turn.speaker;
    const body = document.createElement("p");
    body.textContent = text(turn.text);
    row.append(label, body);
    host.append(row);
  }
}
function copy() {
  $("forest-title").textContent = text(forestCopy.title);
  $("forest-lead").textContent = text(forestCopy.lead);
  $("forest-full").textContent = text(forestCopy.full);
  $("forest-key").textContent = text(forestCopy.key);
  $("forest-loading").textContent = text(forestCopy.loading);
  document.querySelector(".forest-stages").replaceChildren();
  const narrative = document.querySelector(".forest-narrative");
  narrative.replaceChildren();
  for (const [index, item] of forestScenes.entries()) {
    const anchor = document.createElement("a");
    anchor.href = "#" + item.id;
    anchor.textContent = text(item.title);
    anchor.onclick = () => choose(item);
    document.querySelector(".forest-stages").append(anchor);
    const section = document.createElement("section");
    section.id = item.id;
    section.dataset.forestScene = item.id;
    const number = document.createElement("span");
    number.className = "forest-number";
    number.textContent = String(index + 1).padStart(2, "0");
    const heading = document.createElement("h2");
    heading.textContent = text(item.title);
    const body = document.createElement("p");
    body.textContent = text(item.body);
    section.append(number, heading, body);
    if (["foundation", "iterate"].includes(item.id)) {
      const chat = document.createElement("div");
      chat.className = "forest-dialogue";
      dialogue(
        chat,
        item.id === "foundation" ? foundationDialogue : iterationDialogue,
        item.id === "foundation" ? turnCount : undefined,
      );
      section.append(chat);
      if (item.id === "foundation" && turnCount < foundationDialogue.length) {
        const button = document.createElement("button");
        button.className = "forest-next";
        button.id = "forest-next";
        button.textContent = text(forestCopy.next) + " →";
        button.onclick = () => {
          turnCount++;
          dialogue(chat, foundationDialogue, turnCount);
          if (turnCount === foundationDialogue.length) button.hidden = true;
        };
        section.append(button);
      }
    }
    narrative.append(section);
  }
  observer.disconnect();
  document.querySelectorAll(".forest-narrative section").forEach((node) => observer.observe(node));
  stop();
  draw();
}
const observer = new IntersectionObserver(
  (entries) => {
    const candidate = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (candidate) choose(forestScenes.find((item) => item.id === candidate.target.id));
  },
  { rootMargin: "-22% 0px -48% 0px", threshold: 0 },
);

$("forest-position").oninput = () => {
  stop();
  position = Number($("forest-position").value);
  replay();
};
$("forest-play").onclick = () => {
  if (timer) return stop();
  $("forest-play").textContent = "Ⅱ";
  $("forest-play").setAttribute("aria-label", text(forestCopy.pause));
  timer = setInterval(() => {
    position = (position + 1) % steps.length;
    replay();
  }, 1200);
};
for (const next of ["2d", "3d"])
  $("forest-" + next).onclick = async () => {
    mode = next;
    renderer.interact(mode === "3d");
    await renderer.mode(mode);
    for (const id of ["2d", "3d"])
      $("forest-" + id).setAttribute("aria-pressed", String(mode === id));
  };
$("forest-full").onclick = () =>
  window.open(`viewer/index.html?forest=${scene.epoch}&lang=${locale()}`, "_blank", "noopener");
onLanguageChange(copy);
initialize({
  "case.navigation": ["Walkthrough", "演示"],
  "case.install": ["Get VibeLens", "安装"],
});
async function load() {
  try {
    const responses = await Promise.all(
      ["manifest", "initial", "updated"].map((name) =>
        fetch(`forest-data/${name}.json`).then((response) => {
          if (!response.ok) throw Error(`View unavailable (${response.status})`);
          return response.json();
        }),
      ),
    );
    [manifest, epochData.initial, epochData.updated] = responses;
    choose(forestScenes.find((item) => "#" + item.id === location.hash) || forestScenes[0]);
    draw();
  } catch (error) {
    const loading = $("forest-loading");
    loading.hidden = false;
    loading.textContent = error.message + " ";
    const retry = document.createElement("button");
    retry.textContent = text(forestCopy.retry);
    retry.onclick = load;
    loading.append(retry);
  }
}
await load();
