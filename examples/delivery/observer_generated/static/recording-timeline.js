/** Execution timeline dock. The viewer owns replay; this component only requests seeks. */
import { t } from "./i18n.js";
import { eventLabel } from "./recording.js";
import { buildTraceIndex, traceRows, tracePoints } from "./trace-index.js";
import { boundWindow, zoomWindow, panWindow, nearestEvent } from "./trace-viewport.js";
import { paintTrace, traceGeometry, timeLabel } from "./trace-paint.js";
import { layers } from "./graph-layers.js";
import { iconButton } from "./controls.js";
import { boDisplayValue } from "./replay-steps.js";
import { traceHit } from "./trace-routing.js";
import { traceDescription } from "./trace-tooltip.js";
import { lifecycleCaption } from "./node-lifecycle.js";
import { rowMetrics } from "./trace-tracks.js";

export function cleanTimeline(value) {
  return {
    schema: 2,
    visible: value?.visible !== false,
    height: Number.isFinite(value?.height) ? Math.max(180, Math.min(500, value.height)) : 340,
    scope: value?.scope === "all" ? "all" : "view",
    follow: value?.follow !== false,
    depth: layers.some((layer) => layer.id === value?.depth) ? value.depth : "all",
    layerMode: value?.layerMode === "single" ? "single" : "through",
    collapsed: Array.isArray(value?.collapsed)
      ? value.collapsed
          .filter((id) => typeof id === "string" && id.startsWith("lane:"))
          .slice(0, 1000)
      : [],
    collapseAll: value?.collapseAll === true,
  };
}

