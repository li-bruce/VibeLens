"""Keep each batch check's original output and return status in a separate file."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('stage', choices=['targeted', 'full'])
parser.add_argument('--label')
args = parser.parse_args()
out = root / '.validation/p7-repair29-checks' / (args.label or args.stage)
out.mkdir(parents=True, exist_ok=False)
temp = root / '.validation/p7-repair29-temp'
temp.mkdir(exist_ok=True)
env = dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
checks = [('full', ['tools/verify.py', '--database'])] if args.stage == 'full' else [
    (name, ['tests/' + name + '.py']) for name in (
        'test_event_schema_engine', 'test_canonical_digest', 'test_source_files', 'test_protocol_reuse', 'test_event_batch', 'test_remote_event_batch',
        'test_history_batch', 'test_recording_retention', 'test_recording_evidence',
        'test_capture_bridge', 'test_document_links', 'test_behavior_plan')
]
results = []
for name, command in checks:
    started = time.monotonic()
    with (out / (name + '.log')).open('x', encoding='utf-8') as stream:
        process = subprocess.run([sys.executable, '-B', '-X', 'utf8', *command],
                                 cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
    results.append({'name': name, 'command': command, 'exit_code': process.returncode,
                    'seconds': time.monotonic() - started, 'log': name + '.log'})
    (out / 'result.json').write_text(json.dumps({'valid': all(x['exit_code'] == 0 for x in results),
        'complete': len(results) == len(checks), 'checks': results}, indent=2) + '\n', encoding='utf-8')
    print(name, process.returncode, flush=True)
raise SystemExit(any(x['exit_code'] for x in results))
