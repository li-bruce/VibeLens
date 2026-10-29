"""Minimal sharing operations, driven by declared permission and state rules."""

import hashlib
import json
from pathlib import Path
import uuid
from sqlalchemy import select
from werkzeug.security import check_password_hash
from bo_stategraph.policy.runtime import evaluate
from bo_stategraph.workflow import FileWorkflow, file_context
from .models import users, files, shares
from .predicates import same_identity, flag_enabled
from .ports import NullTrace


class DomainError(Exception):
    def __init__(self, code: str, status=403):
        self.code, self.status = code, status
        super().__init__(code)


def metadata_values(values: dict):
    return {"filename": values["filename"], "size": len(values["content"]),
            "sha256": hashlib.sha256(values["content"]).hexdigest()}


class SharingService:
    def __init__(self, root: Path, store, bo_trace=None):
        self.root, self.store = root, store
        self.bo_trace = bo_trace or NullTrace()
        self.workflow = FileWorkflow(root)
        self.policy = self.workflow.project["model"]["policy"]

    def authenticate(self, username: str, password: str):
        user = self.store.user(username)
        allowed = bool(user and check_password_hash(user["password_hash"], password))
        self.bo_trace.record("login", "decision", lambda: {"inputs": {"username": username, "password_present": bool(password)}, "outputs": {"allowed": allowed}})
        if not allowed:
            raise DomainError("invalid_credentials", 401)
        return {"id": user["id"], "display_name": user["display_name"]}

    def logout(self, actor: str):
        self.bo_trace.record("logout", "commit", lambda: {"inputs": {"actor": actor}, "outputs": {"signed_out": True}})

    def list_users(self, actor: str):
        if not self.store.user(actor):
            raise DomainError("login_required", 401)
        result = self.store.all_users()
        self.bo_trace.record("users", "return", lambda: {"inputs": {"actor": actor}, "outputs": {"count": len(result)}})
        return result

    def authorize(self, operation: str, actor: str, row: dict, grants: list):
        facts = {"actor": actor, "owner": row.get("owner_id", ""),
                 "logged_in": bool(actor and self.store.user(actor)),
                 "is_recipient": any(grant["recipient_id"] == actor for grant in grants)}
        result = evaluate(self.policy, operation, facts,
            {"same_identity": same_identity, "flag_enabled": flag_enabled},
            fact_revision=f"{row.get('id', 'new')}:{row.get('revision', 0)}:{uuid.uuid4().hex}", source_root=self.root)
        self.bo_trace.policy(self.policy, result, row.get("id", "application"))
        self.bo_trace.record("authorize", "decision", lambda: {
            "inputs": {"operation": operation, "actor": actor, "owner_id": row.get("owner_id", ""), "grant_count": len(grants)},
            "outputs": {"allowed": result["value"] is True, "decision": result["decision"]}})
        if result["value"] is not True:
            raise DomainError("permission_denied", 403 if actor else 401)
        return True

    def upload(self, actor: str, filename: str, content: bytes):
        self.authorize("upload", actor, {}, [])
        filename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not filename or len(filename) > 180 or any(ord(char) < 32 for char in filename):
            raise DomainError("invalid_filename", 400)
        if len(content) > 16 * 1024 * 1024:
            raise DomainError("file_too_large", 413)
        selected = self.store.bo_data.transform("db_metadata", metadata_values,
            {"filename": filename, "content": content}, before=lambda value: {"filename": value["filename"]},
            after=lambda value: value)
        row = {"id": uuid.uuid4().hex, "owner_id": actor, **selected, "grant_count": 0}
        transition = self.workflow.step("empty", "upload", file_context(row), True)
        journal = [{"seq": 1, "event": "upload", "before": "empty", "after": transition["state"], "guards": transition["guards"]}]
        with self.store.bo_data.transaction("db_upload_tx", self.store.write_transaction()) as connection:
            self.store.bo_data.execute("db_insert_file", lambda: connection.execute(files.insert().values(
                **{k: v for k, v in row.items() if k != "grant_count"}, content=content,
                state=transition["state"], revision=1, journal=json.dumps(journal))),
                connection=connection, statement=str(files.insert()), language="sql", parameters={"file_id": row["id"]}, summarize=lambda result: {"rows": result.rowcount, "result": {"row_count": result.rowcount}})
        row.update(state=transition["state"], revision=1, journal=journal)
        witness = self.bo_trace.record("upload", "commit", lambda: {"inputs": {"actor": actor, "filename": filename, "size": len(content)},
            "outputs": {"file_id": row["id"], "owner_id": actor, "state": row["state"], "revision": 1}},
            entity=row["id"], attempt=row["id"], scope="entity", revision=1)
        self.bo_trace.state(row, witness, transition)
        return row

    def share(self, actor: str, file_id: str, recipient_id: str):
        with self.store.bo_data.transaction("db_share_tx", self.store.write_transaction()) as connection:
            row = self.store.file(connection, file_id)
            if row is None:
                raise DomainError("file_not_found", 404)
            grants = self.store.grants(connection, file_id)
            self.authorize("share", actor, row, grants)
            target = self.store.query("db_users", connection, select(users.c.id).where(users.c.id == recipient_id), {"user_id": recipient_id})
            if not target:
                raise DomainError("recipient_not_found", 400)
            existing = any(grant["recipient_id"] == recipient_id for grant in grants)
            row["grant_count"] = len(grants) + (0 if existing else 1)
            transition = self.workflow.step(row["state"], "share", file_context(row), True)
            revision = row["revision"] + 1
            journal = json.loads(row["journal"]) + [{"seq": revision, "event": "share", "before": row["state"], "after": transition["state"], "guards": transition["guards"]}]
            def persist_share():
                if not existing:
                    connection.execute(shares.insert().values(file_id=file_id, recipient_id=recipient_id))
                return connection.execute(files.update().where(files.c.id == file_id).values(state=transition["state"], revision=revision, journal=json.dumps(journal)))
            self.store.bo_data.execute("db_insert_share", persist_share, connection=connection,
                statement=str(shares.insert()) + "; " + str(files.update().where(files.c.id == file_id).values(state=transition["state"], revision=revision, journal=json.dumps(journal))), language="sql", parameters={"file_id": file_id, "recipient_id": recipient_id}, summarize=lambda result: {"rows": result.rowcount, "result": {"row_count": result.rowcount}})
        row.update(state=transition["state"], revision=revision, journal=journal)
        witness = self.bo_trace.record("share", "commit", lambda: {"inputs": {"actor": actor, "file_id": file_id, "recipient_id": recipient_id},
            "outputs": {"state": row["state"], "revision": revision, "grant_count": row["grant_count"]}}, entity=file_id, attempt=file_id, scope="entity", revision=revision)
        self.bo_trace.state(row, witness, transition)
        return row

    def view(self, actor: str, file_id: str):
        with self.store.engine.connect() as connection:
            row = self.store.file(connection, file_id)
            if row is None:
                raise DomainError("file_not_found", 404)
            grants = self.store.grants(connection, file_id)
            self.authorize("view", actor, row, grants)
            owner = self.store.user(row["owner_id"])
            result = {"id": file_id, "filename": row["filename"], "size": row["size"],
                "owner_id": row["owner_id"], "owner_name": owner["display_name"], "state": row["state"],
                "is_owner": actor == row["owner_id"], "recipients": grants if actor == row["owner_id"] else []}
        self.bo_trace.record("view", "return", lambda: {"inputs": {"actor": actor, "file_id": file_id},
            "outputs": {"owner_id": result["owner_id"], "filename": result["filename"], "size": result["size"], "can_share": result["is_owner"]}}, entity=file_id, attempt=file_id, scope="entity")
        return result

    def revoke(self, actor: str, file_id: str, recipient_id: str):
        with self.store.bo_data.transaction("db_revoke_tx", self.store.write_transaction()) as connection:
            row = self.store.file(connection, file_id)
            if row is None:
                raise DomainError("file_not_found", 404)
            grants = self.store.grants(connection, file_id)
            self.authorize("revoke", actor, row, grants)
            statement = shares.delete().where((shares.c.file_id == file_id) & (shares.c.recipient_id == actor))
            result = self.store.bo_data.execute("db_delete_share", lambda: connection.execute(statement),
                connection=connection, statement=str(statement), language="sql",
                parameters={"file_id": file_id, "recipient_id": recipient_id},
                summarize=lambda result: {"rows": result.rowcount, "result": {"row_count": result.rowcount}})
            removed = result.rowcount > 0
            row["grant_count"] = len(self.store.grants(connection, file_id))
            transition = self.workflow.step(row["state"], "revoke", file_context(row), True)
            revision = row["revision"] + 1
            journal = json.loads(row["journal"]) + [{"seq": revision, "event": "revoke",
                "before": row["state"], "after": transition["state"], "guards": transition["guards"]}]
            update = files.update().where(files.c.id == file_id).values(state=transition["state"], revision=revision, journal=json.dumps(journal))
            self.store.bo_data.execute("db_revoke_state", lambda: connection.execute(update),
                connection=connection, statement=str(update), language="sql", parameters={"file_id": file_id},
                summarize=lambda result: {"rows": result.rowcount, "result": {"row_count": result.rowcount}})
        row.update(state=transition["state"], revision=revision, journal=journal)
        witness = self.bo_trace.record("revoke", "commit", lambda: {
            "inputs": {"actor": actor, "file_id": file_id, "recipient_id": recipient_id},
            "outputs": {"state": row["state"], "revision": revision, "grant_count": row["grant_count"], "removed": removed}},
            entity=file_id, attempt=file_id, scope="entity", revision=revision)
        self.bo_trace.state(row, witness, transition)
        return row

    def list_files(self, actor: str):
        if not self.store.user(actor):
            raise DomainError("login_required", 401)
        result = [self.view(actor, row["id"]) for row in self.store.visible_candidates(actor)]
        self.bo_trace.record("list", "return", lambda: {"inputs": {"actor": actor}, "outputs": {"count": len(result)}})
        return result

    def download(self, actor: str, file_id: str):
        with self.store.engine.connect() as connection:
            row = self.store.file(connection, file_id, include_content=True)
            if row is None:
                raise DomainError("file_not_found", 404)
            grants = self.store.grants(connection, file_id)
            self.authorize("download", actor, row, grants)
            content = bytes(row["content"])
        self.bo_trace.record("download", "return", lambda: {"inputs": {"actor": actor, "file_id": file_id},
            "outputs": {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}}, entity=file_id, attempt=file_id, scope="entity")
        return row["filename"], content
