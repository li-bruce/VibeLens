"""Read the required repository gate and canonical bytes immediately before acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
CANONICAL=ROOT.parents[1]/'SoftwareStatusObserverSkill'
GATE=CANONICAL/'docs/review/execution-lanes-20261031/repository-verification-11.json'
SOURCE=CANONICAL/'skills/vibelens/scripts/bo_observer/control/selection.py'
EXPECTED='78277c1dfc22a0542e6b626be8d2e28818a3be296c8cb42894ee36809042e50f'

def main():
    digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    result={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'path':str(GATE),'canonical_selection_sha256':digest,'expected_sha256':EXPECTED,
        'canonical_unchanged':digest==EXPECTED,'exists':GATE.exists(),'valid':False}
    if GATE.exists():
        raw=GATE.read_bytes()
        report=json.loads(raw.decode('utf-8-sig'))
        result.update(repository_valid=report.get('valid'),exit_code=report.get('exit_code'),
            gate_sha256=hashlib.sha256(raw).hexdigest())
        result['valid']=report.get('valid') is True and report.get('exit_code')==0 and digest==EXPECTED
        if result['valid']:(OUT/'repository-verification-11.json').write_bytes(raw)
    result['status']='ready' if result['valid'] else 'waiting_for_required_repository_gate'
    with (OUT/'gate11-checks.jsonl').open('a',encoding='utf-8') as output:output.write(json.dumps(result)+'\n')
    (OUT/'gate11-readiness.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['valid'] else 2

if __name__=='__main__':raise SystemExit(main())
