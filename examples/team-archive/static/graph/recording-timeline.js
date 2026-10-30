/** Execution timeline dock. The viewer owns replay; this component only requests seeks. */
import { t } from "./i18n.js";
import { eventLabel } from "./recording.js";
import { buildTraceIndex, traceRows, tracePoints } from "./trace-index.js";
import { boundWindow, zoomWindow, panWindow, nearestEvent } from "./trace-viewport.js";
import { paintTrace, traceGeometry, timeLabel } from "./trace-paint.js";
import { layers } from "./graph-layers.js";
import { iconButton } from "./controls.js";
import { boDisplayValue } from "./replay-steps.js";

export function cleanTimeline(value) {
  return {
    visible: value?.visible !== false,
    height: Number.isFinite(value?.height) ? Math.max(180, Math.min(500, value.height)) : 280,
    scope: value?.scope === "all" ? "all" : "view",
    expanded: Array.isArray(value?.expanded)
      ? value.expanded.filter((id) => layers.some((layer) => layer.id === id))
      : [],
    follow: value?.follow !== false,
  };
}

/** Own listeners, indexes and pending frames so leaving replay releases the whole dock. */
export class RecordingTimeline {
  constructor(host, { onSeek, onPause, onRange, onSettings }) {
    this.host = host;
    this.callbacks = { onSeek, onPause, onRange, onSettings };
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
    this.host.innerHTML = `
      <div class="trace-resize" role="separator" tabindex="0" aria-orientation="horizontal"></div>
      <div class="trace-toolbar">
        <strong></strong><span class="trace-key">━ · ◆ · ◇</span><select class="trace-scope"></select>
        <button class="trace-fit"></button><button class="trace-zoom-in"></button><button class="trace-zoom-out"></button>
        <label class="trace-follow"><input type="checkbox" /><span></span></label>
        <button class="trace-loop"></button><button class="trace-clear"></button>
        <span class="trace-health" role="status"></span><button class="trace-close"></button>
      </div>
      <div class="trace-body"><canvas tabindex="0" role="slider" aria-valuemin="0"></canvas>
        <div class="trace-tooltip" hidden></div><pre class="trace-payload" hidden tabindex="0"></pre></div>
      <div class="trace-detail" aria-live="polite"><span class="trace-selected"></span><span class="trace-values"></span><button class="trace-inspect" aria-expanded="false"></button><button class="trace-locate"></button></div>`;
    const find = (name) => host.querySelector(".trace-" + name);
    this.find = find;
    this.canvas = host.querySelector("canvas");
    find("toolbar").querySelector("strong").textContent = t("Timeline");
    find("key").title = t("Call duration · Event · Source mapping");
    find("scope").replaceChildren(
      new Option(t("Current view"), "view"),
      new Option(t("Recorded nodes"), "all"),
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
    order,
    plan,
    raw,
    transfers,
    settings,
    playing,
    selection,
  }) {
    const prior = this.settings;
    this.model = model;
    this.all = all;
    this.preferences = preferences;
    this.settings = cleanTimeline(settings);
    this.raw = raw;
    this.transfers = [...transfers];
    this.plan = plan;
    const indexKey = JSON.stringify([
      recording.id,
      [...all.keys()],
      edges.filter((edge) => edge.code_relation).map((edge) => [edge.id, edge.from, edge.to]),
    ]);
    if (indexKey !== this.indexKey) {
      this.indexKey = indexKey;
      this.index = buildTraceIndex(recording, items, all, edges);
      this.window = { start: 0, end: this.index.axis.total };
      this.range = null;
      this.scroll = 0;
      this.rowKey = null;
    }
    const rowKey = JSON.stringify([
      this.indexKey,
      this.settings.scope,
      this.settings.expanded,
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
        expanded: this.settings.expanded,
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
    this.find("follow").querySelector("input").checked = this.settings.follow;
    const issues = [...(recording.gaps || [])];
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
        ? timeLabel(slice.duration)
        : slice?.unfinished
          ? t("Open call")
          : "";
    const title = `${eventLabel(event, this.model)}${duration ? " · " + duration : ""}`;
    this.find("selected").textContent = title;
    this.find("selected").title = [
      title,
      event.id,
      event.entity,
      event.attempt,
      event.observed_at,
      slice?.ambiguous ? t("Overlapping call ID") : "",
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
        changes,
        graph_transfers: this.transfers,
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
      Math.min(Math.max(0, this.rows.length * traceGeometry.row - height), this.scroll),
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
      const started = performance.now();
      this.geometry = paintTrace(this.canvas, {
        ...this,
        width,
        height,
        expanded: this.settings.expanded,
      });
      this.paintMs = performance.now() - started;
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
      if (pending && (pending.raw !== this.raw || pending.locate))
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
    const p = this.point(event),
      g = this.geometry;
    this.find("tooltip").hidden = true;
    this.canvas.setPointerCapture(event.pointerId);
    if (p.x < g.left) {
      const hit = this.geometry.hits.findLast(
        (hit) =>
          p.x >= hit.x && p.x <= hit.x + hit.width && p.y >= hit.y && p.y <= hit.y + hit.height,
      );
      if (hit?.kind === "layer") {
        const id = hit.row.slice(6);
        this.configure({
          expanded: this.settings.expanded.includes(id)
            ? this.settings.expanded.filter((key) => key !== id)
            : [...this.settings.expanded, id],
        });
      } else if (hit?.kind === "node")
        this.requestSeek(
          nearestEvent(
            this.index.rows
              .get(hit.row)
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
    } else if (p.y < g.top) {
      this.drag = { kind: "seek" };
      this.seekTime(this.time(p.x));
    } else {
      const hit = g.hits.findLast(
        (hit) =>
          ["mark", "slice"].includes(hit.kind) &&
          p.x >= hit.x &&
          p.x <= hit.x + hit.width &&
          p.y >= hit.y &&
          p.y <= hit.y + hit.height,
      );
      if (hit && this.allowed.has(hit.raw)) {
        this.requestSeek(hit.raw, event.detail === 2);
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
    const hit = this.geometry.hits.findLast(
      (hit) =>
        hit.raw !== undefined &&
        point.x >= hit.x &&
        point.x <= hit.x + hit.width &&
        point.y >= hit.y &&
        point.y <= hit.y + hit.height,
    );
    const tooltip = this.find("tooltip");
    if (!hit) {
      tooltip.hidden = true;
      return;
    }
    const event = this.index.items[hit.raw],
      mark = this.index.rows.get(hit.row)?.marks.find((item) => item.raw === hit.raw);
    tooltip.textContent = [
      eventLabel(event, this.model),
      event.observed_at,
      event.entity,
      mark?.projected ? t("Source mapping") : "",
    ]
      .filter(Boolean)
      .join(" · ");
    tooltip.hidden = false;
    tooltip.style.left = `${Math.max(8, Math.min(this.canvas.clientWidth - Math.min(480, this.canvas.clientWidth - 16), point.x + 10))}px`;
    tooltip.style.top = `${Math.max(0, point.y - 28)}px`;
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
    if (anchor === null)
      anchor =
        (this.index.axis.times[this.raw] - this.window.start) /
        (this.window.end - this.window.start);
    this.window = zoomWindow(this.window, factor, anchor, this.index.axis.total);
    this.schedule();
  }
  fit() {
    if (this.index) {
      this.window = { start: 0, end: this.index.axis.total };
      this.schedule();
    }
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
    cancelAnimationFrame(this.seekFrame);
    cancelAnimationFrame(this.drawFrame);
    this.seekFrame = this.drawFrame = null;
    this.pendingSeek = this.drag = this.index = null;
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
          rows: this.rows.map((row) => ({ id: row.id, layer: row.layer })),
          points: this.points.map((point) => ({ ...point })),
          transfers: [...this.transfers],
          clock: this.index.axis.ordered ? "time" : "order",
          scroll: this.scroll,
          painted: this.geometry?.drawn,
          paintMs: this.paintMs,
          geometry: this.geometry && {
            left: this.geometry.left,
            plot: this.geometry.plot,
            top: this.geometry.top,
          },
        }
      : null;
  }
}
