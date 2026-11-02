"""Read-only minimum reproduction of the canonical HTTP dispatch gap."""
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CANONICAL = ROOT.parents[1] / 'SoftwareStatusObserverSkill/skills/vibelens/scripts'
BASE = 'http://127.0.0.1:8983'

def request(route):
    try:
        response = urllib.request.urlopen(BASE + route, timeout=60)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.read()

def main():
    status, raw = request('/api/view')
    assert status == 200 and len(raw) > 8 * 1024 * 1024
    before = json.loads(raw)
    receipts = []
    for _ in range(2):
        status, body = request('/api/vibelens/control/context')
        receipts.append({'status': status, 'body': body.decode(), 'bytes': len(body)})
        assert status == 404
    after_status, after_raw = request('/api/view')
    after = json.loads(after_raw)
    assert after_status == 200
    assert [e['id'] for e in before['events']] == [e['id'] for e in after['events']]
    assert before['health']['producer']['pending'] == after['health']['producer']['pending'] == 0
    assert before['binding_status']['status'] == 'current'
    parity = {}
    for relative in ('bo_observer/service.py', 'bo_observer/control/cli.py',
                     'bo_observer/observation/session.py', 'bo_observer/web/bo_web.py'):
        installed = (ROOT / 'observer_runtime' / relative).read_bytes()
        canonical = (CANONICAL / relative).read_bytes()
        assert installed == canonical, relative
        parity[relative] = hashlib.sha256(installed).hexdigest()
    (OUT / 'final-view.json').write_bytes(after_raw)
    (OUT / 'final-recordings.json').write_bytes(request('/api/recordings')[1])
    payload = {'valid': True, 'classification': 'shared-runtime-http-control-context-dispatch-gap',
               'acceptance_ready': False, 'context_responses': receipts,
               'large_view_bytes': len(raw), 'events': len(before['events']),
               'build_id': before['manifest']['build_id'], 'health': before['health'],
               'binding_status': before['binding_status'], 'managed_parity': parity,
               'observer_requests_added_zero_business_events': True,
               'cause': 'service.Handler.do_GET delegates only exact /api/vibelens/control to BOWeb.get; /api/vibelens/control/context falls through to 404 although BOWeb implements it.',
               'remediation_boundary': 'Repair canonical runtime HTTP dispatch and add standard make_server end-to-end regression, then normal project upgrade; do not patch installed runtime or bypass CLI with a snapshot.'}
    (OUT / 'context-failure.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps({k: payload[k] for k in ('classification', 'context_responses', 'large_view_bytes', 'events', 'build_id', 'observer_requests_added_zero_business_events')}))

if __name__ == '__main__':
    main()
