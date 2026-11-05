/** A focused explanation of the archived model, with source witnesses per edge.
 * This is a confirmation overview, not a second executable or recorded graph.
 */
export function confirmationModel(artifact, tab, language = "en") {
  const chinese = language === "zh-CN";
  const text = (en, zh) => (chinese ? zh : en);
  const model = artifact.view.model;
  const node = (id, x, y, label, glyph) => ({ id, x, y, label, glyph });
  const edge = (from, to, witnesses, label = "") => ({ from, to, witnesses, label });
  if (tab === "states") {
    const labels = {
      empty: text("No file", "尚未上传"),
      private: text("Private", "仅自己可见"),
      shared: text("Shared", "已共享"),
    };
    const nodes = model.machine.states.map((id, i) =>
      node(id, 70 + i * 235, 110, labels[id] || id, "S"),
    );
    const edges = model.machine.transitions.flatMap((transition, index) =>
      (Array.isArray(transition.source) ? transition.source : [transition.source]).map((from) => ({
        ...edge(from, transition.dest, ["machine.transitions[" + index + "]"], transition.trigger),
        condition: [
          ...(transition.conditions || []),
          ...(transition.unless || []).map((id) => "NOT " + id),
        ].join(" AND "),
      })),
    );
    return {
      nodes,
      edges,
      caption: text("Revocation reads the remaining grants", "取消共享后，根据剩余授权确定状态"),
    };
  }
  if (tab === "rules") {
    const nodes = [
      node("policy:signed_in", 65, 45, text("Signed in", "已登录"), "?"),
      node("policy:is_owner", 65, 140, text("Owner", "所有者"), "?"),
      node("policy:received_share", 65, 235, text("Recipient", "接收者"), "?"),
      node("policy:owned_session", 305, 55, text("Share · Revoke", "共享 · 取消共享"), "AND"),
      node("policy:file_access", 305, 210, text("Access", "访问资格"), "OR"),
      node("policy:read_allowed", 540, 140, text("View · Download", "查看 · 下载"), "AND"),
    ];
    const ids = new Set(nodes.map((n) => n.id));
    const edges = model.edges
      .filter((e) => e.type === "guard" && ids.has(e.from) && ids.has(e.to))
      .map((e) => edge(e.from, e.to, [e.id]));
    return {
      nodes,
      edges,
      caption: text("Viewing and downloading use the same decision", "查看与下载共用同一个判定"),
    };
  }
  const labels = artifact.story.captions;
  const nodes = [
    ["upload", 65, 60],
    ["share", 305, 60],
    ["download", 540, 60],
    ["revoke", 305, 210],
  ].map(([id, x, y]) =>
    node(
      id,
      x,
      y,
      labels[id]?.[chinese ? 1 : 0] || model.nodes.find((n) => n.id === id).label,
      "B",
    ),
  );
  const edges = [
    edge("upload", "share", ["upload_owner", "owner_share"], text("Owner", "所有者")),
    edge(
      "share",
      "download",
      ["share_recipient", "recipient_download"],
      text("Recipient", "接收者"),
    ),
    edge("share", "revoke", ["share_revoke"]),
    edge("revoke", "download", ["revoke_download"], text("Recheck access", "重新检查权限")),
  ];
  return {
    nodes,
    edges,
    caption: text(
      "The owner controls sharing and keeps access",
      "所有者控制共享，并保留自己的访问权",
    ),
  };
}
