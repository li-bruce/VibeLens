"""Bridge real business boundaries to canonical probes, policy reports and data probes."""

from contextvars import ContextVar
from contextlib import contextmanager
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"observer_runtime"))

from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.data.runtime import BODataRuntime
from bo_observer.policy.recording import record_evaluation

_bo_scope=ContextVar("trial_monitor_scope",default=None)


class BOMonitor:
    @contextmanager
    def operation(self,node,phase,builder=lambda:{},**options):
        if phase!="return":
            raise ValueError("The operation port supports return boundaries only.")
        with self.span(node,builder,**options) as activation:
            yield activation

    def __init__(self, project, build_id, *, sink=None, endpoint="", token="", enabled=True, capacity=4096, run_id=None):
        self.probe=BOProbe(project,build_id,sink=sink,endpoint=endpoint,token=token,enabled=enabled,capacity=capacity,run_id=run_id)
        self.data=BODataRuntime(self.probe,json.loads((ROOT/"bo_stategraph/databases.json").read_text(encoding="utf-8")))
        self.evaluations=[]

    @contextmanager
    def span(self,node,builder=lambda:{},**options):
        with self.probe.span(node,builder,**options) as activation:
            mark=_bo_scope.set(activation)
            try:
                yield activation
            finally:
                _bo_scope.reset(mark)

    def record(self,node,phase,builder,**options):
        return self.probe.record(node,phase,builder,**options)

    def policy(self,declaration,evaluation,entity,attempt):
        try:
            self.evaluations.append(evaluation)
            record_evaluation(declaration,evaluation,self.probe,entity=entity,attempt=attempt)
        except Exception:
            self.probe.bo_errors+=1

    def state(self,node,row,result,initial=False):
        activation=_bo_scope.get()
        context={key:row[key] for key in ["file_id","owner_id","recipient_id","reviewer_id"]}
        event_id=self.probe.record(node,"change",lambda:{"outputs":{"state":row["state"],"revision":row["revision"]}},entity=row["id"],attempt=row["id"],scope="entity",revision=row["revision"],call_id=activation.call_id if activation else None)
        if event_id:
            self.probe.snapshot(row["id"],row["state"],context,row["revision"],event_id,event=None if initial else result["event"],guards={} if initial else result["guards"],payload={})

    def _context(self):
        activation=_bo_scope.get()
        return {"parent_call_id":activation.call_id} if activation else {}

    def execute(self,node,callback,**options):
        return self.data.execute(node,callback,**options,**self._context())

    def transaction(self,node,manager,**options):
        return self.data.transaction(node,manager,**options,**self._context())

    def transform(self,node,function,value,**options):
        return self.data.transform(node,function,value,**options,**self._context())

    def flush(self):
        return self.probe.flush(10)