/** Own listeners, indexes and pending frames so leaving replay releases the whole dock. */
export class RecordingTimeline {
  constructor(host, { onSeek, onPause, onRange, onSettings, onLive = () => {} }) {
    this.host = host;
    this.callbacks = { onSeek, onPause, onRange, onSettings, onLive };
    this.abort = new AbortController();
    this.settings = cleanTimeline();
    this.window = { start: 0, end: 1 };
    this.scroll = 0;
    this.raw = 0;
    this.rows = [];
    this.points = [];
    this.range = null;
    this.pendingSeek = null;
    this.drawFrame = this.seekFrame = null;
    this.drag = null;
    this.pulseStarted = performance.now();
    this.host.innerHTML = `
      <div class="trace-resize" role="separator" tabindex="0" aria-orientation="horizontal"></div>
      <div class="trace-toolbar">
        <strong></strong><span class="trace-key">━ · ◆ · ◇</span><select class="trace-scope"></select><select class="trace-depth"></select><button class="trace-single" aria-pressed="false"></button><button class="trace-tracks"></button>
        <button class="trace-fit"></button><button class="trace-zoom-in"></button><button class="trace-zoom-out"></button>
        <label class="trace-follow"><input type="checkbox" /><span></span></label>
        <button class="trace-loop"></button><button class="trace-clear"></button>
        <span class="trace-health" role="status"></span><button class="trace-live"></button><button class="trace-maximize"></button><button class="trace-close"></button>
      </div>
      <div class="trace-body"><canvas tabindex="0" role="slider" aria-valuemin="0"></canvas>
        <div class="trace-tooltip" hidden></div><pre class="trace-payload" hidden tabindex="0"></pre></div>
      <div class="trace-detail" aria-live="polite"><span class="trace-selected"></span><span class="trace-values"></span><button class="trace-inspect" aria-expanded="false"></button><button class="trace-locate"></button></div>`;
    const find = (name) => host.querySelector(".trace-" + name);
    this.find = find;
    this.canvas = host.querySelector("canvas");
    find("toolbar").querySelector("strong").textContent = t("Timeline");
    find("key").title = t("Duration · Event · Context or source mapping");
    find("scope").replaceChildren(
      new Option(t("Current view"), "view"),
      new Option(t("Recorded nodes"), "all"),
    );
    find("depth").setAttribute("aria-label", t("Observation depth"));
    find("single").textContent = t("Single layer");
    find("live").textContent = t("Live");
    this.listen(find("depth"), "change", () =>
      this.configure({
        depth: find("depth").value,
        ...(find("depth").value === "all" ? { layerMode: "through" } : {}),
      }),
    );
    this.listen(find("single"), "click", () =>
      this.configure({
        layerMode: this.settings.layerMode === "single" ? "through" : "single",
        depth:
          this.settings.depth === "all" ? (this.order || ["business"])[0] : this.settings.depth,
      }),
    );
    this.listen(find("live"), "click", onLive);
    iconButton(find("maximize"), "expand", t("Expand timeline"));
    this.listen(find("maximize"), "click", () => {
      this.maximized = !this.maximized;
      this.host.classList.toggle("trace-maximized", this.maximized);
      iconButton(
        find("maximize"),
        this.maximized ? "collapse" : "expand",
        t(this.maximized ? "Restore timeline" : "Expand timeline"),
      );
      this.clampScroll();
      this.schedule();
    });
    this.listen(find("tracks"), "click", () =>
      this.configure({
        collapseAll: !this.settings.collapseAll,
        collapsed: [],
      }),
    );
    find("scope").setAttribute("aria-label", t("Timeline scope"));
    find("follow").querySelector("span").textContent = t("Follow cursor");
    find("loop").textContent = t("Loop selection");
    find("clear").textContent = t("Clear range");
    find("inspect").textContent = t("Event data");
    this.listen(find("inspect"), "click", () => {
      find("payload").hidden = !find("payload").hidden;
      find("inspect").setAttribute("aria-expanded", String(!find("payload").hidden));
    });
    for (const [name, icon, label] of [
      ["fit", "fit", "Fit timeline"],
      ["zoom-in", "plus", "Zoom in"],
      ["zoom-out", "minus", "Zoom out"],
      ["close", "collapse", "Hide timeline"],
      ["locate", "locate", "Locate in graph"],
    ])
      iconButton(find(name), icon, t(label));
    find("resize").setAttribute("aria-label", t("Timeline height"));
    this.canvas.setAttribute(
      "aria-label",
      t(
        "Timeline: drag ruler to seek; drag tracks to pan; Ctrl-wheel to zoom; Shift-drag to select a range",
      ),
    );
    this.listen(find("scope"), "change", () => this.configure({ scope: find("scope").value }));
    this.listen(find("follow").querySelector("input"), "change", (event) =>
      this.configure({ follow: event.target.checked }),
    );
    this.listen(find("fit"), "click", () => this.fit());
    this.listen(find("zoom-in"), "click", () => this.zoom(2));
    this.listen(find("zoom-out"), "click", () => this.zoom(0.5));
    this.listen(find("close"), "click", () => this.configure({ visible: false }));
    this.listen(find("locate"), "click", () => this.requestSeek(this.raw, true));
    this.listen(find("loop"), "click", () => this.commitRange());
    this.listen(find("clear"), "click", () => {
      this.range = null;
      onRange({ loop: false });
      this.schedule();
    });
    this.listen(this.canvas, "pointerdown", (event) => this.pointerDown(event));
    this.listen(this.canvas, "pointermove", (event) => this.pointerMove(event));
    this.listen(this.canvas, "pointerup", () => this.pointerEnd());
    this.listen(this.canvas, "pointercancel", () => this.pointerEnd(true));
    this.listen(this.canvas, "pointerleave", () => {
      find("tooltip").hidden = true;
      this.hover = null;
      this.schedule();
    });
    this.listen(this.canvas, "wheel", (event) => this.wheel(event), { passive: false });
    this.listen(this.canvas, "keydown", (event) => this.key(event));
    this.listen(find("resize"), "pointerdown", (event) => {
      find("resize").setPointerCapture(event.pointerId);
      this.resizing = { y: event.clientY, height: this.settings.height };
    });
    this.listen(find("resize"), "pointermove", (event) => {
      if (!this.resizing) return;
      this.settings.height = Math.max(
        180,
        Math.min(500, this.resizing.height + this.resizing.y - event.clientY),
      );
      this.size();
    });
    const finishResize = () => {
      if (!this.resizing) return;
      this.resizing = null;
      this.callbacks.onSettings({ ...this.settings });
    };
    this.listen(find("resize"), "pointerup", finishResize);
    this.listen(find("resize"), "pointercancel", finishResize);
    this.listen(find("resize"), "keydown", (event) => {
      if (!["ArrowUp", "ArrowDown"].includes(event.key)) return;
      event.preventDefault();
      this.configure({ height: this.settings.height + (event.key === "ArrowUp" ? 20 : -20) });
    });
    this.observer = new ResizeObserver(() => {
      this.clampScroll();
      this.schedule();
    });
    this.observer.observe(find("body"));
  }

