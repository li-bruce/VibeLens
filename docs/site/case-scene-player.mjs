/** Stage the real viewer through its public UI controls and original recording. */
import { focusIds, focusTypes, focusRelations } from "./case-focus.mjs?rev=clarity-2";
import {
  guidedIds,
  guidedViewIds,
  recordingWindow,
  eventAtProgress,
} from "./case-guide-model.mjs?rev=guided-1";

export function scenePlayer({ artifact, setDesign, locale, post }) {
  const story = artifact.story;
  const $ = (id) => document.getElementById(id);
  let epoch = 0,
    lastState = "",
    current = "foundation",
    needsPlanarLayout = false,
    editing = false,
    presenting = 0,
    playbackEnd = null,
    orderedEvents = [];
  const pause = (ms = 25) => new Promise((resolve) => setTimeout(resolve, ms));
  const paint = () =>
    new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  function control(id, value) {
    const element = $(id);
    if (value !== undefined) element.value = value;
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }
  async function until(predicate, ticket, waitingFor = "The graph did not finish loading") {
    const deadline = performance.now() + 15000;
    while (performance.now() < deadline) {
      if (ticket !== epoch) return false;
      if (predicate()) return true;
      await pause();
    }
    throw Error(waitingFor);
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
    if (document.body.dataset.caseSource === "true" && !window.graphDebug.layers.enabled) {
      const viewport = $("viewport");
      const bounds = window.graphDebug.displayGraph,
        camera = window.graphDebug.camera;
      // A saved mixed view can span several large regions. The native Locate
      // action frames this function without removing nodes or changing its layout.
      if (
        bounds.width * camera.scale > viewport.clientWidth ||
        bounds.height * camera.scale > viewport.clientHeight
      ) {
        $("focus-selection").click();
        return;
      }
      for (let step = 0; step < 2; step++) {
        const bounds = window.graphDebug.displayGraph,
          camera = window.graphDebug.camera;
        if (
          bounds.width * camera.scale * 1.2 > viewport.clientWidth - 24 ||
          bounds.height * camera.scale * 1.2 > viewport.clientHeight - 70
        )
          break;
        $("zoom-in").click();
      }
    }
  }
  /** A scene becomes ready only after layout, routed edges and canvas paint agree. */
  async function arrange(ticket) {
    await until(() => !window.graphDebug.layoutBusy, ticket);
    if (ticket !== epoch) return;
    $("arrange").click();
    await until(
      () =>
        !window.graphDebug.layoutBusy &&
        !window.graphDebug.geometryBusy &&
        !window.graphDebug.sourceBusy,
      ticket,
    );
    await paint();
    if (ticket === epoch) fit();
  }
  async function hideExcept(keep, ticket) {
    // Projection updates precede the accessible buttons' next paint. Wait for
    // those real controls before selecting nodes that just entered the view.
    for (let pass = 0; pass < 12; pass++) {
      await paint();
      const { glyphs, regions } = window.graphDebug.presentation;
      const outside = window.graphDebug.graph.boxes.filter(
        (box) => !keep.has(box.id) && (glyphs.has(box.id) || regions.has(box.id)),
      );
      if (!outside.length) return;
      for (const { id } of outside) {
        if (ticket !== epoch) return;
        if (nativeSelect(id)) $("hide-node").click();
      }
      // Hiding a region can expose an adjacent boundary in the native projection.
      // Process that new boundary on the next paint, too.
    }
    await paint();
    if (
      ticket === epoch &&
      [
        ...window.graphDebug.presentation.glyphs.keys(),
        ...window.graphDebug.presentation.regions.keys(),
      ].some((id) => !keep.has(id))
    )
      throw Error("The focused view still contains unselected nodes");
  }
  function filterGroup(group, values) {
    const inputs = [...$("filter-" + group).querySelectorAll("input")];
    for (const input of inputs) input.checked = values.includes(input.value);
    inputs[0].dispatchEvent(new Event("change", { bubbles: true }));
  }
  function savedName() {
    return locale === "zh-CN" ? "我的取消共享链路" : "My revocation path";
  }
  function findSaved() {
    // Native saving appends stored views. The unsaved draft is a separate
    // working selection and must never replace a previously saved story view.
    return [...$("analysis-view").options]
      .filter((option) => option.value.startsWith("custom-") && option.value !== "custom-draft")
      .at(-1);
  }
  async function focus(options = {}, ticket, selectedIds = null, preset = "functions") {
    // The static transport already supplies the exported source neighborhood
    // in this recording. Keep that revision rather than opening a live index.
    control("analysis-view", preset);
    // Load the recording before narrowing it. Its context supplies the final
    // inventory; filtering the live inventory first can miss newly loaded nodes.
    if (!(await recording(ticket))) return;
    if (!(await until(() => window.graphDebug.graph?.boxes.length, ticket))) return;
    // Use the shared layer action before narrowing the custom view. Presets
    // already restore their own filters and must retain their selected layers.
    $("layers-all").click();
    filterGroup("nodes", story.focus.node_types || focusTypes);
    // Keep the diagram flat at this scale. Exact code mappings connect the
    // business operation, observed deletion and its implementing function.
    filterGroup("regions", ["decision"]);
    filterGroup("edges", focusRelations);
    // Dispatch even if the value is already "all": the native scope action
    // also establishes the same flat projection used by saved custom views.
    control("filter-scope", "all");
    // The scope control starts a native layout. Let it finish before a second
    // arrangement; disabled toolbar actions otherwise ignore a quick click.
    await until(() => !window.graphDebug.layoutBusy, ticket, "The view layout did not settle");
    if (ticket !== epoch) return;
    await revealRegion(selectedIds || focusIds(options, story), ticket);
  }
  /** Expand just the ancestors needed to expose an actual mapped region. */
  async function revealRegion(keep, ticket) {
    needsPlanarLayout = !!window.graphDebug.layers.enabled;
    $("collapse").click();
    await paint();
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
      await paint();
    }
    await hideExcept(ancestors, ticket);
    $("close-detail").click();
    await arrange(ticket);
  }
  function save(name) {
    $("custom-view-name").value = name || savedName();
    $("save-view").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    $("close-filters").click();
    const selected = $("analysis-view").selectedOptions[0];
    post({
      type: "vibelens-view-saved",
      name: selected.textContent,
      id: selected.value,
    });
  }
  /** Open the minimum containment paths needed to introduce each populated layer. */
  async function revealLayers(ticket) {
    const { layerOf, layers } = await import("./viewer/graph-layers.js");
    for (const layer of layers) {
      if (ticket !== epoch) return;
      const graph = window.graphDebug.graph;
      if (graph.boxes.some((box) => layerOf(box.node) === layer.id)) continue;
      const candidate = [...graph.all.values()].find((node) => layerOf(node) === layer.id);
      const parents = [];
      let parent = candidate?.parent;
      while (parent && !parents.includes(parent)) {
        parents.push(parent);
        parent = graph.all.get(parent)?.parent;
      }
      for (const id of parents.reverse()) {
        const box = window.graphDebug.graph.byId.get(id);
        if (box?.kids.length && !box.open && nativeSelect(id)) $("node-expand").click();
      }
    }
    $("close-detail").click();
  }
  async function recording(ticket) {
    if (!orderedEvents.length) {
      const { timeline } = await import("./viewer/recording.js");
      orderedEvents = timeline(artifact.recording);
    }
    if (
      $("record-list").value === artifact.recording.id &&
      window.graphDebug.view?.replay?.id === artifact.recording.id
    )
      return true;
    control("record-list", artifact.recording.id);
    return until(
      () => !$("replay").hidden && window.graphDebug.view?.replay?.id === artifact.recording.id,
      ticket,
      "The selected recording did not open",
    );
  }
  async function inspectEvent(ticket) {
    if (!(await recording(ticket))) return;
    control("replay-grain", "events");
    const result = artifact.recording.events.find((event) => event.id === story.inspection_event);
    if (!result) throw Error("The exported inspection event is missing");
    const { timeline } = await import("./viewer/recording.js");
    control(
      "replay-events",
      String(timeline(artifact.recording).findIndex((event) => event.id === result.id)),
    );
  }
  async function showSource(ticket) {
    document.body.dataset.caseSource = "true";
    if (!nativeSelect(story.inspection_node)) throw Error("The function is outside this view");
    // Selection updates the native toolbar on the next paint. Use that enabled
    // action, just as a person does, rather than clicking its previous state.
    await until(() => !$("source").disabled, ticket, "The selected function has no source action");
    if (ticket !== epoch) return;
    $("source").click();
    await until(
      () =>
        $("source-code").dataset.location &&
        !$("source-code").hidden &&
        $("source-code").textContent.includes(story.source_excerpt),
      ticket,
      "The selected source file did not open",
    );
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    fit();
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const anchor = [...$("source-code").querySelectorAll("[data-source-line]")].find((line) =>
      line.textContent.includes(story.source_excerpt),
    );
    if (anchor) {
      anchor.classList.add("case-source-anchor");
      $("source-code").scrollTop =
        anchor.offsetTop - $("source-code").offsetTop - $("source-code").clientHeight / 3;
    }
  }
  function leaveSource() {
    document.body.dataset.caseSource = "false";
    $("close-detail").click();
  }
  function isPlaying() {
    return !!$("replay-play")
      .getAttribute("aria-label")
      ?.match(/Pause|暂停/);
  }
  function stopPlayback() {
    if (isPlaying()) $("replay-play").click();
    playbackEnd = null;
  }
  /** Select a captured event using the native control; no parallel replay clock. */
  function seekEvent(index) {
    control("replay-grain", "events");
    control("replay-events", String(index));
  }
  async function overview(ticket) {
    leaveSource();
    setDesign(false);
    await focus({}, ticket, guidedIds(story), "overview");
    seekEvent(recordingWindow(orderedEvents, story).start);
    control("replay-grain", "view");
  }
  async function play(ticket, fromStart = true) {
    if (!(await recording(ticket))) return;
    const bounds = recordingWindow(orderedEvents, story);
    if (fromStart) seekEvent(bounds.start);
    control("replay-grain", "view");
    // A transfer takes 650ms in the native renderer. Let it finish before the
    // next step replaces it, so a viewer can follow the complete edge path.
    control("replay-speed", "900");
    playbackEnd = bounds.end;
    if (
      !$("replay-play")
        .getAttribute("aria-label")
        ?.match(/Pause|暂停/)
    )
      $("replay-play").click();
  }
  async function scene(message) {
    // Native actions may restore focus to their own toolbar or canvas. During a
    // scripted presentation that would focus this iframe and scroll its parent,
    // changing the reader's chapter. Keep presentation work non-interactive;
    // restore native input as soon as all overlapping requests have settled.
    if (message.editing !== undefined) editing = Boolean(message.editing);
    presenting++;
    document.body.inert = true;
    try {
      await present(message);
    } finally {
      presenting--;
      document.body.inert = editing || presenting > 0;
      // Loading a native preset restores its navigation preference. The compact
      // walkthrough promises drag-to-orbit, so restore that tool after the view,
      // not before it. Full tools preserves the developer's own selection mode.
      if (
        !presenting &&
        document.body.dataset.caseCompact === "true" &&
        window.graphDebug.layers.enabled
      )
        $("tool-orbit").click();
    }
  }
  async function present(message) {
    const ticket = message.scene || message.action ? ++epoch : epoch;
    current = message.scene || current;
    if (message.compact !== undefined) document.body.dataset.caseCompact = String(message.compact);
    if (message.mode && (window.graphDebug.layers.enabled ? "3d" : "2d") !== message.mode) {
      $("layered-toggle").click();
      // The walkthrough advertises drag-to-orbit in 3D. Select that native tool
      // explicitly; the application viewer defaults to marquee selection.
      $(message.mode === "3d" ? "tool-orbit" : "tool-select").click();
      // The story may have expanded a larger region while in the other mode.
      // Fit after the native toggle has restored that mode's viewport geometry.
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (ticket !== epoch) return;
      if (message.mode === "2d" && needsPlanarLayout) {
        $("arrange").click();
        needsPlanarLayout = false;
      }
      if (!(await until(() => !window.graphDebug.layoutBusy, ticket))) return;
      fit();
    }
    if (!message.scene && !message.action) return;
    if (message.scene) stopPlayback();
    if (message.action === "pause") {
      stopPlayback();
      return;
    }
    if (message.action === "source") {
      await showSource(ticket);
      return;
    }
    if (message.action === "toggle-play") {
      if (isPlaying()) stopPlayback();
      else {
        if (!(await recording(ticket))) return;
        const bounds = recordingWindow(orderedEvents, story);
        const index = orderedEvents.findIndex(
          (event) => event.id === window.graphDebug.view?.replay?.event?.id,
        );
        await play(ticket, index < bounds.start || index >= bounds.end);
      }
      return;
    }
    if (message.action === "seek") {
      stopPlayback();
      if (!(await recording(ticket))) return;
      seekEvent(eventAtProgress(orderedEvents, story, message.progress));
      return;
    }
    if (message.action === "overview") {
      stopPlayback();
      await overview(ticket);
      post({ type: "vibelens-lens-ready", lens: "overview" });
      return;
    }
    if (message.action === "depth") {
      stopPlayback();
      leaveSource();
      await focus({}, ticket, guidedIds(story, message.depth));
      await inspectEvent(ticket);
      post({ type: "vibelens-scene-ready", scene: current });
      return;
    }
    if (message.action === "restore-watch") {
      stopPlayback();
      leaveSource();
      const saved = findSaved();
      if (saved) control("analysis-view", saved.value);
      else await focus({}, ticket, guidedIds(story, "data"));
      await inspectEvent(ticket);
      fit();
      post({ type: "vibelens-scene-ready", scene: current });
      return;
    }
    if (message.action === "states") {
      leaveSource();
      control("analysis-view", "states");
      await revealRegion(new Set(story.states), ticket);
      fit();
      post({ type: "vibelens-lens-ready", lens: "states" });
      return;
    }
    if (message.action === "rules") {
      leaveSource();
      control("analysis-view", "permission");
      const ids = artifact.view.model.nodes
        .filter((node) => node.id.startsWith("policy:"))
        .map((node) => node.id);
      await revealRegion(new Set(ids), ticket);
      post({ type: "vibelens-lens-ready", lens: "rules" });
      return;
    }
    if (message.action === "business") {
      leaveSource();
      control("analysis-view", "business");
      $("collapse").click();
      await hideExcept(new Set(story.business), ticket);
      await arrange(ticket);
      post({ type: "vibelens-lens-ready", lens: "business" });
      return;
    }
    if (message.action === "implementation") {
      leaveSource();
      await focus({ effects: false }, ticket);
      post({ type: "vibelens-lens-ready", lens: "implementation" });
      return;
    }
    if (message.action === "application") {
      stopPlayback();
      const currentId = window.graphDebug.view?.replay?.event?.id;
      if (!(await recording(ticket))) return;
      // The miniature app is a transport into this recording, not another
      // implementation of the policy. Seek actual completed business actions.
      const { timeline } = await import("./viewer/recording.js");
      const events = timeline(artifact.recording);
      const start = events.findIndex((event) => event.id === currentId);
      const candidates = events.filter(
        (event) =>
          event.node === message.node &&
          event.phase === message.phase &&
          (!message.eventIds?.length || message.eventIds.includes(event.id)),
      );
      const next = candidates.find((event) => events.indexOf(event) > start) || candidates[0];
      if (next) {
        control("replay-grain", "events");
        control("replay-events", String(events.indexOf(next)));
        await paint();
        if (ticket === epoch)
          post({
            type: "vibelens-application-ready",
            requestId: message.requestId,
            eventId: next.id,
          });
      } else throw Error("This application action has no matching recorded event");
      return;
    }
    if (message.action === "all") {
      leaveSource();
      setDesign(false);
      $("replay-live").click();
      control("analysis-view", "code");
      if (
        !(await until(
          () => window.graphDebug.view?.code_structure?.revision === artifact.code.revision,
          ticket,
        ))
      )
        return;
      // The native code view loads the complete source index. Its filters can
      // then retain the authored layers and their original cross-layer links.
      for (const group of ["nodes", "regions", "edges"]) {
        const inputs = [...$("filter-" + group).querySelectorAll("input")];
        for (const input of inputs) input.checked = true;
        inputs[0].dispatchEvent(new Event("change", { bubbles: true }));
      }
      $("layers-all").click();
      control("filter-scope", "all");
      // Start from aggregate regions. The viewer retains every child and its
      // count; developers expand the part they want rather than a wall of code.
      $("collapse").click();
      await revealLayers(ticket);
      await arrange(ticket);
      post({ type: "vibelens-lens-ready", lens: "all" });
      if (message.compact === false) post({ type: "vibelens-scene-ready", scene: current });
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
      leaveSource();
      await focus(
        message.options,
        ticket,
        message.guided ? guidedViewIds(story, message.options) : null,
      );
      await inspectEvent(ticket);
      if (ticket === epoch) post({ type: "vibelens-scene-ready", scene: current });
      return;
    }
    setDesign(current === "foundation");
    document.body.dataset.caseSource = "false";
    $("close-detail").click();
    $("replay-live").click();
    if (current === "foundation") {
      control("analysis-view", "business");
      $("collapse").click();
      await until(
        () =>
          window.graphDebug.graph?.boxes.length > 0 && window.graphDebug.view.stage === "design",
        ticket,
      );
      await hideExcept(new Set(story.business), ticket);
      await arrange(ticket);
    } else if (["build", "run", "verify"].includes(current)) {
      await overview(ticket);
    } else if (["drill", "watch"].includes(current)) {
      await focus({}, ticket, guidedIds(story, "operation"));
      await inspectEvent(ticket);
    } else {
      const saved = findSaved();
      if (saved) control("analysis-view", saved.value);
      else {
        await focus({}, ticket, guidedIds(story, "data"));
      }
      await inspectEvent(ticket);
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
    const rawIndex = orderedEvents.findIndex((item) => item.id === event?.id);
    const bounds = orderedEvents.length
      ? recordingWindow(orderedEvents, story)
      : { start: 0, end: 1 };
    if (playbackEnd !== null && rawIndex >= playbackEnd) {
      // A coarse view can skip an authorization event. End at the actual
      // selected operation, rather than the next unrelated owner's download.
      const end = playbackEnd;
      stopPlayback();
      if (rawIndex !== end) {
        seekEvent(end);
        return;
      }
    }
    const state = {
      type: "vibelens-case-state",
      scene: current,
      node: event?.node,
      phase: event?.phase,
      eventId: event?.id,
      inputs: { ...entry?.inputs, ...event?.inputs },
      outputs: event?.outputs || {},
      replayIndex: view?.replay?.index,
      progress: Math.max(
        0,
        Math.min(100, ((rawIndex - bounds.start) / Math.max(1, bounds.end - bounds.start)) * 100),
      ),
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
