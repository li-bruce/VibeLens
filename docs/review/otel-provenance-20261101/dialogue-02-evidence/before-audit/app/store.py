"""Application-owned schema initialization and explicit SQLite transactions."""
from contextlib import contextmanager
from sqlalchemy import create_engine, select, event
from werkzeug.security import generate_password_hash
from .models import metadata, users


class Store:
    def __init__(self, path):
        self.engine = create_engine("sqlite:///" + str(path), connect_args={"check_same_thread": False, "timeout": 15})
        event.listen(self.engine, "connect", self.configure)

    @staticmethod
    def configure(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

    def initialize(self):
        metadata.create_all(self.engine)
        with self.transaction() as connection:
            if connection.execute(select(users.c.id).limit(1)).first() is None:
                for username, role in [("admin1", "admin"), ("admin2", "admin"), ("member1", "member"), ("member2", "member")]:
                    connection.execute(users.insert().values(id=username, username=username, role=role, password_hash=generate_password_hash("Trial-2026!")))

    @contextmanager
    def transaction(self):
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def close(self):
        self.engine.dispose()
