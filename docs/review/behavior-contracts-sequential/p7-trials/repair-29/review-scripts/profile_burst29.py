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
parser.add_argument('--burst', action='store_true')
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
if not args.burst:
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

if args.burst:
    # Synthetic repetitions use new identities. They retain all captured fields
    # and ordering; they are a transport workload, never new business evidence.
    originals = items
    items = []
    identifiers = {item['body'][key] for item in originals for key in ('id', 'run_id', 'producer_id', 'call_id') if isinstance(item['body'].get(key), str)}
    def remap(value, mapping):
        if isinstance(value, dict): return {key: remap(child, mapping) for key, child in value.items()}
        if isinstance(value, list): return [remap(child, mapping) for child in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    for repeat in range(5):
        mapping = {value: f'd{repeat}:' + value for value in identifiers}
        items.extend(remap(item, mapping) for item in originals)
    client = r"""
let raw='';for await(const chunk of process.stdin)raw+=chunk;
const {base,items,project,sdk}=JSON.parse(raw);
const {BOProbe}=await import(sdk);
const probe=new BOProbe({project,buildId:items[0].body.build_id,endpoint:base,token:'synthetic-detached-diagnostic',capacity:8192,timeout:1000});
let peak=0,index=0;const start=performance.now(),duration=3700;
while(index<items.length){
 const target=Math.min(items.length,Math.floor((performance.now()-start)/duration*items.length)+1);
 while(index<target){
  const item=items[index++];
  if(Buffer.byteLength(JSON.stringify(item.body))>24576)throw Error('Oversize original envelope');
  if(probe.bo_queue.length>=probe.bo_capacity){probe.bo_dropped++;continue;}
  probe.bo_queue.push(item);probe.bo_submitted++;
  peak=Math.max(peak,probe.bo_queue.length);
  queueMicrotask(()=>probe.bo_drain());
 }
 if(index<items.length)await new Promise(resolve=>setTimeout(resolve,1));
}
const afterBurst=probe.bo_health(),elapsedBurst=performance.now()-start;
const flushed=await probe.flush(180000);
console.log(JSON.stringify({synthetic:true,items:items.length,duration,elapsedBurst,peak,flushed,afterBurst,final:probe.bo_health(),totalMs:performance.now()-start}));
process.exitCode=flushed&&probe.bo_dropped===0&&probe.bo_errors===0?0:1;
"""

try:
    process = subprocess.run(['node', '--input-type=module', '-e', client],
        input=json.dumps({'base': f'http://127.0.0.1:{server.server_port}', 'items': items, 'project': project, 'sdk': (args.provider.resolve() / 'scripts/bo_observer/adapters/javascript/bo_runtime.mjs').as_uri()}),
        text=True, encoding='utf-8', capture_output=True, timeout=180)
    (out / 'client.stdout.log').write_text(process.stdout, encoding='utf-8')
    (out / 'client.stderr.log').write_text(process.stderr, encoding='utf-8')
    result = {'valid': process.returncode == 0, 'exit_code': process.returncode,
        'envelopes': len(items), 'batch_costs': stats, 'synthetic_burst': args.burst,
        'recording_active': args.record,
        'scope': 'Detached HTTP replay of recorded producer envelopes with profiler overhead for serial mode; synthetic burst has no profiler. No business workload, UI polling, queue-pressure or lossless claim.'}
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
