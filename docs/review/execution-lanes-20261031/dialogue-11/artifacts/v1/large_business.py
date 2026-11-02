"""Pace real HTTP workflows and retain every health sample at the original budgets."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from http_matrix import Client
from record_control_evidence import drained, get, save

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def main():
    clients = [Client(actor) for actor in ('alice','ben','cara','dan')]
    a,b,c,d = clients
    records, samples = [], []
    started = time.time()
    for index in range(90):
        name = f'control-large-round05-{index}.txt'
        status, body = a.upload(name)
        assert status == 201, (status,body)
        fid = json.loads(body)['id']
        path = '/files/' + fid
        # A paced admission strategy keeps the unchanged queue from a burst overload.
        time.sleep(.15)
        assert c.request(path)[0] == 403
        time.sleep(.15)
        assert b.post(path+'/review', {'decision':'approve'})[0] == 200
        time.sleep(.15)
        assert a.post(path+'/share', {'recipient_id':'cara'})[0] == 200
        time.sleep(.15)
        expected = ('Fresh real concurrent application upload: '+name+'\n').encode()
        assert c.request(path+'/download') == (200,expected)
        time.sleep(.15)
        assert d.request(path)[0] == 403
        raw,view = drained()
        with sqlite3.connect(ROOT/'var/team-files.sqlite3') as db:
            row = db.execute('SELECT state,revision,uploader_id,reviewer_id,recipient_id FROM files WHERE id=?',(fid,)).fetchone()
        assert row == ('approved',3,'alice','ben','cara'), row
        records.append({'file_id':fid,'filename':name,'sqlite':row,'download_sha256':hashlib.sha256(expected).hexdigest()})
        sample = {'workflows':len(records),'bytes':len(raw),'events':len(view['events']), 'health':view['health']}
        samples.append(sample)
        save('large-business-progress.json', {'workflows':records,'samples':samples})
        print(json.dumps({'workflows':len(records),'bytes':len(raw),'health':view['health']}),flush=True)
        producer = view['health']['producer']
        assert producer['dropped']==0 and producer['errors']==0, sample
        assert view['health']['dropped']==0 and view['health']['errors']==0, sample
        if len(raw)>8*1024*1024:
            break
    else:
        raise AssertionError('Real business view did not cross the unchanged 8 MiB budget')
    (OUT/'large-view-drained.json').write_bytes(raw)
    context_raw = get('/api/vibelens/control/context')
    context = json.loads(context_raw)
    assert context['model']==view['model'] and context['manifest']==view['manifest']
    assert not {'events','frames','runtime_frames','runtime','runs'} & set(context)
    after = json.loads(get('/api/view'))
    assert [e['id'] for e in view['events']]==[e['id'] for e in after['events']]
    (OUT/'control-context.json').write_bytes(context_raw)
    save('large-business.json',{'valid':True,'fixed_budget':8*1024*1024,'view_bytes':len(raw),
        'context_bytes':len(context_raw),'build_id':view['manifest']['build_id'],'workflows':records,
        'samples':samples,'health':view['health'],'elapsed_seconds':time.time()-started,
        'observer_reads_added_zero_events':True,'history_or_counters_cleared':False,
        'previous_loss_evidence':'../retest-20261101-04/coverage.md'})

if __name__=='__main__':
    main()
