"""Review the normally upgraded candidate without changing confirmed business meaning."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
path = ROOT / 'resume-first-integration-20261031/review.json'
(OUT / 'previous-candidate-review.json').write_bytes(path.read_bytes())
review = json.loads(path.read_text(encoding='utf-8'))
review['candidate_id'] = json.loads((OUT / 'inspect.result.json').read_text(encoding='utf-8'))['candidate_id']
review['decisions']['probes']['reason'] = (
    'Normal canonical typed-neighbor control selection upgrade; managed source is never patched. '
    'Preserve U001/U002, drive/Python/SQLite, business source and independent expectations. '
    'Observation output and isolated copies route to review/retest-20261101-05. '
    'Verify current mapping/state/business/project reports, paced real large history, exact '
    'four-anchor depth-2 business/decision view, visible original relations, scoped applied '
    'receipt, stopped-current-build filtered native replay, event preservation and exclusion. '
    'Reuse unaffected finite Web evidence from round 02 with provenance and its two blocked '
    '3D orthogonal/bus self relations. Gate 11 and canonical hash must pass before accept.')
path.write_text(json.dumps(review, indent=2) + '\n', encoding='utf-8')
(OUT / 'current-candidate-review.json').write_bytes(path.read_bytes())
print(json.dumps({'candidate_id':review['candidate_id'], 'baseline_sha256':hashlib.sha256(
    (ROOT / 'resume-first-integration-20261031/baseline.json').read_bytes()).hexdigest()}))
