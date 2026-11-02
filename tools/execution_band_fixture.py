"""Real concurrent SQLite operations for execution-band browser acceptance."""

import argparse
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from test_trace_lifecycle import prepare
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.adapters.python.bo_executor import BOExecutor
from bo_observer.service import GraphSession, make_server

BUSINESS = '''"""Sharing operations with one real transaction lock and two independent callers."""
import sqlite3
from contextlib import closing

def read_grant(db):
    return bool(db.execute("select allowed from grants where actor = ?", ("owner",)).fetchone()[0])

def write_share(db, actor):
    db.execute("insert into shares(file_id, recipient) values (?, ?)", ("file-1", actor))
    db.commit()
    return db.execute("select count(*) from shares").fetchone()[0]

def advance(actor, probe, ready, release, path, resource_lock, publication, engine, report):
    state = "pending"
    with probe.span("advance", lambda: {"inputs": {"state": state, "actor": actor}},
                    entity=actor, attempt="share:" + actor, scope="entity") as operation:
        report(actor, state, 0, None, operation)
        state = engine.step(state, "start", {"slots": 1})["state"]
        report(actor, state, 1, "start", operation)
        with closing(sqlite3.connect(path)) as db:
            with probe.span("check") as check:
                with probe.span("query") as query:
                    allowed = read_grant(db)
                    query.result(lambda: {"outputs": {"allowed": allowed}})
                probe.record("rule_fact", "decision", lambda: {"outputs": {"allowed": allowed}},
                             entity="file-1", attempt="evaluation:" + actor, scope="entity")
                check.result(lambda: {"outputs": {"allowed": allowed}})
            if not allowed:
                raise PermissionError("Share denied")
            waited = operation.record("wait", lambda: {"outputs": {"state": state}})
            ready.wait(15)
            if not release.wait(25):
                raise TimeoutError("Operation was not released")
            probe.record("advance", "read", lambda: {"outputs": {"state": state}},
                         **operation.bo_options, depends=[{"event": waited, "type": "control"}])
            with probe.span("write") as transaction:
                with resource_lock:
                    previous = publication.get("release")
                    if previous:
                        probe.record("write", "read", lambda: {}, **transaction.bo_options,
                                     depends=[{"event": previous, "type": "control"}])
                    count = write_share(db, actor)
                    probe.record("rule_fact", "decision", lambda: {"outputs": {"allowed": allowed}},
                                 entity="file-1", attempt="evaluation:" + actor, scope="entity")
                    publication["release"] = transaction.record("commit", lambda: {"outputs": {"count": count}})
                    transaction.result(lambda: {"outputs": {"count": count}})
        state = engine.step(state, "finish", {"slots": 1})["state"]
        report(actor, state, 2, "finish", operation)
        operation.result(lambda: {"outputs": {"state": state}})
        return state
'''


def serve(root):
    """Keep test controls outside probes; the actual worker owns every observation."""
    project = prepare(root, registered=True)
    (root / "worker.py").write_text(BUSINESS, encoding="utf-8")
    project["model"]["nodes"][0]["capture"]["in"]["actor"] = "string"
    project["model"]["nodes"].append(
        {
            "id": "rule_fact",
            "kind": "decision",
            "label": "Grant result",
            "summary": "Permission value returned by the grant query",
            "source": {"path": "worker.py", "symbol": "read_grant"},
            "capture": {"in": {}, "out": {"allowed": "boolean"}},
        }
    )
    project["model"]["edges"].append(
        {
            "id": "observed-grant",
            "from": "check",
            "to": "rule_fact",
            "type": "guard",
            "label": "Observed result",
            "evidence": "Actual query result",
        }
    )
    (root / "bo_stategraph/project.json").write_text(json.dumps(project), encoding="utf-8")
    session = GraphSession(root)
    probe = BOProbe(project, session.manifest["build_id"], sink=session.bo_sink)
    session.bo_bind_capture(
        scope_setter=probe.bo_set_scope,
        flush_capture=lambda: probe.flush(5),
        health=probe.bo_health,
    )
    engine = BOExecutor(
        project["model"]["machine"], {"available": lambda context, payload: context["slots"] > 0}
    )
    ready, release = threading.Barrier(2), threading.Event()
    resource_lock, publication = threading.Lock(), {}
    results, workers = {}, []
    spec = importlib.util.spec_from_file_location("concurrent_sharing", root / "worker.py")
    application = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(application)

    def report(actor, state, revision, event, operation):
        observed = probe.record(
            "advance",
            "change",
            lambda: {"outputs": {"state": state}},
            **operation.bo_options,
            revision=revision,
        )
        if observed is None:
            return  # Deliberately unselected state values have no snapshot witness.
        probe.snapshot(
            actor,
            state,
            {"slots": 1},
            revision,
            observed,
            event=event,
            guards={"available": True} if event == "start" else {},
            payload={} if event else None,
        )

    def operate(actor):
        try:
            results[actor] = application.advance(
                actor,
                probe,
                ready,
                release,
                root / "sharing.sqlite",
                resource_lock,
                publication,
                engine,
                report,
            )
        except Exception as error:
            results[actor] = {"error": str(error)}
        finally:
            probe.flush(5)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            from bo_observer.workflow.observation_requirements import invocation_closure

            with closing(sqlite3.connect(root / "sharing.sqlite")) as db:
                rows = db.execute("select recipient from shares order by recipient").fetchall()
            observed = [
                event
                for event in session.history.snapshot()
                if event.get("protocol") == "bo-event/v1"
            ]
            self.reply(
                {
                    "results": results,
                    "recipients": [row[0] for row in rows],
                    "health": probe.bo_health(),
                    "events": len(session.history.snapshot()),
                    "capture_nodes": (
                        sorted(probe.bo_capture_nodes)
                        if probe.bo_capture_nodes is not None
                        else None
                    ),
                    "closure": invocation_closure(
                        {"runs": [{"mode": "on", "case": "concurrent", "events": observed}]},
                        required=True,
                        model=project["model"],
                    ),
                }
            )

        def do_POST(self):
            route = urlparse(self.path)
            if route.path == "/begin":
                actor = parse_qs(route.query).get("actor", [""])[0]
                if actor not in {"alice", "bob"} or actor in results:
                    self.send_error(400)
                    return
                results[actor] = "running"
                worker = threading.Thread(target=operate, args=(actor,), daemon=True)
                workers.append(worker)
                worker.start()
            elif route.path == "/release":
                release.set()
            elif route.path == "/stop":
                release.set()
                threading.Thread(target=observer.shutdown, daemon=True).start()
            else:
                self.send_error(404)
                return
            self.reply({"accepted": True})

        def reply(self, value):
            data = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    business = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    observer = make_server(session, 0)
    session.program_url = f"http://127.0.0.1:{business.server_port}"
    threading.Thread(target=business.serve_forever, daemon=True).start()
    print(
        json.dumps(
            {
                "observer": f"http://127.0.0.1:{observer.server_port}",
                "application": session.program_url,
            }
        ),
        flush=True,
    )
    try:
        observer.serve_forever()
    finally:
        release.set()
        for worker in workers:
            worker.join(3)
        business.shutdown()
        business.server_close()
        observer.server_close()
        probe.close()
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", type=Path, required=True)
    args = parser.parse_args()
    serve(args.serve.absolute())
