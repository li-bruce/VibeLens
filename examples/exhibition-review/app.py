"""Same-origin frontend/backend demo; application routes stay outside VibeLens."""

import argparse
import json
from pathlib import Path
import sys
import threading
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine


def upload(gallery, values):
    """POST /app/upload: submit a versioned PNG for review."""
    return gallery.upload(**values)


def preview(gallery, values):
    """POST /app/preview: open the current image as a reviewer."""
    return gallery.preview(**values)


def approve(gallery, values):
    """POST /app/approve: apply the version the reviewer actually opened."""
    return gallery.approve(**values)


def public(gallery, values):
    """POST /app/public: load the real exhibition and message list."""
    return gallery.repository.public()


def serve(root, skill, port):
    """Start one local server, using canonical VibeLens routes and viewer assets."""
    sys.path.insert(0, str(skill / "scripts"))
    from bo_observer.service import GraphSession, make_server
    from bo_observer.graph.behavior_model import read
    from bo_integration import BOObservation
    from domain import Gallery
    from repository import Repository

    session = GraphSession(root)
    engine = create_engine("sqlite:///" + (root / "gallery.sqlite").as_posix())
    repository = Repository(engine)
    observation = BOObservation(session, engine, read(root / "bo_stategraph/databases.json"))
    repository.bo = observation
    gallery = Gallery(repository, observation)
    lock = threading.RLock()
    server = make_server(session, port, assets=skill / "assets/stategraph-viewer")
    session.program_url = f"http://127.0.0.1:{port}/app"
    base = server.RequestHandlerClass
    handlers = {
        "/app/upload": ("upload", upload),
        "/app/preview": ("review", preview),
        "/app/approve": ("publish", approve),
        "/app/public": ("exhibit", public),
    }

    class Handler(base):
        """Serve the small application without logging observer requests as business events."""

        revision = 0

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in {"/app", "/app.js"}:
                name = "index.html" if path == "/app" else "app.js"
                return self.reply(
                    200,
                    (root / "web" / name).read_bytes(),
                    "text/html" if name.endswith("html") else "text/javascript",
                )
            if path == "/artwork.png":
                version = int(parse_qs(urlsplit(self.path).query)["version"][0])
                with lock, observation.request("exhibit", {}):
                    content = repository.image(version)
                    Handler.revision += 1
                    observation.finish("exhibit", {}, repository, Handler.revision)
                return self.reply(200 if content else 404, content or b"", "image/png")
            return super().do_GET()

        def do_POST(self):
            if self.path not in handlers:
                return super().do_POST()
            if not self.permitted():
                return self.reply(403, {"error": "same-origin only"})
            node, handler = handlers[self.path]
            values = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            with lock, observation.request(node, values):
                result = handler(gallery, values)
                Handler.revision += 1
                observation.finish(node, result, repository, Handler.revision)
            return self.reply(200, result)

    server.RequestHandlerClass = Handler
    print(
        json.dumps({"application": session.program_url, "graph": f"http://127.0.0.1:{port}/graph"}),
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        observation.close()
        session.close()
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8894)
    args = parser.parse_args()
    serve(args.root.resolve(), args.skill.resolve(), args.port)
