/** Drag a compact change panel within its own canvas, without moving graph nodes. */
export function enableChangePanelDrag(panel, handle) {
  let gesture = null;
  const inset = 12;
  function move(left, top) {
    const host = panel.offsetParent;
    if (!host) return;
    const tools = host.querySelector(".view-tools")?.offsetHeight || 0;
    const maxLeft = Math.max(inset, host.clientWidth - panel.offsetWidth - inset);
    const maxTop = Math.max(inset, host.clientHeight - tools - panel.offsetHeight - inset);
    panel.style.left = Math.max(inset, Math.min(left, maxLeft)) + "px";
    panel.style.top = Math.max(inset, Math.min(top, maxTop)) + "px";
    panel.style.right = "auto";
    panel.style.bottom = "auto";
  }
  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.target.closest("button")) return;
    gesture = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      left: panel.offsetLeft,
      top: panel.offsetTop,
    };
    handle.setPointerCapture(event.pointerId);
    handle.classList.add("is-dragging");
    event.preventDefault();
    event.stopPropagation();
  });
  handle.addEventListener("pointermove", (event) => {
    if (gesture?.id !== event.pointerId) return;
    move(gesture.left + event.clientX - gesture.x, gesture.top + event.clientY - gesture.y);
  });
  const end = () => {
    gesture = null;
    handle.classList.remove("is-dragging");
  };
  handle.addEventListener("lostpointercapture", end);
  handle.addEventListener("pointerup", end);
  handle.addEventListener("pointercancel", end);
  // A resized canvas, expanded detail list or smaller screen must retain a
  // reachable panel. The default dock stays responsive until the first drag.
  const resize = new ResizeObserver(() => {
    if (panel.style.left && !panel.hidden) move(panel.offsetLeft, panel.offsetTop);
  });
  resize.observe(panel);
  if (panel.parentElement) resize.observe(panel.parentElement);
}
