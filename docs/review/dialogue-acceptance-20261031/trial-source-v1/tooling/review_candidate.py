"""Record the reviewed source dispositions for one exact current candidate."""

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"observer_runtime")]
from bo_observer.workflow.sync_config import config,snapshot


if __name__=="__main__":
    cfg=config(ROOT,"sync.json")
    current=snapshot(ROOT,cfg)
    plan=current["model"]["implementation"]
    review={"candidate_id":current["id"],"requirement_changes":{},"decisions":{
        "business":{"action":"updated","reason":"Implement only the confirmed trial rules U001-U006, including the later selected-reviewer and three-party notification answers."},
        "state_machine":{"action":"updated","reason":"The canonical flat bo.fsm declaration drives pending approval, rejection, cancellation and revocation; SQLite owns committed state."},
        "abstraction":{"action":"updated","reason":"Stable design identities map to native service methods, rule expressions, data operations and explicitly classified HTTP handlers."},
        "probes":{"action":"updated","reason":"Capture allowlisted function spans, actual native policy reports, state snapshots and native database outcomes; independent tests check business effects."}},"excluded_symbols":{sid:"Reviewed static implementation helper mapped to "+item["node"]+": "+item["reason"] for sid,item in plan["support"].items()}}
    (ROOT/".stategraph/initial-app/review.json").write_text(json.dumps(review,indent=2),encoding="utf-8")
    print(json.dumps({"candidate_id":current["id"],"support_dispositions":len(review["excluded_symbols"])}))
