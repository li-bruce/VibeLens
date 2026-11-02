"""Create real stopped evidence independently of the failed control-context route."""
import hashlib
import json
from record_control_evidence import OUT, get, post, save, drained
from http_matrix import Client

def main():
    a, b, c, d = [Client(actor) for actor in ('alice', 'ben', 'cara', 'dan')]
    raw, view = drained()
    (OUT / 'large-view-drained.json').write_bytes(raw)
    assert len(raw) > 8 * 1024 * 1024
    assert not json.loads(get('/api/recordings')).get('active')
    started = post('/api/recordings/start', {})
    save('recording-start.json', started)
    status, body = a.upload('stopped-round03-chain.txt')
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
    content = b'Fresh real concurrent application upload: stopped-round03-chain.txt\n'
    assert c.request(path + '/download') == (200, content)
    stopped = post('/api/recordings/stop', {})
    save('recording-stop.json', stopped)
    rec_raw = get('/api/recordings/' + stopped['id'])
    (OUT / 'actual-recording.json').write_bytes(rec_raw)
    recording = json.loads(rec_raw)
    assert recording['status'] == 'stopped' and recording['events'] and not recording['gaps']
    assert recording['build_id'] == view['manifest']['build_id']
    result = {'valid': True, 'recording_id': stopped['id'], 'file_id': fid,
              'build_id': recording['build_id'], 'checks': checks, 'events': len(recording['events']),
              'bytes': len(rec_raw), 'raw_sha256': hashlib.sha256(rec_raw).hexdigest(),
              'download_sha256': hashlib.sha256(content).hexdigest(), 'explicit_stop': True,
              'control_filter_and_replay': 'not_run: activation is blocked by canonical HTTP 404'}
    save('recording-evidence.json', result)
    print(json.dumps(result))

if __name__ == '__main__':
    main()
