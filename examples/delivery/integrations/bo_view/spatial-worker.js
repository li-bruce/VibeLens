import { solveSpatial } from "./spatial-layout.js";

// The caller discards older epochs so a late layout cannot move a newer graph.
self.onmessage = ({ data }) => {
  try {
    const started = performance.now();
    self.postMessage({
      epoch: data.epoch,
      positions: solveSpatial(data),
      elapsed: performance.now() - started,
    });
  } catch (error) {
    self.postMessage({ epoch: data.epoch, error: String(error.message) });
  }
};
