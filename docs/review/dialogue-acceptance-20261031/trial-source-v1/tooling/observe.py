"""Execute real application cases and preserve independent values and public projections."""

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"observer_runtime")]

from bo_stategraph import BOStateGraph
from bo_observer.graph.behavior_model import capture
from app.storage import Store
from app.service import Service,BusinessError
from app.web import create_app
from integrations.bo_monitor import BOMonitor


def machine_from(snapshot):
    return {"configurations":[{"attempt":row["instance_id"],"phase":row["state"],"state_revision":row["revision"],"revision":row["revision"],"run_build_id":row["build_id"],"source_status":"current","context":row["context"],"journal":row["journal"]} for row in snapshot["instances"]]}


def expect_denied(callback):
    try:
        callback()
    except BusinessError as error:
        assert error.status in {400,401,403,404,409}
        return error.status
    raise AssertionError("The unauthorized operation was accepted.")


def outcome_for(case):
    if case in {"rejected","selected_reviewer_rejects","rejected_download_denied","rejected_file_hidden"}:
        return "rejected"
    if case in {"cancelled","owner_cancels_pending","cancelled_request_review_denied","cancelled_file_hidden"}:
        return "cancelled"
    if case in {"revoked","owner_revokes_share","revoked_old_url_denied","revoked_stale_page_denied","revoked_file_hidden"}:
        return "revoked"
    if case in {"pending","unauthorized","unselected_reviewer_denied","ungranted_download_denied","pending_download_denied","pending_file_hidden","nonowner_cancel_denied"}:
        return "pending"
    return "approved"


def run_case(case,mode,project,build_id,directory):
    events=[]
    snapshots=[]
    def sink(body,kind):
        if mode=="fault":
            raise OSError("deliberate observation failure")
        (events if kind=="events" else snapshots).append(body)
    monitor=BOMonitor(project,build_id,sink=sink,enabled=mode!="off",run_id=case+"-"+mode)
    store=Store(directory,monitor)
    store.initialize()
    service=Service(store,project,ROOT)
    service.login("owner","TrialOnly!2026")
    if case=="invalid_login":
        expect_denied(lambda:service.login("owner","wrong-test-password"))
    file=service.upload("owner","trial-notes.txt",b"Synthetic trial file.\n")
    share=service.request_share("owner",file["id"],"recipient","reviewer")
    if case=="upload_anonymous_denied":
        expect_denied(lambda:service.upload("","denied.txt",b"denied"))
    if case=="nonowner_share_denied":
        expect_denied(lambda:service.request_share("other",file["id"],"recipient","reviewer"))
    if case in {"unauthorized","unselected_reviewer_denied"}:
        expect_denied(lambda:service.change_share("other",share["id"],"approve"))
    if case=="nonowner_cancel_denied":
        expect_denied(lambda:service.change_share("other",share["id"],"cancel"))
    state=outcome_for(case)
    if state in {"approved","revoked"}:
        service.change_share("reviewer",share["id"],"approve")
    elif state=="rejected":
        service.change_share("reviewer",share["id"],"reject")
    elif state=="cancelled":
        service.change_share("owner",share["id"],"cancel")
        if case=="cancelled_request_review_denied":
            expect_denied(lambda:service.change_share("reviewer",share["id"],"approve"))
    if case=="nonowner_revoke_denied":
        expect_denied(lambda:service.change_share("other",share["id"],"revoke"))
    if state=="revoked":
        assert service.download("recipient",file["id"])[1]==b"Synthetic trial file.\n"
        service.change_share("owner",share["id"],"revoke")
    if state=="approved":
        filename,body=service.download("recipient",file["id"])
        assert filename=="trial-notes.txt" and body==b"Synthetic trial file.\n"
        allowed=True
    else:
        assert expect_denied(lambda:service.download("recipient",file["id"]))==403
        allowed=False
    dashboard=service.dashboard("recipient")
    if state=="approved":
        message=dashboard["messages"][0]
        service.read_notification("recipient",message["id"])
    assert bool(dashboard["received"])==(state=="approved")
    application=create_app(service)
    client=application.test_client()
    client.get("/")
    with client.session_transaction() as session:
        csrf=session["csrf"]
    client.post("/",data={"action":"login","username":"recipient","password":"TrialOnly!2026","csrf":csrf})
    assert client.get("/").status_code==200
    response=client.get("/download/"+file["id"])
    assert response.status_code==(200 if state=="approved" else 403)
    with client.session_transaction() as session:
        csrf=session["csrf"]
    client.post("/",data={"action":"logout","csrf":csrf})
    service.logout("owner")
    monitor.flush()
    authority=store.snapshot(build_id)
    row=authority["instances"][0]
    messages=authority["messages"]
    observations={"state":row["state"],"download_allowed":allowed,"recipient_visible":bool(dashboard["received"]),"review_results":sum(item["kind"]=="review_result" for item in messages),"share_messages":sum(item["kind"]=="shared" for item in messages),"file_size":len(b"Synthetic trial file.\n"),"recipient_id":"recipient"}
    machine=machine_from(authority)
    graph=BOStateGraph(project["model"],build_id=build_id,mode="drive")
    projection={"build_id":build_id,"machine":machine,"instances":graph.bo_instances(machine)}
    run={"case":case,"mode":mode,"events":events,"snapshots":snapshots,"observations":observations,"authority_snapshot":authority,"projection":projection,"policy_evaluations":monitor.evaluations,"mapping_checks":[{"id":"state-"+case,"source":"Independent SQLite Store.snapshot","projection":["state"],"actual":row["state"],"mapped":projection["instances"][0]["observed"]["state"]}],"probe_health":{"errors":monitor.probe.bo_errors,"dropped":monitor.probe.bo_dropped,"data_errors":monitor.data.bo_errors},"loaded_definition":service.machine}
    monitor.probe.close()
    store.engine.dispose()
    return run


def main():
    os.environ["TRIAL_DATABASE_URL"]="sqlite:///"+(ROOT/"data/application.sqlite3").as_posix()
    project=json.loads((ROOT/"bo_stategraph/project.json").read_text(encoding="utf-8"))
    manifest=capture(ROOT,project["model"])
    contract=json.loads((ROOT/"mapping.json").read_text(encoding="utf-8"))
    output={"build_id":manifest["build_id"],"machine":project["model"]["machine"],"runs":[]}
    for case in contract["cases"]:
        for mode in contract["modes"]:
            with tempfile.TemporaryDirectory(prefix="case-",dir=ROOT/"review") as directory:
                run=run_case(case,mode,project,manifest["build_id"],directory)
                output["runs"].append(run)
    selected=next(run for run in output["runs"] if run["case"]=="approved" and run["mode"]=="on")
    graph=BOStateGraph(project["model"],build_id=manifest["build_id"],mode="drive")
    output["stategraph_export"]=graph.bo_export(runtime={"machine":selected["projection"]["machine"]})
    target=ROOT/"review/runtime-observations.json"
    target.write_text(json.dumps(output,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(output,ensure_ascii=False))


if __name__=="__main__":
    main()
