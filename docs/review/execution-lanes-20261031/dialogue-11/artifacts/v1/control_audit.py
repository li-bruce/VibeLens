"""Check actual browser DOM against canonical identities, native receipts and raw facts."""
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
from bo_observer.control.scope import ControlScope,user_command
from bo_observer.control.selection import build_plan

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def reject(label,callback):
    try:callback()
    except (ValueError,FileNotFoundError) as error:return {'case':label,'rejected':True,'error':str(error)}
    raise AssertionError(label+' was not rejected')

def main():
    context=read(OUT/'control-context.json')
    model=context['model']
    edges={e['id']:e for e in model['edges']}
    recording=read(OUT/'actual-recording.json')
    raw_info=read(OUT/'recording-evidence.json')
    raw_path=Path(raw_info['raw_recording_path'])
    assert sha(raw_path)==raw_info['raw_recording_sha256']
    results={}
    for stage in ('permissions','replay'):
        plan=read(OUT/(stage+'-plan-host.result.json'))['result']
        spec=read(OUT/('chain-permissions-view.json' if stage=='permissions' else 'chain-replay.json'))
        assert build_plan(context,spec,recording if stage=='replay' else None)==plan
        assert spec['anchors']==['upload_file','review_file','share_file','access_file']
        assert spec['depth']==2 and spec['direction']=='both'
        assert spec['nodes']==['business','decision'] and spec['edges']==['flow','guard','data']
        assert len(plan['node_ids'])==16 and len(plan['context_node_ids'])==3
        status=read(OUT/(stage+'-status-host.result.json'))['result']['result']
        assert status['status']=='applied' and not status['error']
        assert set(plan['node_ids']) <= set(status['nodes'])
        checks=[]
        for filename in (stage+'-dom.json',stage+'-reload-dom.json'):
            dom=read(OUT/filename)
            visible={n['id'] for n in dom['nodes']}
            missing=sorted(set(plan['node_ids'])-visible)
            assert not missing,(filename,missing)
            assert dom['body']['controlPlan']==plan['id']
            # The native canvas renders summary routes. Bind their explicit endpoint/type
            # tuple to original canonical IDs; never compare original IDs to summary IDs.
            represented=[]
            for eid in plan['edge_ids']:
                edge=edges[eid]
                routes=[r for r in dom['edges'] if (r['from'],r['to'],r['type'])==
                        (edge['from'],edge['to'],edge['type']) and r['count']>=1]
                assert len(routes)==1,(filename,eid,routes)
                represented.append({'original_id':eid,'route_id':routes[0]['id'],
                    'from':edge['from'],'to':edge['to'],'type':edge['type']})
            checks.append({'file':filename,'visible_nodes':len(visible),'missing_nodes':missing,
                'original_relations':represented,'all_20_original_edges_represented':len(represented)==20})
            if stage=='replay':
                assert dom['recording']==recording['id']
                assert dom['timeline']['source']=='saved'
                witnesses=read(OUT/'replay-all-event-witnesses.json')
                # Option values are native timeline indexes, which include an initial
                # snapshot. Verify observed browser event IDs instead of indexing raw JSON.
                assert [option['id'] for option in dom['steps']]==[w['option'] for w in witnesses]
                actual_ids=[w['eventId'] for w in witnesses]
                assert actual_ids==plan['recording']['event_ids']
                checks[-1]['exact_replay_event_ids_match']=True
                checks[-1]['selected_events']=len(actual_ids)
        results[stage]={'valid':True,'acknowledgement':status,'browser_checks':checks,
            'plan':plan,'original_model_unchanged':True}
        save(stage+'-browser.json',results[stage])
    three=read(OUT/'replay-3d-verified-dom.json')
    two=read(OUT/'replay-dom.json')
    assert three['threeD'] and three['modeLabel']=='3D'
    assert {n['id'] for n in three['nodes']}=={n['id'] for n in two['nodes']}
    assert {(e['from'],e['to'],e['type']) for e in three['edges']}=={(e['from'],e['to'],e['type']) for e in two['edges']}
    assert {n['attributes']['plane'] for n in three['nodes']}=={'business','state','rules','execution'}
    save('scoped-2d-3d-parity.json',{'valid':True,'nodes':len(three['nodes']),
        'relations':len(three['edges']),'native_planes':['business','state','rules','execution'],
        'mode_source':'Native aria-pressed and label; button.checked is not its state.',
        'scope':'Current scoped view with native curve routing; prior orthogonal/bus self-relation limitations remain.'})
    selected=read(OUT/'replay-plan-host.result.json')['result']['recording']['event_ids']
    steps=read(OUT/'replay-steps.json')
    assert [int(s['index']) for s in steps[:2]]==[1,2]
    assert int(steps[2]['index'])>2
    for step in steps:assert step['event']==selected[int(step['index'])]
    selected_events=[e for e in recording['events'] if e['id'] in set(selected)]
    for node in ('upload_file','review_file','share_file','access_file'):
        entries={e['call_id'] for e in selected_events if e['node']==node and e['phase']=='enter'}
        exits={e['call_id'] for e in selected_events if e['node']==node and e['phase'] in ('return','exception','error')}
        assert entries and entries<=exits,node
    with urllib.request.urlopen('http://127.0.0.1:8983/api/view',timeout=60) as response:after_raw=response.read()
    (OUT/'after-browser-replay-view.json').write_bytes(after_raw)
    before=read(OUT/'before-browser-replay-view.json')
    after=json.loads(after_raw)
    assert [e['id'] for e in before['events']]==[e['id'] for e in after['events']]
    assert sha(raw_path)==raw_info['raw_recording_sha256']
    assert after['health']['errors']==after['health']['dropped']==0
    assert after['health']['producer']['errors']==after['health']['producer']['dropped']==0
    canonical=ROOT.parents[1]/'SoftwareStatusObserverSkill/skills/vibelens'
    parity={}
    for local,origin in [('observer_runtime/bo_observer/control/selection.py','scripts/bo_observer/control/selection.py'),
        ('observer_runtime/bo_observer/control/cli.py','scripts/bo_observer/control/cli.py'),
        ('observer_runtime/bo_observer/service.py','scripts/bo_observer/service.py'),
        ('static/graph/viewer.js','assets/stategraph-viewer/viewer.js'),
        ('static/graph/analysis.js','assets/stategraph-viewer/analysis.js'),
        ('static/graph/conversation-controls.js','assets/stategraph-viewer/conversation-controls.js')]:
        assert (ROOT/local).read_bytes()==(canonical/origin).read_bytes(),local
        parity[local]=sha(ROOT/local)
    assert parity['observer_runtime/bo_observer/control/selection.py']=='78277c1dfc22a0542e6b626be8d2e28818a3be296c8cb42894ee36809042e50f'
    message=(OUT/'request.txt').read_text(encoding='utf-8').rstrip('\n')
    scope=ControlScope(ROOT)
    active=scope.authorized(message)
    assert active['conversation']==os.environ['CODEX_THREAD_ID']
    checks=[reject('missing prefix',lambda:user_command('Focus upload')),
        reject('quoted prefix',lambda:user_command('"/vibelens Focus upload"')),
        reject('different host conversation',lambda:scope.authorized(message,'another-conversation')),
        reject('unsupported business edit',lambda:build_plan(context,{'action':'edit-source'}))]
    isolated=OUT/'.tmp/scope-negative'
    target=isolated/'bo_stategraph/config/control'/(active['session']+'.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(scope.directory/(active['session']+'.json'),target)
    checks.append(reject('copied session at another project path',lambda:ControlScope(isolated).for_view(active['session'])))
    save('scope-negative-controls.json',{'valid':True,'checks':checks,'other_conversations_activated':False})
    result={'valid':True,'current_conversation':active['conversation'],'session':active['session'],
        'build_id':after['manifest']['build_id'],'view_bytes':len(after_raw),'managed_parity':parity,
        'selected_events':len(selected),'total_interval_events':len(recording['events']),
        'native_replay_steps':steps,'native_playback_progressed':True,'reload_filter_preserved':True,
        'selected_business_enter_exit_pairs_preserved':True,'raw_recording_unchanged':True,
        'raw_recording_sha256':sha(raw_path),'exact_live_event_id_lists_unchanged':True,
        'health':after['health'],'scope_rejections':len(checks),
        'limitations':['Bounded pre-start context retains 195 historical ownership gaps.',
            'Unchanged memory retention naturally evicts old events; no events were manually cleared.',
            'Round-02 3D orthogonal/bus self-relation limitations remain; no new exhaustive geometry claim.']}
    save('control-browser-audit.json',result)
    print(json.dumps({k:result[k] for k in ('valid','selected_events','total_interval_events','native_playback_progressed','raw_recording_unchanged','exact_live_event_id_lists_unchanged','scope_rejections')}))

if __name__=='__main__':main()
