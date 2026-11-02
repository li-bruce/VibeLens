"""Independently audit the stopped interval and disclose bounded prior context."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'observer_runtime'))
from tooling.observe import transition_witnesses

def main():
    raw = (OUT / 'actual-recording.json').read_bytes()
    recording = json.loads(raw)
    events = recording['events']
    entries = {e['call_id']: e for e in events if e['phase'] == 'enter'}
    exits = {e['call_id']: e for e in events if e['phase'] in ('return', 'exception', 'error', 'commit', 'change')}
    assert recording['status'] == 'stopped' and recording['producer_settlement']['flushed']
    assert set(entries) <= set(exits)
    missing = [e['id'] for e in events if e.get('parent_call_id') and e['parent_call_id'] not in entries]
    assert not missing
    interval_ids = {e['id'] for e in events}
    interval_gaps = [g for g in recording['ownership_gaps'] if g['event'] in interval_ids]
    assert not interval_gaps
    upload = next(e for e in entries.values() if e['node'] == 'upload_file')
    fid = exits[upload['call_id']]['outputs']['file_id']
    review = next(e for e in entries.values() if e['node'] == 'review_file')
    share = next(e for e in entries.values() if e['node'] == 'share_file')
    assert upload['inputs']['filename'] == 'stopped-round04-chain.txt'
    assert upload['inputs']['reviewer_id'] == 'ben'
    assert review['inputs']['decision'] == 'approve' and review['inputs']['actor'] == 'ben'
    assert share['inputs']['recipient_id'] == 'cara' and share['inputs']['actor'] == 'alice'
    with sqlite3.connect(ROOT / 'var/team-files.sqlite3') as connection:
        connection.row_factory = sqlite3.Row
        row = dict(connection.execute('SELECT id,state,revision,uploader_id,reviewer_id,recipient_id,filename,journal FROM files WHERE id=?', (fid,)).fetchone())
    row['journal'] = json.loads(row['journal'])
    assert (row['state'], row['revision'], row['uploader_id'], row['reviewer_id'], row['recipient_id']) == ('approved', 3, 'alice', 'ben', 'cara')
    assert upload['inputs']['reviewer_id'] == row['reviewer_id']
    assert share['inputs']['recipient_id'] == row['recipient_id']
    assert exits[review['call_id']]['outputs']['revision'] == 2
    assert exits[share['call_id']]['outputs']['revision'] == row['revision']
    witnessed = transition_witnesses([row], events)
    raw_path = ROOT / 'bo_stategraph/data/recordings' / (recording['id'] + '.json')
    raw_digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    result = {'valid': True, 'recording_id': recording['id'], 'build_id': recording['build_id'],
              'status': recording['status'], 'interval_events': len(events), 'closed_interval_calls': len(entries),
              'interval_http_roots': sum(e['node'] == 'http_request' and not e.get('parent_call_id') for e in entries.values()),
              'missing_interval_parents': missing, 'interval_ownership_gaps': interval_gaps,
              'prior_context_events': len(recording['context']['events']),
              'prior_context_ownership_gaps': len(recording['ownership_gaps']),
              'raw_gaps': recording['gaps'], 'producer_settlement': recording['producer_settlement'],
              'independent_sqlite': row, 'native_transition_witnesses': witnessed,
              'exact_parameters': {'upload': upload['inputs'], 'review': review['inputs'], 'share': share['inputs']},
              'http_statuses': dict(Counter(e.get('outputs', {}).get('status') for e in exits.values() if e['node'] == 'http_request')),
              'raw_recording_path': str(raw_path), 'raw_recording_sha256': raw_digest,
              'http_payload_sha256': hashlib.sha256(raw).hexdigest(),
              'limit': 'Prior context is capped at 2000 and has incomplete ancestors. The new 153-event interval has closed calls and no missing parents. Do not call the whole recording gap-free.',
              'filtered_control_and_replay': 'pending separate scoped control and browser receipts'}
    (OUT / 'recording-evidence.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('valid', 'recording_id', 'interval_events', 'closed_interval_calls', 'interval_http_roots', 'prior_context_ownership_gaps', 'native_transition_witnesses')}))

if __name__ == '__main__':
    main()
