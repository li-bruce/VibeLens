/** A short product overview; detailed native interactions live in demo.html. */
import { initialize, t, locale, onLanguageChange } from "./site-ui.mjs?rev=files-1";
import { messages } from "./home-messages.mjs?rev=install-20261113";
import { mountLayerExplorer } from "./layer-explorer.mjs?rev=pages-20261112";
function render() {
  document.title =
    locale() === "en"
      ? "VibeLens — See the logic behind your code"
      : "VibeLens · 看懂 AI 写出的程序";
  document.getElementById("install-prompt").textContent = t("install.prompt");
  for (const id of ["copy-status", "install-copy-status"])
    document.getElementById(id).textContent = "";
  for (const image of document.querySelectorAll("[data-product-image]")) {
    const kind = image.dataset.productImage;
    image.src = `images/${kind}-${locale()}.png?rev=pages-20261112`;
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
// Copy the displayed text so the command and current-language prompt stay exact.
for (const [button, content, status] of [
  ["copy-install", "install-command", "install-copy-status"],
  ["copy-prompt", "install-prompt", "copy-status"],
])
  document.getElementById(button).addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(document.getElementById(content).textContent);
      document.getElementById(status).textContent = t("copy.done");
    } catch {
      document.getElementById(status).textContent = t("copy.failed");
    }
  });
onLanguageChange(render);
initialize(messages);
mountLayerExplorer(document.getElementById("layer-explorer"), {
  locale,
  onLanguageChange,
});
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
