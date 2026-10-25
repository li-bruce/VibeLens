import { layers, cleanLayers } from "./graph-layers.js";
import { t } from "./i18n.js";

/** A compact ruler: select names, toggle eyes, drag grips to reorder and gaps to resize. */
export class LayerRuler {
  constructor(host, { change, select }) {
    this.host = host;
    this.change = change;
    this.select = select;
    this.rows = new Map();
    for (const layer of layers) {
      const row = document.createElement("div");
      row.className = "layer-tick";
      row.dataset.layerRow = layer.id;
      row.style.setProperty("--layer-color", "#" + layer.color.toString(16).padStart(6, "0"));
      const grip = document.createElement("button");
      grip.className = "layer-grip";
      grip.textContent = "⠿";
      grip.draggable = true;
      grip.title = t("Drag to reorder; Alt + arrows to move");
      grip.setAttribute("aria-label", t("Reorder {0}", t(layer.label)));
      grip.ondragstart = (event) => event.dataTransfer.setData("text/plain", layer.id);
      row.ondragover = (event) => {
        event.preventDefault();
        row.classList.add("drop-target");
      };
      row.ondragleave = () => row.classList.remove("drop-target");
      row.ondrop = (event) => {
        event.preventDefault();
        row.classList.remove("drop-target");
        const id = event.dataTransfer.getData("text/plain");
        if (!this.config.order.includes(id) || id === layer.id) return;
        const order = this.config.order.filter((item) => item !== id);
        order.splice(order.indexOf(layer.id), 0, id);
        this.change({ ...this.config, order });
      };
      const eye = document.createElement("button");
      eye.className = "layer-eye";
      eye.dataset.layer = layer.id;
      eye.title = t(layer.label);
      eye.draggable = true;
      eye.ondragstart = grip.ondragstart;
      eye.setAttribute("aria-label", t("Toggle {0}", t(layer.label)));
      eye.onclick = () => {
        const visible = this.config.visible.includes(layer.id)
          ? this.config.visible.filter((id) => id !== layer.id)
          : [...this.config.visible, layer.id];
        this.change({ ...this.config, visible });
      };
      const name = document.createElement("button");
      name.className = "layer-select";
      name.textContent = t(layer.label);
      name.onclick = () => this.select(layer.id);
      row.onkeydown = (event) => {
        if (!event.altKey || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        const order = [...this.config.order],
          from = order.indexOf(layer.id);
        const to = Math.max(
          0,
          Math.min(order.length - 1, from + (event.key === "ArrowUp" ? -1 : 1)),
        );
        [order[from], order[to]] = [order[to], order[from]];
        this.change({ ...this.config, order });
        name.focus();
      };
      const gap = document.createElement("div");
      gap.className = "layer-interval";
      gap.dataset.gapAfter = layer.id;
      gap.tabIndex = 0;
      gap.setAttribute("role", "slider");
      gap.setAttribute("aria-label", t("Gap below {0}", t(layer.label)));
      gap.setAttribute("aria-valuemin", "80");
      gap.setAttribute("aria-valuemax", "600");
      gap.innerHTML = '<span class="gap-grip">↕</span><output></output>';
      const resize = (value) =>
        this.change({
          ...this.config,
          gaps: {
            ...this.config.gaps,
            [layer.id]: Math.round(Math.max(80, Math.min(600, value)) / 10) * 10,
          },
        });
      gap.onpointerdown = (event) => {
        if (event.button !== 0 || !this.config.enabled) return;
        event.preventDefault();
        gap.setPointerCapture(event.pointerId);
        this.drag = {
          id: layer.id,
          y: event.clientY,
          value: this.config.gaps[layer.id] ?? this.config.gap,
        };
      };
      gap.onpointermove = (event) => {
        if (this.drag?.id === layer.id) resize(this.drag.value + (event.clientY - this.drag.y) * 8);
      };
      gap.onpointerup = gap.onpointercancel = () => {
        this.drag = null;
      };
      gap.onkeydown = (event) => {
        if (event.altKey) return;
        if (!this.config.enabled || !["ArrowUp", "ArrowDown", "Home"].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        resize(
          event.key === "Home"
            ? this.config.gap
            : (this.config.gaps[layer.id] ?? this.config.gap) +
                (event.key === "ArrowUp" ? -20 : 20),
        );
      };
      row.append(grip, eye, name, gap);
      this.rows.set(layer.id, row);
    }
  }

  render(settings, selected) {
    this.config = cleanLayers(settings);
    const orderKey = this.config.order.join();
    if (orderKey !== this.orderKey) {
      this.host.replaceChildren(...this.config.order.map((id) => this.rows.get(id)));
      this.orderKey = orderKey;
    }
    this.host.dataset.mode = this.config.enabled ? "3D" : "2D";
    for (const [id, row] of this.rows) {
      const visible = this.config.visible.includes(id),
        gap = this.config.gaps[id] ?? this.config.gap;
      row.classList.toggle("is-hidden", !visible);
      row.classList.toggle("is-selected", id === selected);
      const eye = row.querySelector(".layer-eye");
      eye.textContent = visible ? "●" : "○";
      eye.setAttribute("aria-pressed", String(visible));
      row.querySelector(".layer-select").setAttribute("aria-pressed", String(id === selected));
      const interval = row.querySelector(".layer-interval");
      interval.hidden = id === this.config.order.at(-1);
      interval.style.height = `${Math.max(12, Math.min(36, gap / 12))}px`;
      interval.setAttribute("aria-valuenow", String(gap));
      interval.setAttribute("aria-disabled", String(!this.config.enabled));
      interval.querySelector("output").textContent = String(gap);
      interval.title = t("Drag to adjust layer gap") + ` · ${gap}`;
    }
  }
}
