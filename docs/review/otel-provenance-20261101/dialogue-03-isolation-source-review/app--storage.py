"""SQLite storage and consistent read-only snapshots."""
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path
from werkzeug.security import generate_password_hash
from app.ports import ObservationPort

class Connection:
    def __init__(self, raw, bo):
        self.raw,self.bo=raw,bo
    def execute(self, sql, parameters=()):
        return self.bo.execute(sql,parameters,lambda:self.raw.execute(sql,parameters))
    def executescript(self, script):
        return self.raw.executescript(script)
    def commit(self):
        return self.raw.commit()
    def rollback(self):
        return self.raw.rollback()
    def close(self):
        return self.raw.close()
    @property
    def in_transaction(self):
        return self.raw.in_transaction

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,display_name TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','member')),password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES users(id),filename TEXT NOT NULL,size INTEGER NOT NULL CHECK(size>=0),content BLOB NOT NULL,state TEXT NOT NULL CHECK(state IN ('pending_review','review_notice_wait','approved','rejected')),review_decision TEXT,rejection_reason TEXT NOT NULL DEFAULT '',reviewer_id TEXT REFERENCES users(id),workflow_id TEXT UNIQUE NOT NULL,revision INTEGER NOT NULL DEFAULT 1,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS shares(id TEXT PRIMARY KEY,file_id TEXT NOT NULL REFERENCES files(id),recipient_id TEXT NOT NULL REFERENCES users(id),sender_id TEXT NOT NULL REFERENCES users(id),state TEXT NOT NULL CHECK(state IN ('share_notice_wait','active_share')),revision INTEGER NOT NULL DEFAULT 1,created_at REAL NOT NULL,UNIQUE(file_id,recipient_id));
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL CHECK(kind IN ('review','share')),file_id TEXT NOT NULL REFERENCES files(id),share_id TEXT REFERENCES shares(id),recipient_id TEXT NOT NULL REFERENCES users(id),workflow_id TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'waiting' CHECK(state IN ('waiting','delivered')),available_at REAL NOT NULL,bo_carrier TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,last_error TEXT NOT NULL DEFAULT '',delivered_at REAL);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,recipient_id TEXT NOT NULL REFERENCES users(id),job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),file_id TEXT NOT NULL REFERENCES files(id),kind TEXT NOT NULL,text TEXT NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS transitions(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_id TEXT NOT NULL,event TEXT NOT NULL,before_state TEXT NOT NULL,after_state TEXT NOT NULL,revision INTEGER NOT NULL,created_at REAL NOT NULL);
PRAGMA user_version=2;
"""

class Store:
    def __init__(self, path):
        self.path=Path(path)
        self.bo=ObservationPort()
        self.path.parent.mkdir(parents=True,exist_ok=True)
    def connect(self, observe=True):
        connection=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        connection.row_factory=sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return Connection(connection,self.bo if observe else ObservationPort())
    def initialize(self):
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            columns={row["name"] for row in connection.execute("PRAGMA table_info(jobs)")}
            if "carrier" in columns and "bo_carrier" not in columns:
                connection.execute("ALTER TABLE jobs RENAME COLUMN carrier TO bo_carrier")
            connection.executescript(SCHEMA)
            for identity,username,name,role in [
                ("admin-1","admin1","Administrator One","admin"),("admin-2","admin2","Administrator Two","admin"),
                ("member-1","member1","Member One","member"),("member-2","member2","Member Two","member")]:
                if not connection.execute("SELECT 1 FROM users WHERE id=?",(identity,)).fetchone():
                    connection.execute("INSERT INTO users VALUES(?,?,?,?,?)",(identity,username,name,role,generate_password_hash("Trial2026!")))
    @contextmanager
    def transaction(self):
        with self.bo.transaction(self._transaction()) as connection:
            yield connection
    @contextmanager
    def _transaction(self):
        connection=self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
    def read(self, sql, parameters=(), observe=True):
        with closing(self.connect(observe=observe)) as connection:
            return [dict(row) for row in connection.execute(sql,parameters)]
    def snapshot(self, build_id, model_revision):
        with closing(self.connect(observe=False)) as connection:
            connection.execute("BEGIN")
            rows=[dict(row) for row in connection.execute("SELECT id,state,revision FROM files UNION ALL SELECT id,state,revision FROM shares ORDER BY id")]
            return {"instances":[{**row,"entity":row["id"],"build_id":build_id,"model_revision":model_revision} for row in rows],
                "journal":[dict(row) for row in connection.execute("SELECT * FROM transitions ORDER BY id")],
                "jobs":[dict(row) for row in connection.execute("SELECT id,kind,file_id,share_id,recipient_id,state,attempts,last_error,available_at FROM jobs ORDER BY id")]}
    def model_export(self):
        with closing(self.connect(observe=False)) as connection:
            return {name:[dict(row) for row in connection.execute("PRAGMA table_info("+name+")")] for name in ("users","files","shares","jobs","messages","transitions")}
