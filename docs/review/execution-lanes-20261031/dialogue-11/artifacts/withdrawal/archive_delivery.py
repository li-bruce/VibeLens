"""Freeze accepted source/runtime and local evidence without exporting private settings."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import urllib.request
import zipfile
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
accepted=read(ROOT/'withdraw-pending-20261101/accepted.json')
for stage in ('accept','check','normal-project-check'):
    assert read(OUT/(stage+'.command.json'))['returncode']==0
    report=read(OUT/(stage+'.result.json'))
    assert report['valid'] and report['candidate_id']==accepted['candidate_id']
live=read(OUT/'current-live-withdrawal.json')
assert live['build_id']==accepted['build_id']
raw=Path(live['raw_recording_path'])
assert sha(raw)==live['raw_recording_sha256']
shutil.copy2(raw,OUT/('raw-recording-'+raw.name))
for path in (ROOT/'bo_stategraph/data').glob('events.jsonl*'):
    if path.is_file():shutil.copy2(path,OUT/('current-raw-'+path.name))
for route,name in [('/api/view','handoff-view.json'),('/api/stategraph/export','handoff-export.json')]:
    with urllib.request.urlopen('http://127.0.0.1:8983'+route,timeout=60) as response:(OUT/name).write_bytes(response.read())
assert read(OUT/'handoff-view.json')['manifest']['build_id']==accepted['build_id']
database=OUT/'accepted-database.sqlite3'
assert not database.exists()
with sqlite3.connect(ROOT/'var/team-files.sqlite3') as origin,sqlite3.connect(database) as target:origin.backup(target)
paths=[]
for directory in ('app','bo_stategraph','integrations','observer_runtime','static','templates','tooling',
    'resume-first-integration-20261031','withdraw-pending-20261101','.stategraph'):
    for path in (ROOT/directory).rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:continue
        name=path.relative_to(ROOT).as_posix()
        if name.startswith(('bo_stategraph/data/','bo_stategraph/config/views/','bo_stategraph/config/control/')):continue
        paths.append(path)
paths += [p for p in ROOT.iterdir() if p.is_file()]
paths += [p for p in OUT.rglob('*') if p.is_file() and '.tmp' not in p.relative_to(OUT).parts
    and '__pycache__' not in p.parts and p.name not in ('source-runtime-snapshot.zip','handoff-manifest.json')]
paths=sorted(set(paths))
manifest={'accepted':accepted,'files':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
    'exclusions':['Private view/control settings','Session secret / var directory','Dependency environments/caches',
        'Scratch copies','Unchanged older review trees (retained separately)']}
(OUT/'handoff-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
paths.append(OUT/'handoff-manifest.json')
archive=OUT/'source-runtime-snapshot.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as output:
    for path in paths:output.write(path,path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as output:
    assert output.testzip() is None
    mismatches=[name for name,digest in manifest['files'].items() if sha(ROOT/name)!=digest or hashlib.sha256(output.read(name)).hexdigest()!=digest]
assert not mismatches,mismatches
guard=read(OUT/'delivery-guard.json')
result={'valid':True,'accepted':True,'candidate_id':accepted['candidate_id'],'build_id':accepted['build_id'],
    'old_baseline_sha256':guard['old_baseline_sha256'],'protected_files':guard['protected_files'],
    'four_reports':{k:v['status'] for k,v in read(OUT/'verify-error-capture.result.json')['reports'].items()},
    'normal_project_check':True,'recording_id':live['recording_id'],'raw_recording_sha256':sha(raw),
    'archive_files':len(paths),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
    'archive_bytes_and_current_listed_files_match':True,'all_prior_database_rows_preserved':True,
    'independent_human_acceptance':False,'no_publication_or_cross_chat_messages':True}
(OUT/'handoff-final-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
