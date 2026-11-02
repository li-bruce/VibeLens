"""Final offline integrity audit of the stopped, unaccepted handoff."""
import hashlib
import json
from pathlib import Path
import zipfile

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
protected=read(OUT/'integrity-before.json')
changed=[p for p,digest in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=digest]
assert not changed,changed
baseline=sha(ROOT/'resume-first-integration-20261031/baseline.json')
assert baseline=='8544e5bd79f050e8ec314274b75d9e6aa903b2675a9a1f6ddb97bc6cca7d4e5b'
assert not (ROOT/'resume-first-integration-20261031/accepted.json').exists()
verified=read(OUT/'verify-final.result.json')
assert verified['valid'] and all(v['status']=='passed' for v in verified['reports'].values())
gate=read(OUT/'normal-project-check.result.json')
assert not gate['valid'] and 'change is not accepted for current inputs' in gate['errors']
gap=read(OUT/'shared-view-gap.json')
assert gap['actual_acknowledgement']['status']=='rejected'
recording=read(OUT/'recording-evidence.json')
assert sha(Path(recording['raw_recording_path']))==recording['raw_recording_sha256']
assert sha(OUT/('raw-recording-'+recording['recording_id']+'.json'))==recording['raw_recording_sha256']
manifest=read(OUT/'handoff-manifest.json')
archive=read(OUT/'handoff-archive.json')
zip_path=OUT/'source-runtime-snapshot.zip'
assert sha(zip_path)==archive['archive_sha256']
with zipfile.ZipFile(zip_path) as saved:
    assert saved.testzip() is None
    mismatches=[name for name,digest in manifest['files'].items()
                if sha(ROOT/name)!=digest or hashlib.sha256(saved.read(name)).hexdigest()!=digest]
assert not mismatches,mismatches
result={'valid':True,'status':'blocked_before_accept','candidate_id':verified['candidate_id'],
        'runtime_build':gap['build_id'],'baseline_sha256':baseline,'protected_files':len(protected),
        'protected_changed':changed,'accepted':False,'required_view_rejected':True,
        'filtered_replay':'not_run_after_shared_defect','current_recording_raw_unchanged':True,
        'archive_files_checked':len(manifest['files']),'archive_sha256':archive['archive_sha256'],
        'archive_bytes':zip_path.stat().st_size,'archive_matches_current_listed_files':True,
        'services':read(OUT/'owned-service-stop.json'),'no_publication_or_cross_chat_messages':True}
(OUT/'handoff-final-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
