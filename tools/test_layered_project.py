"""Replay a real file-sharing project and verify every layer after a feature edit.

The starting application is extracted from the retained repaired source archive.
All writes stay in a disposable copy. A second process reloads Python modules
after the iteration; no event or business outcome is synthesized.
"""

import argparse
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/vibelens/scripts"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command(root, arguments, log):
    result = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", *map(str, arguments)],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Command failed: {arguments}; see {log}")


def prepare(root):
    """Restore the original synthetic application, then install the current runtime."""
    if root.exists():
        raise ValueError("Use a new output directory; previous trial evidence is retained")
    root.mkdir(parents=True)
    with zipfile.ZipFile(ROOT / "docs/review/file-sharing-demo/materials/green.zip") as bundle:
        with zipfile.ZipFile(io.BytesIO(bundle.read("source.zip"))) as source:
            for name in source.namelist():
                if not (root / name).resolve().is_relative_to(root.resolve()):
                    raise ValueError("Source archive escapes its project")
            source.extractall(root)
    sys.path.insert(0, str(SCRIPTS))
    from bo_upgrade import apply

    apply(root, runtime="observer_runtime", viewers=["static/graph"])
    # The portable source archive intentionally omits conversation documents.
    # Supply this trial's own requirement ledger, without pretending to restore
    # a historical user confirmation that was not included in the archive.
    model = read(root / "bo_stategraph/project.json")["model"]
    write(root / "implementation.json", model["implementation"])
    requirements = sorted(
        {item for node in model["nodes"] for item in node.get("requirements", [])}
    )
    write(
        root / "intent.json",
        {
            "project_id": model["project_id"],
            "revision": "layer-trial-1",
            "requirements": [
                {
                    "id": ident,
                    "text": "Exercise the existing file-sharing behavior: " + ident,
                    "status": "confirmed",
                    "source": "Automated acceptance scenario, not a new human answer",
                }
                for ident in requirements
            ],
        },
    )
    write(
        root / "discovery.json",
        {
            "project_id": model["project_id"],
            "evidence": "Automated acceptance scenario; the original public source archive excludes dialogue records",
            "decisions": [
                {
                    "id": "trial-scope",
                    "status": "answered",
                    "answer": "Exercise the retained sharing application, then add owner-only renaming without changing recipients or content.",
                }
            ],
        },
    )
    (root / "tooling/skill-path.txt").write_text(str(SCRIPTS.parent), encoding="utf-8")
    # The archive excludes runtime databases. Initialize real SQLite tables before
    # the native metadata collector independently compares them with the ORM.
    command(
        root,
        [
            "-c",
            "from app.web import create_app; create_app().extensions['sharing'].store.engine.dispose()",
        ],
        root / "review/layer-init.txt",
    )
    command(root, ["tooling/refresh_graph.py"], root / "review/layer-refresh.txt")


RENAME_SOURCE = '''
    def rename(self, actor: str, file_id: str, filename: str):
        """Change an owned file's title; its recipients and content stay intact."""
        filename = filename.strip()
        if not filename or len(filename) > 180:
            raise DomainError("invalid_filename", 400)
        with self.store.bo_data.transaction("db_rename_tx", self.store.write_transaction()) as connection:
            row = self.store.file(connection, file_id)
            if row is None:
                raise DomainError("file_not_found", 404)
            grants = self.store.grants(connection, file_id)
            self.authorize("rename", actor, row, grants)
            row.update(filename=filename, grant_count=len(grants))
            transition = self.workflow.step(row["state"], "rename", file_context(row), True)
            revision = row["revision"] + 1
            journal = json.loads(row["journal"]) + [{"seq": revision, "event": "rename",
                "before": row["state"], "after": transition["state"], "guards": transition["guards"]}]
            statement = files.update().where(files.c.id == file_id).values(
                filename=filename, revision=revision, journal=json.dumps(journal))
            self.store.bo_data.execute("db_rename_file", lambda: connection.execute(statement),
                connection=connection, statement=str(statement), language="sql",
                parameters={"file_id": file_id, "filename": filename},
                summarize=lambda result: {"rows": result.rowcount, "result": {"row_count": result.rowcount}})
        row.update(state=transition["state"], revision=revision, journal=journal)
        witness = self.bo_trace.record("rename", "commit", lambda: {
            "inputs": {"actor": actor, "file_id": file_id, "filename": filename},
            "outputs": {"filename": filename, "state": row["state"], "revision": revision}},
            entity=file_id, attempt=file_id, scope="entity", revision=revision)
        self.bo_trace.state(row, witness, transition)
        return row
'''

