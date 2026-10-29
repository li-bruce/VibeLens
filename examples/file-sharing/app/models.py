"""Native SQLite schema declarations; import has no database effects."""

from sqlalchemy import (MetaData, Table, Column, String, Integer, LargeBinary,
                        ForeignKey, UniqueConstraint, CheckConstraint)

metadata = MetaData()
users = Table("users", metadata,
    Column("id", String, primary_key=True),
    Column("display_name", String, nullable=False),
    Column("password_hash", String, nullable=False))
files = Table("files", metadata,
    Column("id", String, primary_key=True),
    Column("owner_id", String, ForeignKey("users.id"), nullable=False),
    Column("filename", String, nullable=False),
    Column("size", Integer, nullable=False),
    Column("sha256", String, nullable=False),
    Column("content", LargeBinary, nullable=False),
    Column("state", String, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("journal", String, nullable=False),
    CheckConstraint("size >= 0", name="file_size_nonnegative"),
    CheckConstraint("revision >= 1", name="file_revision_positive"),
    CheckConstraint("state IN ('private', 'shared')", name="file_state_valid"))
shares = Table("shares", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("file_id", String, ForeignKey("files.id"), nullable=False),
    Column("recipient_id", String, ForeignKey("users.id"), nullable=False),
    UniqueConstraint("file_id", "recipient_id", name="unique_file_recipient"))
