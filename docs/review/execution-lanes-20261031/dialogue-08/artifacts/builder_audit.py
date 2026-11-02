"""Count native deferred builders during real application requests in an isolated DB.

This direct-probe test supplements the Web recording. It does not claim collector
validation or replace the separately retained HTTP/Web evidence.
"""
from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "observer_runtime"))
from app.web import create_app
from integrations.bo_integration import BOIntegration
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.data.runtime import BODataRuntime
from tooling.observe import login, upload, post

TARGET = "policy:actor_is_recipient"

def main():
    project = json.loads((ROOT / "bo_stategraph/project.json").read_text(encoding="utf-8-sig"))
    build = json.loads((OUT / "runtime-observations.json").read_text(encoding="utf-8"))["build_id"]
    captured = []
    probe = BOProbe(project, build, capacity=8192, sink=lambda body, kind: captured.append({"kind": kind, "body": body}))
    config = json.loads((ROOT / "bo_stategraph/databases.json").read_text(encoding="utf-8-sig"))
    data = BODataRuntime(probe, config)
    integration = BOIntegration.__new__(BOIntegration)
    integration.probe, integration.data = probe, data
    integration.session = SimpleNamespace(model=project["model"], manifest={"build_id": build})
    integration.evaluations, integration.bo_errors = [], 0
    calls, evaluations = Counter(), Counter()
    native_record = probe.record
    def observe_record(node, phase, builder, **options):
        calls[node] += 1
        def selected_builder():
            evaluations[node] += 1
            return builder()
        return native_record(node, phase, selected_builder, **options)
    probe.record = observe_record
    scratch = OUT / ".tmp"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="builder-audit-", dir=scratch) as directory:
        app = create_app(ROOT, database=Path(directory) / "audit.sqlite3", bo_probe=probe, bo_observer=integration, bo_data=data)
        try:
            clients = {actor: app.test_client() for actor in ("alice", "ben", "cara")}
            for actor, client in clients.items():
                login(client, actor)
            fid = upload(clients["alice"]).json["id"]
            assert post(clients["ben"], "/files/" + fid + "/review", {"decision": "approve"}).status_code == 200
            assert post(clients["alice"], "/files/" + fid + "/share", {"recipient_id": "cara"}).status_code == 200
            assert probe.flush(30)
            calls.clear()
            evaluations.clear()
            probe.bo_set_scope([TARGET, "policy:network"])
            response = clients["cara"].get("/files/" + fid + "/download")
            assert response.status_code == 200
            assert probe.flush(30)
            scoped_calls, scoped_builders = dict(calls), dict(evaluations)
            assert scoped_builders == {TARGET: 1}, scoped_builders
            assert "http_request" in scoped_calls and "access_file" in scoped_calls
            probe.bo_set_scope(None)
            calls.clear()
            evaluations.clear()
            assert clients["cara"].get("/files/" + fid + "/download").status_code == 200
            assert probe.flush(30)
            assert {"http_request", "access_file", TARGET} <= set(evaluations)
            assert probe.bo_health()["errors"] == probe.bo_health()["dropped"] == data.bo_errors == integration.bo_errors == 0
            result = {"valid": True, "boundary": "Actual Flask entrypoint, canonical probe and existing integration methods; direct sink, no GraphSession or Web claim.",
                "scope": [TARGET, "policy:network"], "record_attempts": scoped_calls, "builder_evaluations": scoped_builders,
                "unselected_field_builders_executed": 0, "restored_builder_evaluations": dict(evaluations), "probe_health": probe.bo_health()}
            (OUT / "builder-audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result))
        finally:
            probe.bo_set_scope(None)
            probe.close()
            data.close()
            app.extensions["trial_store"].engine.dispose()

if __name__ == "__main__":
    main()