RENAME_ROUTE = """
@pages.post("/api/files/<file_id>/rename")
def rename(file_id):
    row = service().rename(current_actor(), file_id, request.form.get("filename", ""))
    return jsonify(filename=row["filename"], state=row["state"], revision=row["revision"])

"""


def edit_source(root):
    """Perform a real coding iteration before changing any graph declarations."""
    path = root / "app/service.py"
    path.write_text(path.read_text(encoding="utf-8") + RENAME_SOURCE, encoding="utf-8")
    path = root / "app/web.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "def handle_error(error):", RENAME_ROUTE + "def handle_error(error):"
        ),
        encoding="utf-8",
    )


def map_iteration(root):
    """Apply the coding agent's explicit semantic bindings; scans supply physical facts."""
    sys.path.insert(0, str(SCRIPTS))
    from bo_observer.data.sync import synchronize
    from bo_observer.policy.projection import project as policy_project
    from bo_observer.graph.behavior_model import capture
    from bo_observer.graph.code_structure import scan, enrich

    path = root / "bo_stategraph/project.json"
    document = read(path)
    model = document["model"]
    model["revision"] += "-rename"
    model["nodes"].append(
        {
            "id": "rename",
            "kind": "action",
            "layer": "business",
            "semantic_roles": ["business"],
            "label": "Rename owned file",
            "summary": "Change the file name while preserving its content and recipients.",
            "source": {"path": "app/service.py", "symbol": "SharingService.rename"},
            "capture": {
                "in": {"actor": "string", "file_id": "string", "filename": "string"},
                "out": {"filename": "string", "state": "string", "revision": "number"},
            },
            "requirements": ["R_READ"],
        }
    )
    model["edges"].extend(
        [
            {
                "id": "rename_from_view",
                "from": "view",
                "to": "rename",
                "type": "flow",
                "label": "Rename an owned file",
                "evidence": "Confirmed iteration",
            },
            {
                "id": "rename_to_view",
                "from": "rename",
                "to": "view",
                "type": "flow",
                "label": "Read the changed title",
                "evidence": "Actual next metadata request",
            },
        ]
    )
    source = "app/service.py::SharingService.rename"
    route = "app/web.py::rename"
    feature = {
        "id": "rename",
        "label": "Rename owned file",
        "business_node": "rename",
        "nodes": ["rename", "db_rename_tx", "db_rename_file"],
        "sources": [source, route],
        "parameters": [
            {
                "source": source,
                "name": name,
                "node": "rename",
                "direction": "in",
                "field": name,
                "policy": "value",
            }
            for name in ["actor", "file_id", "filename"]
        ]
        + [
            {
                "source": route,
                "name": "file_id",
                "node": "rename",
                "direction": "in",
                "field": "file_id",
                "policy": "value",
            }
        ],
        "cases": [{"case": "rename", "node": "rename", "phase": "commit"}],
        "requirements": ["R_READ"],
    }
    model["implementation"]["features"].append(feature)
    write(root / "implementation.json", model["implementation"])
    machine = model["machine"]
    machine["events"]["rename"] = {"payload": {"allowed": {"type": "boolean"}}}
    for state in ["private", "shared"]:
        machine["transitions"].append(
            {
                "trigger": "rename",
                "source": state,
                "dest": state,
                "conditions": ["operation_allowed"],
            }
        )
    operation = deepcopy(next(x for x in model["policy"]["operations"] if x["id"] == "revoke"))
    operation.update(id="rename", business_nodes=["rename"], cases=["rename"])
    model["policy"]["revision"] += "-rename"
    model["policy"]["operations"].append(operation)
    document["model"] = policy_project(model)
    write(path, document)
    data_path = root / "bo_stategraph/databases.json"
    data = read(data_path)
    for ident, action in [("db_rename_tx", "transaction"), ("db_rename_file", "write")]:
        data["operations"].append(
            {
                "id": ident,
                "label": "Rename transaction" if action == "transaction" else "Write file title",
                "parent": "rename",
                "store": "sharing",
                "action": action,
                "source": {"path": "app/service.py", "symbol": "SharingService.rename"},
                "targets": ["table:files"] if action == "write" else [],
                "parameters": (
                    {"file_id": "string", "filename": "string"} if action == "write" else {}
                ),
                "before": {},
                "after": {"row_count": "number"} if action == "write" else {},
                "required_cases": ["rename"],
                "requirements": ["R_READ"],
            }
        )
    write(data_path, data)
    data_result = synchronize(root)
    if not data_result["valid"]:
        raise ValueError(data_result)
    document = read(path)
    index = scan(root, read(root / "sync.json")["code_files"])
    document["model"] = policy_project(enrich(document["model"], index, 1))
    write(path, document)
    write(root / "manifest.json", capture(root, document["model"]))


