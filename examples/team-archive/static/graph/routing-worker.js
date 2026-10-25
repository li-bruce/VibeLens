import { AvoidLib } from "./routing-libavoid.vendor.js";
import { routeScene } from "./routing-engine.js";
let epoch = 0,
  pending,
  running = false;
const cache = new Map();
const ready = AvoidLib.load(new URL("./libavoid.wasm", import.meta.url).href);
onmessage = ({ data }) => {
  epoch = data.epoch;
  pending = data;
  if (!running) drain();
};
async function drain() {
  running = true;
  while (pending) {
    const request = pending;
    pending = null;
    try {
      await ready;
      await routeScene(
        request.scene,
        AvoidLib.getInstance(),
        cache,
        (routes, stats) => {
          if (request.epoch === epoch) postMessage({ epoch, routes: [...routes], stats });
        },
        () => request.epoch !== epoch,
      );
    } catch (error) {
      if (request.epoch === epoch) postMessage({ epoch, error: String(error) });
    }
  }
  running = false;
}
