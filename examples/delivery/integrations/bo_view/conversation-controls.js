/** Optional conversation controls. Viewers without an explicit session never poll them. */
export function createControlBridge({ apply, request = fetch, url = location.href }) {
  const session = new URL(url).searchParams.get("vl_session");
  if (session && !/^[a-f0-9]{32}$/.test(session)) throw Error("Invalid VibeLens session");
  let revision = -1,
    busy = false,
    lastPoll = 0;
  const endpoint = "/api/vibelens/control?vl_session=" + session;
  return {
    session,
    request(input, init) {
      return request(
        session && input === "/api/preferences" ? input + "?vl_session=" + session : input,
        init,
      );
    },
    legacy(storage) {
      if (!session || !storage) return storage;
      const prefix = "vibelens.session:" + session + ":";
      return {
        get length() {
          return Array.from({ length: storage.length }, (_, index) => storage.key(index)).filter(
            (key) => key?.startsWith(prefix),
          ).length;
        },
        key(index) {
          return (
            Array.from({ length: storage.length }, (_, item) => storage.key(item))
              .filter((key) => key?.startsWith(prefix))
              [index]?.slice(prefix.length) ?? null
          );
        },
        getItem(key) {
          return storage.getItem(prefix + key);
        },
        setItem(key, value) {
          storage.setItem(prefix + key, value);
        },
      };
    },
    async refresh(view) {
      if (!session || !view || busy || Date.now() - lastPoll < 800) return;
      busy = true;
      lastPoll = Date.now();
      let value;
      try {
        const response = await request(endpoint, { cache: "no-store" });
        if (!response.ok) return;
        value = await response.json();
        if (!value.active || !value.plan || revision === value.revision) return;
        revision = value.revision;
        const plan = value.plan;
        if (
          plan.schema !== "vibelens-control-plan/v1" ||
          !["view", "replay"].includes(plan.action) ||
          plan.base.model_revision !==
            (view.model.revision ??
              (view.stage === "design" ? view.manifest?.build_id : undefined)) ||
          plan.base.build_id !== view.manifest?.build_id
        )
          throw Error("The control plan does not match this graph build");
        const result = await apply(plan, session);
        const acknowledged = await request(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            revision,
            status: "applied",
            ...result,
            nodes: result.nodes.slice(0, 300),
            events: result.events.slice(0, 120),
            error: "",
          }),
        });
        if (!acknowledged.ok)
          throw Error("The view was applied but its acknowledgement was rejected");
      } catch (error) {
        if (value?.revision !== undefined)
          await request(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              revision: value.revision,
              status: "rejected",
              view_id: "",
              nodes: [],
              events: [],
              error: String(error.message).slice(0, 1000),
            }),
          }).catch(() => {});
      } finally {
        busy = false;
      }
    },
  };
}

/** Include projected values and required ancestors without duplicating identities. */
export function controlSelection(all, plan) {
  const selected = new Set(plan.node_ids),
    keep = new Set();
  for (const node of all.values()) {
    const owner = node.referenceOf || node.event_node || node.id;
    if (
      selected.has(node.id) ||
      selected.has(owner) ||
      (node.kind === "state" && selected.has(node.parent))
    )
      keep.add(node.id);
  }
  if (plan.node_ids.some((id) => !all.has(id)))
    throw Error("A selected graph node no longer exists");
  for (const id of [...keep]) {
    let parent = all.get(id)?.parent;
    const seen = new Set();
    while (parent && all.has(parent) && !seen.has(parent)) {
      seen.add(parent);
      keep.add(parent);
      parent = all.get(parent).parent;
    }
  }
  return keep;
}
