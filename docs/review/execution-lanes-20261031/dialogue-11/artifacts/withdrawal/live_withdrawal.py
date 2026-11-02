"""Coordinate a real browser click with independent HTTP sessions and SQLite evidence."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from http_matrix import Client
from record_helpers import get,post,save,drained
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]

def wait_file(name):
    for _ in range(240):
        if (OUT/'.tmp'/name).exists():return
        time.sleep(1)
    raise AssertionError('Browser coordination timed out: '+name)

def main():
    clients=[]
    for actor in ('alice','ben','cara'):
        clients.append(Client(actor))
        drained()
    a,b,c=clients
    filename='withdraw-browser-20261101.txt'
    status,body=a.upload(filename)
    assert status==201
    fid=json.loads(body)['id']
    path='/files/'+fid
    stale=b.request('/')[1]
    assert fid.encode() in stale and ('action="'+path+'/review"').encode() in stale
    save('browser-fixture.json',{'file_id':fid,'filename':filename,'uploader':'alice','reviewer':'ben','state':'pending'})
    (OUT/'reviewer-before.html').write_bytes(stale)
    print(json.dumps({'prepared':True,'file_id':fid,'filename':filename}),flush=True)
    wait_file('browser-fixture-visible.flag')
    drained()
    started=post('/api/recordings/start',{'label':'Uploader withdraws; stale reviewer loses reads'})
    save('recording-start.json',started)
    (OUT/'.tmp/recording-ready.flag').write_text(started['id'],encoding='utf-8')
    wait_file('browser-withdrawn-visible.flag')
    checks=[]
    def check(name,actual,expected):
        checks.append({'case':name,'actual':actual,'expected':expected})
        assert actual==expected,checks[-1]
    check('stale reviewer review',b.post(path+'/review',{'decision':'approve'})[0],409)
    check('stale reviewer metadata',b.request(path)[0],403)
    check('stale reviewer download',b.request(path+'/download')[0],403)
    check('reviewer cannot withdraw',b.post(path+'/withdraw',{})[0],403)
    check('unrelated metadata',c.request(path)[0],403)
    check('unrelated download',c.request(path+'/download')[0],403)
    check('repeat withdrawal',a.post(path+'/withdraw',{})[0],403)
    check('withdrawn sharing',a.post(path+'/share',{'recipient_id':'cara'})[0],403)
    status,body=a.request(path)
    check('uploader metadata',status,200)
    assert json.loads(body)['state']=='withdrawn'
    content=('Fresh real concurrent application upload: '+filename+'\n').encode()
    check('uploader download',a.request(path+'/download'),(200,content))
    status,reviewer_page=b.request('/')
    check('reviewer list',status,200)
    assert fid.encode() not in reviewer_page
    (OUT/'reviewer-after.html').write_bytes(reviewer_page)
    stopped=post('/api/recordings/stop',{})
    save('recording-stop.json',stopped)
    raw=get('/api/recordings/'+stopped['id'])
    (OUT/'actual-recording.json').write_bytes(raw)
    recording=json.loads(raw)
    events=recording['events']
    entries={e['call_id']:e for e in events if e['phase']=='enter'}
    exits={e['call_id']:e for e in events if e['phase'] in ('return','error','exception','commit','change')}
    assert set(entries)<=set(exits)
    assert not [e for e in events if e.get('parent_call_id') and e['parent_call_id'] not in entries]
    withdrawal=next(e for e in entries.values() if e['node']=='withdraw_file' and e['inputs']['actor']=='alice')
    assert withdrawal['inputs']['file_id']==fid and exits[withdrawal['call_id']]['outputs']=={'state':'withdrawn','revision':2}
    transition=next(e for e in entries.values() if e['node']=='state_transition' and e['inputs']['event']=='withdraw')
    assert transition['inputs']['before']=='pending' and exits[transition['call_id']]['outputs']['after']=='withdrawn'
    db=sqlite3.connect(ROOT/'var/team-files.sqlite3')
    try:row=db.execute('SELECT state,revision,content,journal FROM files WHERE id=?',(fid,)).fetchone()
    finally:db.close()
    assert row[:3]==('withdrawn',2,content)
    journal=json.loads(row[3])
    assert [s['event'] for s in journal]==['submit','withdraw']
    raw_path=ROOT/'bo_stategraph/data/recordings'/(stopped['id']+'.json')
    _,view=drained()
    assert recording['build_id']==view['manifest']['build_id']
    assert view['health']['errors']==view['health']['dropped']==view['health']['producer']['errors']==view['health']['producer']['dropped']==0
    result={'valid':True,'file_id':fid,'filename':filename,'recording_id':stopped['id'],'build_id':recording['build_id'],
        'http_checks':[{**v,'actual':str(v['actual']),'expected':str(v['expected'])} for v in checks],
        'state':'withdrawn','revision':2,'content_sha256':hashlib.sha256(content).hexdigest(),'journal':journal,
        'interval_events':len(events),'closed_interval_calls':len(entries),'producer_settlement':recording['producer_settlement'],
        'context_gaps':recording['gaps'],'raw_recording_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        'raw_recording_path':str(raw_path),'explicitly_stopped':True,'health':view['health'],
        'mutation_source':'Actual native browser withdrawal form; independent HTTP clients verify stale reviewer and other actors.'}
    save('live-withdrawal.json',result)
    print(json.dumps({k:result[k] for k in ('valid','file_id','recording_id','interval_events','closed_interval_calls','state','revision')}),flush=True)

if __name__=='__main__':main()
