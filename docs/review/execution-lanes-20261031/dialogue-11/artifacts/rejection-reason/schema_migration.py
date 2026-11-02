"""Rehearse or apply native additive migration while preserving every old field."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT))
from app.storage import Store

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def snapshot(path,columns=None):
    connection=sqlite3.connect(path)
    try:
        if columns is None:
            columns={table:[r[1] for r in connection.execute('PRAGMA table_info('+table+')')] for table in ('users','files')}
        values={table:connection.execute('SELECT '+','.join('"'+name+'"' for name in names)+' FROM '+table+' ORDER BY id').fetchall() for table,names in columns.items()}
        return columns,values
    finally:connection.close()

mode=sys.argv[1]
origin=ROOT/'var/team-files.sqlite3'
backup=OUT/('before-schema.sqlite3' if mode=='apply' else '.tmp/migration-rehearsal.sqlite3')
assert not backup.exists()
with sqlite3.connect(origin) as source,sqlite3.connect(backup) as target:source.backup(target)
columns,before=snapshot(backup)
database=origin if mode=='apply' else backup
if mode=='apply':
    protected={}
    for path in (ROOT/'review').rglob('*'):
        if path.is_file() and OUT not in path.parents and '.tmp' not in path.parts and '__pycache__' not in path.parts:
            protected[path.relative_to(ROOT).as_posix()]=sha(path)
    for directory in ('resume-first-integration-20261031','withdraw-pending-20261101'):
        for path in (ROOT/directory).rglob('*'):
            if path.is_file():protected[path.relative_to(ROOT).as_posix()]=sha(path)
    for path in (ROOT/'bo_stategraph/data/recordings').glob('*.json'):protected[path.relative_to(ROOT).as_posix()]=sha(path)
    (OUT/'protected-before.json').write_text(json.dumps(protected,indent=2),encoding='utf-8')
store=Store(database)
store.initialize()
assert snapshot(database,columns)[1]==before
store.initialize()
assert snapshot(database,columns)[1]==before
connection=sqlite3.connect(database)
try:
    assert not connection.execute('PRAGMA foreign_key_check').fetchall()
    assert connection.execute("SELECT COUNT(*) FROM files WHERE rejection_reason <> ''").fetchone()[0]==0
    rejected=connection.execute("SELECT COUNT(*) FROM files WHERE state='rejected'").fetchone()[0]
finally:connection.close()
store.engine.dispose()
result={'valid':True,'mode':mode,'files_preserved':len(before['files']),'users_preserved':len(before['users']),
    'all_original_columns_and_bytes_equal':True,'legacy_rejected_without_invented_reason':rejected,
    'new_field_default':'','idempotent':True,'backup_sha256':sha(backup),'old_columns':columns}
(OUT/('schema-migration.json' if mode=='apply' else 'migration-rehearsal.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
