/** Read-only HTTP fixture for an actual saved recording and canonical viewer assets. */
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export async function serveRecording(
  recordingPath,
  { names = null, port = 0, preferences: initialPreferences = null } = {},
) {
  const root = fileURLToPath(new URL("../", import.meta.url));
  const assets = path.join(root, "skills/vibelens/assets/stategraph-viewer");
  const bytes = await readFile(recordingPath);
  const recording = JSON.parse(bytes);
  // Optional AI-authored presentation accompanies the immutable recorded facts.
  const displayed = names
    ? {
        ...recording,
        context: {
          ...recording.context,
          model: {
            ...recording.context.model,
            presentation: { ...recording.context.model.presentation, names },
          },
        },
      }
    : recording;
  const writes = [],
    requests = [];
  let preferences = initialPreferences || {
    schema: 1,
    project_id: recording.context.model.project_id,
    revision: 0,
    entries: {},
    conflicts: [],
  };
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, "http://fixture"),
      route = url.pathname;
    requests.push({ method: request.method, route });
    const json = (value, code = 200) => {
      response.writeHead(code, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      response.end(JSON.stringify(value));
    };
    try {
      if (route === "/api/preferences") {
        if (request.method === "POST") {
          let body = "";
          for await (const chunk of request) body += chunk;
          preferences = { ...JSON.parse(body), revision: preferences.revision + 1 };
        }
        return json(preferences);
      }
      if (request.method !== "GET") {
        writes.push({ method: request.method, route });
        return json({ error: "Read-only fixture" }, 405);
      }
      if (route === "/api/source") {
        const name = url.searchParams.get("path"),
          selected = url.searchParams.get("recording");
        if (selected && selected !== recording.id)
          return json({ error: "Recording identity mismatch" }, 409);
        if (!Object.hasOwn(recording.sources || {}, name))
          return json({ error: "Source not retained" }, 404);
        return json({ source: recording.sources[name], build_id: recording.build_id });
      }
      if (route === "/api/view")
        return json({ ...displayed.context, ...recording.final, events: recording.events });
      if (route === "/api/design") return json({ available: false });
      if (route === "/api/recordings")
        return json({
          active: null,
          recordings: [{ ...recording, events: recording.events.length }],
        });
      if (route === "/api/recordings/" + recording.id) return json(displayed);
      if (route.startsWith("/api/")) return json({ error: "Unavailable in saved recording" }, 404);
      const file = path.resolve(
        assets,
        route === "/graph" || route === "/" ? "index.html" : decodeURIComponent(route.slice(1)),
      );
      if (!file.startsWith(assets + path.sep)) return json({ error: "Unknown asset" }, 404);
      const body = await readFile(file);
      response.writeHead(200, {
        "Content-Type":
          { ".js": "text/javascript", ".css": "text/css", ".html": "text/html" }[
            path.extname(file)
          ] || "application/octet-stream",
        "Cache-Control": "no-store",
      });
      response.end(body);
    } catch (error) {
      json({ error: String(error) }, 404);
    }
  });
  await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
  return {
    recording,
    bytes,
    requests,
    writes,
    url: `http://127.0.0.1:${server.address().port}/graph`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}
