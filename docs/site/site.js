/** A short product overview; detailed native interactions live in demo.html. */
import { initialize, t, locale, onLanguageChange } from "./site-ui.mjs?rev=clarity-1";
import { messages } from "./home-messages.mjs?rev=brand-1";
import { revealSections } from "./scroll-story.mjs?rev=story-3";
import { mountConversationTour } from "./conversation-tour.mjs?rev=clarity-1";
function render() {
  document.title =
    locale() === "en" ? "VibeLens — See how your code works" : "VibeLens · 看清 AI 写出的程序";
  document.getElementById("install-prompt").textContent = t("install.prompt");
  for (const image of document.querySelectorAll("[data-product-image]")) {
    const kind = image.dataset.productImage;
    image.src = `images/${kind}-${locale()}.png`;
    image.alt = t("home.image." + kind);
  }
}
for (const button of document.querySelectorAll("[data-capture]"))
  button.addEventListener("click", () => {
    document.getElementById("hero-screenshot").dataset.productImage = button.dataset.capture;
    for (const item of document.querySelectorAll("[data-capture]"))
      item.setAttribute("aria-pressed", String(item === button));
    render();
  });
document.getElementById("copy-prompt").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(t("install.prompt"));
    document.getElementById("copy-status").textContent = t("copy.done");
  } catch {
    document.getElementById("copy-status").textContent = t("copy.failed");
  }
});
onLanguageChange(render);
initialize(messages);
mountConversationTour();
revealSections(document.querySelectorAll("main > section"));
// The progress line follows native scrolling without intercepting input.
let scheduled = false;
function progress() {
  scheduled = false;
  document.documentElement.style.setProperty(
    "--page-progress",
    String(scrollY / Math.max(1, document.documentElement.scrollHeight - innerHeight)),
  );
}
addEventListener(
  "scroll",
  () => {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(progress);
    }
  },
  { passive: true },
);
addEventListener("resize", progress, { passive: true });
progress();
