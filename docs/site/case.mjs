/** Narrate real artifacts. The application never runs inside the static Pages story. */
import { initialize, t, locale, onLanguageChange } from "./site-ui.mjs?rev=0.8.1";
import { messages, chapters, layerLabels } from "./case-messages.mjs?rev=case-1";

const element = (id) => document.getElementById(id);
const pick = (pair) => pair[locale() === "en" ? 0 : 1];
const artifacts = await Promise.all(
  [1, 2].map(async (version) => {
    const response = await fetch(`case-data/v${version}.json`);
    if (!response.ok) throw Error("Recorded case unavailable");
    return response.json();
  }),
);
let chapter = 0,
  mode = "2d",
  loaded = "",
  ready = false;

function send(value) {
  if (ready)
    element("case-graph").contentWindow.postMessage(
      { type: "vibelens-case", ...value },
      location.origin,
    );
}

function paragraph(parent, text, css = "") {
  const node = document.createElement("p");
  node.className = css;
  node.textContent = text;
  parent.append(node);
  return node;
}

/** Extract the mismatched arguments and verdict from matching actual call IDs. */
function mismatch(artifact) {
  const enter = artifact.view.events.find(
    (event) =>
      event.node === "review-policy" &&
      event.inputs.current_version === 2 &&
      event.inputs.reviewed_version === 1,
  );
  const returned = artifact.view.events.find(
    (event) => event.call_id === enter.call_id && event.phase === "return",
  );
  return { ...enter.inputs, ...returned.outputs };
}

function renderEvidence() {
  const panel = element("case-evidence");
  panel.replaceChildren();
  const artifact = artifacts[chapter >= 3 ? 1 : 0];
  if (chapter === 1) {
    const list = document.createElement("ol");
    list.className = "case-steps";
    const steps =
      locale() === "en"
        ? [
            "Upload blue image · version 1",
            "Reviewer opens version 1",
            "Artist replaces it · version 2",
            "Reviewer approves the old preview",
          ]
        : [
            "上传蓝色图片 · 第 1 版",
            "审核者打开第 1 版",
            "上传者替换为橙色图片 · 第 2 版",
            "审核者在旧页面点击通过",
          ];
    for (const step of steps) {
      const item = document.createElement("li");
      item.textContent = step;
      list.append(item);
    }
    panel.append(list);
    paragraph(
      panel,
      locale() === "en"
        ? `${artifact.recording.events.length} actual events · ${artifact.view.runtime_frames.frames.length} state snapshots`
        : `${artifact.recording.events.length} 条实际事件 · ${artifact.view.runtime_frames.frames.length} 份状态快照`,
      "case-result",
    );
  }
  if (chapter >= 2) {
    const values = mismatch(artifact),
      facts = document.createElement("div");
    facts.className = "case-facts";
    for (const key of ["reviewed_version", "current_version", "verdict"]) {
      const row = document.createElement("div");
      const label = document.createElement("span"),
        value = document.createElement("strong");
      label.textContent = key;
      value.textContent = values[key];
      row.append(label, value);
      facts.append(row);
    }
    panel.append(facts);
    paragraph(
      panel,
      (locale() === "en" ? "Business check: " : "业务检查：") +
        (artifact.business.passed
          ? locale() === "en"
            ? "PASS · stale review rejected"
            : "通过 · 拒绝过期审核"
          : locale() === "en"
            ? "FAIL · unreviewed version published"
            : "失败 · 发布了未经审核的版本"),
      "case-result" + (artifact.business.passed ? " passed" : ""),
    );
    if (chapter === 4)
      paragraph(
        panel,
        locale() === "en"
          ? "Fresh review → published v2\nArtist approval → forbidden\nInvalid image → rejected\nObserver requests → 0 business events"
          : "重新审核 → 发布第 2 版\n上传者审核 → 无权限\n无效图片 → 拒绝\n观察器请求 → 0 条业务事件",
        "case-result passed",
      );
  }
}

/** Change the narrated build without reusing another build's recording or source. */
function render() {
  const current = chapters[chapter],
    version = chapter >= 3 ? 2 : 1;
  element("chapter-kicker").textContent = t("case.tab." + chapter);
  element("chapter-title").textContent = pick(current.title);
  element("chapter-body").textContent = pick(current.body);
  element("case-next").textContent = t(chapter === 4 ? "case.restart" : "case.next");
  document.querySelectorAll("[data-chapter]").forEach((button) => {
    if (Number(button.dataset.chapter) === chapter) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
  });
  const dialogue = element("case-dialogue");
  dialogue.replaceChildren();
  for (const [role, en, zh] of current.dialogue) {
    const p = paragraph(dialogue, locale() === "en" ? en : zh),
      who = document.createElement("small");
    who.textContent = t("case." + role);
    p.prepend(who);
  }
  renderEvidence();
  element("case-version").textContent =
    `${t("case.recorded")} ${version} · ${artifacts[version - 1].provenance.build_id.slice(0, 9)}`;
  element("case-view-help").textContent = t("case.help." + mode);
  for (const dimension of ["2d", "3d"])
    element("case-" + dimension).setAttribute("aria-pressed", String(mode === dimension));
  const key = version + ":" + locale();
  if (loaded !== key) {
    ready = false;
    loaded = key;
    element("case-graph").src = `viewer/index.html?case=${version}&lang=${locale()}`;
  } else send({ view: current.view, mode, inspectMismatch: chapter === 2 || chapter === 3 });
  const links = element("case-layer-links"),
    map = element("case-layer-map");
  links.replaceChildren();
  map.replaceChildren();
  const path = document.createElement("div");
  path.className = "layer-path";
  map.append(path);
  for (const [id, en, zh, color, detail] of layerLabels) {
    const button = document.createElement("button");
    button.textContent = locale() === "en" ? en : zh;
    button.style.setProperty("--layer-color", color);
    button.dataset.layer = id;
    button.onclick = () => send({ view: id, expand: true });
    links.append(button);
    const item = document.createElement("span"),
      label = document.createElement("small");
    item.textContent = button.textContent;
    item.style.setProperty("--layer-color", color);
    label.textContent = detail;
    item.append(label);
    path.append(item);
  }
  // Display the actual exported policy from each build, not a handwritten fix snippet.
  const lines = (source) =>
    source
      .split("\n")
      .filter((line) => !line.startsWith('"""') && line.trim())
      .join("\n");
  element("case-source").textContent =
    "— v1 —\n" +
    lines(artifacts[0].sources["policy.py"]) +
    "\n\n+ v2 +\n" +
    lines(artifacts[1].sources["policy.py"]);
}
window.addEventListener("message", (event) => {
  if (
    event.source !== element("case-graph").contentWindow ||
    event.origin !== location.origin ||
    event.data?.type !== "vibelens-case-ready"
  )
    return;
  ready = true;
  send({ view: chapters[chapter].view, mode, inspectMismatch: chapter === 2 || chapter === 3 });
});
document.querySelectorAll("[data-chapter]").forEach(
  (button) =>
    (button.onclick = () => {
      chapter = Number(button.dataset.chapter);
      render();
    }),
);
element("case-next").onclick = () => {
  chapter = (chapter + 1) % chapters.length;
  render();
};
for (const dimension of ["2d", "3d"])
  element("case-" + dimension).onclick = () => {
    mode = dimension;
    for (const value of ["2d", "3d"])
      element("case-" + value).setAttribute("aria-pressed", String(mode === value));
    element("case-view-help").textContent = t("case.help." + mode);
    send({ mode });
  };
element("case-layers").onclick = () => send({ view: "overview", expand: true });
onLanguageChange(render);
initialize(messages);
