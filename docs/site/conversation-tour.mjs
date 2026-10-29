/** Canned chat examples drive checked plans through the native viewer's controller. */
import { t, locale, onLanguageChange } from "./site-ui.mjs?rev=files-1";

export function mountConversationTour() {
  const section = document.getElementById("conversation-controls");
  if (!section) return;
  const frame = document.getElementById("control-preview");
  const result = document.getElementById("control-result");
  let preset = "business",
    mode = "2d",
    loaded = false,
    ready = false;
  const send = (value) => ready && frame.contentWindow.postMessage(value, location.origin);
  function render() {
    document.getElementById("control-command").textContent = t("controls.command." + preset);
    const description = document.getElementById("control-description");
    if (description) description.textContent = t("controls.description." + preset);
    document.getElementById("control-copy-status").textContent = "";
    frame.title = t("controls.preview");
    for (const button of section.querySelectorAll("[data-control-preset]"))
      button.setAttribute("aria-pressed", String(button.dataset.controlPreset === preset));
    for (const button of section.querySelectorAll("[data-control-mode]"))
      button.setAttribute("aria-pressed", String(button.dataset.controlMode === mode));
  }
  function load() {
    delete section.dataset.applied;
    ready = false;
    loaded = true;
    const url = new URL("./viewer/index.html", import.meta.url);
    url.search = new URLSearchParams({
      case: "1",
      lang: locale(),
      controls: "1",
      vl_session: "c".repeat(32),
      rev: "files-1",
    });
    frame.src = url.href;
    result.textContent = t("controls.loading");
  }
  for (const button of section.querySelectorAll("[data-control-preset]"))
    button.addEventListener("click", () => {
      delete section.dataset.applied;
      preset = button.dataset.controlPreset;
      render();
      result.textContent = t("controls.loading");
      send({ type: "vibelens-controls-select", preset });
    });
  for (const button of section.querySelectorAll("[data-control-mode]"))
    button.addEventListener("click", () => {
      mode = button.dataset.controlMode;
      render();
      send({ type: "vibelens-controls-mode", mode });
    });
  document.getElementById("copy-control").addEventListener("click", async () => {
    const status = document.getElementById("control-copy-status");
    try {
      await navigator.clipboard.writeText(t("controls.command." + preset));
      status.textContent = t("copy.done");
    } catch {
      status.textContent = t("copy.failed");
    }
  });
  addEventListener("message", (event) => {
    if (event.source !== frame.contentWindow || event.origin !== location.origin) return;
    if (event.data?.locale && event.data.locale !== locale()) return;
    if (event.data?.type === "vibelens-controls-ready") {
      ready = true;
      send({ type: "vibelens-controls-select", preset });
      send({ type: "vibelens-controls-mode", mode });
    }
    if (event.data?.type === "vibelens-controls-applied" && event.data.preset === preset) {
      const receipt = event.data.result;
      result.textContent = receipt.status === "applied" ? receipt.view_id : receipt.error;
      if (receipt.status === "applied") {
        result.textContent = t("controls.result." + preset);
        if (event.data.recording)
          result.textContent +=
            " · " +
            event.data.recording.selected_events +
            " / " +
            event.data.recording.total_events +
            " " +
            t("controls.events");
        section.dataset.applied = preset;
        send({ type: "vibelens-controls-fit" });
      }
    }
  });
  const visibility = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting && !loaded) load();
        send({
          type: "vibelens-controls-visibility",
          visible: entry.isIntersecting,
        });
      }
    },
    { rootMargin: "180px 0px" },
  );
  visibility.observe(section);
  // Refit after the preview's responsive dimensions have reached the renderer.
  new ResizeObserver(() => send({ type: "vibelens-controls-fit" })).observe(frame);
  onLanguageChange(() => {
    render();
    if (loaded) load();
  });
  render();
}
