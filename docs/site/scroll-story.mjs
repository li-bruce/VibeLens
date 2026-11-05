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
    interaction = event.target.closest?.(interactionSelector) ? event.target : null;
    schedule();
  }
  function measure() {
    scheduled = false;
    if (destroyed) return;
    const focus = innerHeight * (innerWidth < 700 ? 0.72 : 0.48);
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
      const bounds = interaction.getBoundingClientRect();
      const owner = elements.findIndex((element) => element.contains(interaction));
      const x = bounds.left + bounds.width / 2;
      const y = bounds.top + bounds.height / 2;
      const visible = document.elementFromPoint(x, y)?.closest(interactionSelector);
      if (owner >= 0 && visible === interaction.closest(interactionSelector)) next = owner;
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