def verify(root, output, version, browser_path=None):
    """Independently compare actual requests/storage/state/parameters with observations."""
    os.chdir(root)
    sys.path[:0] = [str(root), str(root / "tooling"), str(root / "observer_runtime")]
    from app.web import create_app
    from integrations.bo_adapter import BOTrace
    from integrations.bo_view import BOGraphSession
    from scenarios import login_client, csrf, run_workflow, run_revocation
    from bo_observer.code_graph.service import CodeGraph
    from bo_observer.service import make_server
    from bo_observer.policy.evidence import evaluation_errors
    from bo_observer.data.sync import runtime_errors
    from bo_observer.graph.behavior_model import validate
    import threading
    from sqlalchemy import text

    session = BOGraphSession(root)
    validate(root, session.model)
    graph = CodeGraph(root)
    code, _ = graph.refresh()
    assert not code["errors"], code["errors"]
    trace = BOTrace(
        root,
        capacity=16384,
        sink=lambda event, kind: (
            session.event(event) if kind == "events" else session.snapshot(event)
        ),
    )
    app = create_app(
        root, root / f"data/acceptance-v{version}.sqlite3", bo_trace=trace, bo_data=trace.data
    )
    session.graph.bo_require_definition(app.extensions["sharing"].workflow.executor.bo_definition)
    if version == 2:
        old = read(output / "v1/recording.json")["events"][0]
        try:
            session.event(old)
        except ValueError:
            pass
        else:
            raise AssertionError("An event from the previous build was accepted")
    session.program_url = "http://127.0.0.1/"
    session.recordings.start("All-layer feature trial")
    checks, file_id = run_workflow(app)
    # This original workflow asserts bytes, permissions, SQL effects and state.
    assert checks and all(value is not False for value in checks.values()), checks
    assert trace.probe.flush(30)
    runs = [{"case": "workflow", "mode": "on", "events": deepcopy(trace.events)}]
    start = len(trace.events)
    revoked_app = create_app(
        root, root / f"data/revocation-v{version}.sqlite3", bo_trace=trace, bo_data=trace.data
    )
    revoked, _ = run_revocation(revoked_app)
    assert revoked and all(value is not False for value in revoked.values()), revoked
    assert trace.probe.flush(30)
    runs.append({"case": "revocation", "mode": "on", "events": deepcopy(trace.events[start:])})
    revoked_app.extensions["sharing"].store.engine.dispose()
    start = len(trace.events)
    store = app.extensions["sharing"].store
    if version == 2:
        owner, _ = login_client(app, "linzhou")
        recipient, _ = login_client(app, "xuning")
        changed = owner.post(
            f"/api/files/{file_id}/rename", data={"csrf": csrf(owner), "filename": "renamed.txt"}
        )
        denied = recipient.post(
            f"/api/files/{file_id}/rename",
            data={"csrf": csrf(recipient), "filename": "intrusion.txt"},
        )
        assert changed.status_code == 200, changed.data
        assert denied.status_code == 403, denied.data
        with store.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT filename,state,revision FROM files WHERE id=:id"), {"id": file_id}
                )
                .mappings()
                .one()
            )
        assert row["filename"] == "renamed.txt" and row["state"] == changed.json["state"]
        checks["rename"] = dict(row)
        uploaded = owner.post(
            "/upload",
            data={
                "csrf": csrf(owner),
                "file": (io.BytesIO(b"private rename case"), "private-note.txt"),
            },
            content_type="multipart/form-data",
        )
        assert uploaded.status_code == 302
        private_id = next(
            item["id"]
            for item in owner.get("/api/files").json
            if item["filename"] == "private-note.txt"
        )
        renamed_private = owner.post(
            f"/api/files/{private_id}/rename",
            data={"csrf": csrf(owner), "filename": "private-renamed.txt"},
        )
        assert renamed_private.status_code == 200 and renamed_private.json["state"] == "private"
        invalid = owner.post(
            f"/api/files/{private_id}/rename", data={"csrf": csrf(owner), "filename": ""}
        )
        assert invalid.status_code == 400
        checks["rename_private"] = renamed_private.json
        checks["rename_invalid_denied"] = True
    if not trace.probe.flush(30):
        raise AssertionError(
            {"transport_errors": trace.probe.bo_errors, "rejections": trace.rejections[:3]}
        )
    if version == 2:
        runs.append({"case": "rename", "mode": "on", "events": deepcopy(trace.events[start:])})
    assert not runtime_errors(root, {"runs": runs}, session.model)
    recording = session.recordings.stop()
    saved_recording = session.recordings.get(recording["id"])
    assert saved_recording["gaps"] == [] and saved_recording["final"]["health"]["errors"] == 0
    assert trace.errors == 0 and trace.rejections == [] and trace.probe.bo_errors == 0, (
        trace.errors,
        trace.rejections,
        trace.probe.bo_errors,
    )
    for report in trace.evaluations:
        assert not evaluation_errors(session.model["policy"], report)
    if version == 2:
        event = next(
            event
            for event in trace.events
            if event["node"] == "rename" and event["phase"] == "commit"
        )
        assert event["outputs"]["filename"] == checks["rename"]["filename"]
        assert event["outputs"]["revision"] == checks["rename"]["revision"]
        write_event = next(
            event
            for event in trace.events
            if event["node"] == "db_rename_file" and event["phase"] == "return"
        )
        assert write_event["outputs"]["rows"] == 1, write_event
    before = session.sequence
    for _ in range(3):
        session.view()
        graph.view(projection="project")
        graph.source("app/service.py", code["revision"])
        session.recordings.list()
    assert session.sequence == before
    result = {
        "valid": not bool(browser_path),
        "version": version,
        "business": checks,
        "revocation": revoked,
        "mapping": {
            "events": len(trace.events),
            "snapshots": len(trace.snapshots),
            "policy_evaluations": len(trace.evaluations),
            "observer_events": session.sequence - before,
        },
        "build_id": session.manifest["build_id"],
        "code_revision": code["revision"],
    }
    write(output / f"v{version}/view.json", session.view())
    write(output / f"v{version}/code.json", code)
    write(output / f"v{version}/recording.json", saved_recording)
    write(output / f"v{version}/result.json", result)
    if browser_path:
        from playwright.sync_api import sync_playwright

        server = make_server(session, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    executable_path=browser_path,
                    args=["--enable-unsafe-swiftshader"],
                )
                page = browser.new_page(viewport={"width": 1500, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/graph?lang=en")
                page.wait_for_function(
                    "window.graphDebug?.graph?.boxes.length && !graphDebug.layoutBusy"
                )
                page.select_option("#analysis-view", "business")
                page.wait_for_function("!graphDebug.layoutBusy")
                positions = page.evaluate(
                    "graphDebug.graph.boxes.map(n => ({id:n.id,x:n.x,y:n.y}))"
                )
                page.screenshot(path=str(output / f"v{version}/business.png"))
                page.select_option("#analysis-view", "code")
                page.wait_for_function(
                    "graphDebug.view.code_structure?.projection === 'all' && !graphDebug.layoutBusy"
                )
                page.click("#expand")
                page.click("#fit")
                page.click("#layered-toggle")
                page.wait_for_function("graphDebug.spatial?.webgl && !graphDebug.layoutBusy")
                page.screenshot(path=str(output / f"v{version}/layers.png"))
                result["browser"] = {
                    "errors": errors,
                    "business_positions": positions,
                    "planes": page.evaluate("graphDebug.spatial.layerPlanes.map(p => p.id)"),
                }
                if version == 2:
                    previous = read(output / "v1/result.json")["browser"]["business_positions"]
                    now = {p["id"]: (p["x"], p["y"]) for p in positions}
                    assert all(now[p["id"]] == (p["x"], p["y"]) for p in previous)
                    result["browser"]["positions_preserved"] = True
                assert not errors
                browser.close()
        finally:
            server.shutdown()
            thread.join(3)
            server.server_close()
    result["valid"] = True
    write(output / f"v{version}/result.json", result)
    trace.close()
    session.close()
    store.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=".validation/layered-acceptance")
    parser.add_argument("--worker", choices=["1", "2"])
    parser.add_argument("--browser")
    args = parser.parse_args()
    os.environ["BO_ADAPTER_HOME"] = str(SCRIPTS / "bo_observer/adapters/javascript")
    output = (ROOT / args.out).resolve()
    root = output / "project"
    if args.worker:
        verify(root, output, int(args.worker), args.browser)
        return
    prepare(root)
    os.environ["FILE_SHARING_DB_URL"] = "sqlite:///data/sharing.sqlite3"
    common = [__file__, "--out", output]
    if args.browser:
        common += ["--browser", args.browser]
    command(ROOT, [*common, "--worker", "1"], output / "v1/run.txt")
    edit_source(root)
    # Keep the expected failure: a new API/function cannot silently pass as mapped.
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(SCRIPTS / "bo_sync.py"),
            "scan",
            "--root",
            str(root),
        ],
        capture_output=True,
        encoding="utf-8",
    )
    (output / "unmapped-iteration.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    maintenance = json.loads(result.stdout)
    assert maintenance.get("inventory"), maintenance
    assert any("rename" in str(gap) for gap in maintenance["implementation_gaps"]), maintenance
    map_iteration(root)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(SCRIPTS / "bo_sync.py"),
            "scan",
            "--root",
            str(root),
        ],
        capture_output=True,
        encoding="utf-8",
    )
    (output / "mapped-iteration.json").write_text(result.stdout, encoding="utf-8")
    maintenance = json.loads(result.stdout)
    assert maintenance.get("inventory") and not maintenance.get("implementation_gaps"), maintenance
    command(ROOT, [*common, "--worker", "2"], output / "v2/run.txt")
    for version in [1, 2]:
        result = subprocess.run(
            [
                "node",
                str(ROOT / "tools/check_layer_inventory.mjs"),
                str(output / f"v{version}"),
                str(output / f"v{version}/layers.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            encoding="utf-8",
        )
        (output / f"v{version}/layers.txt").write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
        if result.returncode:
            raise AssertionError(result.stderr)
    before, after = read(output / "v1/code.json"), read(output / "v2/code.json")
    assert before["revision"] != after["revision"]
    assert before["files"]["app/service.py"] != after["files"]["app/service.py"]
    assert before["files"]["app/web.py"] != after["files"]["app/web.py"]
    changes = {"valid": True, "source_refreshed": True, "layers": []}
    for a, b in zip(
        read(output / "v1/layers.json")["layers"], read(output / "v2/layers.json")["layers"]
    ):
        changes["layers"].append(
            {
                "id": a["id"],
                "before": {key: a[key] for key in ["nodes", "edges", "crossing"]},
                "after": {key: b[key] for key in ["nodes", "edges", "crossing"]},
                "expected": (
                    "Schema and file membership stay unchanged; source hashes and links refresh"
                    if a["id"] in ["data", "project"]
                    else "Rename behavior is added to this layer"
                ),
            }
        )
    write(output / "iteration.json", changes)
    print(
        "PASS: actual file-sharing operations, captured evidence and rename iteration; see", output
    )


if __name__ == "__main__":
    main()
