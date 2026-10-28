"""Serve immutable real gallery captures for control/browser acceptance.

This fixture runs the actual control and preference services. It replays existing
execution evidence; it neither runs the gallery business engine nor emits events.
"""

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.web.bo_web import BOWeb, ASSETS
from bo_observer.web.view_preferences import Preferences, PreferenceConflict


def make_server(project):
    artifact = json.loads((ROOT / "docs/site/case-data/v1.json").read_text(encoding="utf-8"))
    project.mkdir(parents=True, exist_ok=True)
    definition = project / "bo_stategraph/project.json"
    definition.parent.mkdir(exist_ok=True)
    definition.write_text(
        json.dumps(
            {"project_id": artifact["view"]["layout_id"], "model": artifact["view"]["model"]}
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    web = BOWeb(project)
    web.control_view = lambda: deepcopy(artifact["view"])
    web.control_recording = lambda identity: (
        deepcopy(artifact["recording"]) if identity == artifact["recording"]["id"] else None
    )
    preferences = Preferences(project, artifact["view"]["layout_id"])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, value, status=200, mime="application/json"):
            raw = (
                value
                if isinstance(value, bytes)
                else json.dumps(value, ensure_ascii=False).encode()
            )
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            parsed = urlsplit(self.path)
            try:
                if parsed.path == "/favicon.ico":
                    return self.reply(
                        (ROOT / "docs/site/favicon.svg").read_bytes(), mime="image/svg+xml"
                    )
                if parsed.path == "/api/view":
                    return self.reply(artifact["view"])
                if parsed.path == "/api/preferences":
                    return self.reply(web.preferences_for(self.path, preferences).read())
                if parsed.path == "/api/design":
                    return self.reply({"available": False})
                if parsed.path == "/api/versions":
                    return self.reply([])
                if parsed.path == "/api/recordings":
                    return self.reply(artifact["catalog"])
                if parsed.path.startswith("/api/recordings/"):
                    value = web.control_recording(parsed.path.rsplit("/", 1)[-1])
                    return self.reply(
                        value if value else {"error": "Recording not found"}, 200 if value else 404
                    )
                if parsed.path in {"/api/source", "/api/code/source"}:
                    query = parse_qs(parsed.query)
                    return self.reply(
                        {
                            "source": artifact["sources"][query["path"][0]],
                            "build_id": artifact["provenance"]["build_id"],
                            "code_revision": artifact["code"]["revision"],
                        }
                    )
                if parsed.path == "/api/code/graph":
                    return self.reply(artifact["code"])
                value = web.get(self.path)
                if value is not None:
                    return self.reply(value)
                name = "index.html" if parsed.path in {"/", "/graph"} else parsed.path[1:]
                if not name or "/" in name or "\\" in name:
                    return self.reply({"error": "Not found"}, 404)
                path = ASSETS / name
                if not path.is_file():
                    return self.reply({"error": "Not found"}, 404)
                return self.reply(
                    path.read_bytes(),
                    mime=mimetypes.guess_type(path)[0] or "application/octet-stream",
                )
            except (OSError, ValueError, KeyError) as error:
                return self.reply({"error": str(error)}, 400)

        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 2 * 1024 * 1024:
                    raise ValueError("Invalid request size")
                body = json.loads(self.rfile.read(size))
                if urlsplit(self.path).path == "/api/preferences":
                    return self.reply(web.preferences_for(self.path, preferences).save(body))
                result = web.control_reply(self.path, body)
                if result is not None:
                    return self.reply(result)
                return self.reply(
                    {"error": "No business or recording writes in the capture fixture"}, 405
                )
            except PreferenceConflict as error:
                return self.reply({"error": str(error)}, 409)
            except (OSError, ValueError, KeyError, TypeError) as error:
                return self.reply({"error": str(error)}, 400)

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler), artifact


if __name__ == "__main__":
    project = Path(sys.argv[1]).resolve()
    server, artifact = make_server(project)
    print(
        json.dumps(
            {
                "url": "http://127.0.0.1:" + str(server.server_port),
                "project": str(project),
                "recording": artifact["recording"]["id"],
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
