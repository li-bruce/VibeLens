"""Application-owned file sharing; persistence and authorization stay independent of Web."""

from pathlib import Path
import sqlite3
import uuid


class DatabaseConnection(sqlite3.Connection):
    """Commit or roll back a unit of work and always release its file handle."""

    def __exit__(self, *error):
        try:
            return super().__exit__(*error)
        finally:
            self.close()


class AccessDenied(Exception):
    """A real authorization rejection carrying the facts used by the application."""

    def __init__(self, facts):
        super().__init__("Access denied")
        self.facts = facts


def same_identity(left: str, right: str) -> bool:
    """Compare the current actor with an owner or recipient.

    Args:
        left: Current actor identity.
        right: Identity required by this operation.
    """
    return left == right


def can_manage(actor: str, owner: str) -> bool:
    """Allow the uploaded file's owner to change its recipient grant."""
    return same_identity(actor, owner)


def can_read(actor: str, recipient: str, active: bool) -> bool:
    """Allow the named recipient to read a currently active grant."""
    return same_identity(actor, recipient) and active


class FileService:
    """Store local files and an independent grant for each selected recipient."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)
        self.database = folder / "files.sqlite3"
        with self.connect() as connection:
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS files "
                "(id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS grants "
                "(file_id TEXT NOT NULL REFERENCES files(id), recipient TEXT NOT NULL, "
                "active INTEGER NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(file_id, recipient));"
            )
            primary_key = [
                row["name"] for row in connection.execute("PRAGMA table_info(grants)") if row["pk"]
            ]
            if primary_key == ["file_id"]:
                # Preserve the real v1 grant and revision while adopting the
                # confirmed v2 identity. The observer never performs migrations.
                connection.executescript(
                    "CREATE TABLE grants_v2 (file_id TEXT NOT NULL REFERENCES files(id), "
                    "recipient TEXT NOT NULL, active INTEGER NOT NULL, revision INTEGER NOT NULL, "
                    "PRIMARY KEY(file_id, recipient));"
                    "INSERT INTO grants_v2 SELECT file_id, recipient, active, revision FROM grants;"
                    "DROP TABLE grants; ALTER TABLE grants_v2 RENAME TO grants;"
                )

    def connect(self):
        """Open one application database connection with foreign keys enabled."""
        connection = sqlite3.connect(self.database, factory=DatabaseConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def upload(self, actor: str, name: str, content: bytes):
        """Store supplied bytes and persist their owner; return the new file identity."""
        file_id = uuid.uuid4().hex
        (self.folder / file_id).write_bytes(content)
        with self.connect() as connection:
            connection.execute("INSERT INTO files VALUES (?, ?, ?)", (file_id, actor, name))
        return {"file_id": file_id, "owner": actor, "name": name}

    def facts(self, actor: str, file_id: str, recipient: str | None = None):
        """Read the selected recipient's grant before an authorization decision.

        A read request selects its actor; owner operations explicitly select the
        recipient whose grant they will change.
        """
        recipient = actor if recipient is None else recipient
        with self.connect() as connection:
            row = connection.execute(
                "SELECT f.owner, COALESCE(g.recipient, ?) recipient, "
                "COALESCE(g.active, 0) active, COALESCE(g.revision, 0) revision "
                "FROM files f LEFT JOIN grants g ON g.file_id=f.id AND g.recipient=? WHERE f.id=?",
                (recipient, recipient, file_id),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(file_id)
        return {
            "actor": actor,
            "owner": row["owner"],
            "recipient": row["recipient"],
            "active": bool(row["active"]),
            "revision": row["revision"],
            "file_id": file_id,
            "timing": "before_effect",
            "scope": "current_request",
        }

    def share(self, actor: str, file_id: str, recipient: str):
        """Activate this recipient's grant after checking the uploaded file's owner."""
        facts = self.facts(actor, file_id, recipient)
        if not can_manage(actor, facts["owner"]):
            raise AccessDenied(facts)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO grants VALUES (?, ?, 1, 1) ON CONFLICT(file_id, recipient) DO UPDATE "
                "SET active=1, revision=revision+1",
                (file_id, recipient),
            )
            revision = connection.execute(
                "SELECT revision FROM grants WHERE file_id=? AND recipient=?", (file_id, recipient)
            ).fetchone()[0]
        return {"file_id": file_id, "recipient": recipient, "state": "active", "revision": revision}

    def revoke(self, actor: str, file_id: str, recipient: str):
        """Deactivate only the selected recipient's grant; other grants remain intact."""
        facts = self.facts(actor, file_id, recipient)
        if not can_manage(actor, facts["owner"]):
            raise AccessDenied(facts)
        with self.connect() as connection:
            connection.execute(
                "UPDATE grants SET active=0, revision=revision+1 WHERE file_id=? AND recipient=?",
                (file_id, recipient),
            )
            row = connection.execute(
                "SELECT recipient, revision FROM grants WHERE file_id=? AND recipient=?",
                (file_id, recipient),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(file_id)
        return {
            "file_id": file_id,
            "recipient": row["recipient"],
            "state": "inactive",
            "revision": row["revision"],
        }

    def received(self, actor: str):
        """List files whose current active grant names this colleague."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT f.id file_id, f.name, f.owner FROM files f JOIN grants g ON g.file_id=f.id "
                "WHERE g.recipient=? ORDER BY f.name",
                (actor,),
            ).fetchall()
        received = []
        for row in rows:
            facts = self.facts(actor, row["file_id"])
            if can_read(actor, facts["recipient"], facts["active"]):
                received.append(dict(row))
        return received

    def download(self, actor: str, file_id: str):
        """Read the current grant for every download, including previously issued URLs."""
        facts = self.facts(actor, file_id)
        if not can_read(actor, facts["recipient"], facts["active"]):
            raise AccessDenied(facts)
        return (self.folder / file_id).read_bytes()
