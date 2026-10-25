import { shapedPath } from "./route-shapes.js";
/** Epochs prevent stale endpoints after a drag; routing never blocks the render thread. */
export class RoutingClient {
  constructor(change = () => {}) {
    this.routes = new Map();
    this.stats = {};
    this.epoch = 0;
    this.worker = new Worker(new URL("./routing-worker.js", import.meta.url), { type: "module" });
    this.worker.onmessage = ({ data }) => {
      if (data.epoch !== this.epoch || this.disposed) return;
      for (const [id, path] of data.routes || []) this.routes.set(id, path);
      this.stats = data.stats || { busy: false, error: data.error };
      if (!this.notify)
        this.notify = setTimeout(
          () => {
            this.notify = null;
            change(this.stats);
          },
          data.stats?.busy ? 150 : 0,
        );
    };
    this.worker.onerror = (error) => {
      this.stats = { busy: false, error: error.message };
      change(this.stats);
    };
  }
  request(scene) {
    const key = JSON.stringify(scene);
    if (key === this.key) return;
    this.key = key;
    this.routes.clear();
    // Do not leave old-style paths or blank edges while the worker catches up.
    // These previews are replaced by the current epoch's final paths.
    if (["straight", "curve"].includes(scene.style))
      for (const edge of scene.edges)
        this.routes.set(
          edge.id,
          shapedPath(edge, scene.style, 1, scene.edges.length > 5000 ? 12 : 24),
        );
    this.stats = { busy: true, total: scene.edges.length };
    this.worker.postMessage({ epoch: ++this.epoch, scene });
  }
  dispose() {
    this.disposed = true;
    clearTimeout(this.notify);
    this.worker.terminate();
  }
}
