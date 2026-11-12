/** Guided actions around the native viewer. Recording here replays captured evidence. */
import { locale } from "./site-ui.mjs?rev=files-1";
import { depthGuide } from "./case-guide-model.mjs?rev=guided-1";
const copy = (pair) => pair[locale() === "en" ? 0 : 1];
function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text) node.textContent = text;
  return node;
}

export function walkthroughGuide({ send, onCaptureChange, onDepthChange }) {
  let current = "foundation";
  const sessions = new Map();
  const panels = new Map();
  const details = new Map();

  function session(id = current) {
    if (!sessions.has(id)) sessions.set(id, { phase: "idle", actions: new Set(), pending: null });
    return sessions.get(id);
  }
  function refresh() {
    for (const [id, panel] of panels) {
      const state = session(id);
      const active = state.phase === "recording";
      panel.dataset.capture = state.phase;
      panel.querySelector("button").textContent = copy(
        active ? ["■ Stop recording", "■ 停止记录"] : ["● Try recording", "● 体验录制"],
      );
      panel.querySelector(".capture-status").textContent = copy(
        active && state.pending
          ? ["Opening the recorded action…", "正在定位记录中的操作…"]
          : active
            ? [
                "Recording · use the three application actions below",
                "记录中 · 依次操作下方应用的三个按钮",
              ]
            : state.phase === "recorded"
              ? [
                  "Stopped · replay or drag the time cursor in VibeLens",
                  "已停止 · 在 VibeLens 播放或拖动时间位置",
                ]
              : ["Choose business + state, then begin", "观察范围：业务与状态，点击开始"],
      );
      panel.querySelector(".capture-count").textContent = copy([
        `${state.actions.size} / 3 application actions visited`,
        `已查看 ${state.actions.size} / 3 个业务操作`,
      ]);
      panel.querySelector(".capture-result").hidden = state.actions.size < 3;
    }
    const recording = ["run", "verify"].includes(current);
    onCaptureChange({
      enabled: recording && session().phase === "recording" && !session().pending,
      replay: recording && session().phase === "recorded",
      phase: recording ? session().phase : "idle",
    });
  }

  function mount(section, chapter) {
    if (["run", "verify"].includes(chapter.id)) {
      const panel = element("div", "capture-guide");
      const action = element("button", "capture-button");
      action.type = "button";
      action.dataset.captureAction = chapter.id;
      action.onclick = () => {
        const state = session(chapter.id);
        if (state.phase === "recording") {
          state.phase = "recorded";
          state.pending = null;
          send({ action: "pause" });
        } else {
          state.phase = "recording";
          state.actions.clear();
          state.pending = "overview";
          send({ action: "overview" });
        }
        refresh();
      };
      const result = element(
        "p",
        "capture-result",
        copy(
          chapter.id === "run"
            ? [
                "The recipient still downloaded after revocation. Pause here and investigate the unchanged state.",
                "取消后，对方仍下载成功。先停在这里，检查为什么状态没有改变。",
              ]
            : [
                "The recipient is denied after revocation. Compare this with the first run.",
                "取消后，接收者的访问被拒绝。对照第一次运行，检查状态与结果。",
              ],
        ),
      );
      result.setAttribute("role", "status");
      panel.append(
        action,
        element("p", "capture-status"),
        element("span", "capture-count"),
        result,
      );
      panels.set(chapter.id, panel);
      section.querySelector(".scene-app-slot").before(panel);
    }
    if (chapter.id === "drill") {
      const steps = element("div", "depth-controls");
      steps.setAttribute("role", "group");
      steps.setAttribute("aria-label", copy(["Progressive investigation", "逐层检查"]));
      const detail = element("div", "depth-detail");
      const heading = element("h3", "");
      const text = element("p", "");
      detail.append(heading, text);
      for (const step of depthGuide) {
        const button = element("button", "depth-button", copy(step.label));
        button.type = "button";
        button.dataset.depth = step.id;
        button.setAttribute("aria-pressed", String(step.id === "operation"));
        button.onclick = () => {
          steps
            .querySelectorAll("button")
            .forEach((other) => other.setAttribute("aria-pressed", String(other === button)));
          heading.textContent = copy(step.title);
          text.textContent = copy(step.text);
          detail.dataset.depth = step.id;
          onDepthChange(step.id);
          send({ action: "depth", depth: step.id });
        };
        steps.append(button);
      }
      heading.textContent = copy(depthGuide[0].title);
      text.textContent = copy(depthGuide[0].text);
      detail.dataset.depth = "operation";
      section.querySelector(".scene-app-slot").after(steps, detail);
      details.set(chapter.id, detail);
    }
    refresh();
  }
  return {
    mount,
    stage(id) {
      current = id;
      if (id === "drill" && details.has(id)) {
        const detail = details.get(id),
          step = depthGuide[0];
        detail.dataset.depth = step.id;
        detail.querySelector("h3").textContent = copy(step.title);
        detail.querySelector("p").textContent = copy(step.text);
        document.querySelectorAll("[data-depth]").forEach((button) => {
          if (button.tagName === "BUTTON")
            button.setAttribute("aria-pressed", String(button.dataset.depth === step.id));
        });
        onDepthChange(step.id);
      }
      refresh();
    },
    application(action) {
      if (session().phase !== "recording" || session().pending) return;
      // A click is only a request. Count it after the viewer selects the
      // archived event, so slow layout cannot masquerade as a recorded action.
      session().pending = action;
      send({
        action: "application",
        requestId: action.id,
        node: action.node,
        phase: action.phase,
        eventIds: action.event_ids,
      });
      refresh();
    },
    update(data) {
      const state = session();
      if (
        data.type === "vibelens-lens-ready" &&
        data.lens === "overview" &&
        state.pending === "overview"
      ) {
        state.pending = null;
        refresh();
      }
      if (
        data.type === "vibelens-application-ready" &&
        state.pending?.id === data.requestId &&
        state.pending.event_ids.includes(data.eventId)
      ) {
        state.actions.add(state.pending.id);
        state.pending = null;
        refresh();
      }
      if (data.type === "vibelens-scene-ready" && current === "drill") {
        const step = depthGuide.find((item) => item.id === details.get(current)?.dataset.depth);
        document.getElementById("case-scope").textContent = copy(
          step?.scope || depthGuide[0].scope,
        );
      }
    },
    get replayEnabled() {
      return ["run", "verify"].includes(current) && session().phase === "recorded";
    },
    destroy() {
      panels.clear();
      details.clear();
    },
  };
}
