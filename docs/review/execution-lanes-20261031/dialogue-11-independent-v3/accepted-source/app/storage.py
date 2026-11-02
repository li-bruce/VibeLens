"""Authoritative SQLite storage and explicit optional data-operation boundaries."""
from contextlib import contextmanager
import json
from pathlib import Path
from sqlalchemy import create_engine, select, event, MetaData
from werkzeug.security import generate_password_hash
from .models import metadata, users, files
from .ports import NullData

TEST_ACCOUNTS = (("alice", "林川"), ("ben", "周宁"), ("cara", "陈禾"), ("dan", "许澄"))
TEST_PASSWORD = "bands-8972-trial"

def configure_sqlite(db, record):
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")

class Store:
    def __init__(self, path: Path, bo_data=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.bo_data = bo_data or NullData()
        self.engine = create_engine("sqlite:///" + str(self.path), connect_args={"check_same_thread": False})
        event.listen(self.engine, "connect", configure_sqlite)

    def initialize(self):
        metadata.create_all(self.engine)
        self.migrate_rejection_reason()
        self.migrate_file_states()
        with self.engine.begin() as db:
            existing = set(db.execute(select(users.c.id)).scalars())
            for identifier, name in TEST_ACCOUNTS:
                if identifier not in existing:
                    db.execute(users.insert().values(id=identifier, display_name=name,
                        password_hash=generate_password_hash(TEST_PASSWORD, method="pbkdf2:sha256:120000")))

    def migrate_rejection_reason(self):
        """Add storage without inventing reasons for historical rejected files."""
        with self.write_transaction() as db:
            columns = {row[1] for row in db.exec_driver_sql("PRAGMA table_info(files)")}
            if "rejection_reason" not in columns:
                db.exec_driver_sql("ALTER TABLE files ADD COLUMN rejection_reason VARCHAR NOT NULL DEFAULT ''")

    def migrate_file_states(self):
        """Atomically extend the original SQLite check without rewriting file facts."""
        with self.write_transaction() as db:
            definition = db.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='files'").scalar_one()
            if "'withdrawn'" in definition:
                return
            custom = db.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE tbl_name='files' "
                "AND type IN ('index','trigger') AND sql IS NOT NULL").fetchall()
            if custom:
                raise RuntimeError("Custom file indexes/triggers require an explicit migration")
            migration_metadata = MetaData()
            users.to_metadata(migration_metadata)
            upgraded = files.to_metadata(migration_metadata, name="files_with_withdrawal")
            upgraded.create(db)
            columns = ", ".join('"' + column.name + '"' for column in files.columns)
            db.exec_driver_sql(f"INSERT INTO files_with_withdrawal ({columns}) SELECT {columns} FROM files")
            db.exec_driver_sql("DROP TABLE files")
            db.exec_driver_sql("ALTER TABLE files_with_withdrawal RENAME TO files")
            if db.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("File state migration violated foreign keys")

    @contextmanager
    def write_transaction(self):
        with self.engine.connect() as db:
            db.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def read_users(self, db):
        statement = select(users)
        return self.bo_data.execute("db_users",
            lambda: [dict(row) for row in db.execute(statement).mappings()],
            statement=str(statement), language="sql",
            summarize=lambda rows: {"rows": len(rows), "result": {"row_count": len(rows)}})

    def read_file(self, db, file_id: str):
        statement = select(files).where(files.c.id == file_id)
        rows = self.bo_data.execute("db_file",
            lambda: [dict(row) for row in db.execute(statement).mappings()],
            statement=str(statement), language="sql",
            parameters={"file_id": file_id},
            summarize=lambda rows: {"rows": len(rows), "result": {"row_count": len(rows)}})
        if not rows:
            return None
        row = rows[0]
        row["recipient_id"] = row["recipient_id"] or ""
        row["journal"] = json.loads(row["journal"])
        return row

    def read_candidates(self, db, actor: str):
        statement = select(files.c.id).where((files.c.uploader_id == actor) |
            ((files.c.reviewer_id == actor) & (files.c.state != "withdrawn")) |
            ((files.c.state == "approved") & (files.c.recipient_id == actor)))
        return self.bo_data.execute("db_candidates",
            lambda: list(db.execute(statement).scalars()),
            statement=str(statement), language="sql", parameters={"actor": actor},
            summarize=lambda rows: {"rows": len(rows), "result": {"row_count": len(rows)}})

    def insert_file(self, db, row: dict):
        values = dict(row, recipient_id=None, journal=json.dumps(row["journal"]))
        statement = files.insert().values(**values)
        return self.bo_data.execute("db_insert", lambda: db.execute(statement).rowcount,
            statement=str(statement), language="sql",
            parameters={"file_id": row["id"]}, summarize=lambda count: {"rows": count, "result": {"row_count": count}})

    def update_file(self, db, row: dict):
        statement = files.update().where(files.c.id == row["id"]).values(
            state=row["state"], revision=row["revision"], recipient_id=row["recipient_id"] or None,
            journal=json.dumps(row["journal"]), rejection_reason=row["rejection_reason"])
        return self.bo_data.execute("db_update",
            lambda: db.execute(statement).rowcount,
            statement=str(statement),
            language="sql", parameters={"file_id": row["id"]},
            summarize=lambda count: {"rows": count, "result": {"row_count": count}})

    def snapshots(self):
        with self.engine.connect() as db:
            rows = [dict(row) for row in db.execute(select(
                files.c.id, files.c.state, files.c.revision, files.c.uploader_id, files.c.reviewer_id,
                files.c.recipient_id, files.c.size, files.c.journal, files.c.rejection_reason)).mappings()]
        for row in rows:
            row["recipient_id"] = row["recipient_id"] or ""
            row["journal"] = json.loads(row["journal"])
        return rows

def metadata_view(row: dict) -> dict:
    return {key: row[key] for key in ("id", "filename", "size", "state", "revision",
        "uploader_id", "reviewer_id", "recipient_id", "rejection_reason")}
