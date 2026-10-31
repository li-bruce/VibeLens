"""Measure real event validation against an isolated copy of the trial sources."""
from copy import deepcopy
import cProfile
import io
import json
import os
from pathlib import Path
import pstats
import shutil
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('BO_PROFILE_SKILL', str(root / 'skills/vibelens/scripts')))
from bo_observer.observation.session import GraphSession

trial = root.parent / 'VibeLensTrials/lifecycle-dialogue-20261031'
project = json.loads((trial / 'bo_stategraph/project.json').read_text(encoding='utf-8-sig'))
recording = json.loads((root / os.environ.get('BO_PROFILE_RECORDING', 'docs/review/dialogue-acceptance-20261031/operations-original-v1-01/actual-recording.json')).read_text(encoding='utf-8'))
out = root / os.environ.get('BO_INGRESS_EVIDENCE', 'docs/review/dialogue-acceptance-20261031/ingress-after')
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=root / '.validation') as folder:
    target = Path(folder)
    names = set(project['model']['source_files']) | {'bo_stategraph/project.json', project['model']['intent']}
    for name in names:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(trial / name, target / name)
    session = GraphSession(target)
    initial_binding = session.binding()
    (out / 'initial-binding.json').write_text(json.dumps(initial_binding, indent=2) + '\n', encoding='utf-8')
    event = deepcopy(next(event for event in recording['events'] if event['node'] == 'db_read'))
    event.pop('source_seq', None)
    event.pop('stream_id', None)
    event.update(run_id='profile', producer_id='profile', build_id=session.manifest['build_id'], parent_call_id=None, depends=[])
    durations = []
    profile = cProfile.Profile()
    profile.enable()
    try:
        batch_size = int(os.environ.get('BO_PROFILE_BATCH', '1'))
        if not 1 <= batch_size <= 64:
            raise ValueError('Use a bounded local batch of 1 to 64 events')
        for first in range(1, 101, batch_size):
            values = []
            for index in range(first, min(101, first + batch_size)):
                value = deepcopy(event)
                value.update(id=f'profile:profile:{index}', seq=index, call_id=f'profile-{index}')
                values.append(value)
            started = time.perf_counter()
            if batch_size == 1:
                session.event(values[0])
            else:
                session.bo_sink.bo_accept_many(values)
            durations.extend([(time.perf_counter() - started) * 1000 / len(values)] * len(values))
    finally:
        profile.disable()
        session.close()
    buffer = io.StringIO()
    pstats.Stats(profile, stream=buffer).strip_dirs().sort_stats('cumtime').print_stats(22)
    (out / 'profile.txt').write_text(buffer.getvalue(), encoding='utf-8')
    report = {'events': len(durations), 'milliseconds': durations, 'total_ms': sum(durations), 'mean_ms': sum(durations) / len(durations), 'source_files': len(names), 'batch_size': batch_size, 'metric': 'Amortized admission milliseconds per event' if batch_size > 1 else 'Single-envelope admission milliseconds'}
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'milliseconds'}))
