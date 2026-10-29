/** Scripted development dialogue and a separate, event-bound application preview. */
import { locale, t } from "./site-ui.mjs?rev=files-1";
import { proposedFlow } from "./case-flow.mjs?rev=files-1";
const copy = (pair) => pair[locale() === "en" ? 0 : 1];
function node(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
import { applicationAt } from "./case-application.mjs?rev=files-1";
export function companion({ host, chapters, artifacts, send, begin }) {
  let chapter = 0,
    source = 0,
    progress = 1,
    open = true;
  const narrow = matchMedia("(max-width: 900px)");
  const conversation = node("section", "case-conversation");
  conversation.id = "case-conversation";
  const toggle = node("button", "conversation-toggle");
  toggle.type = "button";
  const title = node("span", "");
  toggle.append(node("strong", "", "Codex"), title, node("span", "conversation-chevron", "⌄"));
  const turns = node("div", "conversation-turns");
  turns.setAttribute("role", "log");
  turns.tabIndex = 0;
  const next = node("button", "conversation-next");
  next.id = "conversation-next";
  next.type = "button";
  conversation.append(toggle, turns, next);
  function fold() {
    turns.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    conversation.classList.toggle("is-collapsed", !open);
  }
  toggle.onclick = () => {
    if (chapter) {
      open = !open;
      fold();
    }
  };
  function renderConversation() {
    const foundation = chapter === 0;
    const dialogue = chapters[source].dialogue;
    turns.replaceChildren();
    const visible = foundation ? dialogue.slice(0, progress) : dialogue;
    visible.forEach(([role, text], index) => {
      const turn = node("div", "conversation-turn " + role);
      turn.dataset.speaker = role;
      turn.append(
        node("span", "conversation-speaker", role === "user" ? t("case.user") : "Codex"),
        node("p", "", copy(text)),
      );
      if (foundation && index === 3)
        turn.append(proposedFlow(progress >= dialogue.length, artifacts[0]));
      turns.append(turn);
    });
    next.hidden = !foundation;
    next.textContent = t(
      progress < 4
        ? "case.dialogue.next"
        : progress === 4
          ? "case.dialogue.confirm"
          : "case.dialogue.build",
    );
    conversation.dataset.turn = progress;
    conversation.dataset.source = chapters[source].id;
    conversation.dataset.mode = chapters[chapter].dialogue ? "current" : "history";
    title.textContent = t(
      chapters[chapter].dialogue ? "case.conversation" : "case.conversation.previous",
    );
    fold();
  }
  next.onclick = () => {
    if (progress < chapters[0].dialogue.length) {
      progress++;
      renderConversation();
      requestAnimationFrame(() => {
        turns.scrollTop = turns.scrollHeight;
        next.scrollIntoView({
          block: "nearest",
          behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
        });
      });
      if (progress === chapters[0].dialogue.length) document.body.dataset.flowConfirmed = "true";
    } else begin();
  };
  const app = node("section", "case-application");
  app.id = "case-application";
  const heading = node("div", "app-heading");
  heading.append(node("strong", "", t("case.app.name")), node("span", "", t("case.app")));
  const minimize = node("button", "app-minimize", "−");
  minimize.type = "button";
  minimize.setAttribute("aria-label", t("case.app.minimize"));
  minimize.onclick = () => app.classList.toggle("is-collapsed");
  heading.append(minimize);
  app.append(heading);
  const screenshot = node("img", "app-frame");
  screenshot.alt = t("case.app.name");
  screenshot.hidden = true;
  screenshot.tabIndex = 0;
  screenshot.setAttribute("role", "button");
  screenshot.setAttribute("aria-label", t("case.app.open"));
  const capture = node("dialog", "app-capture-dialog");
  const closeCapture = node("button", "app-capture-close", "×");
  closeCapture.type = "button";
  closeCapture.setAttribute("aria-label", t("case.app.close"));
  closeCapture.onclick = () => capture.close();
  const fullCapture = node("img", "");
  fullCapture.alt = t("case.app.name");
  capture.append(closeCapture, fullCapture);
  document.body.append(capture);
  screenshot.onclick = () => {
    fullCapture.src = screenshot.src;
    capture.showModal();
  };
  screenshot.onkeydown = (event) => {
    if (["Enter", " "].includes(event.key)) {
      event.preventDefault();
      screenshot.click();
    }
  };
  const empty = node("p", "app-frame-empty", t("case.app.empty"));
  const actions = node("div", "app-actions");
  for (const action of artifacts[0].story.actions) {
    const button = node("button", "", copy(action.label));
    button.type = "button";
    button.dataset.appAction = action.id;
    button.title = t("case.app.seek");
    button.onclick = () => {
      const selected = artifacts[chapters[chapter].version - 1].story.actions.find(
        (item) => item.id === action.id,
      );
      send({
        action: "application",
        node: selected.node,
        phase: selected.phase,
        eventIds: selected.event_ids,
      });
    };
    actions.append(button);
  }
  const status = node("p", "app-status");
  const restart = node("button", "app-restart", t("case.app.replay"));
  restart.type = "button";
  restart.onclick = () => send({ action: "play" });
  app.append(screenshot, empty, actions, status, restart);
  function place() {
    const current = document.getElementById(chapters[chapter].id);
    const target = current?.querySelector(".scene-companion-slot");
    const before = conversation.getBoundingClientRect();
    const wasFoundation = conversation.closest("#foundation");
    if (target && conversation.parentNode !== target) target.append(conversation);
    const appTarget = narrow.matches
      ? current?.querySelector(".scene-app-slot")
      : document.getElementById("case-app-dock");
    if (appTarget && app.parentNode !== appTarget) appTarget.append(app);
    document.getElementById("case-app-dock").hidden = chapter === 0 || narrow.matches;
    if (
      wasFoundation &&
      chapter === 1 &&
      !matchMedia("(prefers-reduced-motion: reduce)").matches &&
      before.width
    ) {
      const after = conversation.getBoundingClientRect();
      conversation.animate(
        [
          {
            transformOrigin: "top left",
            transform: `translate(${before.x - after.x}px, ${before.y - after.y}px) scale(${before.width / after.width}, ${before.height / after.height})`,
          },
          { transformOrigin: "top left", transform: "none" },
        ],
        { duration: 420, easing: "cubic-bezier(.2,.7,.2,1)" },
      );
    }
  }
  function update(eventId) {
    const artifact = artifacts[chapters[chapter].version - 1];
    let frame = applicationAt(artifact, chapter ? eventId : null, locale());
    if (chapter > 0 && !eventId && (artifact.application_start || artifact.application_overview)) {
      const initial = artifact.application_start || artifact.application_overview;
      frame = {
        ...initial,
        image: initial.images[locale()] || initial.images.en,
      };
    }
    app.dataset.eventId = frame?.eventId || "";
    app.dataset.frameEvent = frame?.event_id || "";
    app.dataset.status = frame?.status || "ready";
    screenshot.hidden = !frame;
    empty.hidden = !!frame;
    if (frame) {
      if (screenshot.getAttribute("src") !== frame.image) screenshot.src = frame.image;
      status.textContent = copy(frame.caption);
    } else {
      screenshot.removeAttribute("src");
      status.textContent = "";
    }
    for (const button of actions.querySelectorAll("button")) button.disabled = chapter === 0;
  }
  function stage(index) {
    chapter = index;
    source = index;
    while (!chapters[source].dialogue) source--;
    host.dataset.scene = chapters[index].id;
    host.dataset.surface = chapters[index].surface;
    open = !!chapters[index].dialogue;
    app.hidden = chapter === 0;
    renderConversation();
    place();
    update(null);
  }
  narrow.addEventListener("change", place);
  return {
    stage,
    update,
    destroy() {
      narrow.removeEventListener("change", place);
      conversation.remove();
      app.remove();
      capture.remove();
    },
  };
}