  listen(target, name, handler, options = {}) {
    target.addEventListener(name, handler, { ...options, signal: this.abort.signal });
  }

  /** Rebuild only on recording/topology/scope changes, never on each graph animation tick. */
  update({
    recording,
    model = recording.context.model,
    preferences,
    items,
    all,
    edges,
    visible,
    order = layers.map((layer) => layer.id),
    plan,
    raw,
    transfers,
    settings,
    playing,
    selection,
    inspection = true,
  }) {
    const prior = this.settings;
    if (this.raw !== raw) this.pulseStarted = performance.now();
    this.playing = playing;
    this.model = model;
    this.inspection = inspection;
    this.all = all;
    this.preferences = preferences;
    this.settings = cleanTimeline(settings);
    this.raw = raw;
    this.order = order;
    this.transfers = [...transfers];
    this.plan = plan;
    const indexKey = JSON.stringify([
      recording.id,
      items.length,
      items.at(-1)?.id,
      recording.status,
      [...all.keys()],
      edges.filter((edge) => edge.code_relation).map((edge) => [edge.id, edge.from, edge.to]),
    ]);
    if (indexKey !== this.indexKey) {
      const same = this.index?.recording.id === recording.id;
      const fitted =
        this.index && this.window.start === 0 && this.window.end === this.index.axis.total;
      this.indexKey = indexKey;
      this.index = buildTraceIndex(recording, items, all, edges);
      if (!same || fitted) this.window = { start: 0, end: this.index.axis.total };
      else this.window = boundWindow(this.window.start, this.window.end, this.index.axis.total);
      if (!same) {
        this.range = null;
        this.scroll = 0;
      }
      this.rowKey = null;
    }
    if (recording.observed_until && this.index.axis.ordered) {
      const total = Math.max(
        this.index.axis.total,
        Date.parse(recording.observed_until) - this.index.axis.origin,
      );
      if (Number.isFinite(total) && total > this.index.axis.total) {
        const fitted = this.window.start === 0 && this.window.end === this.index.axis.total;
        this.index.axis.total = total;
        for (const row of this.index.rows.values()) {
          let max = -Infinity;
          row.maxEnds = row.slices.map((slice) => {
            if (slice.unfinished) {
              slice.end = total;
              if (slice.stages?.length) slice.stages.at(-1).end = total;
            }
            return (max = Math.max(max, slice.end));
          });
        }
        if (fitted) this.window.end = total;
        this.rowKey = null;
      }
    }
    const rowKey = JSON.stringify([
      this.indexKey,
      this.settings.scope,
      this.settings.depth,
      this.settings.layerMode,
      this.settings.collapsed,
      this.settings.collapseAll,
      [...visible],
      order,
      plan,
    ]);
    if (rowKey !== this.rowKey) {
      this.rowKey = rowKey;
      this.rows = traceRows(this.index, {
        visible,
        order,
        scope: this.settings.scope,
        collapsed: this.settings.collapsed,
        collapseAll: this.settings.collapseAll,
        depth: this.settings.depth,
        layerMode: this.settings.layerMode,
      });
      this.points = tracePoints(this.rows, this.index, plan);
      this.allowed = new Set(plan);
      this.density = new Array(256).fill(0);
      for (const point of this.points)
        this.density[Math.min(255, Math.floor((point.time / this.index.axis.total) * 256))]++;
      this.clampScroll();
    }
    this.selection = selection;
    if (playing && this.settings.follow) {
      const time = this.index.axis.times[raw],
        width = this.window.end - this.window.start;
      if (time < this.window.start || time > this.window.end)
        this.window = boundWindow(time - width * 0.15, time + width * 0.85, this.index.axis.total);
    }
    this.host.hidden = !this.settings.visible;
    this.find("scope").value = this.settings.scope;
    const optionKey = order.join(":");
    if (this.find("depth").dataset.order !== optionKey) {
      this.find("depth").replaceChildren(
        new Option(t("All layers"), "all"),
        ...order.map((id) => new Option(t(layers.find((layer) => layer.id === id).label), id)),
      );
      this.find("depth").dataset.order = optionKey;
    }
    this.find("depth").value = this.settings.depth;
    this.find("single").setAttribute("aria-pressed", String(this.settings.layerMode === "single"));
    iconButton(
      this.find("tracks"),
      this.settings.collapseAll ? "expand" : "collapse",
      t(this.settings.collapseAll ? "Expand execution groups" : "Collapse execution groups"),
    );
    this.find("live").hidden = !recording.transient && recording.status !== "recording";
    this.host.dataset.source = recording.transient
      ? "live"
      : recording.status === "recording"
        ? "recording"
        : "saved";
    this.find("follow").querySelector("input").checked = this.settings.follow;
    const issues = [...(recording.gaps || [])];
    if (this.index.axis.boundaryAdjusted)
      issues.push(t("Recording boundary overlaps event delivery"));
    if (!this.index.axis.ordered)
      issues.push(t("Timestamps unavailable or out of order; event-order axis"));
    if (recording.capture?.mode === "focused") issues.push(t("Focused recording"));
    const producers = new Set(
      items
        .filter((item) => item.kind === "probe")
        .map((item) => item.producer_id || item.stream_id || item.run_id),
    );
    if (producers.size > 1) issues.push(t("Multiple producer clocks"));
    this.find("health").textContent = issues.length ? t("{0} recording notes", issues.length) : "";
    this.find("health").title = issues.join("\n");
    this.canvas.setAttribute("aria-valuemax", String(items.length - 1));
    this.canvas.setAttribute("aria-valuenow", String(raw));
    this.canvas.setAttribute("aria-valuetext", eventLabel(items[raw], this.model));
    this.host.dataset.eventId = items[raw].id;
    this.host.dataset.rawIndex = String(raw);
    this.host.dataset.graphTransfers = JSON.stringify(this.transfers);
    this.details();
    if (prior.height !== this.settings.height || !this.host.style.height) this.size();
    this.schedule();
  }

