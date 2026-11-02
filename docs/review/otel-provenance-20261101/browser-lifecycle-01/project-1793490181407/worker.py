"""Minimal sharing operation; all SQL acts on synthetic local records."""
import sqlite3
from contextlib import closing

def read_grant(db):
    return db.execute("select allowed from grants where actor = ?", ("owner",)).fetchone()[0]

def write_share(db):
    db.execute("insert into shares(file_id, recipient) values (?, ?)", ("file-1", "reader"))
    db.commit()
    return db.execute("select count(*) from shares").fetchone()[0]

def advance(state, probe, gate, path, engine, report):
    with probe.span("advance", lambda: {"inputs": {"state": state}}, entity="job", attempt="attempt-1", scope="entity") as operation:
        state = engine.step(state, "start", {"slots": 1})["state"]
        report(state, 1, "start")
        with closing(sqlite3.connect(path)) as db:
            with probe.span("check") as check:
                with probe.span("query") as query:
                    allowed = bool(read_grant(db))
                    query.result(lambda: {"outputs": {"allowed": allowed}})
                check.result(lambda: {"outputs": {"allowed": allowed}})
            if not allowed:
                raise PermissionError("Share denied")
            waiting_event = operation.record("wait", lambda: {"outputs": {"state": state}})
            if not gate.wait(25):
                raise TimeoutError("Sharing operation was not released")
            probe.record("advance", "read", lambda: {"outputs": {"state": state}},
                         entity="job", attempt="attempt-1", scope="entity",
                         call_id=operation.call_id, lifecycle="span",
                         depends=[{"event": waiting_event, "type": "control"}] if waiting_event else [])
            with probe.span("write") as commit:
                count = write_share(db)
                commit.result(lambda: {"outputs": {"count": count}})
        state = engine.step(state, "finish", {"slots": 1})["state"]
        report(state, 2, "finish")
        operation.result(lambda: {"outputs": {"state": state}})
        return state
