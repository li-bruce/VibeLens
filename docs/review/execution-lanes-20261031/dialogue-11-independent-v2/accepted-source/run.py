"""Launch the local application and optional observer together."""
import argparse
import os
from pathlib import Path
import sys
import threading
ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT / "observer_runtime"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-port", type=int, default=8982)
    parser.add_argument("--graph-port", type=int, default=8983)
    parser.add_argument("--observer", choices=["on","off"], default="on")
    args = parser.parse_args()
    from app.web import create_app
    integration, server = None, None
    os.environ["TEAM_FILES_DB_URL"] = "sqlite:///" + str(ROOT / "var/team-files.sqlite3")
    if args.observer == "on":
        try:
            from integrations.bo_integration import BOIntegration
            from bo_observer.service import make_server
            integration = BOIntegration(ROOT)
            server = make_server(integration.session, port=args.graph_port, origins=[f"http://127.0.0.1:{args.app_port}"])
            threading.Thread(target=server.serve_forever, daemon=True).start()
        except Exception as error:
            if integration:
                integration.close()
            integration = None
            print("Observer unavailable: " + type(error).__name__, flush=True)
    app = create_app(ROOT, bo_probe=integration.probe if integration else None,
        bo_observer=integration, bo_data=integration.data if integration else None)
    if integration:
        integration.session.graph.bo_require_definition(app.extensions["trial_service"].workflow.machine)
    print(f"Application: http://127.0.0.1:{args.app_port}/", flush=True)
    print(f"VibeLens: http://127.0.0.1:{args.graph_port}/graph" if server else "VibeLens: unavailable/off", flush=True)
    try:
        app.run(host="127.0.0.1",port=args.app_port,debug=False,use_reloader=False,threaded=True)
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if integration:
            integration.close()

if __name__ == "__main__":
    main()
