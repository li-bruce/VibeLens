"""Replay captured envelopes into a detached collector for cost attribution only.

This starts no business program. It copies source inputs, never the application's
database, credentials, records or settings. Its output is diagnostic throughput,
not a new native run or evidence that any lost events were recovered.
"""
import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import shutil
import subprocess
import sys
import threading
import time

root = Path(__file__).resolve().parents[1]
app = root / '.validation/p7-trials/node-retest-app'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--provider', type=Path, required=True)
parser.add_argument('--record', action='store_true')
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(exist_ok=False)
clone = out / 'project'
clone.mkdir()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
project = read(app / 'bo_stategraph/project.json')
paths = set(project['model']['source_files']) | {'bo_stategraph/project.json', 'manifest.json',
        'discovery.json', 'behavior.json', 'intent.json', 'acceptance.json', 'sync.json'}
for contract in project.get('contracts', {}).values():
    if isinstance(contract, dict) and contract.get('path'):
        paths.add(contract['path'])
for name in paths:
    if (app / name).is_file():
        target = clone / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(app / name, target)
sys.path.insert(0, str(args.provider.resolve() / 'scripts'))
from bo_observer.service import GraphSession, make_server

session = GraphSession(clone)
stats = []
profiles = []
original_batch = session.bo_sink.bo_accept_many
def measured_batch(values):
    profiler = cProfile.Profile()
    start = time.perf_counter()
    try:
        return profiler.runcall(original_batch, values)
    finally:
        stats.append({'events': len(values), 'seconds': time.perf_counter() - start})
        profiles.append(profiler)
session.bo_sink.bo_accept_many = measured_batch
server = make_server(session, port=0, token='synthetic-detached-diagnostic')
worker = threading.Thread(target=server.serve_forever, daemon=True)
worker.start()
if args.record:
    session.recordings.start('Detached collector cost measurement')
runs = read(app / 'review/runtime/native-runs.json')['runs']
items = []
for run in runs:
    if run['mode'] != 'on':
        continue
    snapshots = {}
    for snapshot in run.get('snapshots', []):
        snapshots.setdefault(snapshot['evidence_id'], []).append(snapshot)
    for event in run['events']:
        items.append({'kind': 'events', 'body': event})
        items.extend({'kind': 'snapshots', 'body': value} for value in snapshots.get(event['id'], []))
client = '''
let raw='';for await(const chunk of process.stdin)raw+=chunk;
const {base,items}=JSON.parse(raw), results=[];
while(items.length){
 const group=[items.shift()];let bytes=Buffer.byteLength(JSON.stringify(group[0].body))+64;
 while(group[0].kind==='events'&&group.length<64&&items[0]?.kind==='events'){
  const size=Buffer.byteLength(JSON.stringify(items[0].body))+1;if(bytes+size>262144)break;
  bytes+=size;group.push(items.shift());
 }
 const path=group.length>1?'events/batch':group[0].kind;
 const body=group.length>1?{protocol:'bo-event-batch/v1',events:group.map(x=>x.body)}:group[0].body;
 const start=performance.now();
 const r=await fetch(base+'/api/bo/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-BO-Token':'synthetic-detached-diagnostic'},body:JSON.stringify(body),signal:AbortSignal.timeout(1000)});
 const value=await r.json();results.push({path,count:group.length,status:r.status,ms:performance.now()-start});
 if(!r.ok){console.error(JSON.stringify(value));process.exit(1)}
}
console.log(JSON.stringify({results}));
'''
try:
    process = subprocess.run(['node', '--input-type=module', '-e', client],
        input=json.dumps({'base': f'http://127.0.0.1:{server.server_port}', 'items': items}),
        text=True, encoding='utf-8', capture_output=True, timeout=180)
    (out / 'client.stdout.log').write_text(process.stdout, encoding='utf-8')
    (out / 'client.stderr.log').write_text(process.stderr, encoding='utf-8')
    result = {'valid': process.returncode == 0, 'exit_code': process.returncode,
        'envelopes': len(items), 'batch_costs': stats,
        'recording_active': args.record,
        'scope': 'Detached HTTP replay of recorded producer envelopes with profiler overhead. No business workload, UI polling, queue-pressure or lossless claim.'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if profiles:
        stream = io.StringIO()
        combined = pstats.Stats(profiles[0], stream=stream)
        for profile in profiles[1:]:
            combined.add(profile)
        combined.strip_dirs().sort_stats('cumulative').print_stats(35)
        (out / 'admission.txt').write_text(stream.getvalue(), encoding='utf-8')
    print(json.dumps({'valid': result['valid'], 'envelopes': len(items), 'batches': len(stats)}))
finally:
    server.shutdown()
    server.server_close()
    worker.join(5)
    session.close()
