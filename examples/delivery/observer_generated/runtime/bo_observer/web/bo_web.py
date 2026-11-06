"""Optional graph Web surface: design dialogue, visibility and core delivery.

This module never imports the business engine. Disabling Web is independent of
collection, Python state queries and executable state definitions.
"""

import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import urlsplit, parse_qs
from ..code_graph.service import CodeGraph
from ..control.scope import ControlScope

try:
    from ...bo_design import BODesign
    from ...behavior_model import contained
    from ...requirements_dialogue import read
    from ...sync_io import write
    from ...view_preferences import Preferences, PreferenceConflict, file_lock
    from ...observation_scope import observer_route
except ImportError:
    from bo_design import BODesign
    from behavior_model import contained
    from requirements_dialogue import read
    from sync_io import write
    from view_preferences import Preferences, PreferenceConflict, file_lock
    from observation_scope import observer_route


ASSETS = Path(__file__).resolve().parents[3] / "assets/stategraph-viewer"
MODES = {"visible", "hidden", "disabled"}


class BOHTTPServer(ThreadingHTTPServer):
    """Queue a cold module/worker burst while the local accept thread is scheduled."""

    request_queue_size = 64


def bo_content_type(mime):
    """Keep binary MIME exact for streaming WASM; declare UTF-8 only for text."""
    textual = mime.startswith("text/") or mime in {
        "application/json",
        "application/javascript",
        "application/xml",
        "image/svg+xml",
    }
    return mime + "; charset=utf-8" if textual else mime


