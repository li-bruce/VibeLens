"""A losing concurrent review must not replace the committed decision's reason."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from observe import ROOT,REVIEW,create_app,login,post,upload,CONTENT

def main():
    scratch=REVIEW/'.tmp'
    scratch.mkdir(parents=True,exist_ok=True)
    cases=[]
    with tempfile.TemporaryDirectory(dir=scratch,prefix='review-reason-race-') as directory:
        database=Path(directory)/'trial.sqlite3'
        app=create_app(ROOT,database=database)
        try:
            a=app.test_client()
            reviewers=[app.test_client(),app.test_client()]
            login(a,'alice')
            for client in reviewers:login(client,'ben')
            for index in range(4):
                fid=upload(a).json['id']
                original=f'  Original rejection {index}.\nKeep this exact text.  '
                barrier=threading.Barrier(2)
                def review(decision):
                    barrier.wait(timeout=10)
                    return post(reviewers[0 if decision=='approve' else 1],'/files/'+fid+'/review',
                        {'decision':decision,**({'reason':original} if decision=='reject' else {})}).status_code
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures={decision:pool.submit(review,decision) for decision in ('approve','reject')}
                    statuses={decision:future.result(timeout=20) for decision,future in futures.items()}
                assert sorted(statuses.values())==[200,409]
                connection=sqlite3.connect(database)
                try:row=connection.execute('SELECT state,revision,rejection_reason,content FROM files WHERE id=?',(fid,)).fetchone()
                finally:connection.close()
                expected=('approved','') if statuses['approve']==200 else ('rejected',original)
                assert (row[0],row[2])==expected and row[1]==2 and row[3]==CONTENT
                cases.append({'file_id':fid,'http':statuses,'state':row[0],'revision':row[1],'rejection_reason':row[2]})
            result={'valid':True,'cases':cases,'losing_review_cannot_replace_reason':True}
            (REVIEW/'reason-concurrency.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps({'valid':True,'races':len(cases)}))
        finally:app.extensions['trial_store'].engine.dispose()
if __name__=='__main__':main()
