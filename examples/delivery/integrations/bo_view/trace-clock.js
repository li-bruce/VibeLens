/** Source time and collector sequence answer different questions.
 * Replay keeps its original ordinals. A transport can deliver an older batch
 * after another producer's newer events without either producer's clock moving
 * backwards. The ruler uses reported source time; it never synchronizes clocks
 * or infers causality between independent producers.
 */
import { traceTime } from "./trace-evidence.js";

function sourceClock(item) {
  const identity = [item.build_id, item.run_id, item.producer_id];
  if (!identity.every((value) => typeof value === "string" && value.length)) return null;
  // stream_id belongs to the merged collector. Entity and attempt identify
  // business work; neither creates a separate producer clock.
  return JSON.stringify([item.project_id || "", ...identity]);
}

/** Validate each reported clock without reordering authoritative replay items. */
export function traceClock(items, until) {
  const dates = items.map((item) => traceTime(item.observed_at));
  const observed = items.flatMap((item, raw) =>
    ["start", "end"].includes(item.kind) ? [] : [{ item, raw, time: dates[raw] }],
  );
  const last = new Map();
  let arrivalInversions = 0;
  let sourceReversed = false;
  let unqualified = false;
  for (let index = 0; index < observed.length; index++) {
    const { item, time } = observed[index];
    if (
      index &&
      time !== null &&
      observed[index - 1].time !== null &&
      time < observed[index - 1].time
    )
      arrivalInversions++;
    const identity = sourceClock(item);
    if (identity === null) unqualified = true;
    if (
      last.has(identity) &&
      time !== null &&
      last.get(identity) !== null &&
      time < last.get(identity)
    )
      sourceReversed = true;
    last.set(identity, time);
  }
  const invalid =
    dates.some((value) => value === null) ||
    sourceReversed ||
    (arrivalInversions > 0 && unqualified);
  const visual = [...dates];
  let boundaryAdjusted = false;
  if (!invalid && observed.length) {
    const first = observed.reduce((minimum, row) => Math.min(minimum, row.time), Infinity);
    const final = observed.reduce((maximum, row) => Math.max(maximum, row.time), -Infinity);
    if (items[0].kind === "start" && dates[0] > first) {
      visual[0] = first;
      boundaryAdjusted = true;
    }
    if (items.at(-1).kind === "end" && dates.at(-1) < final) {
      visual[visual.length - 1] = final;
      boundaryAdjusted = true;
    }
  }
  const minimum = visual.reduce(
    (min, value) => (value === null ? min : Math.min(min, value)),
    Infinity,
  );
  const origin = Number.isFinite(minimum) ? minimum : 0;
  const times = invalid ? items.map((_, index) => index) : visual.map((time) => time - origin);
  const tail = traceTime(until);
  return {
    dates,
    times,
    // Existing consumers use ordered to select the time ruler. It means each
    // source clock is ordered, not that batches arrived in timestamp order.
    ordered: !invalid,
    arrivalOrdered: arrivalInversions === 0,
    arrivalInversions,
    sourceReversed,
    boundaryAdjusted,
    total: times.reduce(
      (maximum, time) => Math.max(maximum, time),
      tail !== null && !invalid ? Math.max(1, tail - origin) : 1,
    ),
    origin,
  };
}
