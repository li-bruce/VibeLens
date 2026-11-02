"""Concurrent real handlers must commit exactly one pending-state outcome."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from observe import ROOT, REVIEW, CONTENT, create_app, login, post, upload

def row(database,identifier):
    connection=sqlite3.connect(database)
    try:
        value=connection.execute("SELECT state,revision,content,journal FROM files WHERE id=?",(identifier,)).fetchone()
        return value[0],value[1],value[2],json.loads(value[3])
    finally:connection.close()

def main():
    REVIEW.mkdir(parents=True,exist_ok=True)
    scratch=REVIEW/'.tmp'
    scratch.mkdir(exist_ok=True)
    outcomes=[]
    with tempfile.TemporaryDirectory(dir=scratch,prefix='withdraw-race-') as directory:
        database=Path(directory)/'trial.sqlite3'
        app=create_app(ROOT,database=database)
        try:
            a,b=app.test_client(),app.test_client()
            login(a,'alice')
            login(b,'ben')
            for _ in range(6):
                fid=upload(a).json['id']
                barrier=threading.Barrier(2)
                def operation(kind):
                    barrier.wait(timeout=10)
                    return post(a if kind=='withdraw' else b,'/files/'+fid+'/'+kind,
                        {} if kind=='withdraw' else {'decision':'approve'}).status_code
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures={kind:pool.submit(operation,kind) for kind in ('withdraw','review')}
                    statuses={kind:future.result(timeout=20) for kind,future in futures.items()}
                state,revision,content,journal=row(database,fid)
                assert revision==2 and content==CONTENT and len(journal)==2
                assert statuses in ({'withdraw':200,'review':409},{'withdraw':403,'review':200}),statuses
                assert state==('withdrawn' if statuses['withdraw']==200 else 'approved')
                assert journal[-1]['event']==('withdraw' if state=='withdrawn' else 'approve')
                outcomes.append({'file_id':fid,'http':statuses,'state':state,'revision':revision,'journal':journal})
            fid=upload(a).json['id']
            owners=[app.test_client() for _ in range(3)]
            for client in owners:login(client,'alice')
            barrier=threading.Barrier(3)
            def duplicate(client):
                barrier.wait(timeout=10)
                return post(client,'/files/'+fid+'/withdraw',{}).status_code
            with ThreadPoolExecutor(max_workers=3) as pool:statuses=list(pool.map(duplicate,owners))
            assert sorted(statuses)==[200,403,403]
            state,revision,content,journal=row(database,fid)
            assert (state,revision,content,len(journal))==('withdrawn',2,CONTENT,2)
            machine=app.extensions['trial_service'].workflow.machine
            assert not any(t['source']=='withdrawn' for t in machine['transitions'])
            result={'valid':True,'review_withdraw_races':outcomes,'duplicate_withdraw_statuses':statuses,
                'exactly_one_commit_per_file':True,'file_content_retained':True,'withdrawn_has_no_resubmit_path':True}
            (REVIEW/'concurrency.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps({'valid':True,'concurrent_review_withdraw_cases':len(outcomes),'duplicate_withdraw':statuses}))
        finally:app.extensions['trial_store'].engine.dispose()

if __name__=='__main__':main()
