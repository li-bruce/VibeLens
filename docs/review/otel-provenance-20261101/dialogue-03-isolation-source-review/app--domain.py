"""File review and recipient access activate only with committed notifications."""
import time
import uuid
from pathlib import PurePath
from werkzeug.security import check_password_hash
from app.ports import ObservationPort

class DomainError(Exception):
    def __init__(self, code, status=403):
        super().__init__(code)
        self.code,self.status=code,status

class TeamFiles:
    def __init__(self, store, workflow, bo=None, delay=5.0):
        self.store,self.workflow=store,workflow
        self.bo,self.delay=bo or ObservationPort(),delay
    def principal(self, user_id):
        rows=self.store.read("SELECT id,username,display_name,role FROM users WHERE id=?",(user_id,)) if user_id else []
        return rows[0] if rows else None
    def require_user(self, actor):
        if actor is None:
            raise DomainError("authentication_required",401)
        return actor
    def sign_in(self, username, password):
        with self.bo.span("sign_in",lambda:{"inputs":{"username":username,"credential_supplied":bool(password)}},provenance={"actor":None}) as call:
            rows=self.store.read("SELECT * FROM users WHERE username=?",(username,))
            if not rows or not check_password_hash(rows[0]["password_hash"],password):
                raise DomainError("invalid_credentials",401)
            user=self.principal(rows[0]["id"])
            call.result(lambda:{"outputs":{"user_id":user["id"],"authenticated":True},"provenance":{"actor":{"id":user["id"],"kind":"user"}}})
            return user
    def sign_out(self, actor):
        with self.bo.span("sign_out",provenance=self.bo.bo_provenance(actor)) as call:
            call.result(lambda:{"outputs":{"signed_out":True}})
            return {"signed_out":True}
    def users(self, actor):
        self.require_user(actor)
        with self.bo.span("list_colleagues",provenance=self.bo.bo_provenance(actor)) as call:
            rows=self.store.read("SELECT id,username,display_name,role FROM users WHERE id<>? ORDER BY id",(actor["id"],))
            call.result(lambda:{"outputs":{"count":len(rows)}})
            return rows
    def get_file(self, file_id, connection=None):
        rows=[dict(row) for row in connection.execute("SELECT * FROM files WHERE id=?",(file_id,))] if connection else self.store.read("SELECT * FROM files WHERE id=?",(file_id,))
        if not rows:
            raise DomainError("file_not_found",404)
        return rows[0]
    def allowed(self, operation, actor, file=None, connection=None):
        active=False
        if actor and file:
            sql="SELECT 1 FROM shares WHERE file_id=? AND recipient_id=? AND state='active_share'"
            args=(file["id"],actor["id"])
            active=bool(connection.execute(sql,args).fetchone()) if connection else bool(self.store.read(sql,args))
        inputs={"authenticated":actor is not None,"actor_is_admin":actor is not None and actor["role"]=="admin",
            "actor_is_uploader":actor is not None and file is not None and file["owner_id"]==actor["id"],
            "file_approved":file is not None and file["state"]=="approved","active_recipient":active}
        return self.workflow.permission(operation,inputs,bo=self.bo)
    def check(self, operation, actor, file=None, connection=None):
        self.require_user(actor)
        if not self.allowed(operation,actor,file,connection):
            raise DomainError(operation+"_not_allowed")
    def metadata(self, file):
        return self.bo.transform("db_metadata",self._metadata,file,before=lambda value:{"size":value["size"],"state":value["state"]},after=lambda value:{"size":value["size"],"state":value["state"]})
    def _metadata(self, file):
        return {key:file[key] for key in ("id","owner_id","filename","size","state","review_decision","rejection_reason","reviewer_id","workflow_id","revision","created_at")}
    def upload_file(self, actor, filename, content):
        self.require_user(actor)
        filename=PurePath(filename.replace("\\","/")).name.strip()
        if not filename or len(filename)>200 or len(content)>10*1024*1024:
            raise DomainError("invalid_file",400)
        with self.bo.span("upload_file",lambda:{"inputs":{"filename":filename,"size":len(content)}},provenance=self.bo.bo_provenance(actor)) as call:
            self.check("upload",actor)
            identity="file-"+uuid.uuid4().hex
            with self.store.transaction() as connection:
                connection.execute("INSERT INTO files(id,owner_id,filename,size,content,state,workflow_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (identity,actor["id"],filename,len(content),content,"pending_review","workflow-"+uuid.uuid4().hex,time.time()))
            file=self.get_file(identity)
            result=lambda:{"outputs":{"file_id":identity,"state":file["state"]},"provenance":self.bo.bo_provenance(actor,file,[{"type":"File","id":identity,"role":"output"}])}
            call.record("commit",result)
            call.result(result)
            self.bo.state(file)
            return self.metadata(file)
    def list_files(self, actor):
        self.require_user(actor)
        with self.bo.span("list_files",provenance=self.bo.bo_provenance(actor)) as call:
            visible=[]
            for file in self.store.read("SELECT * FROM files ORDER BY created_at DESC"):
                if self.allowed("view",actor,file):
                    item=self.metadata(file)
                    item["shares"]=[s for s in self.store.read("SELECT id,recipient_id,state FROM shares WHERE file_id=?",(file["id"],)) if actor["id"]==file["owner_id"] or actor["role"]=="admin" or s["recipient_id"]==actor["id"]]
                    item["can_share"]=actor["id"]==file["owner_id"] and file["state"]=="approved"
                    item["can_review"]=actor["role"]=="admin" and actor["id"]!=file["owner_id"] and file["state"]=="pending_review"
                    visible.append(item)
            call.result(lambda:{"outputs":{"count":len(visible)}})
            return visible
    def view_file(self, actor, file_id):
        self.require_user(actor)
        file=self.get_file(file_id)
        with self.bo.span("view_file",lambda:{"inputs":{"file_id":file_id}},provenance=self.bo.bo_provenance(actor,file)) as call:
            self.check("view",actor,file)
            call.result(lambda:{"outputs":{"file_id":file_id,"state":file["state"],"size":file["size"]}})
            return self.metadata(file)
    def download_file(self, actor, file_id):
        self.require_user(actor)
        file=self.get_file(file_id)
        with self.bo.span("download_file",lambda:{"inputs":{"file_id":file_id}},provenance=self.bo.bo_provenance(actor,file)) as call:
            self.check("download",actor,file)
            call.result(lambda:{"outputs":{"file_id":file_id,"size":file["size"]}})
            return file["filename"],file["content"]
    def enqueue(self, connection, kind, file, share_id, recipient_id):
        job_id="job-"+uuid.uuid4().hex
        connection.execute("INSERT INTO jobs(id,kind,file_id,share_id,recipient_id,workflow_id,available_at,bo_carrier) VALUES(?,?,?,?,?,?,?,?)",
            (job_id,kind,file["id"],share_id,recipient_id,file["workflow_id"],time.time()+self.delay,self.bo.bo_queue_metadata()))
        return job_id
    def review_file(self, actor, file_id, decision, reason):
        self.require_user(actor)
        file=self.get_file(file_id)
        with self.bo.span("review_file",lambda:{"inputs":{"file_id":file_id,"decision":decision,"reason":reason}},provenance=self.bo.bo_provenance(actor,file)) as call:
            if decision not in ("approved","rejected") or (decision=="rejected" and not reason.strip()) or len(reason)>1000:
                raise DomainError("invalid_review",400)
            with self.store.transaction() as connection:
                file=self.get_file(file_id,connection)
                self.check("review",actor,file,connection)
                if file["state"]!="pending_review":
                    raise DomainError("review_already_decided",409)
                state=self.workflow.transition(connection,file_id,file["state"],"review",file["revision"]+1,time.time())
                connection.execute("UPDATE files SET state=?,review_decision=?,rejection_reason=?,reviewer_id=?,revision=revision+1 WHERE id=?",
                    (state,decision,reason.strip() if decision=="rejected" else "",actor["id"],file_id))
                job_id=self.enqueue(connection,"review",file,None,file["owner_id"])
            file=self.get_file(file_id)
            call.result(lambda:{"outputs":{"file_id":file_id,"job_id":job_id,"state":file["state"],"decision":decision},
                "provenance":self.bo.bo_provenance(actor,file,[{"type":"Job","id":job_id,"role":"output"}])})
            self.bo.state(file)
            return self.metadata(file)
    def share_file(self, actor, file_id, recipient_id):
        self.require_user(actor)
        file=self.get_file(file_id)
        with self.bo.span("share_file",lambda:{"inputs":{"file_id":file_id,"recipient_id":recipient_id}},provenance=self.bo.bo_provenance(actor,file,[{"type":"User","id":recipient_id,"role":"recipient"}])) as call:
            if recipient_id==actor["id"] or self.principal(recipient_id) is None:
                raise DomainError("invalid_recipient",400)
            with self.store.transaction() as connection:
                file=self.get_file(file_id,connection)
                self.check("share",actor,file,connection)
                if connection.execute("SELECT 1 FROM shares WHERE file_id=? AND recipient_id=?",(file_id,recipient_id)).fetchone():
                    raise DomainError("share_already_exists",409)
                share_id="share-"+uuid.uuid4().hex
                state=self.workflow.transition(connection,share_id,"approved","share",1,time.time())
                connection.execute("INSERT INTO shares(id,file_id,recipient_id,sender_id,state,created_at) VALUES(?,?,?,?,?,?)",
                    (share_id,file_id,recipient_id,actor["id"],state,time.time()))
                job_id=self.enqueue(connection,"share",file,share_id,recipient_id)
            call.result(lambda:{"outputs":{"file_id":file_id,"share_id":share_id,"job_id":job_id,"state":state},
                "provenance":self.bo.bo_provenance(actor,file,[{"type":"Share","id":share_id,"role":"output"},{"type":"Job","id":job_id,"role":"output"},{"type":"User","id":recipient_id,"role":"recipient"}])})
            self.bo.state({"id":share_id,"state":state,"revision":1})
            return {"id":share_id,"state":state,"recipient_id":recipient_id}
    def list_messages(self, actor):
        self.require_user(actor)
        with self.bo.span("message_list",provenance=self.bo.bo_provenance(actor)) as call:
            rows=self.store.read("SELECT id,file_id,kind,text,created_at FROM messages WHERE recipient_id=? ORDER BY created_at DESC",(actor["id"],))
            call.result(lambda:{"outputs":{"count":len(rows)}})
            return rows
    def read_message(self, actor, message_id):
        self.require_user(actor)
        with self.bo.span("read_message",lambda:{"inputs":{"message_id":message_id}},provenance=self.bo.bo_provenance(actor)) as call:
            rows=self.store.read("SELECT id,file_id,kind,text,created_at FROM messages WHERE id=? AND recipient_id=?",(message_id,actor["id"]))
            if not rows:
                raise DomainError("message_not_found",404)
            call.result(lambda:{"outputs":{"message_id":message_id}})
            return rows[0]
    def list_reviews(self, actor):
        self.require_user(actor)
        with self.bo.span("list_reviews",provenance=self.bo.bo_provenance(actor)) as call:
            if actor["role"]!="admin":
                raise DomainError("administrator_required")
            rows=[self.metadata(file) for file in self.store.read("SELECT * FROM files WHERE state='pending_review' AND owner_id<>? ORDER BY created_at",(actor["id"],))]
            call.result(lambda:{"outputs":{"count":len(rows)}})
            return rows
    def deliver_notification(self, job_id, fail_after_message=False):
        jobs=self.store.read("SELECT * FROM jobs WHERE id=?",(job_id,))
        if not jobs or jobs[0]["state"]=="delivered":
            return False
        job=jobs[0]
        with self.bo.bo_receive_metadata(job["bo_carrier"]):
            node="deliver_review_notice" if job["kind"]=="review" else "deliver_share_notice"
            provenance=self.bo.bo_worker_provenance(job)
            with self.bo.span(node,lambda:{"inputs":{"job_id":job_id,"file_id":job["file_id"],"fail_after_message":fail_after_message}},provenance=provenance) as call:
                file=self.get_file(job["file_id"])
                try:
                    with self.store.transaction() as connection:
                        current=connection.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
                        if current["state"]=="delivered":
                            call.result(lambda:{"outputs":{"delivered":False,"state":"already_delivered","job_id":job_id}})
                            return False
                        message_id="message-"+uuid.uuid4().hex
                        file=self.get_file(file["id"],connection)
                        text=("Review "+file["review_decision"]+": "+file["filename"]+(" — "+file["rejection_reason"] if file["rejection_reason"] else "")) if job["kind"]=="review" else "A file was shared with you: "+file["filename"]
                        connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)",(message_id,job["recipient_id"],job_id,file["id"],job["kind"],text,time.time()))
                        if fail_after_message:
                            raise RuntimeError("injected_delivery_failure")
                        if job["kind"]=="review":
                            entity_id=file["id"]
                            state=self.workflow.transition(connection,entity_id,file["state"],file["review_decision"],file["revision"]+1,time.time())
                            connection.execute("UPDATE files SET state=?,revision=revision+1 WHERE id=?",(state,entity_id))
                        else:
                            share=dict(connection.execute("SELECT * FROM shares WHERE id=?",(job["share_id"],)).fetchone())
                            entity_id=share["id"]
                            state=self.workflow.transition(connection,entity_id,share["state"],"deliver",share["revision"]+1,time.time())
                            connection.execute("UPDATE shares SET state=?,revision=revision+1 WHERE id=?",(state,entity_id))
                        connection.execute("UPDATE jobs SET state='delivered',delivered_at=?,attempts=attempts+1,last_error='' WHERE id=?",(time.time(),job_id))
                    result={"delivered":True,"state":state,"job_id":job_id,"message_id":message_id,"file_id":file["id"]}
                    completed={**provenance,"objects":provenance["objects"]+[{"type":"Message","id":message_id,"role":"output"}]}
                    call.record("commit",lambda:{"outputs":result,"provenance":completed})
                    call.result(lambda:{"outputs":result,"provenance":completed})
                    table="files" if job["kind"]=="review" else "shares"
                    self.bo.state({"id":entity_id,"state":state,"revision":self.store.read("SELECT revision FROM "+table+" WHERE id=?",(entity_id,))[0]["revision"]})
                    return True
                except Exception as error:
                    with self.store.transaction() as connection:
                        connection.execute("UPDATE jobs SET attempts=attempts+1,last_error=?,available_at=? WHERE id=? AND state='waiting'",(type(error).__name__,time.time()+self.delay,job_id))
                    raise
    def deliver_due(self):
        count=0
        for job in self.store.read("SELECT id FROM jobs WHERE state='waiting' AND available_at<=? ORDER BY available_at LIMIT 20",(time.time(),),observe=False):
            try:
                count+=int(self.deliver_notification(job["id"]))
            except Exception:
                continue
        return count
