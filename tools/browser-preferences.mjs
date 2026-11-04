/** Server-acknowledged preference waits for maintained browser tests. */
export function analysisPreferences(document) {
  const raw = Object.entries(document?.entries || {}).find(([key]) =>
    key.endsWith(":analysis"),
  )?.[1];
  return raw ? JSON.parse(raw) : null;
}

/** Watch before reading so both in-flight saves and already-saved state are covered. */
export function waitForPreferences(
  page,
  matches,
  { afterRevision = -1, description = "Requested project preference" } = {},
) {
  const current = new URL(page.url());
  const endpoint = new URL("/api/preferences", current);
  if (current.searchParams.has("vl_session"))
    endpoint.searchParams.set("vl_session", current.searchParams.get("vl_session"));
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      page.off("response", onResponse);
      if (error) reject(error);
      else resolve(value);
    };
    const inspect = (document) => {
      if (settled || !(document?.revision > afterRevision)) return;
      const matched = matches(document);
      if (matched?.then) throw Error("Preference matchers must return a synchronous boolean");
      if (matched) finish(null, document);
    };
    const onResponse = async (response) => {
      if (
        response.url() !== endpoint.href ||
        response.request().method() !== "POST" ||
        response.status() !== 200
      )
        return;
      try {
        inspect(await response.json());
      } catch (error) {
        finish(error);
      }
    };
    const timer = setTimeout(
      () => finish(Error(description + " was not acknowledged within 30000ms")),
      30000,
    );
    page.on("response", onResponse);
    page
      .evaluate(async (url) => {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) throw Error("Preference read failed: HTTP " + response.status);
        return response.json();
      }, endpoint.pathname + endpoint.search)
      .then(inspect)
      .catch((error) => finish(error));
  });
}
