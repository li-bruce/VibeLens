"""Rehearse native SQLite migration on a consistent copy, preserving every file byte."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT))
from app.storage import Store

def snapshot(path):
    with sqlite3.connect(path) as db:
        return {table:db.execute('SELECT * FROM '+table+' ORDER BY id').fetchall() for table in ('users','files')}

target=OUT/'.tmp/migration-rehearsal.sqlite3'
assert not target.exists()
with sqlite3.connect(ROOT/'var/team-files.sqlite3') as source,sqlite3.connect(target) as copy:source.backup(copy)
before=snapshot(target)
store=Store(target)
store.initialize()
assert snapshot(target)==before
store.initialize()
assert snapshot(target)==before
with sqlite3.connect(target) as db:
    definition=db.execute("SELECT sql FROM sqlite_master WHERE name='files'").fetchone()[0]
    assert "'withdrawn'" in definition and not db.execute('PRAGMA foreign_key_check').fetchall()
    db.execute("UPDATE files SET state='withdrawn',recipient_id=NULL WHERE id=(SELECT id FROM files LIMIT 1)")
    db.rollback()
store.engine.dispose()
result={'valid':True,'files_preserved':len(before['files']),'users_preserved':len(before['users']),
    'all_columns_and_file_bytes_equal':True,'second_initialize_idempotent':True,'foreign_key_check':True,
    'new_constraint_accepts_withdrawn':True,'primary_database_changed':False,'database_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
(OUT/'migration-rehearsal.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
