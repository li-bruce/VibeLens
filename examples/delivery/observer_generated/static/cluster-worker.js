import { clusterUnits } from "./cluster-layout.js";
onmessage = ({ data }) => {
  try {
    postMessage({ positions: clusterUnits(data.units, data.edges) });
  } catch (error) {
    postMessage({ error: String(error) });
  }
};
