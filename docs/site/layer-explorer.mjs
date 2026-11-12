/** Accessible layer explanations stay useful before WebGL loads or if it fails. */
import { layerContent } from "./layer-content.mjs?rev=0.14.0";

export function mountLayerExplorer(host, { locale, onLanguageChange }) {
  if (!host) return;
  let selected = 0,
    scene,
    loading = false;
  const nav = host.querySelector("[data-layer-tabs]");
  const status = host.querySelector("[data-layer-status]");
  const buttons = layerContent.map((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.role = "tab";
    button.id = "layer-tab-" + item.id;
    button.dataset.layer = item.id;
    button.style.setProperty("--layer-color", "#" + item.color.toString(16).padStart(6, "0"));
    button.setAttribute("aria-controls", "layer-description");
    button.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span><strong></strong>`;
    button.onclick = () => select(index);
    button.onkeydown = (event) => {
      const keys = {
        ArrowDown: (index + 1) % layerContent.length,
        ArrowRight: (index + 1) % layerContent.length,
        ArrowUp: (index + layerContent.length - 1) % layerContent.length,
        ArrowLeft: (index + layerContent.length - 1) % layerContent.length,
        Home: 0,
        End: layerContent.length - 1,
      };
      if (keys[event.key] !== undefined) {
        event.preventDefault();
        select(keys[event.key]);
        buttons[selected].focus();
      }
    };
    nav.append(button);
    return button;
  });
  function select(index) {
    selected = index;
    host.dataset.selectedLayer = layerContent[index].id;
    render();
    scene?.select(index, locale() === "zh-CN" ? 1 : 0);
  }
  function render() {
    const language = locale() === "zh-CN" ? 1 : 0,
      item = layerContent[selected];
    status.textContent =
      host.dataset.webgl === "unavailable"
        ? language
          ? "选择图层，查看内容"
          : "Select a layer to explore"
        : language
          ? "正在准备图层…"
          : "Preparing layers…";
    nav.setAttribute("aria-label", language ? "图的层级" : "Graph layers");
    buttons.forEach((button, index) => {
      button.querySelector("strong").textContent = layerContent[index].name[language];
      button.setAttribute("aria-selected", String(index === selected));
      button.tabIndex = index === selected ? 0 : -1;
    });
    const panel = host.querySelector("[data-layer-description]");
    panel.setAttribute("aria-labelledby", buttons[selected].id);
    panel.querySelector("[data-layer-group]").textContent = item.group[language];
    panel.querySelector("h3").textContent = item.question[language];
    panel.querySelector("[data-layer-body]").textContent = item.body[language];
    panel.querySelector("[data-layer-examples]").textContent =
      item.examples[language].join("  ·  ");
    host.querySelector("[data-layer-hint]").textContent = language
      ? "拖动旋转 · 点击选层"
      : "Drag to orbit · Select a layer";
    const reset = host.querySelector("[data-layer-reset]");
    reset.textContent = language ? "复位视角 ↗" : "Reset view ↗";
    reset.onclick = () => scene?.reset();
    scene?.select(selected, language);
  }
  const observer = new IntersectionObserver(
    async ([entry]) => {
      scene?.visible(entry.isIntersecting);
      if (!entry.isIntersecting || loading) return;
      loading = true;
      try {
        const { layerScene } = await import("./layer-scene.mjs?rev=0.14.0");
        scene = layerScene(host.querySelector("[data-layer-stage]"), layerContent, select);
        scene.select(selected, locale() === "zh-CN" ? 1 : 0);
        scene.visible(entry.isIntersecting);
        host.dataset.webgl = "ready";
        status.hidden = true;
      } catch {
        // The explanatory tabs are the fallback; never leave empty instructions.
        host.dataset.webgl = "unavailable";
        host.querySelector("[data-layer-hint]").hidden = true;
        host.querySelector("[data-layer-reset]").hidden = true;
        render();
      }
    },
    { threshold: 0.08 },
  );
  observer.observe(host);
  onLanguageChange(render);
  select(0);
}
