/** Remove known authoring boilerplate from display models, preserving captured facts. */
const boilerplate = new Set([
  "Native rule predicate",
  "HTTP adapter delegates to the actual service operation.",
  "Local static call; execution requires runtime evidence.",
  "Implementation ownership; source and runtime records establish calls",
]);

export function presentCase(captured) {
  const artifact = structuredClone(captured);
  // Short presentation aliases fit the native icons. Full definitions and
  // canonical identities remain available through the viewer's node details.
  artifact.story.captions = {
    ...artifact.story.captions,
    state_private: ["Private", "私有"],
    db_delete_share: ["Delete grant", "删除授权"],
    "field:revoke:in:recipient_id": ["Recipient", "接收者"],
    "policy:fact_is_recipient": ["Shared?", "拥有共享"],
    "policy:fact_logged_in": ["Session", "登录状态"],
    "policy:owned_session": ["Can share", "可管理共享"],
    "policy:file_access": ["Access", "访问资格"],
    "policy:read_allowed": ["Can read", "可读取"],
  };
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
