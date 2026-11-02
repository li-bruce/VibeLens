"""Accumulate actual HTTP business events without changing history or budgets."""
import hashlib
import json
from pathlib import Path
import sqlite3
import urllib.request
from http_matrix import Client
from record_control_evidence import drained

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = 'http://127.0.0.1:8983'

def main():
    clients = {actor: Client(actor) for actor in ('alice', 'ben', 'cara', 'dan')}
    a, b, c, d = [clients[actor] for actor in clients]
    records, samples = [], []
    for batch in range(12):
        for index in range(5):
            name = f'control-large-round04-{batch}-{index}.txt'
            status, body = a.upload(name)
            assert status == 201, (status, body)
            fid = json.loads(body)['id']
            path = '/files/' + fid
            assert c.request(path)[0] == 403
            assert b.post(path + '/review', {'decision': 'approve'})[0] == 200
            assert a.post(path + '/share', {'recipient_id': 'cara'})[0] == 200
            expected = ('Fresh real concurrent application upload: ' + name + '\n').encode()
            assert c.request(path + '/download') == (200, expected)
            assert d.request(path)[0] == 403
            with sqlite3.connect(ROOT / 'var/team-files.sqlite3') as connection:
                row = connection.execute('SELECT state,revision,uploader_id,reviewer_id,recipient_id FROM files WHERE id=?', (fid,)).fetchone()
            assert row == ('approved', 3, 'alice', 'ben', 'cara'), row
            records.append({'file_id': fid, 'filename': name, 'sqlite': row,
                            'download_sha256': hashlib.sha256(expected).hexdigest()})
        with urllib.request.urlopen(BASE + '/api/view', timeout=60) as response:
            raw = response.read()
        view = json.loads(raw)
        samples.append({'workflows': len(records), 'bytes': len(raw), 'events': len(view['events'])})
        if len(raw) > 8 * 1024 * 1024:
            (OUT / 'large-view.json').write_bytes(raw)
            break
    else:
        raise AssertionError('Real business view did not cross the unchanged inspection budget')
    raw, view = drained()
    assert len(raw) > 8 * 1024 * 1024
    (OUT / 'large-view-drained.json').write_bytes(raw)
    with urllib.request.urlopen(BASE + '/api/vibelens/control/context', timeout=30) as response:
        context_raw = response.read()
    context = json.loads(context_raw)
    assert not {'events', 'frames', 'runtime', 'runs'} & set(context)
    assert context['model'] == view['model'] and context['manifest'] == view['manifest']
    with urllib.request.urlopen(BASE + '/api/view', timeout=60) as response:
        after = json.load(response)
    assert [e['id'] for e in view['events']] == [e['id'] for e in after['events']]
    assert view['binding_status']['status'] == 'current'
    (OUT / 'control-context.json').write_bytes(context_raw)
    result = {'valid': True, 'fixed_budget': 8 * 1024 * 1024, 'samples': samples,
              'build_id': view['manifest']['build_id'], 'context_bytes': len(context_raw),
              'context_keys': sorted(context), 'workflows': records,
              'observer_reads_added_zero_events': True, 'health': view['health']}
    (OUT / 'large-business.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'workflows'}))

if __name__ == '__main__':
    main()
