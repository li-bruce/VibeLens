/** Personal playback choices refer to recorded event IDs. Raw events stay immutable. */
export function cleanReplaySelection(value, items) {
  const ids = new Set(items.map((item) => item.id));
  return {
    skipped: [...new Set(Array.isArray(value?.skipped) ? value.skipped : [])].filter((id) =>
      ids.has(id),
    ),
    loop: value?.loop === true,
    from: ids.has(value?.from) ? value.from : items[0]?.id,
    to: ids.has(value?.to) ? value.to : items.at(-1)?.id,
  };
}

export function selectedReplayPlan(items, plan, value) {
  const settings = cleanReplaySelection(value, items),
    skipped = new Set(settings.skipped);
  const a = items.findIndex((item) => item.id === settings.from);
  const b = items.findIndex((item) => item.id === settings.to);
  return plan.filter(
    (raw) =>
      !skipped.has(items[raw]?.id) &&
      (!settings.loop || (raw >= Math.min(a, b) && raw <= Math.max(a, b))),
  );
}

export function nextReplayIndex(plan, current, loop) {
  return plan.find((raw) => raw > current) ?? (loop ? plan[0] : undefined);
}
