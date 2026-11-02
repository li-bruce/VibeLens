"""Retain the real control activation failure without changing any control limits."""
import hashlib
import json
from pathlib import Path
import urllib.request
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
URL="http://127.0.0.1:8983/api/view"
with urllib.request.urlopen(URL,timeout=30) as response:
    body=response.read()
    status=response.status
view=json.loads(body)
with urllib.request.urlopen(URL,timeout=30) as response:
    after=json.load(response)
assert status==200 and len(body)>8*1024*1024
assert view["binding_status"]["status"]=="current"
assert [e["id"] for e in view["events"]]==[e["id"] for e in after["events"]]
runtime=ROOT/"observer_runtime/bo_observer/control/cli.py"
canonical=ROOT.parents[1]/"SoftwareStatusObserverSkill/skills/vibelens/scripts/bo_observer/control/cli.py"
assert runtime.read_bytes()==canonical.read_bytes()
result={"valid":True,"classification":"shared-framework-control-cli-defect","acceptance_ready":False,
    "http_status":status,"response_bytes":len(body),"fixed_cli_budget":8*1024*1024,
    "response_sha256":hashlib.sha256(body).hexdigest(),"build_id":view["manifest"]["build_id"],
    "events":len(view["events"]),"current_binding":view["binding_status"],"health":view["health"],
    "real_cli_result":json.loads((OUT/"activation-current.stdout.log").read_text(encoding="utf-8")),
    "managed_cli_matches_canonical":True,"cli_sha256":hashlib.sha256(runtime.read_bytes()).hexdigest(),
    "source_locations":["observer_runtime/bo_observer/control/cli.py:27-32 reads at most 8 MiB plus one byte and rejects larger responses",
        "observer_runtime/bo_observer/control/cli.py:60-64 activation unconditionally fetches the full /api/view",
        "observer_runtime/bo_observer/control/cli.py:116-125 snapshot support is confined to non-activation commands"],
    "observer_requests_added_zero_business_events":True,
    "preservation":"No control budget, managed source, raw events, capture requirements, baselines or assertions were changed. Do not clear retained events to make activation pass.",
    "maintenance_boundary":"Repair the canonical activation/inspection identity transport for a normal large live view while preserving explicit project/conversation authorization and bounded reads; include large-view and wrong-project regressions. Upgrade this project only through the normal interface and resume the same active change."}
(OUT/"control-budget-audit.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({key:result[key] for key in ("classification","response_bytes","fixed_cli_budget","events","build_id","managed_cli_matches_canonical","acceptance_ready")}))
