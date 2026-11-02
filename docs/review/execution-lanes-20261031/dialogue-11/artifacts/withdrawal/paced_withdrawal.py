"""Record a settled real HTTP withdrawal interval; retain the earlier timeout unchanged."""
import hashlib
import json
from pathlib import Path
import sqlite3
from http_matrix import Client
from record_helpers import get,post,drained
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def save(name,value):(OUT/('paced-'+name)).write_text(json.dumps(value,indent=2),encoding='utf-8')
def main():
    clients=[]
    for actor in ('alice','ben','cara'):
        clients.append(Client(actor))
        drained()
    a,b,c=clients
    started=post('/api/recordings/start',{'label':'Settled pending withdrawal and stale reviewer denial'})
    save('recording-start.json',started)
    name='withdraw-paced-20261101.txt'
    status,body=a.upload(name)
    assert status==201
    fid=json.loads(body)['id']
    path='/files/'+fid
    checks=[]
    def check(label,actual,expected):
        checks.append({'case':label,'actual':actual,'expected':expected})
        assert actual==expected,checks[-1]
    check('reviewer cannot withdraw',b.post(path+'/withdraw',{})[0],403)
    check('other actor cannot withdraw',c.post(path+'/withdraw',{})[0],403)
    check('uploader pending withdrawal',a.post(path+'/withdraw',{})[0],200)
    check('stale reviewer cannot review',b.post(path+'/review',{'decision':'approve'})[0],409)
    check('reviewer metadata',b.request(path)[0],403)
    check('reviewer download',b.request(path+'/download')[0],403)
    check('other actor metadata',c.request(path)[0],403)
    check('duplicate withdrawal',a.post(path+'/withdraw',{})[0],403)
    check('withdrawn sharing',a.post(path+'/share',{'recipient_id':'cara'})[0],403)
    check('uploader metadata',a.request(path)[0],200)
    content=('Fresh real concurrent application upload: '+name+'\n').encode()
    assert a.request(path+'/download')==(200,content)
    # Drain deliberately before the unchanged bounded native stop/flush operation.
    _,before_stop=drained()
    stopped=post('/api/recordings/stop',{})
    save('recording-stop.json',stopped)
    raw=get('/api/recordings/'+stopped['id'])
    (OUT/'paced-actual-recording.json').write_bytes(raw)
    recording=json.loads(raw)
    assert recording['status']=='stopped' and recording['producer_settlement']['flushed']
    events=recording['events']
    entries={e['call_id']:e for e in events if e['phase']=='enter'}
    exits={e['call_id']:e for e in events if e['phase'] in ('return','error','exception','commit','change')}
    assert set(entries)<=set(exits)
    assert not [e for e in events if e.get('parent_call_id') and e['parent_call_id'] not in entries]
    interval_ids={e['id'] for e in events}
    assert not [g for g in recording['ownership_gaps'] if g['event'] in interval_ids]
    successful=[e for e in entries.values() if e['node']=='withdraw_file' and e['inputs']['actor']=='alice' and exits[e['call_id']]['phase']=='return']
    assert len(successful)==1
    operation=successful[0]
    assert operation['inputs']['file_id']==fid and exits[operation['call_id']]['outputs']=={'state':'withdrawn','revision':2}
    transition=next(e for e in entries.values() if e['node']=='state_transition' and e['inputs']['event']=='withdraw')
    assert transition['inputs']['before']=='pending' and exits[transition['call_id']]['outputs']['after']=='withdrawn'
    database=sqlite3.connect(ROOT/'var/team-files.sqlite3')
    try:row=database.execute('SELECT state,revision,content,journal FROM files WHERE id=?',(fid,)).fetchone()
    finally:database.close()
    assert row[:3]==('withdrawn',2,content)
    journal=json.loads(row[3])
    assert [step['event'] for step in journal]==['submit','withdraw']
    # List removal is independently checked outside the small recorded interval.
    status,page=b.request('/')
    assert status==200 and fid.encode() not in page
    _,view=drained()
    assert before_stop['manifest']['build_id']==recording['build_id']==view['manifest']['build_id']
    assert view['health']['errors']==view['health']['dropped']==view['health']['producer']['errors']==view['health']['producer']['dropped']==0
    raw_path=ROOT/'bo_stategraph/data/recordings'/(stopped['id']+'.json')
    result={'valid':True,'file_id':fid,'filename':name,'recording_id':stopped['id'],'build_id':recording['build_id'],
        'http_checks':checks,'state':'withdrawn','revision':2,'content_sha256':hashlib.sha256(content).hexdigest(),
        'journal':journal,'interval_events':len(events),'closed_interval_calls':len(entries),
        'interval_missing_parents':0,'interval_ownership_gaps':0,'reviewer_list_absent':True,
        'raw_gaps':recording['gaps'],'prior_context_ownership_gaps':len(recording['ownership_gaps']),
        'producer_settlement':recording['producer_settlement'],'raw_recording_path':str(raw_path),
        'raw_recording_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),'health':view['health'],
        'earlier_timeout':'recording-stop.json and actual-recording.json remain unchanged; no complete-capture claim for that attempt.'}
    save('live-withdrawal.json',result)
    print(json.dumps({k:result[k] for k in ('valid','file_id','recording_id','interval_events','closed_interval_calls','state','revision')}))
if __name__=='__main__':main()
