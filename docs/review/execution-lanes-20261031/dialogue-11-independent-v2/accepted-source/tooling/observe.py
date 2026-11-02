"""Exercise real HTTP handlers and read effects independently from SQLite."""
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "observer_runtime"))
from app.web import create_app
from app.storage import TEST_PASSWORD
from bo_stategraph import BOStateGraph
from bo_stategraph.workflow import machine_snapshot
from integrations.bo_integration import BOIntegration
from behavior_model import capture

REVIEW = ROOT / "review/withdrawal-20261101-01"

CONTENT = b"Independent team file review fixture.\n"

def csrf(client):
    client.get("/")
    with client.session_transaction() as current:
        return current["csrf_token"]

def post(client, path, data):
    return client.post(path, data={**data, "csrf_token": csrf(client)}, headers={"Accept":"application/json"})

def login(client, actor):
    response = post(client, "/login", {"username":actor,"password":TEST_PASSWORD})
    assert response.status_code == 302, ("login", actor, response.status_code)
    assert client.get("/").status_code == 200

def upload(client, reviewer="ben"):
    return post(client, "/upload", {"reviewer_id":reviewer,"file":(io.BytesIO(CONTENT),"review-notes.txt")})

def independent_rows(path, build):
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(
            "SELECT id,state,revision,uploader_id,reviewer_id,recipient_id,size,journal FROM files ORDER BY id")]
    for row in rows:
        row["recipient_id"] = row["recipient_id"] or ""
        row["journal"] = json.loads(row["journal"])
        row["build_id"] = build
    return rows

def transition_witnesses(rows, events):
    entries = {event["call_id"]:event for event in events if event["node"]=="state_transition" and event["phase"]=="enter"}
    witnessed = {(entries[event["call_id"]]["inputs"]["event"],entries[event["call_id"]]["inputs"]["before"],event["outputs"]["after"])
        for event in events if event["node"]=="state_transition" and event["phase"]=="return" and event["call_id"] in entries}
    missing = [step for row in rows for step in row["journal"]
        if (step["event"],step["before"],step["after"]) not in witnessed]
    if missing:
        raise AssertionError("missing native transition witness: " + json.dumps(missing))
    return len(witnessed)

