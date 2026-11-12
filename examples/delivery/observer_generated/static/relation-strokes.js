/** One continuous stroke per relationship in both renderers. A subtle border
 * distinguishes constraints without opening a second, parallel route.
 */
export const strokeProfiles = {
  single: { mode: 0, width: 1 },
  bordered: { mode: 2, width: 1.8, inset: 0.6, tint: 0.28 },
};

export function strokeProfile(style) {
  return strokeProfiles[style.stroke] || strokeProfiles.single;
}

/** Lighten within the same hue for a bordered line's center, not its background. */
export function strokeTint(color, amount = strokeProfiles.bordered.tint) {
  const channel = (shift) => {
    const value = (color >> shift) & 255;
    return Math.round(value + (255 - value) * amount);
  };
  return (channel(16) << 16) | (channel(8) << 8) | channel(0);
}

/** Border and core share the exact path used for picking and playback. */
export function strokePasses(points, style, baseWidth) {
  const profile = strokeProfile(style),
    width = baseWidth * (style.width || 1);
  const result = [{ points, color: style.color, width: width * profile.width }];
  if (profile.mode === 2)
    result.push({
      points,
      color: strokeTint(style.color),
      width: width * profile.width * profile.inset,
    });
  return result;
}
