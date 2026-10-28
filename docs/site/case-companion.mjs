/** Scripted development dialogue and a separate, event-bound application preview. */
import { locale, t } from "./site-ui.mjs?rev=clarity-1";
import { proposedFlow } from "./case-flow.mjs?rev=story-6";
const copy = (pair) => pair[locale() === "en" ? 0 : 1];
function node(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
/** Reconstruct only completed responses at or before the selected event. */
export function applicationAt(artifact, eventId) {
  const events = artifact.recording.events;
  const index = events.findIndex((event) => event.id === eventId);
  const state = { image: 0, reviewed: 0, published: 0, status: "empty", eventId };
  for (const event of events.slice(0, index + 1)) {
    if (event.phase !== "return") continue;
    const output = event.outputs || {};
    if (event.node === "upload" && output.image_version) state.image = output.image_version;
    if (event.node === "review" && output.reviewed_version)
      state.reviewed = output.reviewed_version;
    if (event.node === "exhibit" && Object.hasOwn(output, "published_version"))
      state.published = output.published_version || 0;
    if (["upload", "review", "publish"].includes(event.node) && output.status)
      state.status = output.status;
  }
  return state;
}
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
      if (foundation && index === 3) turn.append(proposedFlow(progress >= dialogue.length));
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
  const rooms = node("div", "app-rooms"),
    fields = {};
  for (const [key, action, label] of [
    ["image", "upload", "case.app.artist"],
    ["reviewed", "review", "case.app.reviewer"],
    ["published", "exhibit", "case.app.exhibition"],
  ]) {
    const room = node("div", "app-room");
    room.dataset.appRoom = key;
    const picture = node("div", "app-picture"),
      image = node("img", ""),
      empty = node("span", "app-empty", "+");
    image.alt = t(label);
    image.hidden = true;
    empty.setAttribute("aria-hidden", "true");
    picture.append(image, empty);
    const caption = node("span", "app-caption"),
      button = node("button", "", t(label));
    button.type = "button";
    button.title = t("case.app.seek");
    button.dataset.appAction = action;
    button.onclick = () => send({ action: "application", node: action });
    room.append(picture, button, caption);
    rooms.append(room);
    fields[key] = { room, image, empty, caption, button };
  }
  const footer = node("div", "app-footer"),
    status = node("span", "app-status");
  const approve = node("button", "app-approve", t("case.app.approve"));
  approve.type = "button";
  approve.dataset.appAction = "publish";
  approve.title = t("case.app.seek");
  approve.onclick = () => send({ action: "application", node: "publish" });
  const restart = node("button", "app-restart", "↻");
  restart.type = "button";
  restart.setAttribute("aria-label", t("case.app.replay"));
  restart.onclick = () => send({ action: "play" });
  footer.append(status, approve, restart);
  app.append(rooms, footer);
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
    const state = applicationAt(
      artifacts[chapters[chapter].version - 1],
      chapter === 0 ? null : eventId,
    );
    app.dataset.eventId = state.eventId || "";
    app.dataset.status = state.status;
    status.textContent = t("case.app." + state.status);
    for (const [key, field] of Object.entries(fields)) {
      const version = state[key];
      field.room.dataset.version = version;
      field.image.hidden = !version;
      field.empty.hidden = !!version;
      const url = version ? `case-data/image-${version}.png` : null;
      if (url && field.image.getAttribute("src") !== url) field.image.src = url;
      if (!url) field.image.removeAttribute("src");
      field.caption.textContent = version ? `${t("case.app.image")} ${version}` : "—";
      field.button.disabled = chapter === 0;
    }
    approve.disabled = chapter === 0 || !state.reviewed;
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
    },
  };
}