class BOWeb:
    def __init__(self, root, *, assets=ASSETS, discovery=None, graph_routes=("/graph", "/graph/")):
        self.root = Path(root).absolute().resolve()
        self.assets = Path(assets)
        if self.assets == ASSETS and not self.assets.is_dir():
            self.assets = next(
                (
                    self.root / p
                    for p in ("static/graph", "observer_generated/static", "integrations/bo_view")
                    if (self.root / p / "index.html").is_file()
                ),
                self.assets,
            )
        self.config = contained(self.root, "bo_stategraph/config/web.json")
        self.design = BODesign(self.root, discovery)
        self.graph_routes = set(graph_routes)
        self.code_graph = CodeGraph(self.root)
        # API entrypoints are part of normal observation. Reading their small
        # projection must not opt the project into a persisted full code index.
        self.bo_api_graph = CodeGraph(self.root, persist=False)
        self.control = ControlScope(self.root)
        self.control_view = None
        self.control_recording = None
        self.explanations = None
        self.explanation_lock = threading.Lock()

    def explanation_reply(self, path, value=None):
        """Serve display-only AI jobs through the same local observer boundary."""
        parsed = urlsplit(path)
        if parsed.path != "/api/explanations":
            return None
        from ..explanations.service import Explanations
        from ..explanations.context import revision

        # Concurrent tabs share one bounded job registry, including first use.
        with self.explanation_lock:
            if self.explanations is None:
                self.explanations = Explanations.configured(self.explanation_context)
        if value is not None:
            return self.explanations.start(value)
        identity = parse_qs(parsed.query).get("job", [None])[0]
        if identity:
            return self.explanations.get(identity)
        view = self.explanation_context()
        return {
            **self.explanations.status(),
            "revision": revision(view),
            "build_id": view.get("manifest", {}).get("build_id"),
            "concept_revision": view.get("concept_structure", {}).get("revision"),
            "code_revision": view.get("code_structure", {}).get("revision"),
        }

    def explanation_context(self):
        """Reuse the already refreshed API index for optional code-node details.

        The code inventory has the same source scope as the visible API tree.
        Accessing a detail neither enables a persisted full index nor scans a
        second source tree. Only a bounded node packet reaches the provider.
        """
        view = self.control_context()
        if self.bo_api_graph.graph:
            view["code_structure"] = deepcopy(self.bo_api_graph.graph)
        return view

    def post(self, path, value):
        """Dispatch observer controls and explanation jobs, never business commands."""
        explanation = self.explanation_reply(path, value)
        return explanation if explanation is not None else self.control_reply(path, value)

    def close(self):
        """Retire display jobs when their build or server is closed."""
        if self.explanations:
            self.explanations.close()

    def preferences_for(self, path, fallback):
        """Use a conversation's private view file only for an explicitly scoped URL."""
        session = parse_qs(urlsplit(path).query).get("vl_session", [None])[0]
        return self.control.preferences(session, fallback) if session else fallback

    def control_context(self):
        """Return graph/build evidence without transferring unrelated runtime history.

        Standard sessions expose a static-only query. Existing custom integrations
        keep their view callback. Bound concepts and source/API inventories must
        survive this boundary, so conversation controls select the same graph as
        the page without receiving events, parameter values or runtime frames.
        """
        if not self.control_view:
            raise ValueError("This observer integration has not connected its control view")
        owner = getattr(self.control_view, "__self__", None)
        query = getattr(owner, "control_context", None)
        view = query() if callable(query) else self.control_view()
        return {
            "schema": "vibelens-control-context/v1",
            **deepcopy(
                {
                    key: view[key]
                    for key in (
                        "stage",
                        "layout_id",
                        "model",
                        "manifest",
                        "concept_structure",
                        "project_structure",
                        "api_structure",
                        "code_structure",
                    )
                    if key in view
                }
            ),
        }

    def control_reply(self, path, value=None):
        """Control polling and acknowledgements never execute a business operation."""
        parsed = urlsplit(path)
        if parsed.path != "/api/vibelens/control":
            return None
        session = parse_qs(parsed.query).get("vl_session", [None])[0]
        if value is not None:
            return self.control.acknowledge(session, value)
        result = self.control.for_view(session)
        if result["plan"]:
            from ..control.selection import validate_evidence

            try:
                if not self.control_view:
                    raise ValueError("This observer integration has not connected its control view")
                plan = result["plan"]
                recording = (
                    self.control_recording(plan["recording"]["id"])
                    if plan["recording"] and self.control_recording
                    else None
                )
                validate_evidence(plan, self.control_context(), recording)
            except (ValueError, KeyError, TypeError) as error:
                result["result"] = {
                    "revision": result["revision"],
                    "status": "rejected",
                    "view_id": "",
                    "nodes": [],
                    "events": [],
                    "error": str(error)[:1000],
                }
                self.control.acknowledge(session, result["result"])
                result["plan"] = None
        return result

    def status(self):
        value = read(self.config) if self.config.exists() else {"schema": 1, "mode": "visible"}
        if (
            not isinstance(value, dict)
            or value.get("schema") != 1
            or value.get("mode") not in MODES
            or set(value) != {"schema", "mode"}
        ):
            raise ValueError("Invalid Web configuration; mode must be visible, hidden, or disabled")
        return {
            **value,
            "entry_visible": value["mode"] == "visible",
            "enabled": value["mode"] != "disabled",
        }

    def set_mode(self, mode):
        if mode not in MODES:
            raise ValueError("Unknown Web mode")
        with file_lock(self.config.with_suffix(".lock")):
            self.status()  # Do not replace a malformed configuration silently.
            write(self.config, {"schema": 1, "mode": mode})
        return self.status()

    def is_observer_request(self, path):
        path = urlsplit(path).path
        return (
            path in self.graph_routes
            or observer_route(path)
            or path.startswith("/")
            and "/" not in path[1:]
            and (self.assets / path[1:]).is_file()
        )

    def allowed(self, path):
        return not self.is_observer_request(path) or self.status()["enabled"]

    def entry_html(self, raw):
        if self.status()["entry_visible"]:
            return raw
        return raw.replace(b"data-bo-entry", b"data-bo-entry hidden")

    def get(self, path):
        explanation = self.explanation_reply(path)
        if explanation is not None:
            return explanation
        control = self.control_reply(path)
        if control is not None:
            return control
        parsed = urlsplit(path)
        if parsed.path == "/api/vibelens/control/context":
            return self.control_context()
        if parsed.path == "/api/code/graph":
            query = parse_qs(parsed.query)
            return self.code_graph.view(
                focus=query.get("focus", [None])[0],
                depth=int(query.get("depth", [1])[0]),
                limit=int(query.get("limit", [400])[0]),
                projection=query.get("projection", ["all"])[0],
            )
        if parsed.path == "/api/code/source":
            query = parse_qs(parsed.query)
            return self.code_graph.source(
                query.get("path", [""])[0], query.get("revision", [""])[0]
            )
        if parsed.path == "/api/design":
            return self.design.snapshot()
        return None


