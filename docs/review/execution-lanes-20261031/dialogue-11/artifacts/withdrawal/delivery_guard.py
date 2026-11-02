"""Require current truthful evidence, protected prior history and exact state/actor mapping."""
import hashlib
import json
from pathlib import Path
import sqlite3
from record_helpers import get,drained
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

verification=read(OUT/'verify-error-capture.result.json')
assert verification['valid'] and all(r['status']=='passed' for r in verification['reports'].values())
for name in ('negative-controls.json','concurrency.json','migration-rehearsal.json','schema-migration.json','native-api-comparison.json'):
    assert read(OUT/name)['valid'],name
baseline=ROOT/'resume-first-integration-20261031/baseline.json'
assert sha(baseline)=='8544e5bd79f050e8ec314274b75d9e6aa903b2675a9a1f6ddb97bc6cca7d4e5b'
new_baseline=read(ROOT/'withdraw-pending-20261101/baseline.json')
assert new_baseline['id']=='dd8008b1bf7671016669465ceb8206f0eb8f1a2438c22bb12ba7b27eb75da5eb'
assert set(new_baseline['requested_requirements'])=={'R_ACCESS','R_WITHDRAW'}
protected=read(OUT/'protected-before.json')
earlier=read(ROOT/'review/retest-20261101-05/integrity-before.json')
protected.update({name:value for name,value in earlier.items() if name.startswith('review/')})
changed=[name for name,value in protected.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=value]
assert not changed,changed
with sqlite3.connect(OUT/'before-schema.sqlite3') as before,sqlite3.connect(ROOT/'var/team-files.sqlite3') as after:
    for table in ('files','users'):
        expected={row[0]:row for row in before.execute('SELECT * FROM '+table)}
        actual={row[0]:row for row in after.execute('SELECT * FROM '+table)}
        assert all(actual.get(key)==value for key,value in expected.items()),table
live=read(OUT/'current-live-withdrawal.json')
assert live['valid'] and live['producer_settlement']['flushed']
recording=read(OUT/'current-actual-recording.json')
assert recording['status']=='stopped' and recording['build_id']==live['build_id']
assert sha(Path(live['raw_recording_path']))==live['raw_recording_sha256']
events={e['id']:e for e in recording['events']}
witnesses=read(OUT/'current-replay-witnesses.json')
assert len(witnesses)==5 and all(w['eventId'] in events for w in witnesses)
assert events[witnesses[0]['eventId']]['inputs']=={'actor':'alice','file_id':live['file_id']}
assert events[witnesses[1]['eventId']]['inputs']=={'event':'withdraw','before':'pending'}
assert events[witnesses[2]['eventId']]['outputs']=={'after':'withdrawn','allowed':True}
assert events[witnesses[3]['eventId']]['outputs']=={'state':'withdrawn','revision':2}
assert events[witnesses[4]['eventId']]['node']=='policy:reviewer_access'
assert events[witnesses[4]['eventId']]['outputs']['value'] is False
owner=read(OUT/'uploader-current-dom.json')
assert owner['badge']=='已撤回' and owner['withdrawButtons']==0 and owner['account'].startswith('alice')
assert len(owner['links'])==2 and all(live['file_id'] in link['url'] for link in owner['links'])
graph=read(OUT/'runtime-graph-dom.json')
assert any(n['id']=='withdraw_file' for n in graph['nodes'])
assert {r['id'] for r in graph['recordings']}=={'',live['recording_id']}
raw,view=drained()
assert view['manifest']['build_id']==live['build_id'] and view['binding_status']['status']=='current'
before_ids=[e['id'] for e in view['events']]
for route in ('/api/view','/api/stategraph/export','/api/recordings/'+live['recording_id']):get(route)
after_view=json.loads(get('/api/view'))
assert before_ids==[e['id'] for e in after_view['events']]
assert sha(Path(live['raw_recording_path']))==live['raw_recording_sha256']
health=after_view['health']
assert health['errors']==health['dropped']==health['producer']['errors']==health['producer']['dropped']==0
assert read(OUT/'gate11-readiness.json')['valid']
result={'valid':True,'candidate_id':verification['candidate_id'],'build_id':live['build_id'],
    'old_baseline_sha256':sha(baseline),'new_baseline_sha256':sha(ROOT/'withdraw-pending-20261101/baseline.json'),
    'protected_files':len(protected),'protected_changed':changed,'all_preexisting_database_rows_unchanged':True,
    'current_recording_id':live['recording_id'],'interval_events':len(recording['events']),
    'closed_interval_calls':live['closed_interval_calls'],'raw_recording_unchanged':True,
    'actual_browser_parameters_state_and_reviewer_false_match_raw_events':True,
    'observer_reads_added_zero_events':True,'current_health':health,
    'earlier_interrupted_recording_preserved':read(OUT/'recording-stop.json')['status']=='interrupted',
    'limits':['Bounded recording context still has historical ownership gaps.',
        'Reviewer task removal verified by actual HTTP list; stale reviewer endpoints reject without requiring logout.',
        'Prior 3D orthogonal/bus self-relation limitations remain; no exhaustive new geometry claim.',
        'Business answers are coordinating-AI simulations, not independent human acceptance.']}
(OUT/'delivery-guard.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({key:result[key] for key in ('valid','candidate_id','build_id','protected_files','interval_events','closed_interval_calls','observer_reads_added_zero_events')}))
