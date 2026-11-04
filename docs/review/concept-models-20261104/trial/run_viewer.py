"""Run the independent trial application and the maintained VibeLens viewer."""

import argparse
import os
from pathlib import Path
import sys
import threading


def main():
    """Connect one real Flask application to one external observation session."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--graph-port", type=int, default=8919)
    parser.add_argument("--app-port", type=int, default=8920)
    args = parser.parse_args()
    root, skill = args.project.resolve(), args.skill.resolve()
    sys.path[:0] = [str(root), str(skill / "scripts")]
    os.environ["BO_TRIAL_DATABASE_URL"] = "sqlite:///var/files.sqlite3"

    from app import create_app
    from service import FileService
    from bo_integration import BOIntegration
    from bo_observer.service import GraphSession, make_server as graph_server
    from werkzeug.serving import make_server as app_server

    session = GraphSession(root)
    files = FileService(root / "var")
    integration = BOIntegration(root, session, files)
    app = create_app(files)
    integration.bo_bind_flask(app)
    application = app_server("127.0.0.1", args.app_port, app, threaded=True)
    viewer = graph_server(session, args.graph_port, origins=[f"http://127.0.0.1:{args.app_port}"])
    thread = threading.Thread(target=application.serve_forever, daemon=True)
    thread.start()
    print(f"Application: http://127.0.0.1:{args.app_port}/", flush=True)
    print(f"VibeLens: http://127.0.0.1:{args.graph_port}/graph?lang=zh-CN", flush=True)
    try:
        viewer.serve_forever()
    finally:
        application.shutdown()
        integration.close()
        viewer.server_close()


if __name__ == "__main__":
    main()