def scenario(name, mode="off", with_observer=True):
    if name == "withdrawal":
        return withdrawal_scenario(mode, with_observer)
    integration = BOIntegration(ROOT, mode) if with_observer else None
    project = json.loads((ROOT / "bo_stategraph/project.json").read_text(encoding="utf-8-sig"))
    build = integration.session.manifest["build_id"] if integration else capture(ROOT,project["model"])["build_id"]
    scratch = REVIEW / ".tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    directory = tempfile.TemporaryDirectory(prefix="business-" + name + "-", dir=scratch)
    database = Path(directory.name) / "trial.sqlite3"
    app = create_app(ROOT,database=database,bo_probe=integration.probe if integration else None,
        bo_observer=integration,bo_data=integration.data if integration else None)
    clients = {actor:app.test_client() for actor in ("alice","ben","cara","dan")}
    a,b,c,d = [clients[actor] for actor in ("alice","ben","cara","dan")]
    results = {}
    try:
        if name == "session":
            assert a.get("/files/no-file/download").status_code == 401
            assert post(a,"/login",{"username":"alice","password":"incorrect"}).status_code == 401
            assert a.post("/upload",data={}).status_code == 400
            login(a,"alice")
            assert post(a,"/logout",{}).status_code == 302
            assert a.get("/files/no-file").status_code == 401
        else:
            for actor,client in clients.items():
                login(client,actor)
            if name == "denied":
                assert upload(a,"alice").status_code == 403
                assert upload(a,"missing-user").status_code == 403
            response = upload(a)
            assert response.status_code == 201, response.get_data(as_text=True)
            file_id = response.json["id"]
            path = "/files/" + file_id
            assert a.get(path).status_code == 200
            assert b.get(path+"/download").data == CONTENT
            assert c.get(path).status_code == 403
            assert d.get(path+"/download").status_code == 403
            assert post(a,path+"/share",{"recipient_id":"cara"}).status_code == 403
            assert post(a,path+"/review",{"decision":"approve"}).status_code == 403
            if name == "rejected":
                assert post(b,path+"/review",{"decision":"reject"}).status_code == 200
                assert post(b,path+"/review",{"decision":"approve"}).status_code == 409
                assert post(a,path+"/share",{"recipient_id":"cara"}).status_code == 403
                assert a.get(path+"/download").data == CONTENT
                assert b.get(path).status_code == 200
                assert c.get(path).status_code == 403
            else:
                assert post(b,path+"/review",{"decision":"approve"}).status_code == 200
                assert c.get(path).status_code == 403
                assert post(b,path+"/share",{"recipient_id":"cara"}).status_code == 403
                assert post(a,path+"/share",{"recipient_id":"cara"}).status_code == 200
                assert c.get(path+"/download").data == CONTENT
                assert post(c,path+"/share",{"recipient_id":"dan"}).status_code == 403
                assert post(a,path+"/share",{"recipient_id":"dan"}).status_code == 409
                assert post(b,path+"/review",{"decision":"reject"}).status_code == 409
                assert d.get(path).status_code == 403
                assert file_id not in d.get("/").get_data(as_text=True)
                assert post(c,"/logout",{}).status_code == 302
                assert c.get(path+"/download").status_code == 401
                results["download_size"] = len(CONTENT)
        rows = independent_rows(database,build)
        expected = "rejected" if name == "rejected" else "approved"
        if name != "session":
            assert len(rows)==1 and rows[0]["state"]==expected
            assert rows[0]["reviewer_id"]=="ben" and rows[0]["uploader_id"]=="alice"
            assert rows[0]["recipient_id"]==("" if name=="rejected" else "cara")
            assert rows[0]["revision"]==(2 if name=="rejected" else 3)
            assert len(rows[0]["journal"])==rows[0]["revision"]
        events = []
        if integration:
            assert integration.probe.flush(30), "probe flush timed out"
            events = [event for event in integration.session.current_events() if event["run_id"]==integration.probe.bo_run]
            if mode=="on":
                results["transition_witnesses"] = transition_witnesses(rows,events)
        graph = BOStateGraph(project["model"],build_id=build,mode="drive")
        graph.bo_require_definition(app.extensions["trial_service"].workflow.machine)
        machine = machine_snapshot(rows,build)
        projection = {"build_id":build,"machine":machine,"instances":graph.bo_instances(machine)}
        mapped = {item["observed"]["instance_id"]:item["observed"] for item in projection["instances"]}
        checks = [{"id":name+":"+mode+":"+row["id"],"source":"Independent sqlite3 SELECT files.state",
            "projection":"instances.observed.state","actual":row["state"],"mapped":mapped[row["id"]]["state"]} for row in rows]
        if name=="session":
            checks.append({"id":name+":"+mode+":empty","source":"Independent sqlite3 file count",
                "projection":"instances count","actual":len(rows),"mapped":len(mapped)})
        run = {"case":name,"mode":mode,"events":events,"observations":{"business_ok":True,**results},
            "authority_snapshot":{"files":rows},"projection":projection,"mapping_checks":checks,
            "policy_evaluations":list(integration.evaluations) if integration else [],
            "probe_health":integration.health() if integration else {"errors":0,"dropped":0,"data_errors":0}}
        exported = graph.bo_export(runtime={"machine":machine,"events":events})
        return run,exported
    finally:
        app.extensions["trial_store"].engine.dispose()
        if integration:
            integration.close()
        directory.cleanup()

