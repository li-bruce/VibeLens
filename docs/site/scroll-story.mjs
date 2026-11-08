/** Native scrolling with one active scene. No wheel/touch event interception. */
export function scrollStory({
  scenes,
  onChange = () => {},
  navigation = null,
  interactionSelector = null,
}) {
  const elements = [...scenes],
    reduced = matchMedia("(prefers-reduced-motion: reduce)");
  let active = -1,
    scheduled = false,
    destroyed = false,
    interaction = null;

  // Editing a visible inline panel belongs to its chapter. Native focus scrolling
  // and asynchronously resized content must not replace that chapter mid-click.
  // Scrolling the panel offscreen, clicking elsewhere or explicit navigation
  // releases it; wheel and touch scrolling remain entirely native.
  function rememberInteraction(event) {
    // The embedded graph can focus its own controls after a preview completes.
    // That asynchronous focus is not a reader leaving the parent editor.
    if (event.type === "focusin" && event.target.tagName === "IFRAME") return;
    const element = event.target.closest?.(interactionSelector);
    const owner = element ? elements.findIndex((scene) => scene.contains(element)) : -1;
    // A shared sticky viewer belongs to the chapter that opened its controls.
    // Native iframe focus may scroll the parent without a navigation gesture.
    interaction = element ? { element, owner: owner >= 0 ? owner : active } : null;
    schedule();
  }
  function releaseInteraction() {
    interaction = null;
    schedule();
  }
  function measure() {
    scheduled = false;
    if (destroyed) return;
    // Chapter links use CSS scroll margins to clear the sticky graph. Read below
    // that same inset; a fixed viewport percentage can still fall in the prior
    // chapter after scrollIntoView has correctly positioned the requested one.
    const padding = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    const margin = Math.max(
      0,
      ...elements.map((element) => parseFloat(getComputedStyle(element).scrollMarginTop) || 0),
    );
    const focus = Math.min(innerHeight - 24, Math.max(innerHeight * 0.48, padding + margin + 24));
    let next = 0,
      distance = Infinity;
    elements.forEach((element, index) => {
      const bounds = element.getBoundingClientRect();
      const current =
        bounds.top <= focus && bounds.bottom >= focus
          ? 0
          : Math.min(Math.abs(bounds.top - focus), Math.abs(bounds.bottom - focus));
      if (current < distance) {
        distance = current;
        next = index;
      }
    });
    if (interaction) {
      const { element, owner } = interaction;
      const bounds = element.getBoundingClientRect();
      const x = bounds.left + bounds.width / 2;
      const y = bounds.top + bounds.height / 2;
      const visible = document.elementFromPoint(x, y)?.closest(interactionSelector);
      if (owner >= 0 && visible === element) next = owner;
      else interaction = null;
    }
    if (next !== active) {
      active = next;
      elements.forEach((element, index) => element.classList.toggle("is-active", index === active));
      navigation?.querySelectorAll("[data-chapter]").forEach((link) => {
        if (Number(link.dataset.chapter) === active) link.setAttribute("aria-current", "step");
        else link.removeAttribute("aria-current");
      });
      onChange(active);
    }
  }
  function schedule() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(measure);
    }
  }
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule, { passive: true });
  if (interactionSelector) {
    document.addEventListener("pointerdown", rememberInteraction);
    document.addEventListener("focusin", rememberInteraction);
    // Wheel/touch in the iframe stay local. Deliberate page scrolling releases
    // the chapter even when its sticky viewer is still visible.
    document.addEventListener("wheel", releaseInteraction, { passive: true });
    document.addEventListener("touchmove", releaseInteraction, { passive: true });
  }
  function go(index) {
    interaction = null;
    elements[index]?.scrollIntoView({
      behavior: reduced.matches ? "instant" : "smooth",
      block: "start",
    });
  }
  navigation?.querySelectorAll("[data-chapter]").forEach((link) =>
    link.addEventListener("click", (event) => {
      event.preventDefault();
      go(Number(link.dataset.chapter));
    }),
  );
  measure();
  return {
    go,
    refresh: schedule,
    get active() {
      return active;
    },
    destroy() {
      destroyed = true;
      removeEventListener("scroll", schedule);
      removeEventListener("resize", schedule);
      document.removeEventListener("pointerdown", rememberInteraction);
      document.removeEventListener("focusin", rememberInteraction);
      document.removeEventListener("wheel", releaseInteraction);
      document.removeEventListener("touchmove", releaseInteraction);
    },
  };
}

/** Section reveals settle from their current opacity; reversing scroll stays free. */
export function revealSections(elements) {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) entry.target.classList.toggle("in-view", entry.isIntersecting);
    },
    { rootMargin: "0px 0px -7% 0px", threshold: 0.08 },
  );
  for (const element of elements) {
    element.classList.add("scroll-scene");
    if (reduced.matches) element.classList.add("in-view");
    else observer.observe(element);
  }
  return observer;
}
