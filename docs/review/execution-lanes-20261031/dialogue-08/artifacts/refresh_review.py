"""Reconcile the active candidate after normal ownership sealing."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
path=ROOT/"resume-first-integration-20261031/review.json"
previous=path.read_bytes()
(OUT/"candidate-review-before-seal-refresh.json").write_bytes(previous)
value=json.loads(previous)
value["candidate_id"]=json.loads((OUT/"inspect-after-seal.result.json").read_text(encoding="utf-8"))["candidate_id"]
value["decisions"]["probes"]["reason"] += " Reviewed canonical core parity and refreshed stale ownership seal using architecture_guard seal; retain original baseline and all assertions."
path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
(OUT/"candidate-review-after-seal.json").write_bytes(path.read_bytes())
print(json.dumps({"candidate_id":value["candidate_id"]}))
