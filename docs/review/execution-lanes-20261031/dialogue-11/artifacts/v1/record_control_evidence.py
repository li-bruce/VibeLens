"""Retain a drained large view and one explicitly stopped current-build HTTP recording."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from http_matrix import Client

OUT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8983'

def get(route):
    with urllib.request.urlopen(BASE + route, timeout=60) as response:
        return response.read()

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2), encoding='utf-8')

def post(route, value):
    req = urllib.request.Request(BASE + route, data=json.dumps(value).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def drained():
    for _ in range(60):
        raw = get('/api/view')
        view = json.loads(raw)
        if view['health']['producer']['pending'] == 0:
            return raw, view
        time.sleep(1)
    raise AssertionError('Actual producer did not drain')

def main():
    a, b, c, d = [Client(actor) for actor in ('alice', 'ben', 'cara', 'dan')]
    raw, view = drained()
    (OUT / 'large-view.json').write_bytes(raw)
    assert len(raw) > 8 * 1024 * 1024
    context_raw = get('/api/vibelens/control/context')
    context = json.loads(context_raw)
    assert context['model'] == view['model'] and context['manifest'] == view['manifest']
    assert not {'events', 'runtime_frames', 'runtime', 'runs'} & set(context)
    (OUT / 'control-context.json').write_bytes(context_raw)
    assert [e['id'] for e in view['events']] == [e['id'] for e in json.loads(get('/api/view'))['events']]
    save('large-business.json', {'valid': True, 'view_bytes': len(raw), 'events': len(view['events']),
         'context_bytes': len(context_raw), 'context_keys': sorted(context),
         'build_id': view['manifest']['build_id'], 'health': view['health'],
         'fixed_budget': 8 * 1024 * 1024, 'observer_reads_added_zero_events': True,
         'provenance': 'Actual upload/review/share/download/denied workflows listed in large_business.py receipt, plus account login/list requests; no reset or fabricated event.'})
    listing = json.loads(get('/api/recordings'))
    assert not listing.get('active'), listing
    started = post('/api/recordings/start', {})
    save('recording-start.json', started)
    status, body = a.upload('stopped-round05-chain.txt')
    assert status == 201
    fid = json.loads(body)['id']
    path = '/files/' + fid
    checks = []
    for name, actual, expected in [
        ('recipient before approval', c.request(path)[0], 403),
        ('assigned review', b.post(path + '/review', {'decision': 'approve'})[0], 200),
        ('directed share', a.post(path + '/share', {'recipient_id': 'cara'})[0], 200),
        ('recipient metadata', c.request(path)[0], 200),
        ('unrelated denied', d.request(path)[0], 403)]:
        checks.append({'case': name, 'actual': actual, 'expected': expected})
        assert actual == expected, checks[-1]
    content = b'Fresh real concurrent application upload: stopped-round05-chain.txt\n'
    assert c.request(path + '/download') == (200, content)
    stopped = post('/api/recordings/stop', {})
    save('recording-stop.json', stopped)
    rid = stopped['id']
    rec_raw = get('/api/recordings/' + rid)
    (OUT / 'actual-recording.json').write_bytes(rec_raw)
    recording = json.loads(rec_raw)
    assert recording['status'] == 'stopped' and recording['events']
    # Preserve bounded pre-start context gaps; recording_audit verifies every interval parent and exit.
    assert recording['build_id'] == view['manifest']['build_id']
    save('recording-evidence.json', {'valid': True, 'recording_id': rid, 'file_id': fid,
         'build_id': recording['build_id'], 'checks': checks, 'events': len(recording['events']),
         'bytes': len(rec_raw), 'raw_sha256': hashlib.sha256(rec_raw).hexdigest(),
         'download_sha256': hashlib.sha256(content).hexdigest(), 'explicit_stop': True,
         'raw_gaps': recording['gaps'], 'interval_audit': 'required separately in recording_audit.py'})
    print(json.dumps({'valid': True, 'recording_id': rid, 'events': len(recording['events']),
                      'large_view_bytes': len(raw), 'recording_bytes': len(rec_raw)}))

if __name__ == '__main__':
    main()
