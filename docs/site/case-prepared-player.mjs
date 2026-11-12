/** Presentation controller over small immutable scenes and original event IDs. */
import { preparedGraph } from "./case-prepared-graph.mjs";
import { loadJson } from "./case-data.mjs";

export function preparedPlayer({ host, versions, onState }) {
  let version = 1,
    language = "en",
    chapter = "foundation",
    lens = "overview",
    index = 0,
    playing = false,
    timer = null,
    options = { inputs: true, effects: true, states: true },
    saved = null,
    selectedGraph = null;
  const graph = preparedGraph(host, {
    onInspect: (node) => {
      // Only this recorded revocation has an implementation walkthrough. Other
      // concepts open their own model instead of an unrelated function.
      if (node.layer === "source") send({ action: "source" });
      else if (node.id === "revoke") send({ action: "depth", depth: "inputs" });
      else if (["function", "data"].includes(node.layer)) send({ action: "depth", depth: "data" });
      else send({ action: { business: "business", state: "states", rule: "rules" }[node.layer] });
    },
  });
  const data = () => versions[version - 1];
  const post = (value) => onState({ ...value, version, locale: language });
  const stop = () => {
    playing = false;
    clearTimeout(timer);
  };
  const storage = "vibelens.demo.prepared.view.v1";
  try {
    saved = JSON.parse(localStorage.getItem(storage));
  } catch {
    /* A private view is optional. */
  }
  const source = document.createElement("section");
  source.className = "prepared-source";
  source.hidden = true;
  host.append(source);
  const byOptions = () => {
    const base = data().scenes[options.effects ? "data" : options.inputs ? "inputs" : "operation"];
    const nodes = base.nodes.filter(
      (node) => (options.states || node.layer !== "state") && (options.inputs || !node.field),
    );
    const ids = new Set(nodes.map((node) => node.id));
    return { nodes, edges: base.edges.filter((edge) => ids.has(edge.from) && ids.has(edge.to)) };
  };
  function render() {
    selectedGraph = lens === "custom" ? byOptions() : data().scenes[lens] || data().scenes.overview;
    const event = data().steps[index];
    graph.render(selectedGraph, ["foundation", "build"].includes(chapter) ? null : event, language);
    post({
      type: "vibelens-case-state",
      scene: chapter,
      eventId: event?.id,
      node: event?.node,
      inputs: event?.inputs || {},
      outputs: event?.outputs || {},
      progress: (index / Math.max(1, data().steps.length - 1)) * 100,
      playing,
      nodes: selectedGraph.nodes.length,
      viewId: lens === "custom" ? "custom-prepared" : lens,
      viewName: saved?.name || "",
      sceneKey: lens,
    });
  }
  function ready(type = "vibelens-scene-ready", extra = {}) {
    render();
    post({ type, scene: chapter, ...extra });
  }
  function advance() {
    const ids = new Set(selectedGraph.nodes.map((n) => n.id)),
      edgeIds = new Set(selectedGraph.edges.map((e) => e.id));
    const next = data().steps.findIndex(
      (step, i) =>
        i > index &&
        (ids.has(step.node) ||
          step.transfers.some((id) => edgeIds.has(id)) ||
          i === data().steps.length - 1),
    );
    if (next < 0) {
      stop();
      render();
      return;
    }
    index = next;
    render();
    timer = setTimeout(advance, 1100);
  }
  async function showSource() {
    const record = data(),
      requestedChapter = chapter,
      captured = await loadJson(record.source.url);
    if (record !== data() || chapter !== requestedChapter) return;
    if (captured.sha256 !== record.source.sha256) throw Error("Source archive mismatch");
    const title = document.createElement("header"),
      name = document.createElement("strong"),
      close = document.createElement("button"),
      pre = document.createElement("pre");
    name.textContent = captured.path;
    close.textContent = "×";
    close.setAttribute("aria-label", language === "zh-CN" ? "关闭源码" : "Close source");
    close.onclick = () => {
      source.hidden = true;
    };
    title.append(name, close);
    captured.source.split(/\r?\n/).forEach((line, i) => {
      const row = document.createElement("span");
      row.textContent = `${String(i + 1).padStart(3)}  ${line}`;
      row.dataset.line = i + 1;
      if (i + 1 === record.source.highlight) row.className = "is-highlighted";
      pre.append(row);
    });
    source.replaceChildren(title, pre);
    source.hidden = false;
    requestAnimationFrame(() => {
      const mark = pre.querySelector(".is-highlighted");
      pre.scrollTop = Math.max(0, mark.offsetTop - pre.clientHeight / 2);
    });
  }
  function send(message) {
    const began = performance.now();
    if (message.version) version = message.version;
    if (message.locale) language = message.locale;
    if (message.mode)
      graph
        .mode(message.mode)
        .catch((error) => post({ type: "vibelens-case-error", error: error.message }));
    if (message.scene) {
      stop();
      source.hidden = true;
      chapter = message.scene;
      lens = ["foundation", "build", "run", "verify"].includes(chapter)
        ? "overview"
        : chapter === "drill"
          ? "operation"
          : saved
            ? "custom"
            : "data";
      if (lens === "custom") options = { ...saved.options };
      index = ["drill", "iterate"].includes(chapter)
        ? data().steps.findIndex((e) => e.id === data().inspection)
        : 0;
      ready();
    }
    const action = message.action;
    if (action === "pause") {
      stop();
      render();
    }
    if (action === "overview") {
      stop();
      source.hidden = true;
      lens = "overview";
      index = 0;
      ready("vibelens-lens-ready", { lens });
    }
    if (action === "depth") {
      stop();
      source.hidden = true;
      lens = message.depth;
      options = { inputs: lens !== "operation", effects: lens === "data", states: true };
      index = data().steps.findIndex((e) => e.id === data().inspection);
      post({ type: "vibelens-depth-changed", depth: lens });
      ready();
    }
    if (action === "preview") {
      lens = "custom";
      options = { ...message.options };
      source.hidden = true;
      ready();
    }
    if (action === "save") {
      saved = { name: message.name, options: { ...options } };
      try {
        localStorage.setItem(storage, JSON.stringify(saved));
      } catch {
        /* Continue for this page. */
      }
      lens = "custom";
      ready("vibelens-view-saved", { name: saved.name, id: "custom-prepared" });
    }
    if (action === "restore-watch") {
      stop();
      source.hidden = true;
      lens = saved ? "custom" : "data";
      if (saved) options = { ...saved.options };
      index = data().steps.findIndex((e) => e.id === data().inspection);
      ready();
    }
    if (action === "application") {
      stop();
      index = data().steps.findIndex((e) => message.eventIds.includes(e.id));
      if (index < 0) throw Error("Application action is outside the prepared recording");
      render();
      post({
        type: "vibelens-application-ready",
        requestId: message.requestId,
        eventId: data().steps[index].id,
      });
    }
    if (action === "seek") {
      stop();
      index = Math.round(
        (Math.max(0, Math.min(100, Number(message.progress))) / 100) * (data().steps.length - 1),
      );
      render();
    }
    if (action === "toggle-play") {
      if (playing) stop();
      else {
        if (index >= data().steps.length - 1) index = 0;
        playing = true;
        timer = setTimeout(advance, 1000);
      }
      render();
    }
    if (["business", "states", "rules", "implementation", "all"].includes(action)) {
      stop();
      source.hidden = true;
      lens = action;
      ready("vibelens-lens-ready", { lens });
    }
    if (action === "source")
      showSource().catch((error) => post({ type: "vibelens-case-error", error: error.message }));
    host.dataset.switchMs = (performance.now() - began).toFixed(2);
    host.dataset.scene = chapter;
    host.dataset.scope = lens;
  }
  return {
    send,
    interact: (value) => graph.interact(value),
    pause: stop,
    destroy() {
      stop();
      graph.destroy();
      source.remove();
    },
  };
}