  /** Save presentation preferences through the existing project settings owner. */
  configure(patch) {
    this.settings = cleanTimeline({ ...this.settings, ...patch });
    this.callbacks.onSettings({ ...this.settings });
  }

  size() {
    this.host.style.height = `${this.settings.height}px`;
    this.find("resize").setAttribute("aria-valuenow", String(this.settings.height));
    this.schedule();
  }

  /** Read captured payloads and exact deltas; never derive application outcomes. */
  details() {
    if (!this.index) return;
    const event = this.index.items[this.raw];
    const slice = this.index.rows
      .get(event.node)
      ?.slices.find((item) => item.raw <= this.raw && item.last >= this.raw);
    const duration =
      slice?.duration !== null && slice?.duration !== undefined
        ? (slice.clippedStart ? "≥ " : "") + timeLabel(slice.duration)
        : slice?.unfinished
          ? t("Open call")
          : "";
    const title = `${eventLabel(event, this.model)}${duration ? " · " + duration : ""}`;
    const lifecycleLabel = lifecycleCaption(
      slice?.terminal && this.raw >= slice.last
        ? slice.terminal
        : slice?.stages?.findLast((stage) => stage.raw <= this.raw),
      this.preferences?.nameMode === "source",
    );
    this.find("selected").textContent = [title, lifecycleLabel && t(lifecycleLabel)]
      .filter(Boolean)
      .join(" · ");
    this.find("selected").title = [
      title,
      event.id,
      event.entity,
      event.attempt,
      event.observed_at,
      slice?.ambiguous ? t("Overlapping call ID") : "",
      slice?.context_entry
        ? `${t("Before recording")} · ${slice.context_entry.id} · ${slice.context_entry.observed_at}`
        : "",
    ]
      .filter(Boolean)
      .join("\n");
    const changes = this.index.changes[this.raw] || [];
    const values = changes.length
      ? changes
          .slice(0, 3)
          .map(
            (change) =>
              `${change.field}: ${boDisplayValue(change.before, this.model, change)} → ${boDisplayValue(change.after, this.model, change)}`,
          )
          .join(" · ")
      : Object.entries(event.outputs || {})
          .slice(0, 3)
          .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
          .join(" · ");
    this.find("values").textContent = values;
    this.find("values").title = JSON.stringify(
      { inputs: event.inputs, outputs: event.outputs, depends: event.depends },
      null,
      2,
    );
    this.find("payload").textContent = JSON.stringify(
      {
        id: event.id,
        node: event.node,
        phase: event.phase,
        entity: event.entity,
        attempt: event.attempt,
        observed_at: event.observed_at,
        inputs: event.inputs,
        outputs: event.outputs,
        depends: event.depends,
        ...(event.trace ? { trace: event.trace } : {}),
        ...(event.provenance ? { provenance: event.provenance } : {}),
        changes,
        graph_transfers: this.transfers,
        ...(slice
          ? {
              lifecycle: {
                state: slice.terminal?.state || slice.stages?.at(-1)?.state,
                registered: !!(slice.terminal || slice.stages?.at(-1))?.registered,
                termination: slice.terminal?.termination,
                start: slice.raw,
                end: slice.unfinished ? null : slice.last,
              },
            }
          : {}),
        ...(slice?.context_entry ? { context_entry: slice.context_entry } : {}),
      },
      null,
      2,
    );
    this.find("locate").disabled = !event.node;
    this.find("loop").disabled = !this.range;
    this.find("clear").disabled = !this.range && !this.selection?.loop;
  }

