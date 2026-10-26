/** Source/value presentation owns its bounded cache and source-revision checks.
 * It reads a snapshot from the coordinator and updates DOM only. Annotation,
 * graph, recording and application state remain owned by their existing modules.
 */
import { renderSource } from "./source-view.js";
import { nodeExplanation } from "./capture-fields.js";
import { dataLines } from "./data-layer.js";
import { annotationFor, displayName } from "./layout.js";
import { sourceBinding } from "./graph-core.js";
import { t as boTranslate } from "./i18n.js";

export function createDetailPanel({ read, point, element = (id) => document.getElementById(id) }) {
  const $ = element,
    sources = new Map();
  /** Render the currently selected node, respecting field/source provenance. */
  function update() {
    const { view, graph, preferences, selected, mode: detailMode } = read();
    const b = graph?.byId.get(selected);
    if (!b || !detailMode) {
      $("node-details").hidden = true;
      return;
    }
    const annotation = annotationFor(preferences, b.node.referenceOf || b.id),
      editing = detailMode === "annotation";
    $("node-details").hidden = false;
    $("detail-title").textContent = displayName(b.node, preferences);
    $("annotation-form").hidden = !editing;
    const rows = [
      ...(annotation.label || editing
        ? [{ text: boTranslate("Original name: ") + b.node.label }]
        : []),
      ...(editing
        ? [{ text: boTranslate("Node: ") + b.id }]
        : [
            ...nodeExplanation(b.node, graph.all).map((text) => ({ text })),
            ...(b.node.data_role && !["query", "transform"].includes(b.node.data_role)
              ? dataLines(b.node, {}, {}, false, true)
              : b.rows),
          ]),
      ...(!editing && annotation.note ? [{ text: boTranslate("Note: ") + annotation.note }] : []),
    ];
    $("detail-rows").replaceChildren(
      ...rows.map((r) => {
        const p = document.createElement("p");
        p.textContent = r.text;
        return p;
      }),
    );
    const binding = sourceBinding(view, graph.all, selected),
      source = detailMode === "source" && binding;
    $("source-code").hidden = !source;
    if (source?.provenance === "capture-owner") {
      const note = document.createElement("p");
      note.textContent = boTranslate("Operation source context · no matching source parameter");
      $("detail-rows").append(note);
    }
    $("full-source").hidden = !source;
    if (source) {
      const key = (binding.code_revision || view.manifest.build_id) + ":" + binding.path,
        full = sources.get(key);
      $("detail-title").textContent =
        `${binding.path}:${binding.selection?.line || binding.line} · ${(binding.code_revision || view.manifest.build_id).slice(0, 8)}`;
      $("full-source").hidden = true;
      if (full !== undefined) {
        const renderedKey = [key, selected].join(":");
        if ($("source-code").dataset.location !== renderedKey) {
          const target = renderSource($("source-code"), full, binding);
          $("source-code").dataset.location = renderedKey;
          requestAnimationFrame(() => {
            if (target?.isConnected) {
              const host = $("source-code");
              host.scrollTop +=
                target.getBoundingClientRect().top -
                host.getBoundingClientRect().top -
                host.clientHeight / 3;
            }
          });
        }
      } else {
        $("source-code").textContent = boTranslate("Loading source…");
        delete $("source-code").dataset.location;
      }
    }
    position();
  }

  /** Anchor the panel beside the selected node in either renderer. */
  function position() {
    const { graph, selected, scale, pan, screen } = read();
    if ($("node-details").hidden || !graph?.byId.has(selected)) return;
    const b = graph.byId.get(selected),
      p = point(b),
      panel = $("node-details"),
      w = panel.offsetWidth,
      h = panel.offsetHeight;
    panel.style.left =
      Math.max(10, Math.min(screen.width - w - 10, p.x * scale + pan.x + 45)) + "px";
    panel.style.top =
      Math.max(10, Math.min(screen.height - h - 12, p.y * scale + pan.y - 30)) + "px";
  }

  /** Fetch a complete file, then reject a response for an obsolete build or revision. */
  async function load() {
    const { selected, view, graph, version, recording } = read();
    const id = selected,
      build = view.manifest.build_id,
      binding = sourceBinding(view, graph.all, id),
      requestedVersion = version;
    if (!binding) return;
    const cacheKey = (binding.code_revision || build) + ":" + binding.path;
    if (sources.has(cacheKey)) {
      update();
      return;
    }
    let response;
    try {
      response = await fetch(
        (binding.code_revision
          ? "/api/code/source?revision=" + binding.code_revision + "&path="
          : "/api/source?path=") +
          encodeURIComponent(binding.path) +
          (recording
            ? "&recording=" + recording.id
            : "&version=" + encodeURIComponent(requestedVersion)),
      );
    } catch {
      return;
    }
    if (!response.ok) {
      if (read().selected === id && read().mode === "source")
        $("source-code").textContent = boTranslate(
          "Source changed or unavailable. Refresh the graph.",
        );
      return;
    }
    const data = await response.json();
    const current = read();
    if (
      binding.code_revision
        ? data.code_revision !== current.view?.code_structure?.revision
        : current.view?.manifest.build_id !== build ||
          data.build_id !== build ||
          current.version !== requestedVersion
    )
      return;
    sources.set((binding.code_revision || build) + ":" + binding.path, data.source);
    if (sources.size > 16) sources.delete(sources.keys().next().value);
    if (read().selected === id) update();
  }

  return { update, position, load, clear: () => sources.clear() };
}