def withdrawal_scenario(mode="off", with_observer=True):
    integration = BOIntegration(ROOT, mode) if with_observer else None
    project = json.loads((ROOT / "bo_stategraph/project.json").read_text(encoding="utf-8-sig"))
    build = integration.session.manifest["build_id"] if integration else capture(ROOT,project["model"])["build_id"]
    scratch = REVIEW / ".tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    directory = tempfile.TemporaryDirectory(prefix="withdrawal-", dir=scratch)
    database = Path(directory.name) / "trial.sqlite3"
    app = create_app(ROOT,database=database,bo_probe=integration.probe if integration else None,
        bo_observer=integration,bo_data=integration.data if integration else None)
    clients = {actor:app.test_client() for actor in ("alice","ben","cara","dan")}
    a,b,c,d = [clients[actor] for actor in clients]
    try:
        anonymous = app.test_client()
        assert post(anonymous,"/files/missing/withdraw",{}).status_code == 401
        for actor,client in clients.items():login(client,actor)
        fid = upload(a).json["id"]
        path = "/files/" + fid
        assert fid in b.get("/").get_data(as_text=True)
        assert a.post(path+"/withdraw",data={}).status_code == 400
        for client in (b,c,d):assert post(client,path+"/withdraw",{}).status_code == 403
        assert post(a,"/files/missing/withdraw",{}).status_code == 404
        result = post(a,path+"/withdraw",{})
        assert result.status_code == 200 and result.json["state"] == "withdrawn" and result.json["revision"] == 2
        assert post(a,path+"/withdraw",{}).status_code == 403
        assert post(b,path+"/review",{"decision":"approve"}).status_code == 409
        assert post(a,path+"/share",{"recipient_id":"cara"}).status_code == 403
        assert fid not in b.get("/").get_data(as_text=True)
        assert fid in a.get("/").get_data(as_text=True)
        for client in (b,c,d):
            assert client.get(path).status_code == 403
            assert client.get(path+"/download").status_code == 403
        assert a.get(path).json["state"] == "withdrawn"
        assert a.get(path+"/download").data == CONTENT
        approved = upload(a).json["id"]
        assert post(b,"/files/"+approved+"/review",{"decision":"approve"}).status_code == 200
        assert post(a,"/files/"+approved+"/withdraw",{}).status_code == 403
        rejected = upload(a).json["id"]
        assert post(b,"/files/"+rejected+"/review",{"decision":"reject"}).status_code == 200
        assert post(a,"/files/"+rejected+"/withdraw",{}).status_code == 403
        with sqlite3.connect(database) as connection:
            actual = connection.execute("SELECT state,revision,content FROM files WHERE id=?",(fid,)).fetchone()
        connection.close()
        assert actual == ("withdrawn",2,CONTENT)
        rows = independent_rows(database,build)
        expected = {fid:"withdrawn",approved:"approved",rejected:"rejected"}
        assert len(rows)==3 and all(row["state"]==expected[row["id"]] and row["revision"]==2 for row in rows)
        events = []
        if integration:
            assert integration.probe.flush(30)
            events = [event for event in integration.session.current_events() if event["run_id"]==integration.probe.bo_run]
            if mode=="on":transition_witnesses(rows,events)
        graph = BOStateGraph(project["model"],build_id=build,mode="drive")
        graph.bo_require_definition(app.extensions["trial_service"].workflow.machine)
        machine = machine_snapshot(rows,build)
        projection = {"build_id":build,"machine":machine,"instances":graph.bo_instances(machine)}
        mapped = {item["observed"]["instance_id"]:item["observed"] for item in projection["instances"]}
        checks = [{"id":"withdrawal:"+mode+":"+row["id"],"source":"Independent sqlite3 SELECT files.state",
            "projection":"instances.observed.state","actual":row["state"],"mapped":mapped[row["id"]]["state"]} for row in rows]
        run = {"case":"withdrawal","mode":mode,"events":events,
            "observations":{"business_ok":True,"withdrawn_file":fid,"retained_content":True,"reviewer_task_removed":True,"reviewer_reads_denied":True},
            "authority_snapshot":{"files":rows},"projection":projection,"mapping_checks":checks,
            "policy_evaluations":list(integration.evaluations) if integration else [],
            "probe_health":integration.health() if integration else {"errors":0,"dropped":0,"data_errors":0}}
        return run,graph.bo_export(runtime={"machine":machine,"events":events})
    finally:
        app.extensions["trial_store"].engine.dispose()
        if integration:integration.close()
        directory.cleanup()

def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    runs, exported = [], None
    for mode in ("on","off","fault"):
        for name in ("workflow","rejected","denied","session","withdrawal"):
            run, value = scenario(name,mode)
            runs.append(run)
            if name=="workflow" and mode=="on":
                exported=value
    project=json.loads((ROOT / "bo_stategraph/project.json").read_text(encoding="utf-8-sig"))
    payload={"build_id":runs[0]["projection"]["build_id"],"machine":project["model"]["machine"],
        "runs":runs,"stategraph_export":exported,"mapping_checks":[check for run in runs for check in run["mapping_checks"]]}
    (REVIEW / "runtime-observations.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False))
if __name__=="__main__":
    main()
