"""Sharing operations with one real transaction lock and two independent callers."""
import sqlite3
from contextlib import closing

def read_grant(db):
    return bool(db.execute("select allowed from grants where actor = ?", ("owner",)).fetchone()[0])

def write_share(db, actor):
    db.execute("insert into shares(file_id, recipient) values (?, ?)", ("file-1", actor))
    db.commit()
    return db.execute("select count(*) from shares").fetchone()[0]

def advance(state, actor, probe, ready, release, path, resource_lock, publication, engine, report):
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
