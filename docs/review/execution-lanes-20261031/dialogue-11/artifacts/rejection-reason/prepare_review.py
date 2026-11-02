"""Review the confirmed reason branch and retain all earlier accepted obligations."""
import json
import sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
review=json.loads((ROOT/'withdraw-pending-20261101/review.json').read_text(encoding='utf-8-sig'))
review['candidate_id']=json.loads((OUT/(sys.argv[1] if len(sys.argv)>1 else 'inspect.result.json')).read_text(encoding='utf-8'))['candidate_id']
review['decisions']={
    'business':{'action':'updated','reason':'U006/U007 explicitly require a rejection reason retained verbatim and visible to the uploader in details; approval needs none. Existing role, sharing, terminal review and withdrawal rules remain. Dialogue is a coordinating-AI simulation.'},
    'state_machine':{'action':'updated','reason':'No state or transition is added. A typed rejection_reason context field carries the actual persisted text through native queries/snapshots. Invalid blank rejection stops before state advancement or commit.'},
    'abstraction':{'action':'updated','reason':'Add a source-bound validation decision and explicit reason-parameter/data representation while retaining existing IDs. SQLite adds an empty-default text column without inventing historical reasons. Authorized browser details and JSON metadata use the same current-fact access operation.'},
    'probes':{'action':'updated','reason':'Capture selected original reason input, actual validation Boolean and committed reason output/context. Add exact SQLite/API/HTML/whitespace/approval/permission expectations in on/off/fault cases and a concurrent-decision test. Keep every previous case, mode and validator. New evidence stays in this review.'}}
review['requirement_changes']={
    'R_REVIEW':'U006/U007 add mandatory nonblank reason on rejection only. Previous rejection scenarios now supply a real reason while retaining their original state/status/access assertions.',
    'R_REASON':'U007 confirms preservation of the original text and uploader detail display; validation may inspect whitespace but does not trim, rewrite or fabricate stored text.'}
(ROOT/'.stategraph/rejection-reason-20261101/review.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
(OUT/'candidate-review.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'valid':True,'candidate_id':review['candidate_id']}))
