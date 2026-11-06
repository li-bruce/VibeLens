/** Async explanation UI. The backend owns evidence, providers and job limits.
 * Selection/language/build changes cancel polling and discard late responses.
 * Answers are plain text and never modify labels, identities or declarations.
 */
import { locale, t } from "./i18n.js";

export const explanationKey = (view, node, language = locale()) =>
  JSON.stringify([
    view?.manifest?.build_id,
    view?.concept_structure?.revision,
    view?.code_structure?.revision,
    node,
    language,
  ]);

export function createNodeExplanation({ read, element, refresh = () => {} }) {
  const cache = new Map();
  let request = 0,
    active = null,
    timer = null,
    pending = null;
  const key = () => explanationKey(read().view, read().selected);
  const cancel = () => {
    request++;
    active?.abort();
    active = null;
    clearTimeout(timer);
    timer = null;
    pending = null;
  };
  function render() {
    const host = element("node-explanation"),
      button = element("explain-node"),
      value = cache.get(key()),
      busy = pending === key();
    button.disabled = busy;
    button.textContent = busy ? t("Explaining…") : t("AI explanation");
    host.hidden = !value;
    host.textContent = value
      ? value.answer?.text ||
        t(value.error || "AI explanation unavailable. Check the provider and retry.")
      : "";
    host.dataset.status = value?.status || (busy ? "running" : "idle");
    if (value?.answer) host.dataset.provider = value.provider;
  }
  function update() {
    if (pending && pending !== key()) cancel();
    element("explain-node").onclick = explain;
    render();
  }
  async function explain() {
    cancel();
    const token = request,
      expected = key(),
      state = read(),
      node = state.graph?.all?.get(state.selected)?.referenceOf || state.selected,
      language = locale();
    active = new AbortController();
    const signal = active.signal;
    pending = expected;
    cache.delete(expected);
    render();
    const valid = () => token === request && expected === key();
    const json = async (url, options) => {
      const response = await fetch(url, { ...options, signal, cache: "no-store" });
      let value;
      try {
        value = await response.json();
      } catch {
        throw Error("AI explanation unavailable. Check the provider and retry.");
      }
      if (!response.ok)
        throw Error(value.error || "AI explanation unavailable. Check the provider and retry.");
      return value;
    };
    const finish = (value) => {
      if (!valid()) return;
      pending = null;
      cache.set(expected, value);
      if (cache.size > 32) cache.delete(cache.keys().next().value);
      render();
      refresh();
    };
    try {
      const status = await json("/api/explanations");
      if (!valid()) return;
      if (!status.available) throw Error("No AI explanation provider is connected");
      if (
        status.build_id !== state.view.manifest.build_id ||
        (status.concept_revision ?? null) !== (state.view.concept_structure?.revision ?? null) ||
        (state.view.code_structure?.revision &&
          status.code_revision !== state.view.code_structure.revision)
      )
        throw Error("Graph changed. Refresh the node details.");
      const job = await json("/api/explanations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node, revision: status.revision, language }),
      });
      const deadline = Date.now() + 140000;
      const poll = async (value) => {
        if (!valid()) return;
        if (
          value.node !== node ||
          value.revision !== status.revision ||
          value.language !== language
        )
          throw Error("Graph changed. Refresh the node details.");
        if (value.status === "stale") throw Error("Graph changed. Refresh the node details.");
        if (value.status !== "running") return finish(value);
        if (Date.now() > deadline) throw Error("AI explanation timed out. Try again.");
        timer = setTimeout(async () => {
          try {
            await poll(await json("/api/explanations?job=" + encodeURIComponent(job.id)));
          } catch (error) {
            if (valid()) finish({ status: "error", error: error.message });
          }
        }, 700);
      };
      await poll(job);
    } catch (error) {
      if (valid()) finish({ status: "error", error: error.message });
    }
  }
  return {
    update,
    explain,
    clear: () => {
      cancel();
      cache.clear();
    },
    cancel,
  };
}
