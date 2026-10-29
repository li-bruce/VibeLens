"""Authoritative storage. Files are transactionally stored inside SQLite."""

from contextlib import contextmanager
import json
from pathlib import Path
from sqlalchemy import create_engine, select, func, event
from werkzeug.security import generate_password_hash
from .models import metadata, users, files, shares
from .ports import NullData

DEMO_USERS = (("linzhou", "林舟"), ("xuning", "许宁"), ("zhoulan", "周岚"))
DEMO_PASSWORD = "file-demo-2026"


def enable_foreign_keys(connection, record):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")


class Store:
    def __init__(self, path: Path, bo_data=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.bo_data = bo_data or NullData()
        self.engine = create_engine("sqlite:///" + str(self.path), connect_args={"check_same_thread": False})
        event.listen(self.engine, "connect", enable_foreign_keys)

    def initialize(self):
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            existing = set(connection.execute(select(users.c.id)).scalars())
            for user_id, display_name in DEMO_USERS:
                if user_id not in existing:
                    connection.execute(users.insert().values(id=user_id, display_name=display_name,
                        password_hash=generate_password_hash(DEMO_PASSWORD)))

    @contextmanager
    def write_transaction(self):
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def query(self, operation, connection, statement, parameters=None):
        return self.bo_data.execute(operation,
            lambda: [dict(row) for row in connection.execute(statement).mappings()],
            connection=connection, statement=str(statement), language="sql",
            parameters=parameters or {}, summarize=lambda result: {"rows": len(result), "result": {"row_count": len(result)}})

    def user(self, user_id: str):
        with self.engine.connect() as connection:
            result = self.query("db_users", connection, select(users).where(users.c.id == user_id), {"user_id": user_id})
            return result[0] if result else None

    def all_users(self):
        with self.engine.connect() as connection:
            return self.query("db_users", connection, select(users.c.id, users.c.display_name).order_by(users.c.id), {"user_id": ""})

    def file(self, connection, file_id: str, include_content=False):
        columns = list(files.c) if include_content else [column for column in files.c if column.name != "content"]
        result = self.query("db_file", connection, select(*columns).where(files.c.id == file_id), {"file_id": file_id})
        return result[0] if result else None

    def grants(self, connection, file_id: str):
        return self.query("db_grants", connection,
            select(shares.c.recipient_id, users.c.display_name).join(users, users.c.id == shares.c.recipient_id)
            .where(shares.c.file_id == file_id).order_by(shares.c.id), {"file_id": file_id})

    def visible_candidates(self, actor: str):
        with self.engine.connect() as connection:
            received = select(shares.c.file_id).where(shares.c.recipient_id == actor)
            return self.query("db_list", connection,
                select(files.c.id).where((files.c.owner_id == actor) | files.c.id.in_(received)), {"actor": actor})

    def snapshots(self):
        """Read selected authoritative values for independent checks and unified queries."""
        with self.engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(select(*[c for c in files.c if c.name != "content"])).mappings()]
            for row in rows:
                row["grant_count"] = connection.execute(select(func.count()).select_from(shares).where(shares.c.file_id == row["id"])).scalar_one()
                row["journal"] = json.loads(row["journal"])
            return rows
