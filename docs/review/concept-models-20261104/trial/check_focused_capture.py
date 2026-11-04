"""Exercise a focused recording against the trial's actual Flask HTTP response."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading


def main():
    """Preserve transport errors and collector receipts without weakening health."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args()
    root, skill = options.project.resolve(), options.skill.resolve()
    sys.path[:0] = [str(root / "tests"), str(root), str(skill / "scripts")]
    os.environ["BO_TRIAL_DATABASE_URL"] = "sqlite:///var/files.sqlite3"

    from acceptance_run import request
    from app import create_app
    from service import FileService
    from bo_integration import BOIntegration
    from bo_observer.service import GraphSession
    from werkzeug.serving import make_server

    with tempfile.TemporaryDirectory(dir=root / "var") as folder:
        session = GraphSession(root)
        files = FileService(Path(folder))
        integration = BOIntegration(root, session, files)
        app = create_app(files)
        integration.bo_bind_flask(app)
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            multipart = (
                b'--trial\r\nContent-Disposition: form-data; name="file"; filename="notes.txt"\r\n'
                b"Content-Type: text/plain\r\n\r\nTeam notes\r\n--trial--\r\n"
            )
            uploaded_status, uploaded = request(
                base,
                "/api/files",
                body=multipart,
                content_type="multipart/form-data; boundary=trial",
            )
            integration.probe.flush(30)
            recording = session.recordings.start(scope={"mode": "focused", "roots": ["share"]})
            response_status, response = request(
                base,
                f"/api/files/{uploaded['file_id']}/share",
                body={"recipient": "Bob"},
            )
            integration.probe.flush(30)
            session.recordings.stop()
            saved = session.recordings.get(recording["id"])
            # An entirely unselected grant must remain eligible for its first
            # real state read after the user restores full capture.
            identity = json.dumps([uploaded["file_id"], "Carol"], separators=(",", ":"))
            integration.probe.bo_set_scope(["upload"])
            carol_share, _ = request(
                base, f"/api/files/{uploaded['file_id']}/share", body={"recipient": "Carol"}
            )
            integration.probe.flush(30)
            initialized_while_hidden = identity in integration.bo_initialized
            integration.probe.bo_set_scope(None)
            carol_download, content = request(
                base, f"/api/files/{uploaded['file_id']}/download", actor="Carol"
            )
            bob_download, _ = request(
                base, f"/api/files/{uploaded['file_id']}/download", actor="Bob"
            )
            integration.probe.flush(30)
            resumed = next(
                (
                    entry["observed"]
                    for entry in session.graph.bo_instances()
                    if entry["observed"]["instance_id"] == integration.probe.bo_run + ":" + identity
                ),
                None,
            )
            scope_restored = (
                carol_share == carol_download == bob_download == 200
                and content == b"Team notes"
                and not initialized_while_hidden
                and resumed is not None
                and resumed["state"] == "active"
                and resumed["revision"] == 1
            )
            result = {
                "upload_status": uploaded_status,
                "response_status": response_status,
                "response": response,
                "recording": saved,
                "health": integration.probe.bo_health(),
                "transport_errors": integration.transport_errors,
                "scope_restore": {
                    "valid": scope_restored,
                    "initialized_while_hidden": initialized_while_hidden,
                    "observed": resumed,
                    "carol_share": carol_share,
                    "carol_download": carol_download,
                    "bob_download": bob_download,
                },
            }
            options.out.parent.mkdir(parents=True, exist_ok=True)
            options.out.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(
                json.dumps(
                    {
                        key: result[key]
                        for key in (
                            "upload_status",
                            "response_status",
                            "health",
                            "transport_errors",
                        )
                    }
                )
            )
            print(
                json.dumps(
                    {
                        "status": saved["status"],
                        "gaps": saved["gaps"],
                        "events": len(saved["events"]),
                    }
                )
            )
            return int(
                response_status != 200
                or bool(result["health"]["errors"])
                or saved["status"] != "stopped"
                or bool(saved["gaps"])
                or not scope_restored
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
            integration.close()
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
