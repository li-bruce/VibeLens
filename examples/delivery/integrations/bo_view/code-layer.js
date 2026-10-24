// Optional source structure is a display projection, separate from recorded facts.
import { mergeGraph } from "./graph-links.js";
export const codeTypes = [
  "code-file",
  "code-endpoint",
  "code-class",
  "code-function",
  "code-parameter",
  "code-unresolved",
];
export const codeRelations = [
  "code-defines",
  "code-handles",
  "code-calls",
  "code-imports",
  "code-inherits",
  "code-parameter",
  "code-maps",
];

/** Show display limits so a bounded slice cannot be mistaken for complete coverage. */
export function codeSummary(slice, translate) {
  if (!slice) return "";
  const parts = [
    translate("Code: {0} / {1} nodes", slice.loaded_nodes, slice.total_nodes),
    translate("{0} relations", slice.loaded_edges),
  ];
  if (slice.boundary_nodes) parts.push(translate("{0} boundary nodes", slice.boundary_nodes));
  if (slice.omitted_edges) parts.push(translate("{0} related links omitted", slice.omitted_edges));
  if (slice.errors.length) parts.push(translate("Source analysis incomplete"));
  return parts.join(" · ");
}

export function migrateCodeFilters(value) {
  if (!value || value.codeTypes === 2) return value;
  const next = { ...value, codeTypes: 2 };
  // Upgrade prior all-code selections once. Preserve deliberate narrow/empty filters.
  if (value.codeTypes === 1) {
    for (const key of ["nodes", "regions"])
      if (
        codeTypes
          .filter((type) => type !== "code-endpoint")
          .every((type) => value[key]?.includes(type))
      )
        next[key] = [...new Set([...value[key], "code-endpoint"])];
    if (
      codeRelations
        .filter((type) => type !== "code-handles")
        .every((type) => value.edges?.includes(type))
    )
      next.edges = [...new Set([...value.edges, "code-handles"])];
  }
  return next;
}

/** Merge by stable identity; never replace the authored graph or its build. */
export function withCodeGraph(view, slice) {
  if (!slice) return view;
  return {
    ...view,
    code_structure: slice,
    model: mergeGraph(view.model, slice),
    manifest: {
      ...view.manifest,
      bindings: {
        ...view.manifest.bindings,
        ...Object.fromEntries(
          Object.entries(slice.bindings).map(([id, binding]) => [
            id,
            { ...binding, code_revision: slice.revision, snippet: "" },
          ]),
        ),
      },
    },
  };
}

/** Cancel obsolete focus requests and discard their results if selection changes. */
export class CodeLayer {
  constructor(fetcher = (...args) => fetch(...args)) {
    this.fetcher = fetcher;
    this.epoch = 0;
    this.slice = null;
  }
  clear() {
    this.epoch++;
    this.controller?.abort();
    this.slice = null;
  }
  async load({ enabled, focus = null, limit = 400, depth = 1 }) {
    if (!enabled) {
      this.clear();
      return null;
    }
    const epoch = ++this.epoch;
    this.controller?.abort();
    this.controller = new AbortController();
    const query = new URLSearchParams({ limit, depth });
    if (focus) query.set("focus", focus);
    try {
      const response = await this.fetcher("/api/code/graph?" + query, {
        cache: "no-store",
        signal: this.controller.signal,
      });
      const payload = await response.json();
      if (!response.ok) throw Error(payload.error || "Code structure unavailable");
      if (payload.schema !== "bo-code-graph/v1") throw Error("Unsupported code structure protocol");
      if (epoch !== this.epoch) return null;
      this.slice = payload;
      return payload;
    } catch (error) {
      if (epoch !== this.epoch) return null;
      this.slice = null;
      throw error;
    }
  }
}