def bo_serve(root, *, port=8830, discovery=None, assets=ASSETS):
    web = BOWeb(root, assets=assets, discovery=discovery, graph_routes=("/", "/graph", "/graph/"))
    root = web.root
    initial = web.design.view()  # Validate before listening; no fabricated business engine.
    web.control_view = web.design.view
    if not web.status()["enabled"]:
        raise ValueError("Web is disabled; restore it with mode visible")
    cfg = read(Path(root) / "sync.json") if (Path(root) / "sync.json").exists() else {}
    preferences = Preferences(
        root, initial["layout_id"], legacy_project_ids=cfg.get("view_preferences_legacy_ids", [])
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, body, mime="application/json"):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            for key, value in [
                ("Content-Type", bo_content_type(mime)),
                ("Content-Length", str(len(raw))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
            ]:
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(raw)

        def local(self):
            hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            return self.headers.get("Host") in hosts and (
                not origin or origin == "http://" + self.headers["Host"]
            )

        def do_GET(self):
            if not self.local():
                return self.reply(403, {"error": "Only local same-origin requests are accepted"})
            path = urlsplit(self.path).path
            try:
                if not web.allowed(path):
                    return self.reply(
                        404, {"error": "Debug Web is disabled", "code": "bo_web_disabled"}
                    )
                value = web.get(self.path)
                if value is not None:
                    return self.reply(200, value)
                if path == "/api/view":
                    return self.reply(200, web.design.view())
                if path == "/api/preferences":
                    return self.reply(200, web.preferences_for(self.path, preferences).read())
                name = "index.html" if path in web.graph_routes else path[1:]
                if not name or "/" in name or "\\" in name or name.startswith("."):
                    return self.reply(404, {"error": "Page not found"})
                file = web.assets / name
                if not file.is_file():
                    return self.reply(404, {"error": "Page not found"})
                return self.reply(
                    200,
                    file.read_bytes(),
                    mimetypes.guess_type(name)[0] or "application/octet-stream",
                )
            except (OSError, ValueError) as exc:
                return self.reply(400, {"error": str(exc)})

        def do_POST(self):
            if not self.local():
                return self.reply(403, {"error": "Only local same-origin requests are accepted"})
            path = urlsplit(self.path).path
            try:
                if not web.allowed(path):
                    return self.reply(
                        404, {"error": "Debug Web is disabled", "code": "bo_web_disabled"}
                    )
                size = int(self.headers.get("Content-Length", 0))
                limit = 2 * 1024 * 1024 if path == "/api/preferences" else 32768
                if not 0 < size <= limit:
                    raise ValueError("Invalid request size")
                value = json.loads(self.rfile.read(size))
                if not isinstance(value, dict):
                    raise ValueError("The request must be an object")
                control = web.post(self.path, value)
                if control is not None:
                    return self.reply(200, control)
                if path == "/api/preferences":
                    return self.reply(200, web.preferences_for(self.path, preferences).save(value))
                return self.reply(
                    405,
                    {"error": "The graph is read-only; request changes in the coding conversation"},
                )
            except PreferenceConflict as exc:
                return self.reply(409, {"error": str(exc)})
            except (OSError, ValueError) as exc:
                return self.reply(400, {"error": str(exc)})

    server = BOHTTPServer(("127.0.0.1", port), Handler)
    print(f"Design graph: http://127.0.0.1:{server.server_port}/graph", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        web.close()
        server.server_close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["serve", "status", "mode", "package"])
    p.add_argument("mode", nargs="?", choices=sorted(MODES))
    p.add_argument("--root", default=".")
    p.add_argument("--port", type=int, default=8830)
    p.add_argument("--assets", type=Path, default=ASSETS)
    p.add_argument("--discovery")
    p.add_argument("--out")
    a = p.parse_args()
    try:
        if a.action == "serve":
            bo_serve(a.root, port=a.port, discovery=a.discovery, assets=a.assets)
            return 0
        if a.action == "package":
            if not a.out:
                raise ValueError("package requires --out with a new ZIP path inside the project")
            return subprocess.call(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[2] / "architecture_guard.py"),
                    "package",
                    "--root",
                    a.root,
                    "--out",
                    a.out,
                ]
            )
        web = BOWeb(a.root)
        if a.action == "mode" and not a.mode:
            raise ValueError("Select a Web mode")
        print(
            json.dumps(
                web.set_mode(a.mode) if a.action == "mode" else web.status(), ensure_ascii=False
            )
        )
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
