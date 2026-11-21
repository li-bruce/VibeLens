/** Select a static recording transport; both load the exact canonical viewer. */
const params = new URLSearchParams(location.search);
if (params.has("forest")) {
  const chinese = params.get("lang") === "zh-CN";
  const loading = document.createElement("div");
  loading.id = "forest-viewer-loading";
  loading.setAttribute("role", "status");
  loading.style.cssText =
    "position:fixed;inset:0;z-index:10000;display:grid;place-content:center;background:#f7f9fb;color:#47616c;font:15px system-ui;gap:16px";
  loading.textContent = chinese ? "正在打开完整录制图…" : "Opening the full recorded graph…";
  document.body.append(loading);
  try {
    await import("./forest-viewer.mjs");
    const deadline = Date.now() + 60000;
    while (
      !window.graphDebug?.graph ||
      window.graphDebug.layoutBusy ||
      window.graphDebug.geometryBusy
    ) {
      if (Date.now() > deadline)
        throw Error(chinese ? "图布局超时，请重试" : "Graph layout timed out; please retry");
      await new Promise((resolve) => setTimeout(resolve, 40));
    }
    loading.remove();
  } catch (error) {
    loading.textContent =
      (chinese ? "录制图暂时无法载入：" : "The recording could not be opened: ") + error.message;
    const retry = document.createElement("button");
    retry.textContent = chinese ? "重试" : "Retry";
    retry.onclick = () => location.reload();
    loading.append(retry);
  }
} else await import("./case-viewer.mjs");
