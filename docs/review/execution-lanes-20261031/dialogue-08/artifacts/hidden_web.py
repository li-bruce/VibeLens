"""Disable the actual Web surface and exercise unchanged real business handlers."""
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(OUT))
from http_matrix import Client
BASE="http://127.0.0.1:8983"
def mode(value):
    result=subprocess.run([sys.executable,"-B",str(ROOT/"observer_runtime/bo_web.py"),"mode",value,"--root",str(ROOT)],capture_output=True,text=True,encoding="utf-8")
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout)
def get(path):
    try:
        with urllib.request.urlopen(BASE+path,timeout=15) as response:return response.status,response.read()
    except urllib.error.HTTPError as error:return error.code,error.read()
def main():
    before=json.loads(get("/api/view")[1])
    original=json.loads(subprocess.check_output([sys.executable,"-B",str(ROOT/"observer_runtime/bo_web.py"),"status","--root",str(ROOT)],text=True,encoding="utf-8"))["mode"]
    try:
        disabled=mode("disabled")
        graph_status,graph_body=get("/graph")
        view_status,view_body=get("/api/view")
        assert graph_status==view_status==404
        mode("visible")
        controls_only=json.loads(get("/api/view")[1])
        assert [e["id"] for e in before["events"]]==[e["id"] for e in controls_only["events"]]
        mode("disabled")
        a,b,c,d=[Client(actor) for actor in ("alice","ben","cara","dan")]
        status,body=a.upload("hidden-web-current-build.txt")
        assert status==201
        fid=json.loads(body)["id"]; path="/files/"+fid
        assert a.post(path+"/share",{"recipient_id":"cara"})[0]==403
        assert b.post(path+"/review",{"decision":"approve"})[0]==200
        assert a.post(path+"/share",{"recipient_id":"cara"})[0]==200
        status,download=c.request(path+"/download"); assert status==200
        assert download==b"Fresh real concurrent application upload: hidden-web-current-build.txt\n"
        assert d.request(path+"/download")[0]==403
    finally:
        mode(original)
    after=json.loads(get("/api/view")[1])
    assert after["manifest"]["build_id"]==before["manifest"]["build_id"]
    assert after["health"]["errors"]==after["health"]["dropped"]==0
    result={"valid":True,"mode":"disabled","graph_status":graph_status,"view_status":view_status,
        "disabled_body":json.loads(graph_body),"mode_controls_add_zero_business_events":True,
        "real_upload_review_share_download":True,"unrelated_download_status":403,
        "download_bytes":len(download),"file_id":fid,"build_id":after["manifest"]["build_id"],
        "capture_continued":len(after["events"])>len(before["events"]),"restored_mode":original}
    (OUT/"hidden-web.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))
if __name__=="__main__":main()
