"""Preserve failed ordinary epochs and independent checks without accepting them."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]
app = root / '.validation/p7-trials/node-retest-app'
out = root / 'docs/review/behavior-contracts-sequential/p7-trials/repair-28'
out.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda raw: hashlib.sha256(raw).hexdigest()
secret = read(app / '.stategraph/collector.json')['token'].encode()
allowed = {'.json', '.jsonl', '.log', '.md', '.py', '.png', '.jpg', '.mjs', '.js', '.html', '.css', '.body'}
earlier = app / 'review/runtime/announcement-module-bootstrap-20261122'
current = app / 'review/runtime/announcement-module-bootstrap-repaired-20261122'
ui = root / '.validation/p7-trials/node-repaired27-independent-desktop'

def selected(folder, recursive=False):
    paths = folder.rglob('*') if recursive else folder.iterdir()
    return {p.relative_to(folder).as_posix(): p for p in paths
            if p.is_file() and p.suffix in allowed and '__pycache__' not in p.parts}

def archive(name, entries):
    rows = []
    target = out / (name + '.zip')
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for member, path in sorted(entries.items()):
            raw = path.read_bytes()
            assert secret not in raw, 'Known collector secret in ' + member
            bundle.writestr(member, raw)
            rows.append({'member': member, 'bytes': len(raw), 'sha256': sha(raw)})
    with zipfile.ZipFile(target) as bundle:
        assert bundle.testzip() is None
        assert all(sha(bundle.read(row['member'])) == row['sha256'] for row in rows)
    index = {'archive': target.name, 'bytes': target.stat().st_size,
             'sha256': sha(target.read_bytes()), 'members': rows}
    (out / (name + '.json')).write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    return {k: v for k, v in index.items() if k != 'members'} | {'members': len(rows)}

entries = {}
for label, folder, subdirs in [
    ('first-failure-and-repair', earlier, ['announcement-before-controls', 'announcement-after-controls',
     'bootstrap-before-v2-controls', 'bootstrap-final-controls', 'failed-batch-complete-post-verify',
     'pure-source-comparison-first-failure', 'recovery-source']),
    ('repaired-source-capture-failure', current, ['complete-post-verify-originals',
     'controlled-permission-evidence', 'flow-source-snapshot']),
]:
    entries.update({label + '/' + k: v for k, v in selected(folder).items()})
    for subdir in subdirs:
        entries.update({label + '/' + subdir + '/' + k: v
                        for k, v in selected(folder / subdir, True).items()})
records = []
for run in ('unified-1795290160', 'unified-1795291546'):
    folder = app / 'review/runtime' / run
    entries.update({run + '/' + k: v for k, v in selected(folder).items()})
    browser = read(folder / 'browser-acceptance.json')
    records.append({'run': run, 'build_id': browser['build_id'],
                    'checks': browser['checks'], 'recordings': browser['recordings']})
    for record in browser['recordings']:
        path = app / 'bo_stategraph/data/recordings' / (record['id'] + '.json')
        entries['original-recordings/' + path.name] = path
archives = [archive('failure-and-repair-evidence', entries),
            archive('independent-desktop-evidence', selected(ui, True))]
model = read(app / 'bo_stategraph/project.json')
paths = set(model['model']['source_files']) | {'bo_stategraph/project.json', 'manifest.json',
         'discovery.json', 'behavior.json', 'intent.json', 'acceptance.json'}
archives.append(archive('failed-candidate-source', {p: app / p for p in paths}))
for name in ('FLOW_DIAGNOSIS.md', 'flow-bottleneck-diagnosis.json', 'flow-health-timeline.json',
             'independent-partial-recording-audit.json'):
    shutil.copy2(current / name, out / name)
for name in ('FAILURE_AND_TARGETED_REPAIR.md', 'recovery-targeted-summary.json'):
    shutil.copy2(earlier / name, out / name)
shots = out / 'screenshots'
shots.mkdir(exist_ok=True)
for name in ('layers/business-2D.png', 'layers/states-3D-expanded.png',
             'timeline/timeline-causal-links.png', 'range/selected-native-interval.png',
             'captions/source-visible.png'):
    shutil.copy2(ui / name, shots / name.replace('/', '-'))
result = {'phase': 'P7', 'phase_status': 'in_progress', 'native_acceptance': 'failed',
          'new_chats': 0, 'installed_provider_commit': '66efb5e24ae4b702bfa8f0515c90a3f2c2e637c4',
          'candidate': read(current / 'candidate-build.json'),
          'ordinary_epochs': records, 'independent_desktop': read(ui / 'sequence.json'),
          'interval_selected_events': read(ui / 'range/result.json').get('selected_count'),
          'archives': archives,
          'limits': 'No queue, field, command, timeout or stored-record changes. Viewer checks do not establish complete capture.',
          'database_exported': False, 'known_collector_secret_matches': 0}
(out / 'native-results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'native_acceptance': 'failed', 'archives': archives}))
