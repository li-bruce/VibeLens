/** Selection has one identity set in 2D and 3D. Screen rectangles never mutate
 * the graph; moving selected roots moves each contained subtree exactly once.
 */
export function selectionRoots(ids, all) {
  const selected = new Set(ids);
  return [...selected].filter((id) => {
    const seen = new Set([id]);
    let parent = all.get(id)?.parent;
    while (parent && !seen.has(parent)) {
      if (selected.has(parent)) return false;
      seen.add(parent);
      parent = all.get(parent)?.parent;
    }
    return true;
  });
}
export function rectangleSelection(rect, points) {
  return points
    .filter(
      (point) =>
        point.visible !== false &&
        point.x >= rect.x &&
        point.x <= rect.x + rect.w &&
        point.y >= rect.y &&
        point.y <= rect.y + rect.h,
    )
    .map((point) => point.id);
}

/** One screen-space marquee overlay for both rendering engines. */
export class SelectionMarquee {
  constructor(host) {
    this.host = host;
    this.element = document.createElement("div");
    this.element.className = "selection-marquee";
    this.element.hidden = true;
    host.append(this.element);
  }
  start(event) {
    const bounds = this.host.getBoundingClientRect();
    this.active = {
      pointerId: event.pointerId,
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
      additive: event.ctrlKey || event.metaKey,
    };
    this.move(event);
  }
  move(event) {
    const start = this.active;
    if (!start || start.pointerId !== event.pointerId) return null;
    const bounds = this.host.getBoundingClientRect(),
      x = event.clientX - bounds.left,
      y = event.clientY - bounds.top;
    this.rect = {
      x: Math.min(x, start.x),
      y: Math.min(y, start.y),
      w: Math.abs(x - start.x),
      h: Math.abs(y - start.y),
    };
    const rect = this.rect;
    Object.assign(this.element.style, {
      left: rect.x + "px",
      top: rect.y + "px",
      width: rect.w + "px",
      height: rect.h + "px",
    });
    this.element.hidden = false;
    return rect;
  }
  end(event) {
    if (!this.active || this.active.pointerId !== event.pointerId) return null;
    const result = { rect: this.rect, additive: this.active.additive };
    this.active = null;
    this.element.hidden = true;
    return result;
  }
}
