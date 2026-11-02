"""Exercise real application requests with delayed native capture transport."""
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import threading
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "observer_runtime"))

def clone(name):
    target = OUT / ".tmp" / ("queue-" + name + "-current")
    assert not target.exists()
    project = json.loads((ROOT / "bo_stategraph/project.json").read_text(encoding="utf-8"))
    for name in set(project["model"]["source_files"]) | {"bo_stategraph/project.json"}:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, path)
    shutil.copytree(ROOT / "bo_stategraph/policy", target / "bo_stategraph/policy", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("bo_contracts.py", "execution_contract.py"):
        shutil.copy2(ROOT / "bo_stategraph" / name, target / "bo_stategraph" / name)
    return target

def scenario(name):
    root = clone(name)
    from integrations.bo_integration import BOIntegration
    from app.web import create_app
    from tooling.observe import login, upload, post
    database = root / "var/team-files.sqlite3"
    os.environ["TEAM_FILES_DB_URL"] = "sqlite:///" + str(database)
    integration = BOIntegration(root, capacity=2 if name == "loss" else 8192)
    app = create_app(ROOT, database=database, bo_probe=integration.probe,
        bo_observer=integration, bo_data=integration.data)
    gate, entered = threading.Event(), threading.Event()
    native_sink = integration.probe.bo_sink
    try:
        clients = {actor: app.test_client() for actor in ("alice", "ben", "cara")}
        for actor, client in clients.items():
            login(client, actor)
        fid = upload(clients["alice"]).json["id"]
        assert post(clients["ben"], "/files/" + fid + "/review", {"decision": "approve"}).status_code == 200
        assert post(clients["alice"], "/files/" + fid + "/share", {"recipient_id": "cara"}).status_code == 200
        assert integration.probe.flush(10)
        if name == "timeout":
            integration.session.bo_bind_capture(scope_setter=integration.probe.bo_set_scope,
                flush_capture=lambda: integration.probe.flush(.05), health=integration.health)
        started = integration.session.recordings.start("Real queued request: " + name)
        repeated = integration.session.recordings.start("Repeated start")
        assert repeated["id"] == started["id"]
        before = integration.health()
        def delayed(value, kind):
            entered.set()
            assert gate.wait(15), "Test transport delay exceeded its bound"
            return native_sink(value, kind)
        integration.probe.bo_sink = delayed
        response = clients["cara"].get("/files/" + fid + "/download")
        assert response.status_code == 200 and response.data
        assert entered.wait(2)
        queued = integration.health()
        assert queued["pending"] > 0
        if name == "success":
            result = {}
            def stop():
                result["value"] = integration.session.recordings.stop()
            thread = threading.Thread(target=stop)
            thread.start()
            time.sleep(.1)
            waited = thread.is_alive()
            assert waited, "Stop acknowledged before its actual queue drained"
            gate.set()
            thread.join(10)
            assert not thread.is_alive()
            stopped = result["value"]
        else:
            waited = None
            if name == "loss":
                assert queued["dropped"] > before["dropped"]
                gate.set()
                assert integration.probe.flush(10)
            stopped = integration.session.recordings.stop()
        value = integration.session.recordings.get(started["id"])
        (OUT / ("queue-" + name + "-recording.json")).write_text(json.dumps(value, indent=2), encoding="utf-8")
        if name == "success":
            assert value["status"] == "stopped" and not value["gaps"]
            assert any(event["node"] == "http_request" and event["phase"] == "return" for event in value["events"])
        else:
            assert value["status"] == "interrupted" and value["gaps"]
        assert integration.probe.bo_capture_nodes is None
        gate.set()
        assert integration.probe.flush(10)
        return {"case": name, "valid": True, "actual_http_status": response.status_code,
            "download_bytes": len(response.data), "before": before, "queued": queued,
            "stop_waited_for_queue": waited, "status": value["status"], "gaps": value["gaps"],
            "events": len(value["events"]), "settlement": value.get("producer_settlement"),
            "capture_restored": True, "final_health": integration.health()}
    finally:
        gate.set()
        integration.close()
        app.extensions["trial_store"].engine.dispose()

def main():
    results = []
    for name in ("success", "timeout", "loss"):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), name], capture_output=True, text=True, encoding="utf-8")
        (OUT / ("queue-" + name + ".stdout.log")).write_text(result.stdout, encoding="utf-8")
        (OUT / ("queue-" + name + ".stderr.log")).write_text(result.stderr, encoding="utf-8")
        assert result.returncode == 0, result.stderr[-3000:]
        results.append(json.loads(result.stdout))
        (OUT / "queue-cases.json").write_text(json.dumps({"valid": True, "cases": results,
            "boundary": "Actual Flask request, canonical probe/session/recorder and delayed real native sink in isolated project copies."}, indent=2), encoding="utf-8")
    print(json.dumps({"valid": True, "cases": [{"case": row["case"], "status": row["status"]} for row in results]}))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(scenario(sys.argv[1])))
    else:
        main()