  clampScroll() {
    const height = this.find("body").clientHeight - traceGeometry.overview - traceGeometry.ruler;
    this.scroll = Math.max(
      0,
      Math.min(Math.max(0, rowMetrics(this.rows).total - height), this.scroll),
    );
  }

  /** Coalesce layout/pointer changes to one visible Canvas draw per frame. */
  schedule() {
    if (this.drawFrame !== null || !this.index || this.host.hidden) return;
    this.drawFrame = requestAnimationFrame(() => {
      this.drawFrame = null;
      const width = this.find("body").clientWidth,
        height = this.find("body").clientHeight;
      if (!width || !height) return;
      if (this.zoomMotion) {
        const motion = this.zoomMotion;
        const progress = Math.min(1, (performance.now() - motion.started) / 150);
        const ease = 1 - (1 - progress) ** 3;
        const span = Math.exp(
          Math.log(motion.from.end - motion.from.start) * (1 - ease) +
            Math.log(motion.to.end - motion.to.start) * ease,
        );
        const center =
          ((motion.from.start + motion.from.end) / 2) * (1 - ease) +
          ((motion.to.start + motion.to.end) / 2) * ease;
        this.window = boundWindow(center - span / 2, center + span / 2, this.index.axis.total);
        if (progress === 1) {
          this.window = motion.to;
          this.zoomMotion = null;
        }
      }
      const started = performance.now();
      this.pulse = matchMedia("(prefers-reduced-motion: reduce)").matches
        ? 0
        : ((started - this.pulseStarted) % 1100) / 1100;
      this.geometry = paintTrace(this.canvas, {
        ...this,
        width,
        height,
        depth: this.settings.depth,
        layerMode: this.settings.layerMode,
      });
      this.paintMs = performance.now() - started;
      if (this.zoomMotion) this.schedule();
      else if (
        !document.hidden &&
        this.pulse &&
        (this.playing ||
          (this.inspection && this.transfers.length > 0) ||
          started - this.pulseStarted < 1100)
      ) {
        clearTimeout(this.motionTimer);
        this.motionTimer = setTimeout(() => this.schedule(), 33);
      }
    });
  }

  point(event) {
    const box = this.canvas.getBoundingClientRect();
    return { x: event.clientX - box.left, y: event.clientY - box.top };
  }
  time(x, overview = false) {
    const ratio = Math.max(0, Math.min(1, (x - this.geometry.left) / this.geometry.plot));
    return overview
      ? ratio * this.index.axis.total
      : this.window.start + ratio * (this.window.end - this.window.start);
  }

  /** Coalesce seeks as well: rebuilding a graph frame is more expensive than drawing a cursor. */
  requestSeek(raw, locate = false) {
    if (raw === null || raw === undefined) return;
    this.pendingSeek = { raw, locate };
    if (this.seekFrame !== null) return;
    this.seekFrame = requestAnimationFrame(() => {
      this.seekFrame = null;
      const pending = this.pendingSeek;
      this.pendingSeek = null;
      if (pending && (pending.raw !== this.raw || pending.locate || !this.inspection))
        this.callbacks.onSeek(pending.raw, pending.locate);
    });
  }
  seekTime(time) {
    this.requestSeek(nearestEvent(this.points, time)?.raw);
  }

