"""Team file sharing. SQLite commits are authoritative; capture is optional."""
import json
import time
import uuid
from pathlib import Path
from sqlalchemy import select, and_, or_, exists
from werkzeug.security import check_password_hash
from bo_stategraph.driver import FileDriver
from bo_stategraph.policy.runtime import evaluate
from .policy import flag_enabled, same_identity
from .ports import BOQuiet
from .models import users, files, shares, jobs, messages, journal


class BusinessError(Exception):
    def __init__(self, code, status=403):
        super().__init__(code)
        self.code, self.status = code, status


def new_id():
    return uuid.uuid4().hex


def principal(actor):
    return {"id": actor["id"], "kind": "user"} if actor else None


def normalize_filename(value):
    return value.strip()


class TeamService:
    def __init__(self, store, root, bo=None, delay=3.0):
        self.store, self.root, self.bo, self.delay = store, Path(root), bo or BOQuiet(), delay
        model = json.loads((self.root / "bo_stategraph/project.json").read_text(encoding="utf-8"))["model"]
        self.declaration, self.policy = model["machine"], model["policy"]

    def user(self, user_id):
        with self.store.engine.connect() as connection:
            row = connection.execute(select(users.c.id, users.c.username, users.c.role).where(users.c.id == user_id)).mappings().first()
            return dict(row) if row else None

    def identity(self, actor, file_id=None, recipient_id=None, workflow_id=None):
        value = {"actor": principal(actor)}
        if workflow_id:
            value["workflow_id"] = workflow_id
        objects = []
        if file_id:
            objects.append({"type": "File", "id": file_id, "role": "input"})
        if recipient_id:
            objects.append({"type": "User", "id": recipient_id, "role": "recipient"})
        value["objects"] = objects
        return value

    def facts(self, connection, actor, file=None):
        grant = False
        if actor and file:
            grant = connection.execute(select(shares.c.id).where(and_(shares.c.file_id == file["id"], shares.c.recipient_id == actor["id"]))).first() is not None
        return {"logged_in": actor is not None, "actor": actor["id"] if actor else "", "owner": file["owner_id"] if file else "", "is_administrator": bool(actor and actor["role"] == "admin"), "approved": bool(file and file["state"] == "approved"), "has_share": grant}

    def authorize(self, connection, operation, actor, file=None):
        report = evaluate(self.policy, operation, self.facts(connection, actor, file), {"same_identity": same_identity, "flag_enabled": flag_enabled}, fact_revision=new_id(), source_root=self.root)
        self.bo.policy(self.policy, report)
        return report["value"] is True

    def load_file(self, connection, file_id):
        row = connection.execute(select(files).where(files.c.id == file_id)).mappings().first()
        if row is None:
            raise BusinessError("file_not_found", 404)
        return dict(row)

    def sign_in(self, username, password):
        with self.bo.span("sign_in", lambda: {"inputs": {"username": username}}, provenance={"actor": None, "objects": []}, scope="application") as call:
            with self.store.engine.connect() as connection:
                row = connection.execute(select(users).where(users.c.username == username)).mappings().first()
                actor = {key: row[key] for key in ("id", "username", "role")} if row and check_password_hash(row["password_hash"], password) else None
            call.result(lambda: {"outputs": {"authenticated": actor is not None, "user_id": actor["id"] if actor else ""}, "provenance": {"actor": principal(actor), "objects": []}})
            return actor

    def sign_out(self, actor, clear_session):
        with self.bo.span("sign_out", lambda: {"inputs": {"user_id": actor["id"] if actor else "", "actor_id": actor["id"] if actor else ""}}, provenance=self.identity(actor), scope="application") as call:
            clear_session()
            call.result(lambda: {"outputs": {"outcome": "signed_out"}, "provenance": {"actor": None, "objects": []}})

    def upload_file(self, actor, name, content):
        with self.bo.span("upload_file", lambda: {"inputs": {"filename": name, "bytes": len(content), "actor_id": actor["id"] if actor else ""}}, provenance=self.identity(actor), scope="application") as call:
            outcome = "denied"
            call.result(lambda: {"outputs": {"outcome": outcome}})
            with self.bo.transaction("db_upload_tx", self.store.transaction()) as connection:
                if not self.authorize(connection, "upload", actor):
                    raise BusinessError("sign_in_required", 401)
                if not name or len(name) > 180 or not content or len(content) > 10 * 1024 * 1024:
                    raise BusinessError("invalid_file", 400)
                name = self.bo.transform("filename_transform", normalize_filename, name)
                if not name:
                    raise BusinessError("invalid_file", 400)
                file_id = new_id()
                self.bo.data("db_upload", lambda: connection.execute(files.insert().values(id=file_id, owner_id=actor["id"], name=name, content=content, state=self.declaration["initial"], reason="", revision=1, created_at=time.time())), parameters={"owner_id": actor["id"]}, statement="insert_file", targets=["table:files"], summarize=lambda result: {"count": result.rowcount})
            outcome = "uploaded"
            evidence = self.bo.record("pending_review", "change", lambda: {"outputs": {"state": "pending", "file_id": file_id}}, entity=file_id, scope="entity", revision=1, provenance=self.identity(actor, file_id))
            self.bo.state(file_id, "pending", {"owner_id": actor["id"]}, 1, evidence)
            call.result(lambda: {"outputs": {"outcome": outcome, "file_id": file_id, "state": "pending"}, "provenance": {"actor": principal(actor), "objects": [{"type": "File", "id": file_id, "version": "1", "role": "output"}]}})
            return {"id": file_id, "state": "pending"}

    def queue_notice(self, connection, node, file_id, recipient_id, kind, text, actor):
        with self.bo.span(node, lambda: {"inputs": {"file_id": file_id, "recipient_id": recipient_id}}, provenance=self.identity(actor, file_id, recipient_id), entity=file_id, scope="entity") as call:
            job_id = new_id()
            connection.execute(jobs.insert().values(id=job_id, file_id=file_id, recipient_id=recipient_id, kind=kind, text=text, carrier=json.dumps(self.bo.inject()), due_at=time.time() + self.delay, state="queued"))
            call.result(lambda: {"outputs": {"job_id": job_id, "outcome": "queued"}, "provenance": {**self.identity(actor, file_id, recipient_id), "objects": self.identity(actor, file_id, recipient_id)["objects"] + [{"type": "NotificationJob", "id": job_id, "role": "output"}]}})
            return job_id

    def review_file(self, actor, file_id, verdict, reason=""):
        with self.bo.span("review_file", lambda: {"inputs": {"file_id": file_id, "verdict": verdict, "reason": reason, "actor_id": actor["id"] if actor else ""}}, provenance=self.identity(actor, file_id), entity=file_id, scope="entity") as call:
            outcome = "denied"
            call.result(lambda: {"outputs": {"outcome": outcome}})
            with self.bo.transaction("db_review_tx", self.store.transaction()) as connection:
                file = self.load_file(connection, file_id)
                allowed = self.authorize(connection, "review", actor, file)
                if not allowed:
                    # A completed native denial is distinct from an unrelated exception.
                    call.result(lambda: {"outputs": {"outcome": "denied", "state": file["state"]}})
                    return {"ok": False, "code": "review_denied", "status": 403}
                if verdict not in ("approve", "reject") or (verdict == "reject" and not reason.strip()) or len(reason) > 200:
                    raise BusinessError("invalid_review", 400)
                if file["state"] != "pending":
                    raise BusinessError("review_already_completed", 409)
                witness = FileDriver(self.declaration).step(file["state"], verdict, allowed)
                revision = file["revision"] + 1
                connection.execute(files.update().where(files.c.id == file_id).values(state=witness["after"], reason=reason if verdict == "reject" else "", revision=revision))
                connection.execute(journal.insert().values(id=new_id(), file_id=file_id, event=verdict, before_state=witness["before"], after_state=witness["after"], actor_id=actor["id"], revision=revision, guards=json.dumps(witness["guards"])))
                job_id = self.queue_notice(connection, "review_notice", file_id, file["owner_id"], "review", witness["after"] + (": " + reason if reason else ""), actor)
            state = witness["after"]
            evidence = self.bo.record("approved_file" if state == "approved" else "rejected_file", "change", lambda: {"outputs": {"state": state, "file_id": file_id}}, entity=file_id, scope="entity", revision=revision, provenance=self.identity(actor, file_id))
            self.bo.state(file_id, state, {"owner_id": file["owner_id"]}, revision, evidence, event=verdict, guards={"review_allowed": allowed}, payload={})
            call.record("commit", lambda: {"outputs": {"outcome": "reviewed", "state": state, "before": witness["before"], "event": verdict, "guard": allowed, "revision": revision}})
            call.result(lambda: {"outputs": {"outcome": "reviewed", "state": state, "job_id": job_id}})
            return {"ok": True, "state": state, "job_id": job_id}

    def share_file(self, actor, file_id, recipient_ids):
        with self.bo.span("share_file", lambda: {"inputs": {"file_id": file_id, "recipient_ids": recipient_ids, "actor_id": actor["id"] if actor else ""}}, provenance=self.identity(actor, file_id), entity=file_id, scope="entity") as call:
            with self.bo.transaction("db_share_tx", self.store.transaction()) as connection:
                file = self.load_file(connection, file_id)
                if not self.authorize(connection, "share", actor, file):
                    raise BusinessError("share_denied")
                if not recipient_ids or len(recipient_ids) > 4 or len(set(recipient_ids)) != len(recipient_ids) or actor["id"] in recipient_ids:
                    raise BusinessError("invalid_recipients", 400)
                found = set(connection.execute(select(users.c.id).where(users.c.id.in_(recipient_ids))).scalars())
                if found != set(recipient_ids):
                    raise BusinessError("invalid_recipients", 400)
                share_ids = []
                for recipient_id in recipient_ids:
                    existing = connection.execute(select(shares.c.id).where(and_(shares.c.file_id == file_id, shares.c.recipient_id == recipient_id))).scalar()
                    if existing:
                        share_ids.append(existing)
                        continue
                    share_id = new_id()
                    connection.execute(shares.insert().values(id=share_id, file_id=file_id, recipient_id=recipient_id))
                    self.queue_notice(connection, "share_notice", file_id, recipient_id, "share", file["name"], actor)
                    share_ids.append(share_id)
            call.record("commit", lambda: {"outputs": {"outcome": "shared", "granted": True}})
            call.result(lambda: {"outputs": {"outcome": "shared", "share_ids": share_ids}, "provenance": {**self.identity(actor, file_id), "objects": self.identity(actor, file_id)["objects"] + [{"type": "Share", "id": value, "role": "output"} for value in share_ids] + [{"type": "User", "id": value, "role": "recipient"} for value in recipient_ids]}})
            return {"ok": True, "share_ids": share_ids}

    def access_file(self, actor, file_id):
        with self.bo.span("access_file", lambda: {"inputs": {"file_id": file_id, "actor_id": actor["id"] if actor else ""}}, provenance=self.identity(actor, file_id), entity=file_id, scope="entity") as call:
            with self.store.engine.connect() as connection:
                file = self.load_file(connection, file_id)
                if not self.authorize(connection, "access", actor, file):
                    raise BusinessError("access_denied", 403 if actor else 401)
            call.result(lambda: {"outputs": {"outcome": "allowed", "bytes": len(file["content"]), "state": file["state"]}})
            return file

    def list_files(self, actor, review=False):
        with self.bo.span("list_files", lambda: {"inputs": {"review": review, "actor_id": actor["id"] if actor else ""}}, provenance=self.identity(actor), scope="application") as call:
            if not actor:
                raise BusinessError("sign_in_required", 401)
            if review and actor["role"] != "admin":
                raise BusinessError("review_denied")
            with self.store.engine.connect() as connection:
                query = select(files.c.id, files.c.name, files.c.owner_id, files.c.state, files.c.reason, files.c.revision).order_by(files.c.created_at.desc()).limit(64)
                if review:
                    query = query.where(and_(files.c.state == "pending", files.c.owner_id != actor["id"]))
                elif actor["role"] != "admin":
                    query = query.where(or_(files.c.owner_id == actor["id"], and_(files.c.state == "approved", exists(select(shares.c.id).where(and_(shares.c.file_id == files.c.id, shares.c.recipient_id == actor["id"]))))))
                rows = self.bo.data("db_list_files", lambda: [dict(row) for row in connection.execute(query).mappings()], parameters={"actor_id": actor["id"]}, statement="list_files", targets=["table:files", "table:shares"], summarize=lambda result: {"count": len(result)})
            call.result(lambda: {"outputs": {"count": len(rows), "file_ids": [row["id"] for row in rows]}})
            return rows

    def list_messages(self, actor):
        with self.bo.span("list_messages", lambda: {"inputs": {"recipient_id": actor["id"] if actor else "", "actor_id": actor["id"] if actor else ""}}, provenance=self.identity(actor), scope="application") as call:
            if not actor:
                raise BusinessError("sign_in_required", 401)
            with self.store.engine.connect() as connection:
                rows = [dict(row) for row in connection.execute(select(messages).where(messages.c.recipient_id == actor["id"]).order_by(messages.c.created_at.desc()).limit(64)).mappings()]
            call.result(lambda: {"outputs": {"count": len(rows), "message_ids": [row["id"] for row in rows]}})
            return rows

    def deliver_notices(self, clock=None):
        clock = time.time() if clock is None else clock
        with self.store.engine.connect() as connection:
            due = [dict(row) for row in connection.execute(select(jobs).where(and_(jobs.c.state == "queued", jobs.c.due_at <= clock)).limit(32)).mappings()]
        delivered = []
        for job in due:
            with self.bo.receive(json.loads(job["carrier"])):
                provenance = {"actor": {"id": "notification-worker", "kind": "service"}, "workflow_id": job["id"], "objects": [{"type": "File", "id": job["file_id"], "role": "input"}, {"type": "NotificationJob", "id": job["id"], "role": "input"}, {"type": "User", "id": job["recipient_id"], "role": "recipient"}]}
                with self.bo.span("deliver_notices", lambda: {"inputs": {"job_id": job["id"], "recipient_id": job["recipient_id"]}}, provenance=provenance, entity=job["file_id"], scope="entity") as call:
                    with self.bo.transaction("db_delivery_tx", self.store.transaction()) as connection:
                        current = connection.execute(select(jobs.c.state).where(jobs.c.id == job["id"])).scalar()
                        if current != "queued":
                            call.result(lambda: {"outputs": {"outcome": "already_delivered", "message_id": ""}})
                            continue
                        message_id = new_id()
                        connection.execute(messages.insert().values(id=message_id, job_id=job["id"], recipient_id=job["recipient_id"], file_id=job["file_id"], kind=job["kind"], text=job["text"], created_at=clock))
                        connection.execute(jobs.update().where(jobs.c.id == job["id"]).values(state="delivered"))
                    call.result(lambda: {"outputs": {"outcome": "delivered", "message_id": message_id}, "provenance": {**provenance, "objects": provenance["objects"] + [{"type": "Message", "id": message_id, "role": "output"}]}})
                    delivered.append(message_id)
        return delivered

    def snapshot(self):
        with self.store.engine.connect() as connection:
            return [{"id": row.id, "state": row.state, "revision": row.revision, "context": {"owner_id": row.owner_id}} for row in connection.execute(select(files.c.id, files.c.state, files.c.revision, files.c.owner_id))]
