"""Run a source-identical trial copy against the repaired canonical observer.

This is repair verification, separate from the original conversation's delivery
gate. Business sources and expectations are copied without editing them.
"""

import json
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import traceback

repository = Path(__file__).resolve().parents[1]
original = repository.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
target = Path(tempfile.mkdtemp(prefix="dialogue-candidate-", dir=repository / ".validation"))
skip = shutil.ignore_patterns("__pycache__", "data", "node_modules")
for name in ("app", "integrations", "bo_stategraph", "templates", "static", "tooling", "tests"):
    shutil.copytree(original / name, target / name, ignore=skip)
for name in ("behavior.json", "intent.json", "sync.json", "discovery.json", "implementation.json"):
    shutil.copyfile(original / name, target / name)
(target / "review").mkdir()
for source in (original / "review").glob("*hashes.json"):
    shutil.copyfile(source, target / "review" / source.name)
patch = None
if os.environ.get("BO_DIALOGUE_PATCH_HTTP") == "1":
    path = target / "app/web.py"
    before = path.read_text(encoding="utf-8")
    capture = 'operation.result(lambda:{"outputs":{"status":error.status}})'
    if before.count(capture) != 2:
        raise ValueError("The exact reviewed two-boundary capture patch no longer applies")
    # POST's handled business error still returns an actual HTTP 303 redirect.
    after = before.replace(capture, 'operation.result(lambda:{"outputs":{"status":303}})', 1)
    after = after.replace(capture, 'operation.result(lambda status=error.status:{"outputs":{"status":status}})', 1)
    path.write_text(after, encoding="utf-8", newline="\n")
    patch = {"path": "app/web.py", "original_sha256": hashlib.sha256(before.encode()).hexdigest(),
             "patched_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "scope": "Two deferred HTTP return builders only; independent repair verification, not accepted dialogue delivery"}
canonical = repository / "skills/vibelens/scripts"
sys.path[:0] = [str(target), str(canonical)]
os.environ["TRIAL_DATABASE_URL"] = "sqlite:///" + (target / "data/application.sqlite3").as_posix()

from bo_observer.service import GraphSession, make_server
from app.storage import Store
from app.service import Service
from app.web import create_app
from integrations.bo_monitor import BOMonitor
from werkzeug.serving import make_server as make_application_server

project = json.loads((target / "bo_stategraph/project.json").read_text(encoding="utf-8"))
session = GraphSession(target)


def receive(value, kind):
    try:
        return session.event(value) if kind == "events" else session.snapshot(value)
    except Exception:
        traceback.print_exc()
        raise


monitor = BOMonitor(project, session.manifest["build_id"], sink=receive)
session.bo_bind_capture(
    scope_setter=monitor.probe.bo_set_scope,
    flush_capture=lambda: monitor.probe.flush(30),
    health=lambda: {**monitor.probe.bo_health(), "data_errors": monitor.data.bo_errors},
)
store = Store(target / "data", monitor)
store.initialize()
service = Service(store, project, target)
graph_server = make_server(session, port=0)
graph_url = f"http://127.0.0.1:{graph_server.server_port}/graph"
application = create_app(service, graph_url, session.manifest["build_id"])
app_server = make_application_server("127.0.0.1", 0, application, threaded=True)
application_url = f"http://127.0.0.1:{app_server.server_port}"
session.program_url = application_url
out = repository / "docs/review/dialogue-acceptance-20261031/repair-candidate"
out.mkdir(parents=True, exist_ok=True)
info = {"kind": "Dialogue application with isolated HTTP capture repair" if patch else "Unedited dialogue application copied for canonical observer repair verification", "root": str(target),
        "application_url": application_url, "graph_url": graph_url, "pid": os.getpid(), "build_id": session.manifest["build_id"]}
if patch:
    info["capture_patch"] = patch
(out / "runtime.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print(json.dumps(info), flush=True)
for server in (graph_server, app_server):
    threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    stop = threading.Event()
    while not (target / "stop.requested").exists():
        stop.wait(0.25)
finally:
    monitor.probe.flush(30)
    for server in (graph_server, app_server):
        server.shutdown()
        server.server_close()
    monitor.probe.close()
    session.close()
    store.engine.dispose()
