import { clusterUnits } from "./cluster-layout.js";
onmessage = ({ data }) => {
  try {
    postMessage({ positions: clusterUnits(data.units, data.edges, data.seeds) });
  } catch (error) {
    postMessage({ error: String(error) });
  }
};
