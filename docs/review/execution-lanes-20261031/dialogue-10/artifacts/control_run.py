"""Invoke the installed scoped CLI with the exact current user message and host ID."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
message = (OUT / 'request.txt').read_text(encoding='utf-8').rstrip('\n')
command = sys.argv[1]
arguments = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'observer_runtime/bo_control.py'),
             command, '--root', str(ROOT), '--url', 'http://127.0.0.1:8983', '--message', message]
arguments += sys.argv[2:]
result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
print(result.stdout, end='')
print(result.stderr, end='', file=sys.stderr)
receipt = {'command': command, 'extra_arguments': sys.argv[2:], 'returncode': result.returncode,
           'actual_message_file': 'request.txt', 'message_sha256': hashlib.sha256(message.encode()).hexdigest(),
           'host_conversation': os.environ.get('CODEX_THREAD_ID'), 'project': str(ROOT)}
(OUT / ('control-' + command + '-invocation.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
raise SystemExit(result.returncode)
