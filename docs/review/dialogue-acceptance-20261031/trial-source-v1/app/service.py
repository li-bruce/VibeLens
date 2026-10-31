"""Authenticated file sharing, selected review and revocable downloads."""

import json
from pathlib import Path
import uuid

from sqlalchemy import select, insert, update, and_
from werkzeug.security import check_password_hash
from app.models import users, files, shares, notifications, journal
from app.policy import authorize
from app.storage import timestamp
from bo_stategraph.workflow import SharingWorkflow


class BusinessError(Exception):
    def __init__(self, code, status=403):
        self.code, self.status = code, status
        super().__init__(code)


def clean_filename(value: str) -> str:
    name = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or len(name) > 180 or any(ord(char) < 32 for char in name):
        raise BusinessError("invalid_filename", 400)
    return name


class Service:
    def __init__(self, store, project, root):
        self.store, self.project, self.root = store, project, Path(root)
        self.monitor = store.monitor
        self.machine = project["model"]["machine"]
        self.policy = project["model"]["policy"]

    def _one(self, connection, table, identifier):
        rows = self.store.read(connection, select(table).where(table.c.id == identifier))
        if not rows:
            raise BusinessError("not_found", 404)
        return rows[0]

    def _facts(self, connection, actor_id, file=None, share=None):
        authenticated = bool(actor_id) and bool(self.store.read(connection, select(users.c.id).where(users.c.id == actor_id)))
        owner_id = file["owner_id"] if file else share["owner_id"] if share else ""
        granted = bool(file and actor_id == owner_id)
        if file and not granted:
            granted = bool(self.store.read(connection, select(shares.c.id).where(and_(shares.c.file_id == file["id"],shares.c.recipient_id == actor_id,shares.c.state == "approved"))))
        return {"signed_in":authenticated,"actor_is_owner":bool(owner_id and actor_id == owner_id),"download_granted":granted,"actor_is_selected_reviewer":bool(share and actor_id == share["reviewer_id"]),"share_is_pending":bool(share and share["state"] == "pending"),"share_is_approved":bool(share and share["state"] == "approved")}

    def _evaluate(self, connection, actor_id, operation, file=None, share=None):
        facts = self._facts(connection, actor_id, file, share)
        entity = share["id"] if share else file["id"] if file else "application"
        evaluation = authorize(self.policy, operation, facts, entity + ":" + str(share["revision"] if share else uuid.uuid4().hex), self.root)
        self.monitor.policy(self.policy, evaluation, entity, entity)
        return evaluation, facts

    def _authorize(self, connection, actor_id, operation, file=None, share=None):
        evaluation, facts = self._evaluate(connection, actor_id, operation, file, share)
        if evaluation["value"] is not True:
            raise BusinessError("permission_denied", 403 if facts["signed_in"] else 401)
        return evaluation

    def login(self, username: str, password: str) -> dict:
        with self.monitor.span("login", lambda:{"inputs":{"username":username,"password_supplied":bool(password)}}) as operation:
            with self.store.transaction() as connection:
                rows = self.store.read(connection, select(users).where(users.c.id == username))
                allowed = bool(rows) and check_password_hash(rows[0]["password_hash"], password)
            operation.result(lambda:{"outputs":{"allowed":allowed,"user_id":username if allowed else ""}})
            operation.record("decision",lambda:{"outputs":{"allowed":allowed,"user_id":username if allowed else ""}})
            if not allowed:
                raise BusinessError("invalid_login", 401)
            return {"id":rows[0]["id"],"name":rows[0]["name"]}

    def logout(self, actor_id: str) -> None:
        with self.monitor.span("logout", lambda:{"inputs":{"actor_id":actor_id}}) as operation:
            operation.result(lambda:{"outputs":{"logged_out":True}})

    def upload(self, actor_id: str, filename: str, content: bytes) -> dict:
        with self.monitor.span("upload", lambda:{"inputs":{"actor_id":actor_id,"filename":filename,"size":len(content)}}) as operation:
            if len(content) > 20 * 1024 * 1024:
                raise BusinessError("file_too_large", 413)
            name = self.monitor.transform("db_transform", clean_filename, filename, before=lambda value:{"filename":value}, after=lambda value:{"filename":value})
            identifier = uuid.uuid4().hex
            path = self.store.blobs / identifier
            row = {"id":identifier,"owner_id":actor_id,"filename":name,"size":len(content),"created_at":timestamp()}
            try:
                with self.store.transaction() as connection:
                    self._authorize(connection, actor_id, "upload")
                    path.write_bytes(content)
                    self.store.write(connection, insert(files).values(**row))
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            operation.record("commit", lambda:{"outputs":{"file_id":identifier,"saved":True,"size":len(content)}})
            operation.result(lambda:{"outputs":{"file_id":identifier,"saved":True,"size":len(content)}})
            return row

    def request_share(self, actor_id: str, file_id: str, recipient_id: str, reviewer_id: str) -> dict:
        with self.monitor.span("share", lambda:{"inputs":{"actor_id":actor_id,"file_id":file_id,"recipient_id":recipient_id,"reviewer_id":reviewer_id}}) as operation:
            with self.store.transaction() as connection:
                file = self._one(connection, files, file_id)
                self._authorize(connection, actor_id, "share", file=file)
                self._one(connection, users, recipient_id)
                self._one(connection, users, reviewer_id)
                if recipient_id == actor_id:
                    raise BusinessError("recipient_must_differ", 400)
                existing = self.store.read(connection, select(shares.c.id).where(and_(shares.c.file_id == file_id,shares.c.recipient_id == recipient_id,shares.c.state.in_(["pending","approved"]))))
                if existing:
                    raise BusinessError("share_already_active", 409)
                row={"id":uuid.uuid4().hex,"file_id":file_id,"owner_id":actor_id,"recipient_id":recipient_id,"reviewer_id":reviewer_id,"state":self.machine["initial"],"revision":1,"created_at":timestamp()}
                self.store.write(connection, insert(shares).values(**row))
                self._journal(connection,row,"submit",row["state"],{"authorized":True})
            self.monitor.state("share",row,{"event":None,"guards":{},"payload":{}},initial=True)
            operation.record("commit",lambda:{"outputs":{"share_id":row["id"],"state":row["state"],"revision":1}})
            operation.result(lambda:{"outputs":{"share_id":row["id"],"state":row["state"],"revision":1}})
            return row

    def _journal(self, connection, row, event, before, guards):
        self.store.write(connection, insert(journal).values(id=uuid.uuid4().hex,share_id=row["id"],revision=row["revision"],event=event,before_state=before,after_state=row["state"],guards=json.dumps(guards),created_at=timestamp()))

    def _messages(self, connection, row, file, kind):
        recipients = sorted({row["owner_id"],row["recipient_id"],row["reviewer_id"]})
        with self.monitor.span("notification" if kind == "review_result" else "share_message", lambda:{"inputs":{"share_id":row["id"],"kind":kind,"recipients":recipients}}) as operation:
            for recipient in recipients:
                self.store.write(connection, insert(notifications).values(id=uuid.uuid4().hex,user_id=recipient,share_id=row["id"],kind=kind,state=row["state"],filename=file["filename"],is_read=0,created_at=timestamp()))
            operation.result(lambda:{"outputs":{"count":len(recipients),"state":row["state"]}})

    def change_share(self, actor_id: str, share_id: str, event: str) -> dict:
        node = "review" if event in {"approve","reject"} else "cancel_share" if event == "cancel" else "revoke"
        policy_operation = "review" if node == "review" else node
        with self.monitor.span(node,lambda:{"inputs":{"actor_id":actor_id,"share_id":share_id,"event":event}}) as operation:
            with self.store.transaction() as connection:
                row=self._one(connection,shares,share_id)
                self._authorize(connection,actor_id,policy_operation,share=row)
                context={key:row[key] for key in self.machine["context"]}
                try:
                    result=SharingWorkflow(self.machine,True).advance(row["state"],event,context)
                except ValueError:
                    raise BusinessError("invalid_transition",409) from None
                before=row["state"]
                row.update(state=result["state"],revision=row["revision"]+1)
                self.store.write(connection,update(shares).where(shares.c.id==share_id).values(state=row["state"],revision=row["revision"]))
                self._journal(connection,row,event,before,result["guards"])
                if event in {"approve","reject"}:
                    file=self._one(connection,files,row["file_id"])
                    self._messages(connection,row,file,"review_result")
                    if event == "approve":
                        self._messages(connection,row,file,"shared")
            self.monitor.state(node,row,result)
            operation.record("commit",lambda:{"outputs":{"state":row["state"],"revision":row["revision"],"changed":True}})
            operation.result(lambda:{"outputs":{"state":row["state"],"revision":row["revision"],"changed":True}})
            return row

    def download(self, actor_id: str, file_id: str) -> tuple:
        with self.monitor.operation("download","return",lambda:{"inputs":{"actor_id":actor_id,"file_id":file_id}}) as operation:
            with self.store.transaction() as connection:
                file=self._one(connection,files,file_id)
                self._authorize(connection,actor_id,"download",file=file)
                content=(self.store.blobs/file_id).read_bytes()
            operation.result(lambda:{"inputs":{"actor_id":actor_id,"file_id":file_id},"outputs":{"allowed":True,"size":len(content),"file_id":file_id}})
            return file["filename"],content

    def dashboard(self, actor_id: str) -> dict:
        with self.monitor.span("received_files",lambda:{"inputs":{"actor_id":actor_id}}) as operation:
            with self.store.transaction() as connection:
                self._authorize(connection,actor_id,"upload")
                members=self.store.read(connection,select(users.c.id,users.c.name))
                owned=self.store.read(connection,select(files).where(files.c.owner_id==actor_id).order_by(files.c.created_at.desc()))
                candidates=self.store.read(connection,select(files,shares.c.id.label("share_id"),shares.c.owner_id.label("sharer_id")).join(shares,files.c.id==shares.c.file_id).where(shares.c.recipient_id==actor_id))
                received=[]
                for candidate in candidates:
                    evaluation, _ = self._evaluate(connection,actor_id,"received_files",file=candidate)
                    if evaluation["value"] is True and candidate["id"] not in {item["id"] for item in received}:
                        received.append(candidate)
                outgoing=self.store.read(connection,select(shares,files.c.filename).join(files,shares.c.file_id==files.c.id).where(shares.c.owner_id==actor_id).order_by(shares.c.created_at.desc()))
                reviews=self.store.read(connection,select(shares,files.c.filename).join(files,shares.c.file_id==files.c.id).where(and_(shares.c.reviewer_id==actor_id,shares.c.state=="pending")))
                messages=self.store.read(connection,select(notifications).where(notifications.c.user_id==actor_id).order_by(notifications.c.created_at.desc()))
            operation.result(lambda:{"outputs":{"owned_count":len(owned),"received_count":len(received),"review_count":len(reviews),"message_count":len(messages)}})
            return {"members":members,"owned":owned,"received":received,"outgoing":outgoing,"reviews":reviews,"messages":messages}

    def read_notification(self, actor_id: str, notification_id: str) -> None:
        with self.monitor.span("read_notification",lambda:{"inputs":{"actor_id":actor_id,"notification_id":notification_id}}) as operation:
            with self.store.transaction() as connection:
                message=self._one(connection,notifications,notification_id)
                if message["user_id"] != actor_id:
                    raise BusinessError("permission_denied")
                self.store.write(connection,update(notifications).where(notifications.c.id==notification_id).values(is_read=1))
            operation.result(lambda:{"outputs":{"is_read":True}})
