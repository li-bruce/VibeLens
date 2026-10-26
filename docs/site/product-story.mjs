/** Scroll changes the depth of one connected visual; manual tabs stay available. */
import { scrollStory } from "./scroll-story.mjs?rev=story-3";

export function mountProductStory(selectView) {
  const stages = [...document.querySelectorAll("[data-depth-view]")];
  const story = scrollStory({
    scenes: stages,
    onChange(index) {
      document.getElementById("explore").dataset.depth = stages[index].dataset.depthView;
      selectView(stages[index].dataset.depthView);
    },
  });
  let scheduled = false;
  function progress() {
    scheduled = false;
    const distance = document.documentElement.scrollHeight - innerHeight;
    document.documentElement.style.setProperty(
      "--page-progress",
      String(scrollY / Math.max(1, distance)),
    );
  }
  function requestProgress() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(progress);
  }
  addEventListener("scroll", requestProgress, { passive: true });
  addEventListener("resize", requestProgress, { passive: true });
  progress();
  return story;
}