  /** Distinct hit zones keep track panning, ruler seeking and overview resizing predictable. */
  pointerDown(event) {
    if (!this.geometry || event.button !== 0) return;
    event.preventDefault();
    this.canvas.focus();
    this.callbacks.onPause();
    this.zoomMotion = null;
    const p = this.point(event),
      g = this.geometry;
    this.find("tooltip").hidden = true;
    this.canvas.setPointerCapture(event.pointerId);
    if (p.x < g.left) {
      const hit = this.geometry.hits.findLast(
        (hit) =>
          p.x >= hit.x && p.x <= hit.x + hit.width && p.y >= hit.y && p.y <= hit.y + hit.height,
      );
      if (hit?.kind === "group") {
        const row = this.rows.find((item) => item.id === hit.row),
          id = row.group;
        const current = this.settings.collapseAll
          ? this.index.executions.lanes.map((lane) => lane.id)
          : this.settings.collapsed;
        this.configure({
          collapseAll: false,
          collapsed: current.includes(id) ? current.filter((key) => key !== id) : [...current, id],
        });
      } else if (hit?.kind === "layer")
        this.requestSeek(
          nearestEvent(
            this.rows
              .find((row) => row.id === hit.row)
              .marks.map((mark) => ({ ...mark, time: this.index.axis.times[mark.raw] }))
              .filter((mark) => this.allowed.has(mark.raw)),
            this.index.axis.times[this.raw],
          )?.raw,
          true,
        );
      return;
    }
    if (p.y < traceGeometry.overview) {
      const startX = g.left + (this.window.start / this.index.axis.total) * g.plot,
        endX = g.left + (this.window.end / this.index.axis.total) * g.plot;
      const kind =
        Math.abs(p.x - startX) < 8 ? "start" : Math.abs(p.x - endX) < 8 ? "end" : "overview";
      this.drag = { kind, p, window: { ...this.window } };
      if (p.x < startX || p.x > endX) {
        const width = this.window.end - this.window.start,
          time = this.time(p.x, true);
        this.window = boundWindow(time - width / 2, time + width / 2, this.index.axis.total);
        this.drag.window = { ...this.window };
        this.schedule();
      }
    } else if (event.shiftKey) {
      this.drag = { kind: "range", time: this.time(p.x), p };
      this.range = [this.drag.time, this.drag.time];
    } else if (
      p.y < g.top ||
      (Math.abs(
        p.x -
          (g.left +
            ((this.index.axis.times[this.raw] - this.window.start) /
              (this.window.end - this.window.start)) *
              g.plot),
      ) < 7 &&
        p.y > this.canvas.clientHeight - 18)
    ) {
      this.drag = { kind: "seek" };
      this.seekTime(this.time(p.x));
    } else {
      const hit = traceHit(g.hits, p);
      if (hit && this.allowed.has(hit.raw)) {
        const nearest =
          hit.kind === "slice"
            ? nearestEvent(
                this.rows
                  .find((row) => row.id === hit.row)
                  ?.marks.filter(
                    (mark) => mark.node === hit.slice.node && this.allowed.has(mark.raw),
                  ) || [],
                this.time(p.x),
              )?.raw
            : hit.raw;
        this.requestSeek(nearest, event.detail === 2);
        this.drag = { kind: "seek" };
      } else this.drag = { kind: "pan", p, window: { ...this.window }, scroll: this.scroll };
    }
  }

  pointerMove(event) {
    if (!this.geometry) return;
    const p = this.point(event),
      drag = this.drag;
    if (!drag) return this.tooltip(p);
    if (drag.kind === "seek") this.seekTime(this.time(p.x));
    else if (drag.kind === "range") {
      this.range = [Math.min(drag.time, this.time(p.x)), Math.max(drag.time, this.time(p.x))];
      this.find("loop").disabled = false;
      this.find("clear").disabled = false;
    } else if (drag.kind === "pan") {
      const delta = ((drag.p.x - p.x) / this.geometry.plot) * (drag.window.end - drag.window.start);
      this.window = panWindow(drag.window, delta, this.index.axis.total);
      this.scroll = drag.scroll + drag.p.y - p.y;
      this.clampScroll();
    } else {
      const delta = ((p.x - drag.p.x) / this.geometry.plot) * this.index.axis.total;
      this.window =
        drag.kind === "start"
          ? boundWindow(
              Math.min(drag.window.end - this.index.axis.total / 100000, drag.window.start + delta),
              drag.window.end,
              this.index.axis.total,
            )
          : drag.kind === "end"
            ? boundWindow(
                drag.window.start,
                Math.max(
                  drag.window.start + this.index.axis.total / 100000,
                  drag.window.end + delta,
                ),
                this.index.axis.total,
              )
            : panWindow(drag.window, delta, this.index.axis.total);
    }
    this.schedule();
  }

