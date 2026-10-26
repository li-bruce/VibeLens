/** Keep the authored conversation and application replay beside the real graph.
 * Application controls seek captured actions; Pages never executes a backend.
 */
import { locale, t } from "./site-ui.mjs?rev=story-3";

const copy = (pair) => pair[locale() === "en" ? 0 : 1];
const node = (tag, className, text) => {
  const element = document.createElement(tag);
  element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
};

/** Project completed application responses up to this exact recorded event.
 * Scrubbing backward rebuilds the UI from the beginning, without future facts.
 * The open preview and exhibition follow their own responses, not request values.
 */
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

/** One shared companion moves into the active narrative on narrow screens. */
export function companion({ host, chapters, artifacts, send, begin }) {
  let chapter = 0;
  const narrow = matchMedia("(max-width: 700px)");
  const conversation = node("section", "case-conversation");
  conversation.append(node("h3", "companion-heading", t("case.conversation")));
  const turns = node("div", "conversation-turns");
  turns.tabIndex = 0;
  turns.setAttribute("role", "log");
  turns.setAttribute("aria-label", t("case.conversation"));
  conversation.append(turns);

  const app = node("section", "case-application");
  const heading = node("div", "app-heading");
  heading.append(node("strong", "", "Afterlight"), node("span", "", t("case.app")));
  const restart = node("button", "app-restart", "↻");
  restart.type = "button";
  restart.setAttribute("aria-label", t("case.app.replay"));
  restart.title = t("case.app.replay");
  restart.onclick = () => (chapter === 0 ? begin() : send({ action: "play" }));
  heading.append(restart);
  app.append(heading);
  const rooms = node("div", "app-rooms");
  const fields = {};
  for (const [key, action, label] of [
    ["image", "upload", "case.app.artist"],
    ["reviewed", "review", "case.app.reviewer"],
    ["published", "exhibit", "case.app.exhibition"],
  ]) {
    const room = node("div", "app-room");
    room.dataset.appRoom = key;
    const picture = node("div", "app-picture");
    const image = node("img", "");
    image.alt = t(label);
    image.hidden = true;
    const empty = node("span", "app-empty", "+");
    empty.setAttribute("aria-hidden", "true");
    picture.append(image, empty);
    const caption = node("span", "app-caption");
    const button = node("button", "", t(label));
    button.type = "button";
    button.title = t("case.app.seek");
    button.dataset.appAction = action;
    button.onclick = () => send({ action: "application", node: action });
    room.append(button, picture, caption);
    fields[key] = { room, image, empty, caption, button };
    rooms.append(room);
  }
  app.append(rooms);
  const footer = node("div", "app-footer");
  const status = node("span", "app-status");
  const approve = node("button", "app-approve", t("case.app.approve"));
  approve.type = "button";
  approve.dataset.appAction = "publish";
  approve.title = t("case.app.seek");
  approve.onclick = () => send({ action: "application", node: "publish" });
  footer.append(status, approve);
  app.append(footer);
  host.replaceChildren(conversation, app);

  function place() {
    const parent = narrow.matches
      ? document.querySelector(`#${chapters[chapter].id} .scene-companion-slot`)
      : document.querySelector(".case-visual");
    if (parent && host.parentNode !== parent) parent.append(host);
  }
  function update(eventId) {
    const artifact = artifacts[chapter >= 4 ? 1 : 0];
    const state = applicationAt(artifact, chapter === 0 ? null : eventId);
    app.dataset.eventId = state.eventId || "";
    app.dataset.status = state.status;
    status.textContent = t("case.app." + state.status);
    for (const [key, field] of Object.entries(fields)) {
      const version = state[key];
      field.room.dataset.version = version;
      field.image.hidden = !version;
      field.empty.hidden = !!version;
      if (version) field.image.src = `case-data/image-${version}.png`;
      else field.image.removeAttribute("src");
      field.caption.textContent = version ? `${t("case.app.image")} ${version}` : "—";
      field.button.disabled = chapter === 0;
    }
    approve.disabled = chapter === 0 || !state.reviewed;
  }
  function stage(index) {
    chapter = index;
    host.dataset.scene = chapters[index].id;
    turns.replaceChildren();
    for (const [role, text] of chapters[index].dialogue) {
      const turn = node("div", "conversation-turn " + role);
      turn.dataset.speaker = role;
      turn.append(
        node("span", "conversation-speaker", role === "user" ? t("case.user") : "Codex"),
        node("p", "", copy(text)),
      );
      turns.append(turn);
    }
    turns.scrollTop = 0;
    update(null);
    place();
  }
  narrow.addEventListener("change", place);
  return { stage, update, destroy: () => narrow.removeEventListener("change", place) };
}
