"""Independently verify accepted identities, protected facts and the delivery archive."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
from preserve_evidence import integrity

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

protected=integrity()
verified=read(OUT/'verify-final.result.json')
assert verified['valid'] and all(r['status']=='passed' for r in verified['reports'].values())
for stage in ('accept','check','normal-project-check'):
    result=read(OUT/(stage+'.result.json'))
    command=read(OUT/(stage+'.command.json'))
    assert result['valid'] and command['returncode']==0 and result['candidate_id']==verified['candidate_id']
accepted=read(ROOT/'resume-first-integration-20261031/accepted.json')
assert accepted['candidate_id']==verified['candidate_id']
gate=read(OUT/'repository-verification-11.json')
assert gate['valid'] is True and gate['exit_code']==0
canonical=ROOT.parents[1]/'SoftwareStatusObserverSkill/skills/vibelens/scripts/bo_observer/control/selection.py'
assert sha(canonical)==sha(ROOT/'observer_runtime/bo_observer/control/selection.py')=='78277c1dfc22a0542e6b626be8d2e28818a3be296c8cb42894ee36809042e50f'
assert read(OUT/'control-browser-audit.json')['valid']
assert read(OUT/'scoped-2d-3d-parity.json')['valid']
recording=read(OUT/'recording-evidence.json')
assert accepted['build_id']==recording['build_id']
assert sha(Path(recording['raw_recording_path']))==recording['raw_recording_sha256']
assert sha(OUT/('raw-recording-'+recording['recording_id']+'.json'))==recording['raw_recording_sha256']
with urllib.request.urlopen('http://127.0.0.1:8983/api/view',timeout=60) as response:view=json.load(response)
assert view['manifest']['build_id']==accepted['build_id'] and view['binding_status']['status']=='current'
assert [e['id'] for e in view['events']]==[e['id'] for e in read(OUT/'before-browser-replay-view.json')['events']]
assert view['health']['producer']['pending']==0
assert view['health']['errors']==view['health']['dropped']==view['health']['producer']['errors']==view['health']['producer']['dropped']==0
archive=read(OUT/'handoff-archive.json')
manifest=read(OUT/'handoff-manifest.json')
assert archive['valid'] and archive['accepted'] and manifest['accepted']
zip_path=OUT/'source-runtime-snapshot.zip'
assert sha(zip_path)==archive['archive_sha256']
with zipfile.ZipFile(zip_path) as saved:
    assert saved.testzip() is None
    mismatches=[name for name,digest in manifest['files'].items() if sha(ROOT/name)!=digest or hashlib.sha256(saved.read(name)).hexdigest()!=digest]
assert not mismatches,mismatches
result={'valid':True,'accepted':True,'candidate_id':accepted['candidate_id'],'build_id':accepted['build_id'],
    'baseline_sha256':sha(ROOT/'resume-first-integration-20261031/baseline.json'),'protected':protected,
    'four_reports':{name:r['status'] for name,r in verified['reports'].items()},
    'repository_gate':{'valid':True,'exit_code':0,'command':gate['command'],'record_sha256':sha(OUT/'repository-verification-11.json')},
    'canonical_selection_sha256':sha(canonical),'scoped_view_and_filtered_native_replay':True,
    'raw_recording_unchanged':True,'recording_id':recording['recording_id'],
    'exact_live_event_id_list_unchanged':True,'live_health':view['health'],
    'archive_files_checked':len(manifest['files']),'archive_sha256':archive['archive_sha256'],
    'prior_evidence_and_limitations_preserved':True,'independent_human_acceptance':False,
    'no_commits_pushes_publication_or_cross_chat_messages':True}
(OUT/'handoff-final-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({key:result[key] for key in ('valid','accepted','candidate_id','build_id','archive_files_checked','raw_recording_unchanged')}))
