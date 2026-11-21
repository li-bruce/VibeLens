"""Compare envelope validation only; never feed the application or collector."""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

root = Path(__file__).resolve().parents[1]
app = root / '.validation/p7-trials/node-retest-app'
baseline = root / '.validation/p7-trials/context-closure-skills/vibelens'
out = root / '.validation/p7-repair28-checks/index-comparison.json'
sys.path.insert(0, str(root / 'skills/vibelens/scripts'))
from bo_observer.protocol import validate_event_batch

spec = importlib.util.spec_from_file_location('bo_observer._baseline_protocol', baseline / 'scripts/bo_observer/protocol.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
project = read(app / 'bo_stategraph/project.json')
runs = read(app / 'review/runtime/native-runs.json')
events = next(run['events'] for run in runs['runs'] if run['mode'] == 'on' and run['events'])[:128]
build = runs['build_id']
callbacks = {
    'baseline': lambda: [old.validate_event(event, project, build) for event in events],
    'request_index': lambda: validate_event_batch(events[:64], project, build) + validate_event_batch(events[64:], project, build),
}
assert callbacks['baseline']() == callbacks['request_index']() == events
samples = {name: [] for name in callbacks}
for round_number in range(10):
    order = list(callbacks) if round_number % 2 == 0 else list(reversed(callbacks))
    for name in order:
        start = time.perf_counter()
        assert callbacks[name]() == events
        samples[name].append(1000 * (time.perf_counter() - start))
medians = {name: statistics.median(values) for name, values in samples.items()}
result = {'valid': True, 'envelopes_per_sample': len(events), 'samples_ms': samples,
    'median_ms': medians, 'relative_median_reduction': 1 - medians['request_index'] / medians['baseline'],
    'captured_values_identical': True, 'native_application_runs': 0,
    'scope': 'Alternating same-process validation of already captured envelopes. Includes no source-boundary checks, HTTP, UI polling, writes, or runtime workload. Not a throughput or lossless-capture claim.'}
out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'valid': True, 'median_ms': medians, 'relative_median_reduction': result['relative_median_reduction']}))
