"""SQLite transactions and independently readable authoritative application state."""

from contextlib import contextmanager, closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading

from sqlalchemy import create_engine, event, select, insert
from werkzeug.security import generate_password_hash
from app.models import metadata, users
from app.ports import NullMonitor


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, directory, monitor=None):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.blobs = self.directory / "files"
        self.blobs.mkdir(exist_ok=True)
        self.database = self.directory / "application.sqlite3"
        self.engine = create_engine("sqlite:///" + self.database.as_posix(), connect_args={"check_same_thread":False,"timeout":15})
        self.lock = threading.RLock()
        self.monitor = monitor or NullMonitor()
        event.listen(self.engine, "connect", self.configure)

    @staticmethod
    def configure(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")

    def initialize(self):
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            if connection.execute(select(users.c.id)).first() is None:
                for identifier, name in [("owner","Lin"),("recipient","Xu"),("reviewer","Zhou"),("other","Chen")]:
                    connection.execute(insert(users).values(id=identifier,name=name,password_hash=generate_password_hash("TrialOnly!2026")))

    @contextmanager
    def unit(self):
        with self.lock, self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def transaction(self):
        return self.monitor.transaction("db_transaction", self.unit())

    def read(self, connection, statement):
        return self.monitor.execute("db_read", lambda: [dict(row) for row in connection.execute(statement).mappings()], connection=connection, statement=str(statement), language="sql", summarize=lambda rows: {"rows":len(rows),"result":{"count":len(rows)}})

    def write(self, connection, statement):
        return self.monitor.execute("db_write", lambda: connection.execute(statement).rowcount, connection=connection, statement=str(statement), language="sql", summarize=lambda count: {"rows":max(0,count),"result":{"count":max(0,count)}})

    def snapshot(self, build_id):
        with self.lock, closing(sqlite3.connect(self.database)) as connection:
            connection.row_factory = sqlite3.Row
            rows = [dict(row) for row in connection.execute("SELECT * FROM shares ORDER BY id")]
            history = [dict(row) for row in connection.execute("SELECT * FROM journal ORDER BY share_id, revision")]
            messages = [dict(row) for row in connection.execute("SELECT id,user_id,share_id,kind,state,is_read FROM notifications ORDER BY id")]
        instances = []
        for row in rows:
            entries = [entry for entry in history if entry["share_id"] == row["id"]]
            instances.append({"instance_id":row["id"],"state":row["state"],"revision":row["revision"],"build_id":build_id,"context":{key:row[key] for key in ["file_id","owner_id","recipient_id","reviewer_id"]},"evidence_id":entries[-1]["id"] if entries else "missing", "event":entries[-1]["event"] if entries else None,"guards":json.loads(entries[-1]["guards"]) if entries else {},"payload":{},"journal":entries})
        return {"instances":instances,"messages":messages}
