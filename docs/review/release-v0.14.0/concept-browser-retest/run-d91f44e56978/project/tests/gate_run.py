"""Run independent HTTP effects with working, disabled and unavailable observation."""

# These portable entrypoints load the explicitly selected Skill before importing it.
# ruff: noqa: E402

import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SKILL = Path(os.environ["VIBELENS_SKILL"]).resolve()
sys.path.insert(0, str(SKILL / "scripts"))

from werkzeug.serving import make_server
from app import create_app
from service import FileService
from acceptance_run import request
from bo_integration import BOIntegration
from bo_projection import bo_native_state
from bo_observer.service import GraphSession
from mapping_contract import instance_witnesses


def exercise(case, mode):
    """Keep every case isolated; errors are actual final Flask responses."""
    with tempfile.TemporaryDirectory(dir=ROOT / "var") as folder:
        files = FileService(Path(folder))
        session = GraphSession(ROOT)
        integration = BOIntegration(ROOT, session, files, mode=mode)
        app = create_app(files)
        integration.bo_bind_flask(app)
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            assert request(base, "/")[0] == 200
            assert request(base, "/api/files/missing/download", actor="Bob")[0] == 404
            assert (
                request(
                    base, "/api/files", body=b"", content_type="multipart/form-data; boundary=empty"
                )[0]
                == 400
            )
            multipart = (
                b'--trial\r\nContent-Disposition: form-data; name="file"; filename="notes.txt"\r\n'
                b"Content-Type: text/plain\r\n\r\nTeam notes\r\n--trial--\r\n"
            )
            status, uploaded = request(
                base,
                "/api/files",
                body=multipart,
                content_type="multipart/form-data; boundary=trial",
            )
            assert status == 201
            file_id = uploaded["file_id"]
            assert (Path(folder) / file_id).read_bytes() == b"Team notes"
            denied, _ = request(
                base, f"/api/files/{file_id}/share", actor="Carol", body={"recipient": "Bob"}
            )
            assert denied == 403
            assert request(base, f"/api/files/{file_id}/share", body={"recipient": "Bob"})[0] == 200
            # Exercise independent grants and a repeat share of the same recipient.
            assert (
                request(base, f"/api/files/{file_id}/share", body={"recipient": "Carol"})[0] == 200
            )
            assert request(base, f"/api/files/{file_id}/download", actor="Bob")[0] == 200
            assert request(base, f"/api/files/{file_id}/download", actor="Carol")[0] == 200
            assert request(base, f"/api/files/{file_id}/share", body={"recipient": "Bob"})[0] == 200
            assert len(request(base, "/api/received", actor="Bob")[1]) == 1
            integration.probe.flush(30)
            if mode == "on":
                instances = session.graph.bo_instances()
                current = next(
                    item["observed"]
                    for item in instances
                    if item["observed"]["instance_id"]
                    == integration.probe.bo_run
                    + ":"
                    + json.dumps([file_id, "Bob"], separators=(",", ":"))
                )
                with closing(sqlite3.connect(files.database)) as connection:
                    active, revision = connection.execute(
                        "SELECT active, revision FROM grants WHERE file_id=? AND recipient=?",
                        (file_id, "Bob"),
                    ).fetchone()
                assert (
                    current["state"] == "active" and active == 1 and current["revision"] == revision
                )
            allowed, data = request(base, f"/api/files/{file_id}/download", actor="Bob")
            assert allowed == 200 and data == b"Team notes"
            assert (
                request(base, f"/api/files/{file_id}/revoke", body={"recipient": "Bob"})[0] == 200
            )
            rejected, _ = request(base, f"/api/files/{file_id}/download", actor="Bob")
            assert rejected == 403
            # This native read is made by the denial path before its response,
            # not reconstructed from the graph or the final database snapshot.
            read = integration.fact_reads[-1]
            assert read["active"] is False and read["actor"] == "Bob"
            carol_status, carol_content = request(
                base, f"/api/files/{file_id}/download", actor="Carol"
            )
            assert carol_status == 200 and carol_content == b"Team notes"
            assert request(base, "/api/received", actor="Bob")[1] == []
            integration.probe.flush(30)
            health = {**integration.probe.bo_health(), "data_errors": integration.data.bo_errors}
            if mode == "on":
                assert health["errors"] == health["dropped"] == health["data_errors"] == 0, (
                    health,
                    integration.transport_errors,
                )
            elif mode == "fault":
                assert health["errors"] > 0, health
            events = session.history.snapshot()
            if mode == "off":
                assert not events
            if mode == "on":
                statuses = {
                    (event["node"], event.get("outputs", {}).get("status"))
                    for event in events
                    if event["phase"] == "return"
                }
                assert {
                    ("http.download", 404),
                    ("http.download", 403),
                    ("http.upload", 400),
                } <= statuses
                entries = {event["call_id"] for event in events if event["phase"] == "enter"}
                exits = {
                    event["call_id"] for event in events if event["phase"] in {"return", "error"}
                }
                assert entries == exits
            baseline = len(events)
            for _ in range(3):
                session.view()
            assert len(session.history.snapshot()) == baseline
            build = session.manifest["build_id"]
            # Read SQLite independently for comparison with the separate
            # adapter's complete-state export in every probe mode.
            with closing(sqlite3.connect(files.database)) as connection:
                rows = connection.execute(
                    "SELECT file_id, recipient, active, revision FROM grants"
                ).fetchall()
            actual = [
                {
                    "id": json.dumps([ident, recipient], separators=(",", ":")),
                    "state": "active" if active else "inactive",
                    "revision": revision,
                    "build_id": build,
                }
                for ident, recipient, active, revision in rows
            ]
            machine = bo_native_state(files.database, build)
            exported = session.graph.bo_export(runtime={"machine": machine})
            fields = {
                "actor-id": "actor",
                "owner-id": "owner",
                "recipient-id": "recipient",
                "active-grant": "active",
            }
            values = {
                "status": {"owner-only": denied, "revoke-denies-old-link": rejected}.get(
                    case, allowed
                ),
                "carol_status": carol_status,
                "bob_status": rejected,
                "reads": {
                    fact: {
                        "node": "facts",
                        "direction": "out",
                        "field": field,
                        "read_basis": {"timing": read["timing"], "scope": read["scope"]},
                    }
                    for fact, field in fields.items()
                },
            }
            run = {
                "case": case,
                "mode": mode,
                "observations": values,
                "events": events,
                "policy_evaluations": integration.evaluations if mode == "on" else [],
                "probe_health": health,
                "native": {"grants": actual},
                "projection": {
                    "build_id": build,
                    "machine": machine,
                    "instances": exported["instances"],
                },
            }
            checks = instance_witnesses(
                exported["instances"],
                {
                    row["id"]: {key: row[key] for key in ("state", "revision", "build_id")}
                    for row in actual
                },
                case=case + ":" + mode,
                source="Independent SELECT on SQLite grants",
            )
            return run, exported, checks
        finally:
            server.shutdown()
            integration.close()


def main():
    """Emit exactly the canonical observation payload on stdout for change_sync."""
    runs, checks, public = [], [], None
    for case in (
        "roundtrip",
        "owner-only",
        "allowed-download",
        "revoke-denies-old-link",
        "other-recipient-retained",
    ):
        for mode in ("on", "off", "fault"):
            run, exported, actual_checks = exercise(case, mode)
            runs.append(run)
            checks.extend(actual_checks)
            if (case, mode) == ("roundtrip", "on"):
                public = exported
    value = {
        "build_id": public["build_id"],
        "machine": public["model"]["machine"],
        "stategraph_export": public,
        "runs": runs,
        "mapping_checks": checks,
    }
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
