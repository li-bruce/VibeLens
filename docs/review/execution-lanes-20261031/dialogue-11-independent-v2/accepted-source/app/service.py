"""Confirmed file review, directed sharing, and current-fact authorization."""
import json
from pathlib import Path
import uuid
from werkzeug.security import check_password_hash
from bo_stategraph.policy.runtime import evaluate
from bo_stategraph.workflow import FileWorkflow, file_context
from .predicates import same_identity
from .ports import NullProbe, NullObserver
from .storage import metadata_view

class DomainError(Exception):
    def __init__(self, code: str, status: int = 403):
        self.code, self.status = code, status
        super().__init__(code)

class FileService:
    def __init__(self, root: Path, store, bo_probe=None, bo_observer=None):
        self.root, self.store = root, store
        self.bo_probe, self.bo_observer = bo_probe or NullProbe(), bo_observer or NullObserver()
        project = json.loads((root / "bo_stategraph/project.json").read_text(encoding="utf-8-sig"))
        self.policy = project["model"]["policy"]
        self.workflow = FileWorkflow(root)

    def authorize(self, db, actor: str, operation: str, row: dict) -> bool:
        known = {user["id"] for user in self.store.read_users(db)}
        inputs = {"actor": actor, "uploader": row["uploader_id"], "reviewer": row["reviewer_id"],
            "recipient": row["recipient_id"], "logged_in": actor in known,
            "approved": row["state"] == "approved", "shared": bool(row["recipient_id"]),
            "pending": row["state"] == "pending", "withdrawn": row["state"] == "withdrawn",
            "reviewer_exists": row["reviewer_id"] in known}
        report = evaluate(self.policy, operation, inputs, {"same_identity": same_identity},
            fact_revision=row["id"] + ":" + str(row["revision"]), source_root=self.root)
        self.bo_observer.policy(report, row["id"])
        self.bo_probe.record("authorize_file", "decision", lambda: {
            "inputs": {"actor": actor, "operation": operation, "file_id": row["id"], "revision": row["revision"]},
            "outputs": {"allowed": report["value"] is True}})
        return report["value"] is True

    def login(self, username: str, password: str) -> bool:
        with self.bo_probe.span("sign_in", lambda: {"inputs": {"username": username, "password_present": bool(password)}}) as activation:
            with self.store.engine.connect() as connection:
                user = next((row for row in self.store.read_users(connection) if row["id"] == username), None)
            allowed = bool(user and check_password_hash(user["password_hash"], password))
            activation.result(lambda: {"outputs": {"allowed": allowed}})
            return allowed

    def users(self) -> list:
        with self.bo_probe.span("list_users") as activation:
            with self.store.engine.connect() as connection:
                rows = [{"id": user["id"], "display_name": user["display_name"]} for user in self.store.read_users(connection)]
            activation.result(lambda: {"outputs": {"count": len(rows)}})
            return rows

    def advance(self, row: dict, event: str, allowed: bool):
        with self.bo_probe.span("state_transition", lambda: {"inputs": {"event": event, "before": row["state"]}}) as activation:
            before = row["state"]
            result = self.workflow.step(before, event, file_context(row), allowed)
            row["state"], row["revision"] = result["state"], row["revision"] + 1
            row["journal"] = [*row["journal"], {"seq": row["revision"], "event": event, "before": before,
                "after": result["state"], "guards": result["guards"], "payload": result["payload"]}]
            activation.result(lambda: {"outputs": {"after": result["state"], "allowed": allowed}})
            return result

    def upload(self, actor: str, reviewer_id: str, filename: str, content: bytes) -> dict:
        with self.bo_probe.span("upload_file", lambda: {"inputs": {
            "actor": actor, "reviewer_id": reviewer_id, "filename": filename, "size": len(content)}}) as activation:
            if not filename or len(filename) > 200 or len(content) > 10 * 1024 * 1024:
                raise DomainError("invalid_upload", 400)
            row = {"id": uuid.uuid4().hex, "uploader_id": actor, "reviewer_id": reviewer_id,
                "recipient_id": "", "filename": filename, "size": len(content), "content": content,
                "state": "new", "revision": 0, "journal": []}
            with self.store.bo_data.transaction("db_transaction", self.store.write_transaction()) as connection:
                if not self.authorize(connection, actor, "upload", row):
                    raise DomainError("upload_denied")
                transition = self.advance(row, "submit", True)
                self.store.insert_file(connection, row)
            self.bo_observer.state(row, "upload_file", transition)
            result = self.store.bo_data.transform("db_metadata", metadata_view, row,
                before=lambda value: {"size": value["size"]}, after=lambda value: {"size": value["size"]})
            activation.result(lambda: {"outputs": {"file_id": row["id"], "state": row["state"], "revision": row["revision"]}})
            return result

    def review(self, actor: str, file_id: str, decision: str) -> dict:
        with self.bo_probe.span("review_file", lambda: {"inputs": {
            "actor": actor, "file_id": file_id, "decision": decision}}) as activation:
            if decision not in {"approve", "reject"}:
                raise DomainError("invalid_decision", 400)
            with self.store.bo_data.transaction("db_transaction", self.store.write_transaction()) as connection:
                row = self.store.read_file(connection, file_id)
                if not row:
                    raise DomainError("file_not_found", 404)
                if not self.authorize(connection, actor, "review", row):
                    raise DomainError("review_denied")
                try:
                    transition = self.advance(row, decision, True)
                except ValueError:
                    raise DomainError("review_closed", 409) from None
                self.store.update_file(connection, row)
            self.bo_observer.state(row, "review_file", transition)
            activation.result(lambda: {"outputs": {"state": row["state"], "revision": row["revision"]}})
            return metadata_view(row)

    def withdraw(self, actor: str, file_id: str) -> dict:
        with self.bo_probe.span("withdraw_file", lambda: {"inputs": {
            "actor": actor, "file_id": file_id}}) as activation:
            # The same write transaction orders withdrawal against a concurrent review.
            with self.store.bo_data.transaction("db_transaction", self.store.write_transaction()) as connection:
                row = self.store.read_file(connection, file_id)
                if not row:
                    raise DomainError("file_not_found", 404)
                if not self.authorize(connection, actor, "withdraw", row):
                    raise DomainError("withdraw_denied")
                transition = self.advance(row, "withdraw", True)
                self.store.update_file(connection, row)
            self.bo_observer.state(row, "withdraw_file", transition)
            activation.result(lambda: {"outputs": {"state": row["state"], "revision": row["revision"]}})
            return metadata_view(row)

    def share(self, actor: str, file_id: str, recipient_id: str) -> dict:
        with self.bo_probe.span("share_file", lambda: {"inputs": {
            "actor": actor, "file_id": file_id, "recipient_id": recipient_id}}) as activation:
            with self.store.bo_data.transaction("db_transaction", self.store.write_transaction()) as connection:
                row = self.store.read_file(connection, file_id)
                if not row:
                    raise DomainError("file_not_found", 404)
                if not self.authorize(connection, actor, "share", row):
                    raise DomainError("share_denied")
                if recipient_id not in {user["id"] for user in self.store.read_users(connection)}:
                    raise DomainError("recipient_not_found", 400)
                if row["recipient_id"] and row["recipient_id"] != recipient_id:
                    raise DomainError("recipient_already_set", 409)
                row["recipient_id"] = recipient_id
                transition = self.advance(row, "share", True)
                self.store.update_file(connection, row)
            self.bo_observer.state(row, "share_file", transition)
            activation.result(lambda: {"outputs": {"recipient_id": recipient_id, "state": row["state"], "revision": row["revision"]}})
            return metadata_view(row)

    def access(self, actor: str, file_id: str, download: bool = False) -> dict:
        with self.bo_probe.span("access_file", lambda: {"inputs": {
            "actor": actor, "file_id": file_id, "download": download}}) as activation:
            with self.store.engine.connect() as connection:
                row = self.store.read_file(connection, file_id)
                if not row:
                    raise DomainError("file_not_found", 404)
                if not self.authorize(connection, actor, "access", row):
                    raise DomainError("access_denied")
            result = metadata_view(row)
            if download:
                result["content"] = row["content"]
            activation.result(lambda: {"outputs": {"allowed": True, "size": row["size"], "state": row["state"]}})
            return result

    def visible_files(self, actor: str) -> list:
        with self.bo_probe.span("list_files", lambda: {"inputs": {"actor": actor}}) as activation:
            with self.store.engine.connect() as connection:
                identifiers = self.store.read_candidates(connection, actor)
            rows = [self.access(actor, identifier) for identifier in identifiers]
            activation.result(lambda: {"outputs": {"count": len(rows)}})
            return rows
