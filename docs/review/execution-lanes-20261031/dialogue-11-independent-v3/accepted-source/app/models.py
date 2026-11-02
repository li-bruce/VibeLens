"""Database-enforced structure; importing declarations never opens a database."""
from sqlalchemy import MetaData, Table, Column, String, Integer, LargeBinary, ForeignKey, CheckConstraint
metadata = MetaData()
users = Table("users", metadata,
    Column("id", String, primary_key=True),
    Column("display_name", String, nullable=False),
    Column("password_hash", String, nullable=False))
files = Table("files", metadata,
    Column("id", String, primary_key=True),
    Column("uploader_id", ForeignKey("users.id"), nullable=False),
    Column("reviewer_id", ForeignKey("users.id"), nullable=False),
    Column("recipient_id", ForeignKey("users.id"), nullable=True),
    Column("filename", String, nullable=False),
    Column("size", Integer, nullable=False),
    Column("content", LargeBinary, nullable=False),
    Column("state", String, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("journal", String, nullable=False),
    Column("rejection_reason", String, nullable=False, server_default=""),
    CheckConstraint("uploader_id <> reviewer_id"),
    CheckConstraint("size >= 0"),
    CheckConstraint("revision >= 1"),
    CheckConstraint("state IN ('pending', 'approved', 'rejected', 'withdrawn')"),
    CheckConstraint("recipient_id IS NULL OR state = 'approved'"))