  pointerEnd(cancelled = false) {
    if (cancelled && this.drag?.kind === "range") this.range = null;
    this.drag = null;
    this.details();
    this.schedule();
  }

  tooltip(point) {
    const hit =
      point.x >= this.geometry.left && point.y >= this.geometry.top
        ? traceHit(this.geometry.hits, point)
        : null;
    const tooltip = this.find("tooltip");
    if (!hit || hit.raw === undefined) {
      tooltip.hidden = true;
      if (this.hover) {
        this.hover = null;
        this.schedule();
      }
      return;
    }
    const key = hit.key || `${hit.row}:${hit.startRaw ?? hit.raw}`;
    if (this.hover?.key !== key) {
      this.hover = { key, row: hit.row, raw: hit.raw };
      this.schedule();
    }
    const time = this.time(point.x);
    const stage = hit.slice?.stages?.find((item) => item.start <= time && item.end > time);
    const description = traceDescription(
      { ...hit, stage },
      this.index,
      this.all,
      this.preferences,
      timeLabel,
    );
    const title = document.createElement("strong");
    title.textContent = description.title;
    tooltip.title = description.identity || "";
    tooltip.replaceChildren(
      title,
      ...description.lines.map((text) => {
        const line = document.createElement("span");
        line.textContent = text;
        return line;
      }),
    );
    tooltip.hidden = false;
    tooltip.style.left = `${Math.max(8, Math.min(this.canvas.clientWidth - Math.min(350, this.canvas.clientWidth - 16), point.x + 10))}px`;
    tooltip.style.top = `${Math.max(0, Math.min(this.canvas.clientHeight - tooltip.offsetHeight - 6, point.y - tooltip.offsetHeight - 8))}px`;
  }

