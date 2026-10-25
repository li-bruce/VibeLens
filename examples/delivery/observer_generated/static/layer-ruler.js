import { layers, cleanLayers } from "./graph-layers.js";
import { t } from "./i18n.js";

/** Event-driven Canvas2D layer navigator. Plane tokens toggle visibility,
 * labels select, and dragging reorders. No extra GPU context or per-frame work.
 * The parallel hidden action tree preserves keyboard/screen-reader access.
 */
export class LayerRuler {
  constructor(host, { change, select }) {
    this.host = host;
    this.change = change;
    this.select = select;
    this.focus = 0;
    this.canvas = document.createElement("canvas");
    this.canvas.tabIndex = 0;
    this.canvas.setAttribute("aria-label", t("Graph layers"));
    this.canvas.setAttribute("role", "group");
    this.canvas.setAttribute("aria-describedby", "layer-keyboard-help");
    const actions = document.createElement("div");
    actions.className = "layer-accessibility";
    const help = document.createElement("span");
    help.id = "layer-keyboard-help";
    help.textContent = t("Arrows select; Space toggles; Alt + arrows reorders");
    actions.append(help);
    for (const id of ["layers-toggle", "layers-all"]) actions.append(document.getElementById(id));
    this.rows = new Map();
    for (const layer of layers) {
      const row = document.createElement("div");
      row.dataset.layerRow = layer.id;
      const eye = document.createElement("button");
      eye.dataset.layer = layer.id;
      eye.setAttribute("aria-label", t("Toggle {0}", t(layer.label)));
      eye.onclick = () => this.toggle(layer.id);
      const name = document.createElement("button");
      name.className = "layer-select";
      name.textContent = t(layer.label);
      name.onclick = () => this.select(layer.id);
      row.onkeydown = (e) => {
        if (e.altKey && ["ArrowUp", "ArrowDown"].includes(e.key)) {
          e.preventDefault();
          e.stopPropagation();
          this.reorder(layer.id, e.key === "ArrowUp" ? -1 : 1);
        }
      };
      row.append(eye, name);
      actions.append(row);
      this.rows.set(layer.id, row);
    }
    host.replaceChildren(this.canvas, actions);
    this.canvas.onpointerdown = (e) => {
      if (e.button !== 0) return;
      const hit = this.hit(e);
      if (!hit) return;
      e.preventDefault();
      this.canvas.focus();
      this.canvas.setPointerCapture(e.pointerId);
      this.drag = { ...hit, startY: e.clientY, moved: false };
      if (hit.id) {
        this.focus = this.config.order.indexOf(hit.id);
        this.select(hit.id);
      }
    };
    this.canvas.onpointermove = (e) => {
      const hit = this.hit(e);
      this.canvas.style.cursor = hit?.id ? "grab" : "pointer";
      this.canvas.title = hit?.id
        ? t(layers.find((l) => l.id === hit.id).label)
        : t(hit?.action === "all" ? "Show all layers" : "Layers");
      if (!this.drag?.id) return;
      if (Math.abs(e.clientY - this.drag.startY) > 5) this.drag.moved = true;
      this.drop = hit?.id;
      this.draw();
    };
    this.canvas.onpointerup = (e) => {
      const drag = this.drag;
      this.drag = null;
      this.drop = null;
      if (!drag) return;
      if (drag.moved && drag.id) {
        const target = this.hit(e)?.id;
        if (target && target !== drag.id) {
          const order = this.config.order.filter((id) => id !== drag.id);
          order.splice(this.config.order.indexOf(target), 0, drag.id);
          this.change({ ...this.config, order });
        }
      } else if (drag.action === "collapse") document.getElementById("layers-toggle").click();
      else if (drag.action === "all") document.getElementById("layers-all").click();
      else if (drag.toggle) this.toggle(drag.id);
      this.draw();
    };
    this.canvas.onpointercancel = () => {
      this.drag = null;
      this.drop = null;
      this.draw();
    };
    this.canvas.onkeydown = (e) => {
      const id = this.config.order[this.focus];
      if (["ArrowUp", "ArrowDown"].includes(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        const delta = e.key === "ArrowUp" ? -1 : 1;
        if (e.altKey) this.reorder(id, delta);
        else {
          this.focus = Math.max(0, Math.min(layers.length - 1, this.focus + delta));
          this.select(this.config.order[this.focus]);
        }
        this.draw();
      } else if (e.key === " ") {
        e.preventDefault();
        this.toggle(id);
      } else if (e.key === "Enter") this.select(id);
    };
    this.canvas.onfocus = () => this.draw();
    this.canvas.onblur = () => this.draw();
  }
  toggle(id) {
    const visible = this.config.visible.includes(id)
      ? this.config.visible.filter((n) => n !== id)
      : [...this.config.visible, id];
    this.change({ ...this.config, visible });
  }
  reorder(id, delta) {
    const order = [...this.config.order],
      i = order.indexOf(id),
      j = Math.max(0, Math.min(order.length - 1, i + delta));
    [order[i], order[j]] = [order[j], order[i]];
    this.focus = j;
    this.change({ ...this.config, order });
  }
  hit(event) {
    const rect = this.canvas.getBoundingClientRect(),
      x = event.clientX - rect.left,
      y = event.clientY - rect.top;
    if (y < 34) return { action: x < this.width / 2 ? "collapse" : "all" };
    const index = Math.floor((y - 40) / 34),
      id = this.config.order[index];
    return id && y >= 40 ? { id, toggle: this.config.compact || x < 36 } : null;
  }
  render(settings, selected) {
    this.config = cleanLayers(settings);
    this.selected = selected;
    this.host.dataset.mode = this.config.enabled ? "3D" : "2D";
    for (const [id, row] of this.rows) {
      row
        .querySelector("[data-layer]")
        .setAttribute("aria-pressed", String(this.config.visible.includes(id)));
      row.querySelector(".layer-select").setAttribute("aria-pressed", String(id === selected));
    }
    this.draw();
  }
  draw() {
    if (!this.config) return;
    const ctx = this.canvas.getContext("2d"),
      ratio = Math.min(devicePixelRatio || 1, 2);
    ctx.font = "11px Segoe UI, Microsoft YaHei, sans-serif";
    this.width = this.config.compact
      ? 48
      : Math.max(164, ...layers.map((l) => ctx.measureText(t(l.label)).width + 68));
    const height = 40 + layers.length * 34;
    this.canvas.width = this.width * ratio;
    this.canvas.height = height * ratio;
    this.canvas.style.width = this.width + "px";
    this.canvas.style.height = height + "px";
    ctx.scale(ratio, ratio);
    ctx.font = "11px Segoe UI, Microsoft YaHei, sans-serif";
    ctx.fillStyle = "#ffffffed";
    ctx.strokeStyle = "#dce5ec";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(0.5, 0.5, this.width - 1, height - 1, 12);
    ctx.fill();
    ctx.stroke();
    ctx.strokeStyle = "#668196";
    ctx.lineWidth = 1.5;
    const cx = this.config.compact ? 13 : 20;
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.moveTo(cx - 5, 12 + i * 4);
      ctx.lineTo(cx + 5, 12 + i * 4);
      ctx.stroke();
    }
    ctx.fillStyle = "#668196";
    ctx.textAlign = "right";
    ctx.fillText("◎", this.width - 12, 22);
    if (!this.config.compact) {
      ctx.textAlign = "left";
      ctx.fillText(t("Layers"), 38, 22);
    }
    this.config.order.forEach((id, i) => {
      const layer = layers.find((l) => l.id === id),
        y = 40 + i * 34,
        visible = this.config.visible.includes(id);
      const color = "#" + layer.color.toString(16).padStart(6, "0");
      if (id === this.selected || id === this.drop) {
        ctx.fillStyle = "#eaf1f8";
        ctx.beginPath();
        ctx.roundRect(4, y, this.width - 8, 30, 6);
        ctx.fill();
      }
      ctx.globalAlpha = visible ? 1 : 0.3;
      ctx.beginPath();
      ctx.moveTo(11, y + 15);
      ctx.lineTo(22, y + 9);
      ctx.lineTo(33, y + 15);
      ctx.lineTo(22, y + 21);
      ctx.closePath();
      ctx.fillStyle = color + "33";
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.stroke();
      if (visible) {
        ctx.beginPath();
        ctx.moveTo(11, y + 20);
        ctx.lineTo(22, y + 26);
        ctx.lineTo(33, y + 20);
        ctx.stroke();
      }
      if (!this.config.compact) {
        ctx.fillStyle = "#354d5e";
        ctx.textAlign = "left";
        ctx.fillText(t(layer.label), 43, y + 20);
      }
      ctx.globalAlpha = 1;
      if (document.activeElement === this.canvas && i === this.focus) {
        ctx.strokeStyle = "#7194b4";
        ctx.setLineDash([2, 3]);
        ctx.strokeRect(5, y + 2, this.width - 10, 27);
        ctx.setLineDash([]);
      }
    });
  }
}
