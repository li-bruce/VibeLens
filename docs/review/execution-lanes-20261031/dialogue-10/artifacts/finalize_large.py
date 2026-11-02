"""Retain the settled result of the 60 already executed real HTTP workflows."""
import json
from pathlib import Path
import sqlite3
from record_control_evidence import drained, get, save

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

raw, view = drained()
(OUT / 'large-view-drained.json').write_bytes(raw)
with sqlite3.connect(ROOT / 'var/team-files.sqlite3') as connection:
    connection.row_factory = sqlite3.Row
    rows = [dict(row) for row in connection.execute(
        "SELECT id,filename,state,revision,uploader_id,reviewer_id,recipient_id FROM files WHERE filename LIKE 'control-large-round04-%' ORDER BY filename")]
assert len(rows) == 60, len(rows)
assert all((r['state'], r['revision'], r['uploader_id'], r['reviewer_id'], r['recipient_id']) ==
           ('approved', 3, 'alice', 'ben', 'cara') for r in rows)
assert len(raw) > 8 * 1024 * 1024, len(raw)
context_raw = get('/api/vibelens/control/context')
context = json.loads(context_raw)
assert context['model'] == view['model'] and context['manifest'] == view['manifest']
assert not {'events', 'frames', 'runtime_frames', 'runtime', 'runs'} & set(context)
assert len(context_raw) < 8 * 1024 * 1024
after = json.loads(get('/api/view'))
assert [e['id'] for e in view['events']] == [e['id'] for e in after['events']]
assert view['binding_status']['status'] == 'current'
assert all(view['health']['producer'][k] == 0 for k in ('errors','dropped','data_errors','integration_errors','pending'))
(OUT / 'control-context.json').write_bytes(context_raw)
result = {'valid': True, 'fixed_budget': 8 * 1024 * 1024, 'view_bytes': len(raw),
          'events': len(view['events']), 'context_bytes': len(context_raw), 'context_keys': sorted(context),
          'build_id': view['manifest']['build_id'], 'workflows': rows,
          'observer_reads_added_zero_events': True, 'health': view['health'],
          'provenance': 'large-business-host ran all 60 workflow assertions successfully before its premature last view sample failed. This receipt drains that same real queue, reads independent SQLite, and retains the unchanged budget; no additional workflows or fabricated events.'}
save('large-business.json', result)
print(json.dumps({k:v for k,v in result.items() if k not in ('workflows','provenance')}))
