/** Stage the real viewer through its public UI controls and original recording. */
import { focusIds, focusTypes, focusRelations } from "./case-focus.mjs?rev=story-2";

export function scenePlayer({ artifact, setDesign, locale, post }) {
  const $ = (id) => document.getElementById(id);
  let epoch = 0,
    lastState = "",
    current = "foundation";
  const pause = (ms = 25) => new Promise((resolve) => setTimeout(resolve, ms));
  function control(id, value) {
    const element = $(id);
    if (value !== undefined) element.value = value;
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }
  async function until(predicate, ticket) {
    for (let i = 0; i < 200; i++) {
      if (ticket !== epoch) return false;
      if (predicate()) return true;
      await pause();
    }
    throw Error("The graph did not finish loading");
  }
  function nativeSelect(id) {
    const target = [...$("semantic").querySelectorAll("[data-node-id]")].find(
      (node) => node.dataset.nodeId === id,
    );
    target?.click();
    return !!target;
  }
  function fit() {
    $("fit").click();
  }
  function hideExcept(keep, ticket) {
    for (const id of window.graphDebug.graph.boxes.map((box) => box.id)) {
      if (ticket !== epoch) return;
      if (!keep.has(id) && nativeSelect(id)) $("hide-node").click();
    }
  }
  function filterGroup(group, values) {
    const inputs = [...$("filter-" + group).querySelectorAll("input")];
    for (const input of inputs) input.checked = values.includes(input.value);
    inputs[0].dispatchEvent(new Event("change", { bubbles: true }));
  }
  function savedName() {
    return locale === "zh-CN" ? "我的审核链路" : "My approval path";
  }
  function findSaved() {
    // Native saving appends the newly created or updated view to this list.
    return [...$("analysis-view").options]
      .filter((option) => option.value.startsWith("custom-"))
      .at(-1);
  }
  async function focus(options = {}, ticket) {
    $("replay-live").click();
    control("analysis-view", "overview");
    if (!(await until(() => window.graphDebug.graph?.boxes.length, ticket))) return;
    $("show-all").click();
    filterGroup("nodes", focusTypes);
    filterGroup("edges", focusRelations);
    control("filter-scope", "all");
    const keep = focusIds(options);
    $("collapse").click();
    // Open the containing groups before choosing individual visible children.
    // Hiding a parent intentionally hides its descendants in the real viewer.
    const ancestors = new Set(keep);
    for (const id of keep) {
      let parent = window.graphDebug.graph.all.get(id)?.parent;
      while (parent && !ancestors.has(parent)) {
        ancestors.add(parent);
        parent = window.graphDebug.graph.all.get(parent)?.parent;
      }
    }
    for (let depth = 0; depth < 5; depth++) {
      const groups = window.graphDebug.graph.boxes.filter(
        (box) => ancestors.has(box.id) && box.kids.length && !box.open,
      );
      if (!groups.length) break;
      for (const group of groups) {
        if (ticket !== epoch) return;
        if (nativeSelect(group.id)) $("node-expand").click();
      }
    }
    hideExcept(ancestors, ticket);
    $("close-detail").click();
    $("arrange").click();
    await until(() => !window.graphDebug.layoutBusy, ticket);
    fit();
  }
  function save(name) {
    $("custom-view-name").value = name || savedName();
    $("save-view").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    $("close-filters").click();
    const selected = $("analysis-view").selectedOptions[0];
    post({ type: "vibelens-view-saved", name: selected.textContent, id: selected.value });
  }
  async function recording(ticket) {
    control("record-list", artifact.recording.id);
    return until(
      () => !$("replay").hidden && window.graphDebug.view?.replay?.id === artifact.recording.id,
      ticket,
    );
  }
  async function mismatch(ticket) {
    if (!(await recording(ticket))) return;
    control("replay-grain", "events");
    const enter = artifact.recording.events.find(
      (event) =>
        event.node === "review-policy" &&
        event.inputs.current_version === 2 &&
        event.inputs.reviewed_version === 1,
    );
    const result = artifact.recording.events.find(
      (event) => event.call_id === enter.call_id && event.phase === "return",
    );
    const { timeline } = await import("./viewer/recording.js");
    control(
      "replay-events",
      String(timeline(artifact.recording).findIndex((event) => event.id === result.id)),
    );
  }
  async function play(ticket, fromStart = true) {
    if (!(await recording(ticket))) return;
    control("replay-grain", "view");
    control("replay-speed", "300");
    if (fromStart) {
      const range = $("replay-range");
      range.value = 0;
      range.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (
      !$("replay-play")
        .getAttribute("aria-label")
        ?.match(/Pause|暂停/)
    )
      $("replay-play").click();
  }
  async function scene(message) {
    const ticket = message.scene || message.action ? ++epoch : epoch;
    current = message.scene || current;
    if (message.compact !== undefined) document.body.dataset.caseCompact = String(message.compact);
    if (message.mode && (window.graphDebug.layers.enabled ? "3d" : "2d") !== message.mode)
      $("layered-toggle").click();
    if (!message.scene && !message.action) return;
    if (message.action === "toggle-play") {
      $("replay-play").click();
      return;
    }
    if (message.action === "seek") {
      const range = $("replay-range");
      range.value = (Number(message.progress) * Number(range.max)) / 100;
      range.dispatchEvent(new Event("input", { bubbles: true }));
      return;
    }
    if (message.action === "states") {
      control("analysis-view", "states");
      hideExcept(new Set(["state.empty", "state.pending", "state.displayed"]), ticket);
      fit();
      return;
    }
    if (message.action === "all") {
      $("replay-live").click();
      control("analysis-view", "overview");
      $("show-all").click();
      $("expand").click();
      fit();
      return;
    }
    if (message.action === "play") {
      await play(ticket);
      return;
    }
    if (message.action === "save") {
      save(message.name);
      return;
    }
    if (message.action === "preview") {
      await focus(message.options, ticket);
      await mismatch(ticket);
      if (ticket === epoch) post({ type: "vibelens-scene-ready", scene: current });
      return;
    }
    setDesign(current === "foundation");
    $("replay-live").click();
    if (current === "foundation" || current === "run") {
      control("analysis-view", "business");
      $("collapse").click();
      await until(
        () =>
          window.graphDebug.graph?.boxes.length > 0 &&
          window.graphDebug.view.stage === (current === "foundation" ? "design" : "runtime"),
        ticket,
      );
      hideExcept(new Set(["upload", "review", "publish", "exhibit"]), ticket);
      $("arrange").click();
      fit();
      if (current === "run" && !matchMedia("(prefers-reduced-motion: reduce)").matches)
        await play(ticket);
    } else if (["drill", "watch"].includes(current)) {
      await focus(message.options || { effects: current === "watch" }, ticket);
      await mismatch(ticket);
    } else {
      const saved = findSaved();
      if (saved) control("analysis-view", saved.value);
      else {
        await focus(message.options, ticket);
        save(message.name);
      }
      if (current === "iterate") await mismatch(ticket);
      else if (!matchMedia("(prefers-reduced-motion: reduce)").matches) await play(ticket);
    }
    if (ticket === epoch) {
      fit();
      post({ type: "vibelens-scene-ready", scene: current });
    }
  }
  // Publish the native replay position and selected facts, rather than a second
  // animation clock. The parent uses these for its slim transport controls.
  const timer = setInterval(() => {
    const view = window.graphDebug?.view,
      event = view?.replay?.event,
      entry = event?.call_id
        ? artifact.recording.events.find(
            (item) => item.call_id === event.call_id && item.phase === "enter",
          )
        : null;
    const state = {
      type: "vibelens-case-state",
      scene: current,
      node: event?.node,
      phase: event?.phase,
      inputs: { ...entry?.inputs, ...event?.inputs },
      outputs: event?.outputs || {},
      replayIndex: view?.replay?.index,
      progress:
        (Number($("replay-range").value) / Math.max(1, Number($("replay-range").max))) * 100,
      playing: !!$("replay-play")
        .getAttribute("aria-label")
        ?.match(/Pause|暂停/),
      nodes: window.graphDebug?.graph?.boxes.length || 0,
      viewId: $("analysis-view").value,
      viewName: $("analysis-view").selectedOptions[0]?.textContent,
      state: view?.machine?.current,
    };
    const encoded = JSON.stringify(state);
    if (encoded !== lastState) {
      lastState = encoded;
      post(state);
    }
  }, 150);
  addEventListener("pagehide", () => clearInterval(timer), { once: true });
  return { scene };
}
