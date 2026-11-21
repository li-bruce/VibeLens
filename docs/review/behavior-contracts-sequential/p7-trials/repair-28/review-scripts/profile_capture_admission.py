"""Profile source checks and event validation on a detached trial source copy.

This does not start the application, send a probe, edit a recording, or create
runtime acceptance evidence. The input samples are already captured facts.
"""
import cProfile
import argparse
import hashlib
import io
import json
from pathlib import Path
import pstats
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / '.validation/p7-trials/node-retest-app'
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--provider', type=Path, required=True)
args = parser.parse_args()
OUT = args.out.resolve()
OUT.mkdir(exist_ok=False)
clone = OUT / 'source-copy'
clone.mkdir()
project = json.loads((APP / 'bo_stategraph/project.json').read_text(encoding='utf-8'))
paths = set(project['model']['source_files']) | {
    'bo_stategraph/project.json', 'discovery.json', 'behavior.json', 'intent.json',
    'acceptance.json', 'sync.json', 'manifest.json',
}
for ref in project.get('contracts', {}).values():
    if isinstance(ref, dict) and ref.get('path'):
        paths.add(ref['path'])
before = {}
for relative in sorted(paths):
    src = APP / relative
    if not src.is_file():
        continue
    dst = clone / relative
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    before[relative] = hashlib.sha256(src.read_bytes()).hexdigest()
sys.path.insert(0, str(args.provider.resolve() / 'scripts'))
from bo_observer.observation.session import GraphSession
from bo_observer.protocol import validate_event
from bo_observer.observation.event_batch import BOSessionSink

session = GraphSession(clone)
record = json.loads((APP / 'review/runtime/native-runs.json').read_text(encoding='utf-8'))
events = next(run['events'] for run in record['runs'] if run['mode'] == 'on' and run['events'])[:128]
results = []
sink = BOSessionSink(session)
for name, count, fn in [
    ('binding', 12, lambda i: session.binding()),
    ('validate_event', len(events), lambda i: validate_event(events[i], session.project, session.manifest['build_id'])),
    ('admission', 2, lambda i: sink.bo_accept_many(events[i * 64:(i + 1) * 64])),
]:
    profiler = cProfile.Profile()
    start = time.perf_counter()
    profiler.enable()
    for index in range(count):
        fn(index)
    profiler.disable()
    elapsed = time.perf_counter() - start
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(25)
    (OUT / (name + '.txt')).write_text(stream.getvalue(), encoding='utf-8')
    results.append({'name': name, 'count': count, 'seconds': elapsed, 'mean_ms': elapsed * 1000 / count})
session.close()
assert all(hashlib.sha256((APP / p).read_bytes()).hexdigest() == value for p, value in before.items())
(OUT / 'result.json').write_text(json.dumps({'source_unchanged': True, 'build_id': session.manifest['build_id'], 'measurements': results, 'meaning': 'Detached diagnostic profile with profiler overhead; not native runtime or capacity acceptance.'}, indent=2) + '\n', encoding='utf-8')
print(json.dumps(results))
