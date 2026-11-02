"""Preserve a bounded read-only reproduction and strict-scope counterexamples."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import urllib.request

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'observer_runtime'))
from bo_observer.control.scope import ControlScope, user_command
from bo_observer.control.selection import build_plan

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
def reject(label,callback):
    try:callback()
    except (ValueError,FileNotFoundError) as error:
        return {'case':label,'rejected':True,'error':str(error)}
    raise AssertionError(label+' was not rejected')

with urllib.request.urlopen('http://127.0.0.1:8983/api/vibelens/control/context',timeout=60) as response:
    raw=response.read()
(OUT/'control-context-at-gap.json').write_bytes(raw)
view=json.loads(raw)
spec=read(OUT/'chain-permissions-view.json')
plan=build_plan(view,spec)
actual=read(OUT/'permissions-browser.json')
assert plan==actual['plan']
assert actual['acknowledgement']['status']=='rejected'
assert actual['missing_nodes']==['state_new']
assert actual['missing_original_edges']==['transition:submit']
nodes={n['id']:n for n in view['model']['nodes']}
assert nodes['state_new']['kind']=='state'
assert actual['observer_reads_added_zero_events'] and actual['raw_recording_unchanged']
canonical=ROOT.parents[1]/'SoftwareStatusObserverSkill/skills/vibelens'
parity={}
for local,original in [('observer_runtime/bo_observer/control/selection.py','scripts/bo_observer/control/selection.py'),
                       ('observer_runtime/bo_observer/control/cli.py','scripts/bo_observer/control/cli.py'),
                       ('observer_runtime/bo_observer/service.py','scripts/bo_observer/service.py'),
                       ('static/graph/viewer.js','assets/stategraph-viewer/viewer.js'),
                       ('static/graph/analysis.js','assets/stategraph-viewer/analysis.js'),
                       ('static/graph/conversation-controls.js','assets/stategraph-viewer/conversation-controls.js')]:
    assert (ROOT/local).read_bytes()==(canonical/original).read_bytes(),local
    parity[local]=sha(ROOT/local)
message=(OUT/'request.txt').read_text(encoding='utf-8').rstrip('\n')
scope=ControlScope(ROOT)
active=scope.authorized(message)
assert active['conversation']==os.environ['CODEX_THREAD_ID']
checks=[reject('missing prefix',lambda:user_command('Focus upload')),
        reject('quoted prefix',lambda:user_command('"/vibelens Focus upload"')),
        reject('different host conversation',lambda:scope.authorized(message,'another-conversation')),
        reject('unsupported business edit',lambda:build_plan(view,{'action':'edit-source'}))]
isolated=OUT/'.tmp'/'scope-negative'
target=isolated/'bo_stategraph/config/control'/ (active['session']+'.json')
target.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(scope.directory/(active['session']+'.json'),target)
checks.append(reject('copied session at another project path',lambda:ControlScope(isolated).for_view(active['session'])))
save('scope-negative-controls.json',{'valid':True,'checks':checks,'other_conversations_activated':False})
save('shared-view-gap.json',{'valid_reproduction':True,'acceptance_ready':False,
     'classification':'shared-control-plan-versus-typed-view-projection',
     'build_id':view['manifest']['build_id'],'model_revision':view['model']['revision'],
     'current_conversation':active['conversation'],'session':active['session'],
     'context_bytes':len(raw),'plan':plan,'missing_node':nodes['state_new'],
     'related_edges':[e for e in view['model']['edges'] if e['from']=='state_new' or e['to']=='state_new'],
     'actual_acknowledgement':actual['acknowledgement'],'managed_parity':parity,
     'observer_reads_added_zero_events':True,'raw_recording_unchanged':True,
     'inference':'The planner selects state_new two relationships from the business anchors despite business/decision filters. The native view retains one-hop filtered endpoints, but state_new is absent. Its transition:submit is also absent. The viewer correctly rejects acknowledgement; model planning and display projection are inconsistent.',
     'replay':'Not applied after this shared defect; no workaround, event clearing, budget increase or altered expectation.'})
print(json.dumps({'valid_reproduction':True,'status':actual['acknowledgement']['status'],'missing_nodes':actual['missing_nodes'],'strict_scope_checks':len(checks)}))
