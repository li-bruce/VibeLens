"""Launch the application and canonical observer together on free loopback ports."""

from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"observer_runtime")]

from bo_observer.observation.session import GraphSession
from bo_observer.service import make_server
from werkzeug.serving import make_server as make_application_server
from app.storage import Store
from app.service import Service
from app.web import create_app
from integrations.bo_monitor import BOMonitor


def main():
    os.environ["TRIAL_DATABASE_URL"]="sqlite:///"+(ROOT/"data/application.sqlite3").as_posix()
    project=json.loads((ROOT/"bo_stategraph/project.json").read_text(encoding="utf-8"))
    session=GraphSession(ROOT)
    graph_server=make_server(session,port=0)
    graph_url="http://127.0.0.1:"+str(graph_server.server_port)+"/graph"
    def sink(body,kind):
        if kind=="events":
            session.event(body)
        else:
            session.snapshot(body)
    monitor=BOMonitor(project,session.manifest["build_id"],sink=sink)
    store=Store(ROOT/"data",monitor)
    store.initialize()
    service=Service(store,project,ROOT)
    application=create_app(service,graph_url,session.manifest["build_id"])
    application_server=make_application_server("127.0.0.1",0,application,threaded=True)
    app_url="http://127.0.0.1:"+str(application_server.server_port)+"/"
    session.program_url=app_url
    record={"server_pid":os.getpid(),"parent_pid":os.getppid(),"root":str(ROOT),"application_url":app_url,"graph_url":graph_url,"build_id":session.manifest["build_id"],"phase":"implementation"}
    (ROOT/"review/runtime-process.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record),flush=True)
    threading.Thread(target=graph_server.serve_forever,daemon=True,name="trial-graph-http").start()
    try:
        application_server.serve_forever()
    finally:
        graph_server.shutdown()
        graph_server.server_close()
        application_server.server_close()
        monitor.probe.close()
        store.engine.dispose()


if __name__=="__main__":
    main()
