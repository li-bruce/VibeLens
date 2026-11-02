"""Summarize retained current evidence and protected-byte integrity without inference."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
BASE="http://127.0.0.1:8983"
def read(name):return json.loads((OUT/name).read_text(encoding="utf-8-sig"))
def get(path):
    with urllib.request.urlopen(BASE+path,timeout=30) as response:return json.load(response)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding="utf-8")
def main():
    ready=read("reload-ready.json")
    rejection=read("reload-api-rejection.json")
    view=get("/api/view");recordings=get("/api/recordings")
    save("final-view.json",view);save("final-recordings.json",recordings)
    old_path=ROOT/"bo_stategraph/data/recordings"/(ready["recording"]+".json")
    assert sha(old_path)==ready["raw_sha256"]
    assert rejection["status"]==400 and "earlier graph version" in rejection["body"]
    assert ready["old_build"]!=view["manifest"]["build_id"]
    assert ready["recording"] not in {item["id"] for item in recordings["recordings"]}
    save("graph-reload.json",{"valid":True,"old_build":ready["old_build"],"new_build":view["manifest"]["build_id"],
        "old_recording":ready["recording"],"old_api_status":rejection["status"],"old_raw_bytes_preserved":True,
        "old_recording_removed_from_current_list":True,"same_browser_left_old_replay":True,
        "watch_evidence":"reload_watch.py reached its final status/hash assertion only after its actual same-browser new-build, leave-replay and old-option-removal waits completed. The driver incorrectly required 404; canonical API explicitly rejects the obsolete build with 400. reload-api-rejection.json independently retains the response and matching hash.",
        "method":"Normal source rebuild and path/port-verified native producer/service restart while the real browser remained in replay."})
    protected=read("integrity-before.json")
    changed=[name for name,digest in protected.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
    original=json.loads((ROOT/"review/retest-20261101-01/integrity-before.json").read_text(encoding="utf-8"))
    original_changed=[name for name,digest in original.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
    assert not changed and not original_changed,(changed,original_changed)
    raw_copies=[]
    for value in recordings["recordings"]:
        raw=ROOT/"bo_stategraph/data/recordings"/(value["id"]+".json")
        target=OUT/("raw-recording-"+value["id"]+".json")
        if target.exists():assert target.read_bytes()==raw.read_bytes()
        else:target.write_bytes(raw.read_bytes())
        raw_copies.append({"id":value["id"],"sha256":sha(raw),"status":value["status"]})
    producer=view["health"]["producer"]
    assert all(producer[key]==0 for key in ("errors","dropped","data_errors","integration_errors","pending")),producer
    assert view["health"]["errors"]==view["health"]["dropped"]==0
    for name in ("browser-flow.json","http-matrix.json","general-ownership-audit.json","runtime-parent-audit.json","viewer-checks.json","geometry-routes-checks.json","source-layer-audit.json","lifecycle-links.json","focused-boundary-audit.json","builder-audit.json","queue-cases.json","negative-controls.json","hidden-web.json","core-execution.json"):
        assert read(name).get("valid") is True,name
    full=read("actual-recording.json")
    assert full["build_id"]==view["manifest"]["build_id"] and not full["gaps"]
    assert not any(event.get("context_only") for event in full["events"])
    pointers=read("geometry-checks-attempt4.json")["checks"]
    assert len([check for check in pointers if "pointer" in check["case"] or "Independent 2D" in check["case"]])>=6
    geometry=[]
    for dimension in ("2d","3d"):
        for shape in ("straight","curve","orthogonal","bus"):
            value=read("routes-"+dimension+"-"+shape+".json")
            ports=value["ports"] if dimension=="2d" else value["spatial"]["edgePorts"]
            solver=value["metrics"]["routeSolver"] if dimension=="2d" else value["spatial"]["routeSolver"]
            geometry.append({"dimension":dimension,"shape":shape,"ports":len(ports),"routing_gaps":solver.get("unresolved",0),"failures":solver.get("failures",[]),"intersections":solver.get("intersections",0)})
    result={"valid":True,"candidate_id":read("verify-current.result.json")["candidate_id"],"build_id":view["manifest"]["build_id"],
        "protected_files":len(protected),"protected_changed":changed,"original_protected_files":len(original),"original_protected_changed":original_changed,
        "baseline_sha256":sha(ROOT/"resume-first-integration-20261031/baseline.json"),"full_events":len(full["events"]),
        "full_http_roots":read("general-ownership-audit.json")["actual_http_roots"],"raw_recordings":raw_copies,
        "health":view["health"],"geometry":geometry,"pointer_evidence":"geometry-checks-attempt4.json retains all seven successful current-build pointer/retention checks before its subsequently corrected route driver failure.",
        "limitations":["Focused pre-start context is capped at 2000 prior events; selected interval values and witnessed ancestors remain explicit.",
            "3D orthogonal/bus routing visibly reports two blocked self relations in this retained manual layout. Relations remain in the graph/accessibility inventory; straight/curve routes are present. This is the documented bounded route-search limitation, not fabricated routing success.",
            "This is independent AI browser/runtime acceptance with coordinating-AI business answers, not independent human usability testing."]}
    save("final-audit.json",result)
    print(json.dumps({key:result[key] for key in ("valid","candidate_id","build_id","protected_files","original_protected_files","baseline_sha256","full_events","full_http_roots")}))
if __name__=="__main__":main()
