/** Fit is determined by visible geometry, never a fixed minimum zoom percentage. */
export function fittedScale(width, height, area, maximum = 1.05) {
  return Math.max(
    1e-6,
    Math.min(maximum, area.width / Math.max(1, width), area.height / Math.max(1, height)),
  );
}

/** Keep room to zoom out beyond Fit, including a large expanded rules network. */
export function zoomedScale(current, factor, width, height, area) {
  const minimum = Math.min(0.12, fittedScale(width, height, area) / 4);
  return Math.max(minimum, Math.min(3, current * factor));
}

/** DOM labels and canvas wheel input use the same direction and unit conversion. */
export function wheelFactor(event, height) {
  const pixels = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? height : 1);
  return Math.exp(-Math.max(-1200, Math.min(1200, pixels)) * 0.0015);
}
