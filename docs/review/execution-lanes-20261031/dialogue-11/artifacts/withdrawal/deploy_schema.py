"""Run the application's native migration after backup and verify all prior facts."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT))
from app.storage import Store
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with sqlite3.connect(path) as db:return {t:db.execute('SELECT * FROM '+t+' ORDER BY id').fetchall() for t in ('files','users')}
database=ROOT/'var/team-files.sqlite3'
backup=OUT/'before-schema.sqlite3'
assert not backup.exists()
before=rows(database)
with sqlite3.connect(database) as origin,sqlite3.connect(backup) as target:origin.backup(target)
protected={p.relative_to(ROOT).as_posix():sha(p) for directory in ('review/retest-20261101-05','resume-first-integration-20261031') for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'bo_stategraph/data/recordings').glob('*.json')})
(OUT/'protected-before.json').write_text(json.dumps(protected,indent=2),encoding='utf-8')
for path in (ROOT/'bo_stategraph/data').glob('events.jsonl*'):
    if path.is_file():shutil.copy2(path,OUT/('prior-raw-'+path.name))
store=Store(database)
store.initialize()
store.engine.dispose()
assert before==rows(database)==rows(backup)
with sqlite3.connect(database) as db:
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    schema=db.execute("SELECT sql FROM sqlite_master WHERE name='files'").fetchone()[0]
    assert "'withdrawn'" in schema
result={'valid':True,'all_prior_rows_and_content_preserved':True,'files':len(before['files']),
    'backup_sha256':sha(backup),'protected_files':len(protected),'migration':'Store.initialize / migrate_file_states',
    'canonical_observer_did_not_migrate':True,'schema':schema}
(OUT/'schema-migration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({key:result[key] for key in ('valid','files','protected_files','all_prior_rows_and_content_preserved')}))
