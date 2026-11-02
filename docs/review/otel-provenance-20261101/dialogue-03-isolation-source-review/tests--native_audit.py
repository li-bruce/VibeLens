"""Independent native boundary readers for per-invocation context comparisons."""
import copy
import threading
from collections import defaultdict
from contextvars import ContextVar
from functools import wraps
from contextlib import contextmanager
from opentelemetry import trace
from flask import has_request_context,session

class NativeReader:
    def __init__(self, store):
        self.store=store
    def read(self, sql, parameters=()):
        return self.store.read(sql,parameters,observe=False)
    def snapshot(self, build_id, revision):
        return self.store.snapshot(build_id,revision)

class NativeAudit:
    def __init__(self, service, build_id, revision):
        self.service,self.store=service,NativeReader(service.store)
        self.build_id,self.revision=build_id,revision
        self.active=ContextVar("trial_native_boundary",default=None)
        self.records=[]
        self.counts=defaultdict(int)
        self.lock=threading.Lock()
        self.native_calls={}
        self.install_store_reader(service.store)
        methods={"sign_in":"sign_in","sign_out":"sign_out","users":"list_colleagues",
            "upload_file":"upload_file","list_files":"list_files","view_file":"view_file","download_file":"download_file",
            "review_file":"review_file","share_file":"share_file","list_messages":"message_list",
            "read_message":"read_message","list_reviews":"list_reviews","deliver_notification":None}
        self.methods=methods
        for name,node in methods.items():
            self.wrap(name,node)
    def attach_service(self, service):
        original=self.service
        self.service=service
        try:
            for name,node in self.methods.items():
                self.wrap(name,node)
        finally:
            self.service=original
    def sdk(self):
        context=trace.get_current_span().get_span_context()
        return {"trace_id":format(context.trace_id,"032x"),"span_id":format(context.span_id,"016x")} if context.is_valid else None
    def add(self, node, phase, identity, metadata, **extra):
        if identity is None:
            return
        value={**identity,"provenance":copy.deepcopy(metadata),**extra}
        with self.lock:
            self.native_calls.setdefault(node,{}).setdefault(phase,[]).append(value)
    def install_store_reader(self, store):
        original_connect=store.connect
        @wraps(original_connect)
        def connect(observe=True):
            connection=original_connect(observe=observe)
            if observe:
                connection.raw=NativeRawConnection(connection.raw,self)
            return connection
        store.connect=connect
        original_transaction=store._transaction
        @contextmanager
        def transaction():
            identity=self.sdk()
            active=self.active.get()
            metadata=copy.deepcopy(active["entry"]) if active and active.get("_inside_span") else None
            if metadata is not None:
                self.add("db_transaction","enter",identity,metadata)
            try:
                with original_transaction() as connection:
                    yield connection
            except BaseException:
                if metadata is not None:
                    self.add("db_transaction","error",identity,metadata)
                raise
            else:
                if metadata is not None:
                    self.add("db_transaction","commit",identity,metadata)
                if active is not None:
                    active["native_commits"]=active.get("native_commits",0)+1
        store._transaction=transaction
    def record_state(self):
        active=self.active.get()
        if active is not None:
            self.add(active["node"],"change",self.sdk(),active["entry"])
    def record_policy(self, evaluation):
        active=self.active.get()
        if active is not None:
            identity=self.sdk()
            for step in evaluation["trace"]:
                self.add("policy:"+step["node"],"decision",identity,active["entry"],check_id=evaluation["check_id"])
    def native_context(self, name, args, returned=None, complete=False):
        if name=="sign_in":
            rows=self.store.read("SELECT id FROM users WHERE id=?",(session.get("user_id"),)) if has_request_context() and not complete else []
            principal=rows[0] if rows else None
            return {"actor":({"id":returned["id"],"kind":"user"} if complete else {"id":principal["id"],"kind":"user"} if principal else None)}
        if name=="deliver_notification":
            job=self.store.read("SELECT * FROM jobs WHERE id=?",(args[0],))[0]
            file=self.store.read("SELECT * FROM files WHERE id=?",(job["file_id"],))[0]
            objects=[{"type":"Job","id":job["id"],"role":"input"},{"type":"File","id":file["id"],"role":"input"},{"type":"User","id":job["recipient_id"],"role":"recipient"}]
            if complete and returned:
                messages=self.store.read("SELECT id FROM messages WHERE job_id=?",(job["id"],))
                objects.append({"type":"Message","id":messages[0]["id"],"role":"output"})
            return {"actor":{"id":"notification-worker","kind":"service"},"workflow_id":job["workflow_id"],"objects":objects}
        actor=args[0]
        value={"actor":None if actor is None else {"id":actor["id"],"kind":"user"}}
        file=None
        if name in {"view_file","download_file","review_file","share_file"}:
            file=self.store.read("SELECT * FROM files WHERE id=?",(args[1],))[0]
        if name=="upload_file" and complete:
            file=self.store.read("SELECT * FROM files WHERE id=?",(returned["id"],))[0]
        if file:
            value.update(workflow_id=file["workflow_id"],objects=[{"type":"File","id":file["id"],"role":"input"}])
        if name=="upload_file" and complete:
            value["objects"].append({"type":"File","id":file["id"],"role":"output"})
        if name=="review_file" and complete:
            job=self.store.read("SELECT id FROM jobs WHERE file_id=? AND kind='review'",(file["id"],))[0]
            value["objects"].append({"type":"Job","id":job["id"],"role":"output"})
        if name=="share_file":
            if complete:
                share=self.store.read("SELECT * FROM shares WHERE id=?",(returned["id"],))[0]
                job=self.store.read("SELECT id FROM jobs WHERE share_id=?",(share["id"],))[0]
                value["objects"].extend([{"type":"Share","id":share["id"],"role":"output"},{"type":"Job","id":job["id"],"role":"output"}])
            value["objects"].append({"type":"User","id":args[2],"role":"recipient"})
        return value
    def wrap(self, name, node):
        original=getattr(self.service,name)
        @wraps(original)
        def invoke(*args,**kwargs):
            selected=node
            if name=="deliver_notification":
                jobs=self.store.read("SELECT kind FROM jobs WHERE id=?",(args[0],))
                selected="deliver_review_notice" if jobs and jobs[0]["kind"]=="review" else "deliver_share_notice"
            with self.lock:
                self.counts[selected]+=1
                record={"node":selected,"ordinal":self.counts[selected]}
            record["entry"]=self.native_context(name,args)
            token=self.active.set(record)
            try:
                result=original(*args,**kwargs)
                if type(result) is bool:
                    record["native_returned"]=result
                record["completion"]=self.native_context(name,args,result,True)
                if record.get("span_id"):
                    identity={key:record[key] for key in ("trace_id","span_id")}
                    self.add(selected,"return",identity,record["completion"])
                    if record.get("native_commits",0) and (name=="upload_file" or name=="deliver_notification" and result is True):
                        self.add(selected,"commit",identity,record["completion"])
                return result
            except BaseException as error:
                record["completion"]=copy.deepcopy(record["entry"])
                record["exception_type"]=type(error).__name__
                if record.get("span_id"):
                    self.add(selected,"error",{key:record[key] for key in ("trace_id","span_id")},record["entry"])
                raise
            finally:
                record["snapshot"]=self.store.snapshot(self.build_id,self.revision)
                with self.lock:
                    self.records.append(record)
                self.active.reset(token)
        setattr(self.service,name,invoke)
        if name=="upload_file":
            self.wrap_metadata(self.service)
    def wrap_metadata(self, service):
        if getattr(service,"_native_metadata_wrapped",False):
            return
        original=service._metadata
        @wraps(original)
        def transform(value):
            identity=self.sdk(); active=self.active.get()
            metadata=copy.deepcopy(active["entry"]) if active and active.get("_inside_span") else None
            if metadata is not None:
                self.add("db_metadata","enter",identity,metadata)
            try:
                result=original(value)
            except BaseException:
                if metadata is not None:
                    self.add("db_metadata","error",identity,metadata)
                raise
            if metadata is not None:
                self.add("db_metadata","change",identity,metadata)
            return result
        service._metadata=transform
        service._native_metadata_wrapped=True


class NativeRawConnection:
    def __init__(self, raw, audit):
        self.raw,self.audit=raw,audit
    def __getattr__(self, name):
        return getattr(self.raw,name)
    def execute(self, sql, parameters=()):
        verb=sql.lstrip().split(None,1)[0].upper()
        if verb not in {"SELECT","INSERT","UPDATE","DELETE"}:
            return self.raw.execute(sql,parameters)
        active=self.audit.active.get()
        inside=bool(active and active.get("_inside_span"))
        node=("db_read" if inside else "db_context_read") if verb=="SELECT" else "db_write"
        identity=self.audit.sdk()
        metadata=copy.deepcopy(active["entry"]) if inside else None
        if metadata is not None:
            self.audit.add(node,"enter",identity,metadata)
        try:
            result=self.raw.execute(sql,parameters)
        except BaseException:
            if metadata is not None:
                self.audit.add(node,"error",identity,metadata)
            raise
        if metadata is not None:
            self.audit.add(node,"return",identity,metadata)
        return result
