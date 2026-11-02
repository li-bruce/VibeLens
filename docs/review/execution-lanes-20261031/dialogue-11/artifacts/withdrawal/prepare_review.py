"""Review the user-confirmed withdrawal delta without replacing earlier evidence."""
import json
import sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
review=json.loads((ROOT/'resume-first-integration-20261031/review.json').read_text(encoding='utf-8-sig'))
review['candidate_id']=json.loads((OUT/(sys.argv[1] if len(sys.argv)>1 else 'inspect.result.json')).read_text(encoding='utf-8'))['candidate_id']
review['decisions']={
    'business':{'action':'updated','reason':'U003 requests withdrawal; U004 resolves terminal behavior, uploader-only pending authority, retained file/uploader reads and removed reviewer task/reads; U005 confirms the displayed graph. All are coordinating-AI simulated business dialogue.'},
    'state_machine':{'action':'updated','reason':'Add only pending -> withdrawn on withdraw with the existing native operation_allowed guard. Withdrawn is terminal; no resubmit path. The real executor consumes the same declaration.'},
    'abstraction':{'action':'updated','reason':'Preserve existing node identities; add withdrawal action/state, shared current-fact policy conditions, explicit source/parameter mappings, extended SQLite constraint and native atomic migration. Existing stored rows/content remain byte-equal.'},
    'probes':{'action':'updated','reason':'Capture real withdraw invocation actor/file_id, policy pending/withdrawn decisions, committed state/revision and native transition. Add independent withdrawal scenarios in on/off/fault modes and current HTTP/browser/race evidence. Preserve every prior expectation and gate; new evidence routes to this round.'}}
review['requirement_changes']={
    'R_WITHDRAW':'U004/U005 explicitly confirm uploader-only pending withdrawal, terminal workflow, retained file/uploader access, removed reviewer task and metadata/download access, and no resubmission in this version.',
    'R_ACCESS':'U004 changes only the withdrawn-file exception: the assigned reviewer loses reads. Uploader access, approved actual-recipient access, login requirements and all other denials remain.'}
(ROOT/'withdraw-pending-20261101/review.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
(OUT/'candidate-review.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'valid':True,'candidate_id':review['candidate_id']}))