  wheel(event) {
    if (!this.index || !this.geometry) return;
    event.preventDefault();
    const p = this.point(event);
    if (event.ctrlKey || event.metaKey)
      this.zoom(Math.exp(-event.deltaY * 0.005), (p.x - this.geometry.left) / this.geometry.plot);
    else if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
      this.window = panWindow(
        this.window,
        ((event.deltaX || event.deltaY) / this.geometry.plot) *
          (this.window.end - this.window.start),
        this.index.axis.total,
      );
      this.schedule();
    } else {
      this.scroll += event.deltaY;
      this.clampScroll();
      this.schedule();
    }
  }
  zoom(factor, anchor = null) {
    if (!this.index) return;
    const base = this.zoomMotion?.to || this.window;
    if (anchor === null)
      anchor = (this.index.axis.times[this.raw] - base.start) / (base.end - base.start);
    const target = zoomWindow(base, factor, anchor, this.index.axis.total);
    this.animateWindow(target);
  }
  animateWindow(target) {
    if (globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches) this.window = target;
    else this.zoomMotion = { from: { ...this.window }, to: target, started: performance.now() };
    this.schedule();
  }
  fit() {
    if (this.index) this.animateWindow({ start: 0, end: this.index.axis.total });
  }
  /** Reuse ID-based replay ranges so skipping/looping never rewrites recorded facts. */
  commitRange() {
    if (!this.range) return;
    const from = nearestEvent(this.points, this.range[0]),
      to = nearestEvent(this.points, this.range[1]);
    if (from && to)
      this.callbacks.onRange({
        loop: true,
        from: this.index.items[from.raw].id,
        to: this.index.items[to.raw].id,
      });
  }
  key(event) {
    const current = this.points.findIndex((point) => point.raw === this.raw);
    const move = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (move) {
      event.preventDefault();
      this.callbacks.onPause();
      const raw =
        this.points[Math.max(0, Math.min(this.points.length - 1, current < 0 ? 0 : current + move))]
          ?.raw;
      this.requestSeek(raw);
    } else if (["Home", "End"].includes(event.key)) {
      event.preventDefault();
      this.callbacks.onPause();
      this.requestSeek(event.key === "Home" ? this.points[0]?.raw : this.points.at(-1)?.raw);
    } else if (["+", "=", "-"].includes(event.key)) {
      event.preventDefault();
      this.zoom(event.key === "-" ? 0.5 : 2);
    } else if (event.key === "Escape") {
      this.range = null;
      this.details();
      this.schedule();
    } else if (event.key === "Enter") this.requestSeek(this.raw, true);
  }

  clear() {
    clearTimeout(this.motionTimer);
    this.hover = null;
    this.maximized = false;
    this.host.classList.remove("trace-maximized");
    cancelAnimationFrame(this.seekFrame);
    cancelAnimationFrame(this.drawFrame);
    this.seekFrame = this.drawFrame = null;
    this.pendingSeek = this.drag = this.index = this.zoomMotion = null;
    this.all = this.model = this.preferences = null;
    this.indexKey = this.rowKey = null;
    this.rows = [];
    this.points = [];
    this.plan = [];
    this.transfers = [];
    this.geometry = this.range = this.selection = null;
    this.allowed = new Set();
    this.density = [];
    this.raw = 0;
    this.find("tooltip").hidden = this.find("payload").hidden = true;
    this.find("payload").textContent = "";
    this.find("inspect").setAttribute("aria-expanded", "false");
    this.host.hidden = true;
  }
  dispose() {
    this.clear();
    this.observer.disconnect();
    this.abort.abort();
  }

  /** Read-only test diagnostics; UI tests still drive actual pointers and controls. */
  get diagnostics() {
    return this.index
      ? {
          eventId: this.index.items[this.raw].id,
          raw: this.raw,
          window: { ...this.window },
          range: this.range && [...this.range],
          rows: this.rows.map((row) => ({
            id: row.id,
            layer: row.layer,
            group: row.group,
            groupStart: row.groupStart,
            groupKind: row.groupKind,
            folded: row.folded,
            members: [...row.members],
          })),
          executions: this.index.executions.chains.map((chain) => ({
            id: chain.id,
            start: chain.start,
            end: chain.end,
            root: chain.root.id,
            kind: chain.kind,
            lane: this.index.executions.laneByChain.get(chain.id),
          })),
          groups: this.index.executions.lanes.length,
          invocationGroups: this.index.executions.lanes.filter((lane) => lane.kind === "invocation")
            .length,
          unassignedObservations: this.index.executions.chains.filter(
            (chain) => chain.kind === "observation",
          ).length,
          points: this.points.map((point) => ({ ...point })),
          transfers: [...this.transfers],
          clock: this.index.axis.ordered ? "time" : "order",
          scroll: this.scroll,
          painted: this.geometry?.drawn,
          flows: this.geometry?.flows,
          source: this.host.dataset.source,
          depth: this.settings.depth,
          layerMode: this.settings.layerMode,
          lifecycles: [...this.index.rows.values()].flatMap((row) =>
            row.slices.map((slice) => ({
              node: row.id,
              start: slice.start,
              end: slice.end,
              duration: slice.duration,
              unfinished: slice.unfinished,
              clippedStart: !!slice.clippedStart,
              entryEventId: slice.context_entry?.id || this.index.items[slice.raw]?.id,
              raw: slice.raw,
              last: slice.last,
              stages: slice.stages?.map((stage) => ({
                state: stage.state,
                label: stage.label,
                start: stage.start,
                end: stage.end,
                registered: !!stage.registered,
              })),
              terminal: slice.terminal,
            })),
          ),
          paintMs: this.paintMs,
          routes: this.geometry?.hits
            .filter((hit) => hit.kind === "flow")
            .map((hit) => ({
              key: hit.key,
              type: hit.flow.type,
              raw: hit.raw,
              row: hit.row,
              fromRow: hit.flow.fromRow,
              toRow: hit.flow.toRow,
              route: hit.route,
            })),
          zooming: !!this.zoomMotion,
          geometry: this.geometry && {
            left: this.geometry.left,
            plot: this.geometry.plot,
            top: this.geometry.top,
          },
        }
      : null;
  }
}
