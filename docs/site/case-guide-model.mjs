/** Presentation scopes select existing identities; they never generate facts. */
export function guidedIds(story, depth = "overview") {
  const business = new Set([...story.business, ...story.states]);
  if (depth === "overview") return business;
  return guidedViewIds(story, {
    inputs: depth !== "operation",
    effects: depth === "data",
    states: true,
  });
}

/** The custom-view toggles use the same groups as progressive inspection. */
export function guidedViewIds(story, { inputs = true, effects = false, states = true } = {}) {
  const focused = new Set(["revoke", "download", ...(states ? story.states : [])]);
  if (inputs || effects) for (const id of story.focus.core) focused.add(id);
  if (inputs) for (const id of story.focus.inputs) focused.add(id);
  if (effects) {
    // This question concerns the deletion target and its implementation.
    // Authentication and HTTP routing remain available in the full viewer.
    for (const id of story.focus.effects)
      if (id.startsWith("db:") || id.startsWith("code:symbol:")) focused.add(id);
  }
  return focused;
}

/** Playback boundaries use archived action IDs, independent of labels or locale. */
export function recordingWindow(events, story) {
  const indexes = story.actions.flatMap((action) =>
    action.event_ids.map((id) => events.findIndex((event) => event.id === id)),
  );
  if (!indexes.length || indexes.some((index) => index < 0))
    throw Error("The walkthrough action is missing from the recorded sequence");
  return { start: Math.min(...indexes), end: Math.max(...indexes) };
}

export function eventAtProgress(events, story, progress) {
  const { start, end } = recordingWindow(events, story);
  const fraction = Math.min(100, Math.max(0, Number(progress) || 0)) / 100;
  return Math.round(start + (end - start) * fraction);
}

/** A readable starting arrangement, stored as ordinary viewer preferences. */
export function investigationPositions(story, codeNodes = []) {
  const points = {
    file: [180, 40],
    state_private: [440, 40],
    state_shared: [720, 40],
    revoke: [440, 280],
    download: [760, 280],
    "field:revoke:in:actor": [180, 200],
    "field:revoke:in:recipient_id": [180, 360],
    db_delete_share: [440, 520],
    "field:db_delete_share:out:rows": [700, 520],
  };
  for (const id of story.focus.effects) {
    if (id.startsWith("db:")) points[id] = [920, 520];
    if (id.startsWith("code:symbol:")) {
      points[id] = [1020, 280];
      const byId = new Map(codeNodes.map((node) => [node.id, node]));
      let parent = byId.get(id)?.parent;
      let y = 160;
      while (parent && byId.has(parent)) {
        points[parent] = [1120, y];
        y -= 120;
        parent = byId.get(parent).parent;
      }
    }
  }
  return Object.fromEntries(
    Object.entries(points).map(([id, [x, y]]) => [id, { x, y, pinned: true }]),
  );
}

export const depthGuide = [
  {
    id: "operation",
    label: ["1 · Focus the operation", "1 · 聚焦取消共享"],
    title: ["The file stayed Shared after revocation", "操作执行了，状态却仍是已共享"],
    text: [
      "Keep this action, the next download and the file states. This is the question to investigate.",
      "保留取消、再次下载和文件状态。先把需要解释的现象圈出来。",
    ],
    scope: ["Business → State", "业务 → 状态"],
  },
  {
    id: "inputs",
    label: ["2 · Open inputs & execution", "2 · 展开参数与执行"],
    title: ["Who performed it? Whose access should end?", "谁在操作，要取消谁的权限"],
    text: [
      "The actor is Lin, the recipient is Xu. Follow these inputs into the deletion operation and its return value.",
      "操作者是林舟，接收者是许宁。沿输入继续查看删除操作及其返回值。",
    ],
    scope: ["Business → Function → Values", "业务 → 函数 → 参数"],
  },
  {
    id: "data",
    label: ["3 · Follow the data result", "3 · 核对数据结果"],
    title: ["Zero deleted rows explains the unchanged access", "删除影响 0 行，授权自然还在"],
    text: [
      "Inspect the shares table and mapped function. The source reveals a deletion condition using the actor instead of the recipient.",
      "接着查看共享表和对应函数。源码中的删除条件错用了操作者，而不是要取消的接收者。",
    ],
    scope: ["Function → Storage → Source", "函数 → 存储 → 源码"],
  },
];
