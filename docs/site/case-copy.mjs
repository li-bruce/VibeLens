/** Remove known authoring boilerplate from display models, preserving captured facts. */
const boilerplate = new Set([
  "Native rule predicate",
  "HTTP adapter delegates to the actual service operation.",
  "Local static call; execution requires runtime evidence.",
  "Implementation ownership; source and runtime records establish calls",
]);

export function presentCase(captured) {
  const artifact = structuredClone(captured);
  const models = [artifact.view.model, artifact.recording.context.model, artifact.code];
  for (const model of models) {
    for (const node of model.nodes || []) {
      const summary = node.summary || "";
      if (
        boilerplate.has(summary) ||
        summary === node.label ||
        summary === `${node.label}: actual inputs and outcomes from the running application.` ||
        summary.startsWith("Canonical declaration state: ")
      )
        node.summary = "";
      // These exact trial captions describe model bookkeeping, rather than behavior.
      if (summary.endsWith(" read from SQLite; a relation is not a global role."))
        node.summary = "";
      if (node.id === "db:sharing:store" && summary === "sqlalchemy · complete")
        node.summary = "SQLite";
    }
  }
  return artifact;
}
