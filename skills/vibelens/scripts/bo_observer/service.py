"""Local HTTP transport for read-only graph inspection and observation ingestion.

GraphSession remains re-exported for existing launchers. SessionHost keeps each
request on one build while reloads retire old sessions only after their borrowers
finish. No route invokes an application business command.
"""

from functools import wraps
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
from urllib.parse import urlsplit, parse_qs
from .observation.session import GraphSession
from .session_lifecycle import SessionHost

try:
    from ..view_preferences import PreferenceConflict
    from ..bo_web import ASSETS
except ImportError:
    from view_preferences import PreferenceConflict
    from bo_web import ASSETS


def make_server(session, port=8830, *, token=None, origins=(), assets=ASSETS):
    """Create a localhost collector and viewer with explicit origin and ingestion-token checks."""
    token = token or secrets.token_urlsafe(32)
    origins = frozenset(origins)
    if any(
        urlsplit(o).scheme not in ("http", "https")
        or urlsplit(o).hostname not in ("localhost", "127.0.0.1")
        or urlsplit(o).path
        for o in origins
    ):
        raise ValueError("collector origins must be explicit local development origins")
    assets = Path(session.web.assets if assets == ASSETS else assets).resolve()
    session.program_url = next(iter(origins)) if len(origins) == 1 else None
    host = SessionHost(
        session,
        lambda previous: GraphSession(
            previous.root, previous.path.relative_to(previous.root).as_posix()
        ),
    )

    def consistent_request(method):
        """Finish each request against one session while a watcher may replace the build."""

        @wraps(method)
        def handle(handler):
            with host.borrow() as current:
                return method(handler, current)

        return handle

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def permitted(self, ingest=False):
            """Validate local Host/Origin and require the collector token only for ingestion."""
            if self.headers.get("Host") not in {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }:
                return False
            origin = self.headers.get("Origin")
            allowed = (
                not origin
                or origin == "http://" + self.headers["Host"]
                or ingest
                and origin in origins
            )
            return allowed and (
                not ingest or secrets.compare_digest(self.headers.get("X-BO-Token", ""), token)
            )

        def reply(self, code, body, mime="application/json"):
            """Serialize JSON or asset bytes with explicit local-origin and no-cache headers."""
            raw = (
                body
                if isinstance(body, bytes)
                else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            )
            self.send_response(code)
            for k, v in [
                ("Content-Type", mime + "; charset=utf-8"),
                ("Content-Length", str(len(raw))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
            ]:
                self.send_header(k, v)
            origin = self.headers.get("Origin")
            if origin in origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self):
            """Grant preflight only to the explicitly configured application origins."""
            if self.headers.get("Origin") not in origins:
                return self.reply(403, {"error": "origin denied"})
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Access-Control-Allow-Methods", "POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type,X-BO-Token")
            self.send_header("Vary", "Origin")
            self.end_headers()

        @consistent_request
        def do_GET(self, session):
            """Read one borrowed build; health remains available when the debug UI is hidden."""
            if not self.permitted():
                return self.reply(403, {"error": "local same-origin only"})
            path = urlsplit(self.path).path
            try:
                if path == "/api/bo/health":
                    return self.reply(
                        200,
                        {
                            "protocol": "bo-project/v1",
                            "project_id": session.project["project_id"],
                            "build_id": session.manifest["build_id"],
                            "binding": session.binding(),
                        },
                    )
                if not session.web.allowed(path):
                    return self.reply(
                        404, {"error": "Debug Web is disabled", "code": "bo_web_disabled"}
                    )
                if path == "/api/view":
                    return self.reply(200, session.view())
                if path.startswith("/api/code/"):
                    return self.reply(200, session.web.get(self.path))
                if path in ("/api/stategraph", "/api/stategraph/export"):
                    return self.reply(200, session.export())
                if path == "/api/preferences":
                    return self.reply(200, session.preferences.read())
                if path == "/api/design":
                    return self.reply(200, session.web.design.snapshot())
                if path == "/api/versions":
                    return self.reply(200, [])
                if path == "/api/recordings":
                    return self.reply(200, session.recordings.list())
                if path.startswith("/api/recordings/"):
                    return self.reply(200, session.recordings.get(path.rsplit("/", 1)[-1]))
                if path == "/api/source":
                    q = parse_qs(urlsplit(self.path).query)
                    name = q.get("path", [""])[0]
                    sources = (
                        session.recordings.get(q["recording"][0])["sources"]
                        if q.get("recording")
                        else session.recordings.sources
                    )
                    if name not in sources:
                        return self.reply(404, {"error": "Source not in this build"})
                    return self.reply(
                        200, {"source": sources[name], "build_id": session.manifest["build_id"]}
                    )
                name = "index.html" if path in ("/", "/graph", "/graph/") else path[1:]
                if "/" in name or "\\" in name or name.startswith("."):
                    return self.reply(404, {"error": "not found"})
                file = assets / name
                if not file.is_file():
                    return self.reply(404, {"error": "not found"})
                return self.reply(
                    200,
                    file.read_bytes(),
                    mimetypes.guess_type(name)[0] or "application/octet-stream",
                )
            except (OSError, ValueError, KeyError) as exc:
                return self.reply(400, {"error": str(exc)})

        @consistent_request
        def do_POST(self, session):
            """Accept observations or viewer settings; never dispatch application commands."""
            path = urlsplit(self.path).path
            ingest = path.startswith("/api/bo/")
            if not self.permitted(ingest):
                return self.reply(403, {"error": "origin or collector token denied"})
            try:
                if not ingest and not session.web.allowed(path):
                    return self.reply(
                        404, {"error": "Debug Web is disabled", "code": "bo_web_disabled"}
                    )
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= (24576 if ingest else 2 * 1024 * 1024):
                    raise ValueError("invalid payload size")
                body = json.loads(self.rfile.read(size))
                if path == "/api/bo/events":
                    return self.reply(200, session.event(body))
                if path == "/api/bo/snapshots":
                    return self.reply(200, session.snapshot(body))
                if path == "/api/preferences":
                    return self.reply(200, session.preferences.save(body))
                if path == "/api/recordings/start":
                    return self.reply(
                        200, session.recordings.start(body.get("label", ""), body.get("scope"))
                    )
                if path == "/api/recordings/stop":
                    return self.reply(200, session.recordings.stop())
                if path == "/api/recordings/clear":
                    return self.reply(200, session.recordings.clear(body.get("id")))
                return self.reply(405, {"error": "No business commands are exposed"})
            except PreferenceConflict as exc:
                return self.reply(409, {"error": str(exc)})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                if ingest:
                    with session.lock:
                        session.errors += 1
                        session.last_error = str(exc)
                return self.reply(400, {"error": str(exc)})

    class SessionServer(ThreadingHTTPServer):
        def server_close(self):
            """Retire the session host only after the HTTP server has closed."""
            super().server_close()
            host.close()

    server = SessionServer(("127.0.0.1", port), Handler)
    server.bo_token = token
    server.bo_session = session

    def reload_session():
        """Load current declarations without transferring obsolete events or machine instances."""
        changed = host.reload()
        server.bo_session = host.current
        return changed

    server.bo_reload = reload_session
    return server
