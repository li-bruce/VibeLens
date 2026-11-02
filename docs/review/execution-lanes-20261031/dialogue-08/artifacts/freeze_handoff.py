"""Preserve the explicitly frozen source/runtime and real acceptance evidence."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import urllib.request
import zipfile
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(path):return json.loads(path.read_text(encoding="utf-8-sig"))
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding="utf-8")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify():
    results={}
    for label,path in (("this_round_protected",OUT/"integrity-before.json"),("original_protected",ROOT/"review/retest-20261101-01/integrity-before.json")):
        expected=read(path)
        changed=[name for name,value in expected.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=value]
        results[label]={"files":len(expected),"changed":changed}
        assert not changed,(label,changed)
    results["baseline_sha256"]=sha(ROOT/"resume-first-integration-20261031/baseline.json")
    assert results["baseline_sha256"]=="8544e5bd79f050e8ec314274b75d9e6aa903b2675a9a1f6ddb97bc6cca7d4e5b"
    results["accepted_file_exists"]=(ROOT/"resume-first-integration-20261031/accepted.json").exists()
    assert not results["accepted_file_exists"]
    results["valid"]=True
    return results
def collect():
    for route,name in (("/api/view","final-view.json"),("/api/recordings","final-recordings.json"),("/api/stategraph/export","final-export.json")):
        with urllib.request.urlopen("http://127.0.0.1:8983"+route,timeout=30) as response:
            value=json.load(response)
        write(OUT/name,value)
    assert read(OUT/"final-recordings.json").get("active") is None
    for raw in (ROOT/"bo_stategraph/data/recordings").glob("*.json"):
        copy=OUT/("raw-recording-"+raw.name)
        if copy.exists():assert copy.read_bytes()==raw.read_bytes()
        else:copy.write_bytes(raw.read_bytes())
    backup=OUT/"sqlite-snapshot.sqlite3"
    assert not backup.exists()
    with sqlite3.connect(ROOT/"var/team-files.sqlite3") as origin,sqlite3.connect(backup) as target:origin.backup(target)
    result=verify();result["freeze_authority"]="Explicit coordinating/user instruction after canonical control-budget defect confirmation"
    result["database_backup_sha256"]=sha(backup)
    result["runtime_build"]=read(OUT/"final-view.json")["manifest"]["build_id"]
    write(OUT/"freeze-verification.json",result)
    print(json.dumps({"valid":True,"stage":"collected","runtime_build":result["runtime_build"],"accepted":False}))
def archive():
    verify()
    target=OUT/"source-runtime-snapshot.zip"
    assert not target.exists()
    paths=[]
    for directory in ("app","bo_stategraph","integrations","observer_runtime","static","templates","tooling","resume-first-integration-20261031",".stategraph"):
        for path in (ROOT/directory).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:continue
            name=path.relative_to(ROOT).as_posix()
            if name.startswith(("bo_stategraph/data/","bo_stategraph/config/views/","bo_stategraph/config/control/")):continue
            paths.append(path)
    paths += [path for path in ROOT.iterdir() if path.is_file()]
    paths += [path for path in OUT.rglob("*") if path.is_file() and ".tmp" not in path.relative_to(OUT).parts and "__pycache__" not in path.parts and path!=target and path.name!="freeze-manifest.json"]
    paths=sorted(set(paths))
    manifest={"status":"frozen_before_accept","source_root":str(ROOT),"candidate_id":read(OUT/"verify-current.result.json")["candidate_id"],
        "build_id":read(OUT/"final-view.json")["manifest"]["build_id"],"baseline_sha256":sha(ROOT/"resume-first-integration-20261031/baseline.json"),
        "files":{path.relative_to(ROOT).as_posix():sha(path) for path in paths},
        "exclusions":["Dependency environment/cache","Credentials and session-secret","Personal control/view state","Runtime JSONL logs: retained on disk; public snapshots and original raw recordings are preserved separately in this review","Scratch project copies under this round's .tmp","Older review trees: preserved unchanged on disk and verified against protected hashes"]}
    write(OUT/"freeze-manifest.json",manifest)
    paths.append(OUT/"freeze-manifest.json")
    with zipfile.ZipFile(target,"x",zipfile.ZIP_DEFLATED) as archive:
        for path in paths:archive.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:assert archive.testzip() is None
    result={"valid":True,"stage":"archived","files":len(paths),"archive_bytes":target.stat().st_size,"archive_sha256":sha(target),"accepted":False}
    write(OUT/"freeze-archive.json",result)
    print(json.dumps(result))
if __name__=="__main__":
    {"collect":collect,"archive":archive}[sys.argv[1]]()
