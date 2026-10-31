"""Retain per-suite evidence while the independent application is developed."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
out = root / os.environ.get('BO_DIALOGUE_REGR_ROOT', 'docs/review/dialogue-acceptance-20261031/regressions')
out.mkdir(parents=True, exist_ok=True)
base = os.environ.copy()
base.update({
    'NODE_PATH': 'C:/Users/Lvi_P/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules',
    'BO_BROWSER_EXECUTABLE': 'C:/Users/Lvi_P/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe',
    'BO_PYTHON': str(root / '.venv/Scripts/python.exe'),
    'BO_ADAPTER_HOME': str(root / 'skills/vibelens/scripts/bo_observer/adapters/javascript'),
    'PYTHONDONTWRITEBYTECODE': '1',
})
cases = [
    ('timeline', ['node', 'tools/test_recording_timeline_browser.mjs'], {}),
    ('lifecycles', ['node', 'tools/test_trace_lifecycle_browser.mjs'], {'BO_REGISTERED_LIFECYCLE': '1'}),
    ('midspan', ['node', 'tools/test_trace_lifecycle_browser.mjs'], {'BO_REGISTERED_LIFECYCLE': '1', 'BO_RECORD_MIDSPAN': '1'}),
    ('names', ['node', 'tools/test_graph_names_browser.mjs'], {}),
    ('controls', ['node', 'tools/test_conversation_controls_browser.mjs'], {}),
    ('design-controls', ['node', 'tools/test_design_controls_browser.mjs'], {}),
    ('viewer-controls', ['node', 'tools/test_viewer_controls.mjs'], {}),
    ('engineering', [sys.executable, '-B', '-X', 'utf8', 'tools/test_engineering_browser.py', '--browser', base['BO_BROWSER_EXECUTABLE']], {}),
    ('data', ['node', 'tools/test_database_browser.mjs'], {}),
    ('code', ['node', 'tools/test_code_browser.mjs'], {}),
    ('3d', ['node', 'tools/test_layered_browser.mjs'], {}),
    ('routes', ['node', 'tools/test_routing_browser.mjs'], {}),
    ('clusters', ['node', 'tools/test_cluster_browser.mjs'], {}),
    ('layers', ['node', 'tools/test_ruler_browser.mjs'], {}),
    ('replay', ['node', 'tools/test_replay_browser.mjs'], {}),
]
report = {'kind': 'Existing viewer regressions; separate from independent application acceptance', 'cases': []}
for name, command, extra in cases:
    if len(sys.argv) > 1 and name not in sys.argv[1:]:
        continue
    folder = out / name
    folder.mkdir(parents=True, exist_ok=True)
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        port = str(port_socket.getsockname()[1])
    env = dict(base, **extra)
    env.update({key: str(folder) for key in (
        'BO_BROWSER_EVIDENCE', 'BO_TIMELINE_EVIDENCE', 'BO_LIFECYCLE_EVIDENCE',
        'BO_NAMES_EVIDENCE', 'BO_CONTROL_EVIDENCE', 'BO_DESIGN_CONTROL_EVIDENCE',
    )})
    env['BO_BROWSER_PORT'] = env['BO_CLUSTER_PORT'] = port
    args = command + (['--out', str(folder)] if name == 'engineering' else [])
    started = time.monotonic()
    print('START ' + name, flush=True)
    try:
        with (folder / 'runner.log').open('wb') as log:
            result = subprocess.run(args, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240)
        item = {'name': name, 'command': args, 'exit_code': result.returncode}
    except subprocess.TimeoutExpired:
        item = {'name': name, 'command': args, 'exit_code': 124, 'failure': 'timeout'}
    item['seconds'] = round(time.monotonic() - started, 3)
    report['cases'].append(item)
    report['passed'] = all(case['exit_code'] == 0 for case in report['cases'])
    (out / 'suite-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(item), flush=True)
sys.exit(0 if report['passed'] else 1)
