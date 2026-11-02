"""Preserve the blocked candidate without accepting it or changing old evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import urllib.request
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')

def verify():
    results = {}
    for label, path in [('this_round_protected', OUT / 'integrity-before.json'),
                        ('original_protected', ROOT / 'review/retest-20261101-01/integrity-before.json')]:
        expected = read(path)
        changed = [name for name, value in expected.items() if not (ROOT / name).is_file() or sha(ROOT / name) != value]
        assert not changed, (label, changed)
        results[label] = {'files': len(expected), 'changed': changed}
    baseline = sha(ROOT / 'resume-first-integration-20261031/baseline.json')
    assert baseline == '8544e5bd79f050e8ec314274b75d9e6aa903b2675a9a1f6ddb97bc6cca7d4e5b'
    assert not (ROOT / 'resume-first-integration-20261031/accepted.json').exists()
    recording = read(OUT / 'recording-evidence.json')
    assert sha(Path(recording['raw_recording_path'])) == recording['raw_recording_sha256']
    results.update(valid=True, baseline_sha256=baseline, accepted=False, raw_recording_unchanged=True)
    return results

def collect():
    result = verify()
    for route, name in [('/api/view', 'handoff-view.json'), ('/api/recordings', 'handoff-recordings.json'),
                        ('/api/stategraph/export', 'handoff-export.json')]:
        assert not (OUT / name).exists()
        with urllib.request.urlopen('http://127.0.0.1:8983' + route, timeout=60) as response:
            (OUT / name).write_bytes(response.read())
    assert not read(OUT / 'handoff-recordings.json').get('active')
    view = read(OUT / 'handoff-view.json')
    assert view['health']['producer']['pending'] == 0
    for path in (ROOT / 'bo_stategraph/data').glob('events.jsonl*'):
        if path.is_file():
            shutil.copy2(path, OUT / ('raw-event-log-' + path.name))
    raw = Path(read(OUT / 'recording-evidence.json')['raw_recording_path'])
    shutil.copy2(raw, OUT / ('raw-recording-' + raw.name))
    database = OUT / 'sqlite-snapshot.sqlite3'
    assert not database.exists()
    with sqlite3.connect(ROOT / 'var/team-files.sqlite3') as source, sqlite3.connect(database) as target:
        source.backup(target)
    result.update(runtime_build=view['manifest']['build_id'],
                  candidate_id=read(OUT / 'verify-reviewed.result.json')['candidate_id'],
                  database_backup_sha256=sha(database), status='blocked_before_accept')
    write(OUT / 'handoff-verification.json', result)
    print(json.dumps(result))

def archive():
    verify()
    target = OUT / 'source-runtime-snapshot.zip'
    assert not target.exists()
    paths = []
    for directory in ('app', 'bo_stategraph', 'integrations', 'observer_runtime', 'static',
                      'templates', 'tooling', 'resume-first-integration-20261031', '.stategraph'):
        for path in (ROOT / directory).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            name = path.relative_to(ROOT).as_posix()
            if name.startswith(('bo_stategraph/data/', 'bo_stategraph/config/views/', 'bo_stategraph/config/control/')):
                continue
            paths.append(path)
    paths += [p for p in ROOT.iterdir() if p.is_file()]
    paths += [p for p in OUT.rglob('*') if p.is_file() and '.tmp' not in p.relative_to(OUT).parts
              and '__pycache__' not in p.parts and p.name not in ('source-runtime-snapshot.zip', 'handoff-manifest.json')]
    paths = sorted(set(paths))
    manifest = {'status': 'blocked_before_accept', 'files': {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
                'exclusions': ['Dependency environment/cache', 'Session secret and var directory',
                               'Personal view/control files', 'Scratch copies', 'Unchanged older review trees'],
                'raw_evidence': 'Current live JSONL files, current raw recording and actual HTTP snapshots preserved in this review; prior historical recordings remain unchanged on disk.'}
    write(OUT / 'handoff-manifest.json', manifest)
    paths.append(OUT / 'handoff-manifest.json')
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as output:
        for path in paths:
            output.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as output:
        assert output.testzip() is None
    result = {'valid': True, 'files': len(paths), 'archive_bytes': target.stat().st_size,
              'archive_sha256': sha(target), 'accepted': False}
    write(OUT / 'handoff-archive.json', result)
    print(json.dumps(result))

if __name__ == '__main__':
    {'collect': collect, 'archive': archive}[sys.argv[1]]()
